"""Exercise the offline assembler; these are not AWS authorization simulations."""
import importlib
from pathlib import Path

import pytest


def assembler():
    assert (Path(__file__).parents[2] / "scripts/build_access_review.py").exists()
    return importlib.import_module("scripts.build_access_review").build_bundle


def values():
    return {
        "AccountId": "000000000000", "ApiId": "abc123def4",
        "ArtifactBucketName": "fictional-neighborgear-artifacts",
        "WorkloadIdentityArn": "arn:aws:bedrock-agentcore:eu-west-1:000000000000:workload-identity-directory/default/workload-identity/fictional-example",
    }


def simulator_values():
    supplied = values()
    del supplied["WorkloadIdentityArn"]
    return supplied


def test_assembled_policy_is_resolved_but_never_marked_application_ready():
    import json
    result = assembler()(values())
    assert result["application_ready"] is False
    assert result["review_only"] is True
    assert "${" not in json.dumps(result["policy"])
    assert result["policy_characters"] <= 10240
    statements = result["policy"]["Statement"]
    assert any("bedrock-agentcore:CreateAgentRuntime" in s["Action"] for s in statements)
    assert any("iam:DeleteRolePermissionsBoundary" in s["Action"] and s["Effect"] == "Deny" for s in statements)


def test_assembler_refuses_unresolved_identity_instead_of_defaulting_to_directory():
    supplied = values()
    del supplied["WorkloadIdentityArn"]
    with pytest.raises(ValueError, match="WorkloadIdentityArn"):
        assembler()(supplied, mode="live")


def test_simulator_bundle_needs_no_workload_identity_or_agentcore_permissions():
    result = assembler()(simulator_values(), mode="simulator")
    statements = result["policy"]["Statement"]
    assert result["deployment_mode"] == "simulator"
    assert not any(action.startswith("bedrock-agentcore:") for statement in statements
                   for action in statement["Action"])
    runtime_role = "arn:aws:iam::000000000000:role/neighborgear-demo/neighborgear-demo-Runtime"
    assert not any(runtime_role in statement.get("Resource", []) for statement in statements)


@pytest.mark.parametrize("field,value", [
    ("ApiId", "*"), ("AccountId", "123*"), ("ArtifactBucketName", "bucket/*"),
    ("WorkloadIdentityArn", "arn:aws:bedrock-agentcore:eu-west-1:000000000000:workload-identity-directory/default"),
    ("WorkloadIdentityArn", "arn:aws:bedrock-agentcore:eu-west-1:111111111111:workload-identity-directory/default/workload-identity/another-account"),
    ("WorkloadIdentityArn", "arn:aws:bedrock-agentcore:us-east-1:000000000000:workload-identity-directory/default/workload-identity/another-region"),
])
def test_assembler_rejects_scope_expansion_inputs(field, value):
    supplied = values()
    supplied[field] = value
    with pytest.raises(ValueError, match=field):
        assembler()(supplied)


@pytest.mark.parametrize("resource,sid,message", [
    ("${UnknownScope}", "Example", "Unresolved placeholder"),
    ("*", "x" * 10300, "10,240"),
])
def test_assembler_rejects_new_unresolved_or_oversized_components(tmp_path, monkeypatch, resource, sid, message):
    import json
    build = assembler()
    module = importlib.import_module("scripts.build_access_review")
    component = {"Version": "2012-10-17", "Statement": [{
        "Sid": sid, "Effect": "Allow", "Action": ["logs:DescribeLogGroups"], "Resource": resource,
    }]}
    (tmp_path / "component.json").write_text(json.dumps(component))
    monkeypatch.setattr(module, "POLICY_ROOT", tmp_path)
    monkeypatch.setattr(module, "BASE_COMPONENTS", ("component.json",))
    monkeypatch.setattr(module, "LIVE_COMPONENTS", ("component.json",))
    with pytest.raises(ValueError, match=message):
        build(values())
