"""Offline shutdown contracts; fake AWS boundaries, real stop orchestration."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

ACCOUNT = "123456789012"
PREFIX = f"arn:aws:cloudformation:eu-west-1:{ACCOUNT}:stack/"
APP = PREFIX + "neighborgear-demo/11111111-1111-1111-1111-111111111111"
OWNER = PREFIX + "neighborgear-security/22222222-2222-2222-2222-222222222222"
LAMBDA = f"arn:aws:lambda:eu-west-1:{ACCOUNT}:function:neighborgear-demo-"


class FakeAWS:
    def __init__(self):
        self.account = ACCOUNT
        self.root = False
        self.writes = []
        self.control = {"pk": "CONTROL", "enabled": True, "starts_at": 1, "expires_at": 21601}
        self.schedule = {
            "Name": "demo-reminder", "GroupName": "neighborgear-demo-reminders",
            "Arn": f"arn:aws:scheduler:eu-west-1:{ACCOUNT}:schedule/neighborgear-demo-reminders/demo-reminder",
            "State": "ENABLED", "ScheduleExpression": "rate(5 minutes)",
            "FlexibleTimeWindow": {"Mode": "OFF"}, "Description": "Preserve this",
            "ScheduleExpressionTimezone": "Europe/London", "ActionAfterCompletion": "NONE",
            "Target": {"Arn": LAMBDA + "sweep", "RoleArn": f"arn:aws:iam::{ACCOUNT}:role/neighborgear-demo/neighborgear-demo-Scheduler", "Input": "{}", "RetryPolicy": {"MaximumRetryAttempts": 2}},
        }
        self.mapping = {"UUID": "33333333-3333-3333-3333-333333333333", "State": "Enabled",
                        "FunctionArn": LAMBDA + "worker", "EventSourceArn": f"arn:aws:sqs:eu-west-1:{ACCOUNT}:neighborgear-demo-work.fifo"}
        def resource(logical, kind, physical):
            return {"LogicalResourceId": logical, "ResourceType": "AWS::" + kind,
                    "PhysicalResourceId": physical, "ResourceStatus": "CREATE_COMPLETE"}
        self.resources = {
            APP: [resource("SweepFunctionReminders", "Scheduler::Schedule", "demo-reminder"),
                  resource("WorkerFunctionWork", "Lambda::EventSourceMapping", self.mapping["UUID"])],
            OWNER: [resource("DemoControls", "DynamoDB::Table", "neighborgear-demo-controls")],
        }
        self.fail_schedule = False
        self.async_mapping = False
        self.clients = SimpleNamespace(sts=self, cfn=self, scheduler=self, lambdas=self, dynamodb=self)

    def get_caller_identity(self):
        return {"Account": self.account, "Arn": f"arn:aws:iam::{self.account}:" + ("root" if self.root else "user/operator")}

    def describe_stacks(self, StackName):
        return {"Stacks": [{"StackId": StackName, "StackStatus": "CREATE_COMPLETE"}]}

    def get_paginator(self, name):
        assert name == "list_stack_resources"
        return self

    def paginate(self, StackName):
        # Separate pages ensure the implementation really consumes the paginator.
        return [{"StackResourceSummaries": [r]} for r in self.resources[StackName]]

    def get_schedule(self, **kwargs):
        assert kwargs == {"Name": "demo-reminder", "GroupName": "neighborgear-demo-reminders"}
        return deepcopy(self.schedule)

    def get_event_source_mapping(self, UUID):
        assert UUID == self.mapping["UUID"]
        return deepcopy(self.mapping)

    def Table(self, name):
        assert name == "neighborgear-demo-controls"
        return self

    def get_item(self, **kwargs):
        assert kwargs == {"Key": {"pk": "CONTROL"}, "ConsistentRead": True}
        return {"Item": deepcopy(self.control)}

    def update_item(self, **kwargs):
        assert kwargs["Key"] == {"pk": "CONTROL"}
        assert kwargs["ExpressionAttributeValues"] == {":off": False}
        assert kwargs["ConditionExpression"] is not None
        self.writes.append("control")
        self.control["enabled"] = False

    def update_schedule(self, **kwargs):
        if self.fail_schedule:
            raise RuntimeError("simulated interruption")
        assert kwargs == {**{k: v for k, v in self.schedule.items() if k != "Arn"}, "State": "DISABLED"}
        self.writes.append("schedule")
        self.schedule["State"] = "DISABLED"

    def update_event_source_mapping(self, UUID, Enabled):
        assert Enabled is False and UUID == self.mapping["UUID"]
        self.writes.append("mapping")
        self.mapping["State"] = "Disabling" if self.async_mapping else "Disabled"


def run(fake, **kwargs):
    from scripts.stop_demo import stop_demo
    return stop_demo(fake.clients, ACCOUNT, APP, OWNER, **kwargs)


def test_dry_run_is_read_only_and_lists_exact_targets():
    fake = FakeAWS()
    result = run(fake)
    assert result["mode"] == "dry-run"
    assert result["targets"]["mapping"] == fake.mapping["UUID"]
    assert not fake.writes


def test_apply_closes_gate_first_preserves_schedule_and_is_idempotent():
    fake = FakeAWS()
    assert run(fake, apply=True)["status"] == "stopped"
    assert fake.writes == ["control", "schedule", "mapping"]
    assert fake.control == {"pk": "CONTROL", "enabled": False, "starts_at": 1, "expires_at": 21601}
    assert run(fake, apply=True)["status"] == "stopped"
    assert fake.writes == ["control", "schedule", "mapping"]


@pytest.mark.parametrize("bad", ["account", "root", "owner", "target", "queue", "role", "missing-control", "duplicate"])
def test_unverified_targets_refused_before_any_write(bad):
    fake = FakeAWS()
    if bad == "account": fake.account = "999999999999"
    if bad == "root": fake.root = True
    if bad == "owner": fake.resources[OWNER][0]["PhysicalResourceId"] = "foreign-controls"
    if bad == "target": fake.schedule["Target"]["Arn"] = LAMBDA + "foreign"
    if bad == "queue": fake.mapping["EventSourceArn"] += "foreign"
    if bad == "role": fake.schedule["Target"]["RoleArn"] += "foreign"
    if bad == "missing-control": fake.control = None
    if bad == "duplicate": fake.resources[APP].append(deepcopy(fake.resources[APP][0]))
    with pytest.raises(ValueError): run(fake, apply=True)
    assert not fake.writes


def test_foreign_stack_arn_rejected():
    from scripts.stop_demo import stop_demo
    fake = FakeAWS()
    with pytest.raises(ValueError):
        stop_demo(fake.clients, ACCOUNT, APP.replace("neighborgear-demo/", "foreign/"), OWNER, apply=True)
    assert not fake.writes


def test_partial_failure_does_not_reopen_gate_and_reports_progress():
    fake = FakeAWS()
    fake.fail_schedule = True
    progress = {}
    with pytest.raises(RuntimeError): run(fake, apply=True, progress=progress)
    assert fake.control["enabled"] is False
    assert progress["completed"] == ["control"]
    assert progress["status"] == "incomplete"


def test_asynchronous_disable_reports_pending_not_stopped():
    fake = FakeAWS()
    fake.async_mapping = True
    assert run(fake, apply=True)["status"] == "pending"
    assert run(fake, apply=True)["status"] == "pending"
    assert fake.writes == ["control", "schedule", "mapping"]


def test_real_dynamodb_update_preserves_owner_window_and_other_records():
    import boto3
    from moto import mock_aws
    with mock_aws():
        db = boto3.resource("dynamodb", region_name="eu-west-1")
        table = db.create_table(TableName="neighborgear-demo-controls", BillingMode="PAY_PER_REQUEST",
                                KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
                                AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}])
        fake = FakeAWS()
        table.put_item(Item=fake.control)
        table.put_item(Item={"pk": "OTHER", "enabled": True})
        fake.clients.dynamodb = db
        assert run(fake, apply=True)["status"] == "stopped"
        item = table.get_item(Key={"pk": "CONTROL"})["Item"]
        assert item == {**fake.control, "enabled": False}
        assert table.get_item(Key={"pk": "OTHER"})["Item"]["enabled"] is True


def test_cli_help_needs_no_aws_credentials():
    import subprocess
    import sys
    result = subprocess.run([sys.executable, "scripts/stop-demo.py", "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "--apply" in result.stdout and "--owner-stack-arn" in result.stdout


def test_cli_returns_nonzero_with_partial_progress_on_aws_failure(monkeypatch, capsys):
    from botocore.exceptions import ClientError
    from scripts import stop_demo
    fake = FakeAWS()
    def fail(**kwargs):
        raise ClientError({"Error": {"Code": "AccessDeniedException", "Message": "denied"}}, "UpdateSchedule")
    fake.update_schedule = fail
    class Session:
        def client(self, name, **kwargs):
            return fake
        def resource(self, name, **kwargs):
            return fake
    monkeypatch.setattr(stop_demo.boto3, "Session", lambda **kwargs: Session())
    assert stop_demo.main(["--account-id", ACCOUNT, "--app-stack-arn", APP, "--owner-stack-arn", OWNER,
                           "--profile", "fictional", "--apply"]) == 1
    import json
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "incomplete" and report["completed"] == ["control"]
    assert fake.control["enabled"] is False
