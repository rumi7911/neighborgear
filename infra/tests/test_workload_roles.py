"""Check security properties of the actual SAM expansion without AWS calls."""
import json
from pathlib import Path

import pytest
from cfnlint.decode import decode
from samtranslator.translator.transform import transform


class OfflinePolicyNames:
    def load(self):
        return {
            name: f"arn:aws:iam::aws:policy/service-role/{name}"
            for name in ("AWSLambdaBasicExecutionRole", "AWSLambdaSQSQueueExecutionRole")
        }


def expand_template(monkeypatch, mode):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-1")
    template, errors = decode(str(Path(__file__).parents[1] / "template.yaml"))
    assert not errors
    # Packaging changes CodeUri before SAM runs; no artifact is uploaded here.
    template["Globals"]["Function"]["CodeUri"] = "s3://offline-fixture/artifact.zip"
    return transform(template, {
        "EnableResources": "true", "CreditsVerified": "true",
        "Mode": mode,
        "JudgeKey": "fictional-offline-test-key-only", "CodeBucket": "offline-fixture",
        "CodeKey": "agent/artifact.zip", "NetworkApiId": "abc123def4",
        "NetworkDomainName": "d123example.cloudfront.net",
    }, OfflinePolicyNames())


@pytest.fixture
def expanded(monkeypatch):
    return expand_template(monkeypatch, "live")


@pytest.fixture
def simulator_expanded(monkeypatch):
    return expand_template(monkeypatch, "simulator")


def test_sam_expansion_cannot_introduce_unbounded_or_managed_policy_roles(expanded):
    roles = {k: v for k, v in expanded["Resources"].items() if v["Type"] == "AWS::IAM::Role"}
    assert set(roles) == {"ApiRole", "WorkerRole", "SweepRole", "SchedulerRole", "RuntimeRole"}
    for role in roles.values():
        props = role["Properties"]
        assert props["PermissionsBoundary"] == {"Fn::Sub": "arn:${AWS::Partition}:iam::${AWS::AccountId}:policy/NeighborGearWorkloadBoundary"}
        assert props["Path"] == {"Fn::Sub": "/${AWS::StackName}/"}
        assert not props.get("ManagedPolicyArns")


def test_expanded_functions_and_schedule_use_only_explicit_roles(expanded):
    resources = expanded["Resources"]
    for purpose in ("Api", "Worker", "Sweep"):
        assert resources[f"{purpose}Function"]["Properties"]["Role"] == {"Fn::GetAtt": [f"{purpose}Role", "Arn"]}
        assert f"{purpose}Logs" in resources[f"{purpose}Function"].get("DependsOn", [])
    schedules = [v for v in resources.values() if v["Type"] == "AWS::Scheduler::Schedule"]
    assert len(schedules) == 1
    assert schedules[0]["Properties"]["Target"]["RoleArn"] == {"Fn::GetAtt": ["SchedulerRole", "Arn"]}


def test_runtime_model_permissions_match_reviewed_policy(expanded):
    statements = expanded["Resources"]["RuntimeRole"]["Properties"]["Policies"][0]["PolicyDocument"]["Statement"]
    bedrock = [s for s in statements if "bedrock:InvokeModel" in s["Action"]]
    assert len(bedrock) == 2
    text = json.dumps(bedrock)
    assert "bedrock:*:" not in text
    assert "bedrock:InferenceProfileArn" in text
    for region in ("eu-west-1", "eu-west-3", "eu-central-1", "eu-north-1"):
        assert f"bedrock:{region}::foundation-model/amazon.nova-lite-v1:0" in text


def test_runtime_create_supplies_required_project_tag_without_instances_compute(expanded):
    runtime = expanded["Resources"]["AgentRuntime"]["Properties"]
    assert runtime.get("Tags", {}).get("Project") == "NeighborGear"
    assert "CapacityProviderConfiguration" not in runtime


def test_simulator_stack_conditions_agentcore_resources_and_worker_grant_on_live_mode(simulator_expanded):
    resources = simulator_expanded["Resources"]
    assert resources["AgentRuntime"]["Condition"] == "LiveEnabled"
    assert resources["RuntimeRole"]["Condition"] == "LiveEnabled"
    worker = resources["WorkerFunction"]["Properties"]
    assert worker["Environment"]["Variables"]["NEIGHBORGEAR_RUNTIME_ARN"] == {
        "Fn::If": ["LiveEnabled", {"Fn::GetAtt": ["AgentRuntime", "AgentRuntimeArn"]}, {"Ref": "AWS::NoValue"}]
    }
    statements = resources["WorkerRole"]["Properties"]["Policies"][0]["PolicyDocument"]["Statement"]
    conditional = [statement for statement in statements if "Fn::If" in statement]
    assert len(conditional) == 1
    assert conditional[0]["Fn::If"][0] == "LiveEnabled"
    assert conditional[0]["Fn::If"][1]["Action"] == "bedrock-agentcore:InvokeAgentRuntime"


def test_all_entry_roles_can_read_but_not_write_owner_control(expanded):
    for name in ("ApiRole", "WorkerRole", "SweepRole", "RuntimeRole"):
        policies = expanded["Resources"][name]["Properties"]["Policies"]
        controls = [s for p in policies for s in p["PolicyDocument"]["Statement"]
                    if "-controls" in json.dumps(s.get("Resource"))]
        assert len(controls) == 1
        assert controls[0]["Action"] == ["dynamodb:GetItem"]
    assert expanded["Parameters"]["MaxLiveRuns"]["Default"] == 10
    assert expanded["Parameters"]["MaxLiveRuns"]["MaxValue"] == 10


def test_scheduler_trust_is_scoped_to_project_group_not_individual_schedule(expanded):
    roles = expanded["Resources"]
    assert "SchedulerRole" in roles
    statement = roles["SchedulerRole"]["Properties"]["AssumeRolePolicyDocument"]["Statement"][0]
    assert statement["Principal"] == {"Service": "scheduler.amazonaws.com"}
    assert statement["Condition"]["StringEquals"]["aws:SourceAccount"] == {"Ref": "AWS::AccountId"}
    assert statement["Condition"]["ArnEquals"]["aws:SourceArn"] == {"Fn::GetAtt": ["ReminderGroup", "Arn"]}


def test_owner_boundary_has_no_iam_or_unscoped_allow_grants():
    path = Path(__file__).parents[1] / "workload-boundary.yaml"
    assert path.exists(), "The owner-controlled boundary must be reviewable"
    template, errors = decode(str(path))
    assert not errors
    boundary = template["Resources"]["WorkloadBoundary"]
    assert boundary["Type"] == "AWS::IAM::ManagedPolicy"
    assert boundary["Properties"]["ManagedPolicyName"] == "NeighborGearWorkloadBoundary"
    for statement in boundary["Properties"]["PolicyDocument"]["Statement"]:
        actions = statement["Action"]
        assert all(not a.startswith("iam:") and "*" not in a for a in actions)
        assert statement["Resource"] != "*"
    assert boundary["Condition"] == "Approved"
    assert template["Parameters"]["EnableBoundary"]["Default"] == "false"


def test_provisioning_names_do_not_require_account_wide_queue_or_bucket_management(expanded):
    resources = expanded["Resources"]
    assert resources["DeadLetters"]["Properties"]["QueueName"] == {"Fn::Sub": "${AWS::StackName}-dead-letters.fifo"}


def test_app_cannot_create_or_replace_owner_network_resources(expanded):
    forbidden = {"AWS::ApiGatewayV2::Api", "AWS::ApiGatewayV2::Stage", "AWS::S3::BucketPolicy"}
    for resource in expanded["Resources"].values():
        assert resource["Type"] not in forbidden
        assert not resource["Type"].startswith("AWS::CloudFront::")
    assert "WebAssets" not in expanded["Resources"]


def test_external_api_routes_to_lambda_with_v2_payload_and_scoped_permission(expanded):
    resources = expanded["Resources"]
    assert "ApiIntegration" in resources
    integration = resources["ApiIntegration"]["Properties"]
    assert integration["ApiId"] == {"Ref": "NetworkApiId"}
    assert integration["IntegrationType"] == "AWS_PROXY"
    assert integration["PayloadFormatVersion"] == "2.0"
    assert integration["IntegrationUri"] == {"Fn::GetAtt": ["ApiFunction", "Arn"]}
    assert "CredentialsArn" not in integration
    route = resources["ApiRoute"]["Properties"]
    assert route["RouteKey"] == "ANY /api/{proxy+}"
    assert route["ApiId"] == {"Ref": "NetworkApiId"}
    assert route["Target"] == {"Fn::Sub": "integrations/${ApiIntegration}"}
    permission = resources["ApiInvokePermission"]["Properties"]
    assert permission["Principal"] == "apigateway.amazonaws.com"
    assert permission["SourceAccount"] == {"Ref": "AWS::AccountId"}
    assert permission["SourceArn"] == {"Fn::Sub": "arn:${AWS::Partition}:execute-api:${AWS::Region}:${AWS::AccountId}:${NetworkApiId}/*/*/api/*"}
