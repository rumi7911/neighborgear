"""Bootstrap contract: review scaffolding must never enable deployment access."""
from pathlib import Path

from cfnlint.decode import decode


def bootstrap():
    path = Path(__file__).parents[1] / "security-bootstrap.yaml"
    assert path.exists(), "Owner bootstrap must be independently reviewable"
    template, errors = decode(str(path))
    assert not errors
    return template


def test_bootstrap_cannot_create_any_resource_by_default():
    template = bootstrap()
    assert template["Parameters"]["EnableBootstrap"]["Default"] == "false"
    assert template["Conditions"]["Approved"] == {"Fn::Equals": [{"Ref": "EnableBootstrap"}, "true"]}
    assert all(r["Condition"] == "Approved" for r in template["Resources"].values())


def test_bootstrap_roles_remain_quarantined_even_if_owner_enables_creation():
    template = bootstrap()
    roles = [r for r in template["Resources"].values() if r["Type"] == "AWS::IAM::Role"]
    assert len(roles) == 2
    for role in roles:
        props = role["Properties"]
        assert props["MaxSessionDuration"] == 3600
        assert not props.get("ManagedPolicyArns")
        assert props["Policies"] == [{"PolicyName": "DeploymentQuarantine", "PolicyDocument": {
            "Version": "2012-10-17", "Statement": [{"Effect": "Deny", "Action": "*", "Resource": "*"}]
        }}]
    assert not any(r["Type"] in {"AWS::IAM::User", "AWS::IAM::AccessKey", "AWS::IAM::Policy"}
                   for r in template["Resources"].values())


def test_bootstrap_artifacts_are_private_encrypted_versioned_and_retained():
    bucket = bootstrap()["Resources"]["Artifacts"]
    props = bucket["Properties"]
    assert bucket["DeletionPolicy"] == bucket["UpdateReplacePolicy"] == "Retain"
    assert props["PublicAccessBlockConfiguration"] == {
        "BlockPublicAcls": True, "BlockPublicPolicy": True,
        "IgnorePublicAcls": True, "RestrictPublicBuckets": True,
    }
    assert props["VersioningConfiguration"] == {"Status": "Enabled"}
    assert props["BucketEncryption"]["ServerSideEncryptionConfiguration"] == [
        {"ServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
    ]


def test_bootstrap_does_not_weaken_operator_mfa_requirement():
    statement = bootstrap()["Resources"]["Deployer"]["Properties"]["AssumeRolePolicyDocument"]["Statement"]
    assert statement == [{
        "Effect": "Allow", "Action": "sts:AssumeRole",
        "Principal": {"AWS": {"Fn::Sub": "arn:${AWS::Partition}:iam::${AWS::AccountId}:user/NeighborGearOperator"}},
        "Condition": {"Bool": {"aws:MultiFactorAuthPresent": "true"}},
    }]


def test_owner_control_table_is_retained_and_never_ttl_deleted():
    resources = bootstrap()["Resources"]
    assert "DemoControls" in resources
    table = resources["DemoControls"]
    assert table["Type"] == "AWS::DynamoDB::Table"
    assert table["DeletionPolicy"] == table["UpdateReplacePolicy"] == "Retain"
    assert "TimeToLiveSpecification" not in table["Properties"]
