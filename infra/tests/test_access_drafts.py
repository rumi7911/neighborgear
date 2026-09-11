"""Structural guardrails for review-only IAM documents, not an IAM evaluator."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "iam-review"


def policy(name):
    path = ROOT / name
    assert path.exists(), f"Missing review document: {name}"
    return json.loads(path.read_text())


def test_operator_cannot_gain_any_permission_except_mfa_role_assumption():
    statements = policy("operator.json")["Statement"]
    assert len(statements) == 1
    statement = statements[0]
    assert statement["Effect"] == "Allow"
    assert statement["Action"] == "sts:AssumeRole"
    assert statement["Resource"] == "arn:aws:iam::${AccountId}:role/NeighborGearDeployer"
    assert statement["Condition"] == {"Bool": {"aws:MultiFactorAuthPresent": "true"}}


def test_deployer_trust_requires_exact_operator_and_mfa():
    statements = policy("deployer-trust.json")["Statement"]
    assert len(statements) == 1
    statement = statements[0]
    assert statement["Principal"] == {"AWS": "arn:aws:iam::${AccountId}:user/NeighborGearOperator"}
    assert statement["Action"] == "sts:AssumeRole"
    assert statement["Condition"] == {"Bool": {"aws:MultiFactorAuthPresent": "true"}}


def test_deployer_cannot_pass_an_arbitrary_role_or_manage_iam():
    statements = policy("deployer.json")["Statement"]
    iam = [s for s in statements if any(a.startswith("iam:") for a in s["Action"])]
    assert len(iam) == 1
    assert iam[0]["Action"] == ["iam:PassRole"]
    assert iam[0]["Resource"] == "arn:aws:iam::${AccountId}:role/NeighborGearCloudFormation"
    assert iam[0]["Condition"] == {"StringEquals": {"iam:PassedToService": "cloudformation.amazonaws.com"}}
    for s in statements:
        assert all("*" not in a for a in s["Action"])
        if s["Resource"] == "*":
            assert set(s["Action"]) <= {"cloudformation:ListStacks", "cloudformation:ValidateTemplate"}


def test_changesets_cannot_select_an_unreviewed_service_role():
    statements = policy("deployer.json")["Statement"]
    create = [s for s in statements if "cloudformation:CreateChangeSet" in s["Action"]]
    assert len(create) == 1
    assert create[0]["Resource"] == "arn:aws:cloudformation:eu-west-1:${AccountId}:stack/neighborgear-demo/*"
    assert create[0]["Condition"]["ArnEquals"]["cloudformation:RoleArn"] == "arn:aws:iam::${AccountId}:role/NeighborGearCloudFormation"


def test_workload_role_creation_requires_the_owner_boundary():
    statements = policy("cloudformation-role-management.json")["Statement"]
    create = [s for s in statements if s["Effect"] == "Allow" and "iam:CreateRole" in s["Action"]]
    assert len(create) == 1
    assert create[0]["Resource"] == "arn:aws:iam::${AccountId}:role/neighborgear-demo/*"
    assert create[0]["Condition"] == {"ArnEquals": {"iam:PermissionsBoundary": "arn:aws:iam::${AccountId}:policy/NeighborGearWorkloadBoundary"}}


def test_cloudformation_cannot_remove_or_replace_the_boundary():
    statements = policy("cloudformation-role-management.json")["Statement"]
    denials = [s for s in statements if s["Effect"] == "Deny"]
    assert any("iam:DeleteRolePermissionsBoundary" in s["Action"] and s["Resource"] == "*" for s in denials)
    assert any("iam:PutRolePermissionsBoundary" in s["Action"] and s["Resource"] == "*" for s in denials)
    assert any("iam:CreatePolicyVersion" in s["Action"] and s["Resource"] == "*" for s in denials)


def test_workload_passrole_is_split_by_service_and_role_name():
    statements = policy("cloudformation-role-management.json")["Statement"]
    passes = [s for s in statements if s["Effect"] == "Allow" and "iam:PassRole" in s["Action"]]
    assert len(passes) == 3
    expected = {
        "lambda.amazonaws.com": {"Api", "Worker", "Sweep"},
        "bedrock-agentcore.amazonaws.com": {"Runtime"},
        "scheduler.amazonaws.com": {"Scheduler"},
    }
    for statement in passes:
        service = statement["Condition"]["StringEquals"]["iam:PassedToService"]
        assert set(statement["Resource"]) == {
            f"arn:aws:iam::${{AccountId}}:role/neighborgear-demo/neighborgear-demo-{name}" for name in expected[service]
        }


def test_bedrock_draft_grants_only_both_required_inference_actions():
    statements = policy("runtime-bedrock.json")["Statement"]
    assert len(statements) == 2
    for statement in statements:
        assert statement["Effect"] == "Allow"
        assert set(statement["Action"]) == {"bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"}


def test_bedrock_draft_has_no_model_or_region_wildcard():
    statements = policy("runtime-bedrock.json")["Statement"]
    resources = {arn for statement in statements for arn in statement["Resource"]}
    assert resources == {
        "arn:aws:bedrock:eu-west-1:${AccountId}:inference-profile/eu.amazon.nova-lite-v1:0",
        "arn:aws:bedrock:eu-west-1::foundation-model/amazon.nova-lite-v1:0",
        "arn:aws:bedrock:eu-west-3::foundation-model/amazon.nova-lite-v1:0",
        "arn:aws:bedrock:eu-central-1::foundation-model/amazon.nova-lite-v1:0",
        "arn:aws:bedrock:eu-north-1::foundation-model/amazon.nova-lite-v1:0",
    }


def test_foundation_model_grant_requires_the_exact_profile_context():
    statements = policy("runtime-bedrock.json")["Statement"]
    foundation = [s for s in statements if any(":foundation-model/" in arn for arn in s["Resource"])]
    assert len(foundation) == 1
    assert foundation[0]["Condition"] == {
        "ArnEquals": {"bedrock:InferenceProfileArn": "arn:aws:bedrock:eu-west-1:${AccountId}:inference-profile/eu.amazon.nova-lite-v1:0"}
    }


def test_artifact_uploads_cannot_write_outside_owner_bucket_agent_prefix():
    statements = policy("deployer.json")["Statement"]
    uploads = [s for s in statements if "s3:PutObject" in s["Action"]]
    assert len(uploads) == 1
    assert uploads[0]["Resource"] == "arn:aws:s3:::${ArtifactBucketName}/agent/*"
    assert uploads[0]["Condition"] == {"StringEquals": {"s3:ResourceAccount": "${AccountId}"}}
    assert not any("s3:DeleteObject" in s["Action"] or "s3:PutBucketPolicy" in s["Action"] for s in statements)


def test_named_provisioning_draft_does_not_grant_runtime_data_or_iam_access():
    statements = policy("cloudformation-named-resources.json")["Statement"]
    forbidden = {"dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Scan",
                 "sqs:SendMessage", "sqs:ReceiveMessage", "lambda:InvokeFunction", "s3:PutObject"}
    for statement in statements:
        assert statement["Effect"] == "Allow"
        assert not forbidden.intersection(statement["Action"])
        assert all("*" not in action and not action.startswith(("iam:", "bedrock:"))
                   for action in statement["Action"])


def test_named_provisioning_global_exceptions_are_read_only_or_worker_bound():
    statements = policy("cloudformation-named-resources.json")["Statement"]
    for statement in statements:
        if statement["Resource"] != "*":
            continue
        assert statement["Condition"]["StringEquals"]["aws:RequestedRegion"] == "eu-west-1"
        if statement["Action"] == ["lambda:CreateEventSourceMapping"]:
            assert statement["Condition"]["ArnEquals"]["lambda:FunctionArn"] == (
                "arn:aws:lambda:eu-west-1:${AccountId}:function:neighborgear-demo-worker"
            )
        else:
            assert statement["Action"] == ["logs:DescribeLogGroups"]


def test_app_provisioning_cannot_modify_owner_network_or_artifact_bucket_configuration():
    statements = policy("cloudformation-named-resources.json")["Statement"]
    policy_writes = [s for s in statements if "s3:PutBucketPolicy" in s["Action"]]
    assert not policy_writes
    assert "eu-west-1-web" not in json.dumps(statements)
    for statement in statements:
        if "s3:CreateBucket" in statement["Action"]:
            assert statement["Condition"] == {"StringEquals": {"s3:LocationConstraint": "eu-west-1"}}


def test_api_grant_cannot_create_delete_or_reconfigure_the_owner_api_or_stage():
    statements = policy("cloudformation-api-routes.json")["Statement"]
    assert len(statements) == 2
    create, manage = statements
    assert create["Action"] == ["apigateway:POST"]
    assert set(create["Resource"]) == {
        "arn:aws:apigateway:eu-west-1::/apis/${ApiId}/integrations",
        "arn:aws:apigateway:eu-west-1::/apis/${ApiId}/routes",
    }
    assert set(manage["Action"]) == {"apigateway:GET", "apigateway:PATCH", "apigateway:DELETE"}
    assert set(manage["Resource"]) == {
        "arn:aws:apigateway:eu-west-1::/apis/${ApiId}/integrations/*",
        "arn:aws:apigateway:eu-west-1::/apis/${ApiId}/routes/*",
    }


def test_existing_event_mapping_management_is_bound_to_worker_not_all_functions():
    statements = policy("cloudformation-named-resources.json")["Statement"]
    mapping = [s for s in statements if "lambda:UpdateEventSourceMapping" in s["Action"]]
    assert len(mapping) == 1
    assert mapping[0]["Resource"] == "arn:aws:lambda:eu-west-1:${AccountId}:event-source-mapping:*"
    assert mapping[0]["Condition"]["ArnEquals"]["lambda:FunctionArn"] == (
        "arn:aws:lambda:eu-west-1:${AccountId}:function:neighborgear-demo-worker"
    )


def test_agentcore_creation_requires_project_tag_and_ireland():
    statements = policy("cloudformation-agentcore.json")["Statement"]
    create = [s for s in statements if "bedrock-agentcore:CreateAgentRuntime" in s["Action"]]
    assert len(create) == 1
    assert create[0]["Resource"] == "*"
    assert create[0]["Condition"] == {"StringEquals": {
        "aws:RequestedRegion": "eu-west-1", "aws:RequestTag/Project": "NeighborGear"
    }}


def test_agentcore_cleanup_cannot_delete_an_entire_identity_directory():
    statements = policy("cloudformation-agentcore.json")["Statement"]
    cleanup = [s for s in statements if "bedrock-agentcore:DeleteWorkloadIdentity" in s["Action"]]
    assert len(cleanup) == 1
    assert cleanup[0]["Resource"] == "${WorkloadIdentityArn}"
    assert cleanup[0]["Condition"] == {"StringEquals": {"aws:RequestedRegion": "eu-west-1"}}


def test_agentcore_provisioning_never_grants_model_calls_or_capacity_providers():
    statements = policy("cloudformation-agentcore.json")["Statement"]
    for statement in statements:
        if statement["Effect"] == "Allow":
            assert all(a.startswith("bedrock-agentcore:") and "Invoke" not in a
                       and "CapacityProvider" not in a and "*" not in a for a in statement["Action"])
            if statement["Resource"] == "*":
                assert statement["Action"] == ["bedrock-agentcore:CreateAgentRuntime"]
    assert any(s["Effect"] == "Deny" and s["Action"] == ["bedrock-agentcore:PassCapacityProvider"]
               and s["Resource"] == "*" for s in statements)
