"""Dry-run-first NeighborGear stop control. Does not delete resources or cancel in-flight work."""
import argparse
import json
import re
from types import SimpleNamespace

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

REGION = "eu-west-1"
APP_NAME = "neighborgear-demo"
CONTROL_TABLE = APP_NAME + "-controls"
GROUP = APP_NAME + "-reminders"
UPDATE_FIELDS = {
    "Name", "GroupName", "ScheduleExpression", "FlexibleTimeWindow", "Target",
    "ActionAfterCompletion", "Description", "EndDate", "KmsKeyArn",
    "ScheduleExpressionTimezone", "StartDate", "State",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def stack_resources(cfn, arn, account, *, application=False):
    match = re.fullmatch(
        rf"arn:aws:cloudformation:{REGION}:{account}:stack/([A-Za-z][A-Za-z0-9-]*)/"
        r"[0-9a-fA-F-]{36}", arn,
    )
    require(match is not None, "Require an exact same-account Ireland stack ARN")
    require(not application or match[1] == APP_NAME, "Foreign application stack refused")
    stacks = cfn.describe_stacks(StackName=arn)["Stacks"]
    require(len(stacks) == 1 and stacks[0]["StackId"] == arn, "Stack identity mismatch")
    require(stacks[0]["StackStatus"] in {"CREATE_COMPLETE", "UPDATE_COMPLETE", "UPDATE_ROLLBACK_COMPLETE"},
            "Stack must be stable; owner must inspect failed or in-progress stacks")
    return [r for page in cfn.get_paginator("list_stack_resources").paginate(StackName=arn)
            for r in page["StackResourceSummaries"]]


def one_resource(resources, kind, logical=None):
    selected = [r for r in resources if r["ResourceType"] == "AWS::" + kind
                and (logical is None or r["LogicalResourceId"] == logical)]
    require(len(selected) == 1, f"Require exactly one owned {logical or kind}")
    resource = selected[0]
    require(resource["ResourceStatus"] in {"CREATE_COMPLETE", "UPDATE_COMPLETE", "UPDATE_ROLLBACK_COMPLETE"},
            "Resource is not stable")
    return resource["PhysicalResourceId"]


def inspect(clients, account, app_stack, owner_stack):
    require(re.fullmatch(r"[0-9]{12}", account) is not None, "Require expected 12-digit account")
    identity = clients.sts.get_caller_identity()
    require(identity["Account"] == account, "Wrong AWS account")
    require(identity["Arn"] != f"arn:aws:iam::{account}:root", "Use an approved non-root identity")
    require(app_stack != owner_stack, "Owner controls must belong to a separate stack")
    app = stack_resources(clients.cfn, app_stack, account, application=True)
    owner = stack_resources(clients.cfn, owner_stack, account)
    table_name = one_resource(owner, "DynamoDB::Table", "DemoControls")
    require(table_name == CONTROL_TABLE, "Foreign control table refused")
    schedule_name = one_resource(app, "Scheduler::Schedule")
    require(re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", schedule_name) is not None, "Invalid schedule name")
    mapping_id = one_resource(app, "Lambda::EventSourceMapping")
    require(re.fullmatch(r"[0-9a-fA-F-]{36}", mapping_id) is not None, "Invalid mapping UUID")
    schedule = clients.scheduler.get_schedule(Name=schedule_name, GroupName=GROUP)
    require(schedule.get("Arn") == f"arn:aws:scheduler:{REGION}:{account}:schedule/{GROUP}/{schedule_name}"
            and schedule.get("Name") == schedule_name and schedule.get("GroupName") == GROUP,
            "Foreign schedule refused")
    function_prefix = f"arn:aws:lambda:{REGION}:{account}:function:{APP_NAME}-"
    require(schedule["Target"]["Arn"] == function_prefix + "sweep", "Foreign schedule target refused")
    require(schedule["Target"]["RoleArn"] == f"arn:aws:iam::{account}:role/{APP_NAME}/{APP_NAME}-Scheduler",
            "Foreign schedule role refused")
    require(schedule.get("State") in {"ENABLED", "DISABLED"}, "Unknown schedule state")
    require({"ScheduleExpression", "FlexibleTimeWindow"} <= schedule.keys(), "Incomplete schedule")
    mapping = clients.lambdas.get_event_source_mapping(UUID=mapping_id)
    require(mapping.get("UUID") == mapping_id and mapping.get("FunctionArn") == function_prefix + "worker"
            and mapping.get("EventSourceArn") == f"arn:aws:sqs:{REGION}:{account}:{APP_NAME}-work.fifo",
            "Foreign queue mapping refused")
    require(mapping.get("State") in {"Enabled", "Disabled", "Disabling"}, "Mapping transition requires a later retry")
    table = clients.dynamodb.Table(table_name)
    control = table.get_item(Key={"pk": "CONTROL"}, ConsistentRead=True).get("Item")
    require(isinstance(control, dict) and control.get("pk") == "CONTROL", "Missing owner CONTROL record")
    return table, control, schedule, mapping


def stop_demo(clients, account, app_stack, owner_stack, *, apply=False, progress=None):
    """Revalidate targets each invocation; exceptions leave confirmed progress for the caller."""
    report = progress if progress is not None else {}
    report.update(mode="apply" if apply else "dry-run", status="incomplete", completed=[],
                  in_flight="Unknown: admitted work may finish; no cancellation attempted.",
                  retained="All data, network, compute and logs retained; residual charges remain possible.")
    table, control, schedule, mapping = inspect(clients, account, app_stack, owner_stack)
    report["targets"] = {"app_stack": app_stack, "owner_stack": owner_stack,
                         "control_table": CONTROL_TABLE, "control_key": "CONTROL",
                         "schedule": schedule["Arn"], "mapping": mapping["UUID"]}
    report["observed"] = {"control_disabled": control.get("enabled") is False,
                          "schedule": schedule["State"], "mapping": mapping["State"]}
    if not apply:
        report["status"] = "preview"
        return report

    # No saved plan is trusted: repeat ownership checks immediately before writes.
    table, control, schedule, mapping = inspect(clients, account, app_stack, owner_stack)
    require(report["targets"]["schedule"] == schedule["Arn"]
            and report["targets"]["mapping"] == mapping["UUID"], "Targets changed during preflight")
    if control.get("enabled") is not False:
        table.update_item(Key={"pk": "CONTROL"}, UpdateExpression="SET #enabled = :off",
                          ExpressionAttributeNames={"#enabled": "enabled"},
                          ExpressionAttributeValues={":off": False}, ConditionExpression=Attr("pk").exists())
    require(table.get_item(Key={"pk": "CONTROL"}, ConsistentRead=True).get("Item", {}).get("enabled") is False,
            "Control closure not confirmed; no triggers changed")
    report["completed"].append("control")
    if schedule["State"] != "DISABLED":
        # UpdateSchedule replaces the configuration, so preserve every writable field.
        clients.scheduler.update_schedule(**{**{k: v for k, v in schedule.items() if k in UPDATE_FIELDS},
                                             "State": "DISABLED"})
    report["completed"].append("schedule-disable-request")
    if mapping["State"] == "Enabled":
        clients.lambdas.update_event_source_mapping(UUID=mapping["UUID"], Enabled=False)
    report["completed"].append("mapping-disable-request")
    _, control, schedule, mapping = inspect(clients, account, app_stack, owner_stack)
    report["observed"] = {"control_disabled": control.get("enabled") is False,
                          "schedule": schedule["State"], "mapping": mapping["State"]}
    report["status"] = "stopped" if report["observed"] == {
        "control_disabled": True, "schedule": "DISABLED", "mapping": "Disabled",
    } else "pending"
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--app-stack-arn", required=True)
    parser.add_argument("--owner-stack-arn", required=True)
    parser.add_argument("--profile", required=True, help="Approved non-root AWS profile")
    parser.add_argument("--apply", action="store_true", help="Close gate and disable verified triggers")
    args = parser.parse_args(argv)
    report = {"status": "incomplete", "completed": []}
    try:
        session = boto3.Session(profile_name=args.profile, region_name=REGION)
        config = Config(connect_timeout=3, read_timeout=5, retries={"total_max_attempts": 1, "mode": "standard"},
                        ignore_configured_endpoint_urls=True)
        clients = SimpleNamespace(
            sts=session.client("sts", config=config), cfn=session.client("cloudformation", config=config),
            scheduler=session.client("scheduler", config=config), lambdas=session.client("lambda", config=config),
            dynamodb=session.resource("dynamodb", config=config))
        stop_demo(clients, args.account_id, args.app_stack_arn, args.owner_stack_arn,
                  apply=args.apply, progress=report)
    except (ValueError, KeyError, BotoCoreError, ClientError) as error:
        report["error"] = str(error)
        report["next_action"] = "Inspect confirmed progress; do not reopen the gate. Re-run dry-run after resolving the error."
        print(json.dumps(report, indent=2))
        return 1
    print(json.dumps(report, indent=2))
    return 2 if report["status"] == "pending" else 0


if __name__ == "__main__":
    raise SystemExit(main())
