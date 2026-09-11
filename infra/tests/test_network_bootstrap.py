from pathlib import Path

from cfnlint.decode import decode


def network():
    path = Path(__file__).parents[1] / "network-bootstrap.yaml"
    assert path.exists(), "Networking needs an independently approved owner template"
    template, errors = decode(str(path))
    assert not errors
    return template


def test_owner_network_is_disabled_credit_gated_and_has_no_compute_or_iam():
    template = network()
    assert template["Parameters"]["EnableNetwork"]["Default"] == "false"
    assert template["Parameters"]["CreditsVerified"]["Default"] == "false"
    assert template["Rules"]["CreditGate"]["Assertions"][0]["Assert"] == {"Fn::Equals": [{"Ref": "CreditsVerified"}, "true"]}
    allowed = {"AWS::S3::Bucket", "AWS::S3::BucketPolicy", "AWS::ApiGatewayV2::Api",
               "AWS::ApiGatewayV2::Stage", "AWS::CloudFront::OriginAccessControl",
               "AWS::CloudFront::OriginRequestPolicy", "AWS::CloudFront::Distribution"}
    assert all(r["Type"] in allowed and r["Condition"] == "Enabled" for r in template["Resources"].values())


def test_owner_retains_api_throttle_and_sensitive_headers_are_never_cached():
    resources = network()["Resources"]
    stage = resources["ApiStage"]["Properties"]
    assert stage["StageName"] == "$default"
    assert stage["AutoDeploy"] is True
    assert stage["DefaultRouteSettings"] == {"ThrottlingBurstLimit": 5, "ThrottlingRateLimit": 2}
    assert resources["Api"]["Properties"]["ProtocolType"] == "HTTP"
    api = resources["Distribution"]["Properties"]["DistributionConfig"]["CacheBehaviors"][0]
    assert api["PathPattern"] == "/api/*"
    assert api["CachePolicyId"] == "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
    headers = resources["ForwardHeaders"]["Properties"]["OriginRequestPolicyConfig"]["HeadersConfig"]
    assert set(headers["Headers"]) == {"Content-Type", "X-Sandbox-Token", "X-Judge-Key", "Idempotency-Key"}


def test_owner_web_bucket_is_private_and_cloudfront_grant_is_distribution_scoped():
    resources = network()["Resources"]
    bucket = resources["WebAssets"]
    assert bucket["DeletionPolicy"] == bucket["UpdateReplacePolicy"] == "Retain"
    assert all(bucket["Properties"]["PublicAccessBlockConfiguration"].values())
    grant = resources["AssetsPolicy"]["Properties"]["PolicyDocument"]["Statement"][0]
    assert grant["Principal"] == {"Service": "cloudfront.amazonaws.com"}
    assert grant["Condition"]["StringEquals"]["AWS:SourceArn"] == {"Fn::Sub": "arn:${AWS::Partition}:cloudfront::${AWS::AccountId}:distribution/${Distribution}"}
