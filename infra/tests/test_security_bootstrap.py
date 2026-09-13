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
    assert template["Parameters"]["EnableSimulatorAccess"]["Default"] == "false"
    assert all(r["Condition"] in {"Approved", "SimulatorAccess"} for r in template["Resources"].values())


def test_bootstrap_roles_use_quarantine_until_simulator_access_is_separately_enabled():
    template = bootstrap()
    roles = [r for r in template["Resources"].values() if r["Type"] == "AWS::IAM::Role"]
    assert len(roles) == 2
    for role in roles:
        props = role["Properties"]
        assert props["MaxSessionDuration"] == 3600
        assert not props.get("ManagedPolicyArns")
        assert props["Policies"]["Fn::If"][0] == "SimulatorAccess"
        assert props["Policies"]["Fn::If"][2] == [{"PolicyName": "DeploymentQuarantine", "PolicyDocument": {
            "Version": "2012-10-17", "Statement": [{"Effect": "Deny", "Action": "*", "Resource": "*"}]
        }}]
    assert not any(r["Type"] in {"AWS::IAM::User", "AWS::IAM::AccessKey"}
                   for r in template["Resources"].values())


def test_simulator_activation_grants_only_mfa_assumption_to_existing_operator():
    template = bootstrap()
    policy = template["Resources"]["OperatorAssumeDeployer"]
    assert policy["Condition"] == "SimulatorAccess"
    assert policy["Type"] == "AWS::IAM::Policy"
    props = policy["Properties"]
    assert props["Users"] == ["NeighborGearOperator"]
    statement = props["PolicyDocument"]["Statement"]
    assert statement == [{
        "Effect": "Allow", "Action": "sts:AssumeRole",
        "Resource": {"Fn::GetAtt": ["Deployer", "Arn"]},
        "Condition": {"Bool": {"aws:MultiFactorAuthPresent": "true"}},
    }]


def test_simulator_cloudformation_policy_excludes_agentcore_and_runtime_passrole():
    policies = bootstrap()["Resources"]["CloudFormation"]["Properties"]["Policies"]["Fn::If"][1]
    statements = policies[0]["PolicyDocument"]["Statement"]
    assert len(statements) == 24
    for statement in statements:
        actions = statement["Action"] if isinstance(statement["Action"], list) else [statement["Action"]]
        assert not any(action.startswith("bedrock-agentcore:") or action.startswith("bedrock:") for action in actions)
        resources = statement["Resource"] if isinstance(statement["Resource"], list) else [statement["Resource"]]
        assert not any(isinstance(resource, str) and resource.endswith("neighborgear-demo-Runtime")
                       for resource in resources)


def test_simulator_deployer_can_publish_only_to_owned_web_origin_and_invalidate_exact_distribution():
    template = bootstrap()
    assert template["Parameters"]["NetworkDistributionId"]["Default"] == "disabled"
    policies = template["Resources"]["Deployer"]["Properties"]["Policies"]["Fn::If"][1]
    statements = policies[0]["PolicyDocument"]["Statement"]
    web = next(statement for statement in statements if statement["Sid"] == "PublishOnlyNetworkOwnedWebAssets")
    assert web["Action"] == ["s3:PutObject", "s3:GetObject"]
    assert web["Resource"] == {"Fn::Sub": "arn:${AWS::Partition}:s3:::neighborgear-demo-${AWS::AccountId}-${AWS::Region}-web/*"}
    invalidation = next(statement for statement in statements if statement["Sid"] == "InvalidateOnlyNeighborGearDistribution")
    assert invalidation["Action"] == ["cloudfront:CreateInvalidation", "cloudfront:GetInvalidation"]
    assert invalidation["Resource"] == {"Fn::Sub": "arn:${AWS::Partition}:cloudfront::${AWS::AccountId}:distribution/${NetworkDistributionId}"}
    assert not any("s3:DeleteObject" in statement["Action"] or "s3:PutBucketPolicy" in statement["Action"]
                   for statement in statements)


def test_simulator_activation_refuses_placeholder_network_identifiers():
    rule = bootstrap()["Rules"]["ExactNetworkOutputsForSimulatorAccess"]
    assert rule["RuleCondition"] == {"Fn::Equals": [{"Ref": "EnableSimulatorAccess"}, "true"]}
    asserted = {item["AssertDescription"] for item in rule["Assertions"]}
    assert asserted == {
        "Supply the exact deployed HTTP API ID before enabling simulator access.",
        "Supply the exact deployed CloudFront distribution ID before enabling simulator access.",
    }


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
