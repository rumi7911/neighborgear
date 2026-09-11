"""Assemble a PRIVATE review document on stdout. No AWS calls or policy attachment."""
import argparse
import json
from pathlib import Path
import re


POLICY_ROOT = Path(__file__).resolve().parents[1] / "infra/iam-review"
COMPONENTS = (
    "cloudformation-role-management.json", "cloudformation-named-resources.json",
    "cloudformation-api-routes.json", "cloudformation-agentcore.json",
)


def build_bundle(values: dict) -> dict:
    patterns = {
        "AccountId": r"[0-9]{12}",
        "ApiId": r"[a-z0-9]{1,64}",
        "ArtifactBucketName": r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]",
    }
    for key, pattern in patterns.items():
        if not isinstance(values.get(key), str) or not re.fullmatch(pattern, values[key]):
            raise ValueError(f"Invalid or missing {key}")
    identity = values.get("WorkloadIdentityArn")
    identity_pattern = (
        rf"arn:aws:bedrock-agentcore:eu-west-1:{values['AccountId']}:"
        r"workload-identity-directory/default/workload-identity/[A-Za-z0-9_.-]{3,255}"
    )
    if not isinstance(identity, str) or not re.fullmatch(identity_pattern, identity):
        raise ValueError("Invalid or missing WorkloadIdentityArn; require one exact same-account Ireland identity")
    if set(values) != set(patterns) | {"WorkloadIdentityArn"}:
        raise ValueError("Unexpected substitution keys")
    statements = []
    for name in COMPONENTS:
        source = (POLICY_ROOT / name).read_text()
        for key, value in values.items():
            source = source.replace("${" + key + "}", value)
        if "${" in source:
            raise ValueError(f"Unresolved placeholder in {name}")
        statements.extend(json.loads(source)["Statement"])
    policy = {"Version": "2012-10-17", "Statement": statements}
    size = len(json.dumps(policy, separators=(",", ":")))
    if size > 10240:
        raise ValueError("Combined review policy exceeds the 10,240-character role inline-policy limit")
    return {
        "review_only": True, "application_ready": False,
        "policy_characters": size, "policy": policy,
        "remaining_gates": [
            "Verify input ownership and runtime-to-workload-identity association against AWS responses",
            "Approve a first-creation and rollback procedure before the identity ARN exists",
            "Resolve remaining named-resource handler dependencies and run live IAM validation",
            "Audit all other role policies against the aggregate inline-policy limit",
            "Complete owner approval, non-root access, credit, quota and shutdown gates",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("values_file", type=Path, help="Private JSON with verified resource identifiers; never commit it")
    args = parser.parse_args()
    try:
        result = build_bundle(json.loads(args.values_file.read_text()))
    except (ValueError, OSError, TypeError) as error:
        parser.exit(2, f"Review assembly refused: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
