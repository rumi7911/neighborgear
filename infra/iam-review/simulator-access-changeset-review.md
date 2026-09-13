# Simulator access change-set review — 13 September 2026

Status: **created and validated; not executed**.

CloudFormation created the standard update change set `neighborgear-simulator-access-review-20260913` for the existing `neighborgear-security` stack in `eu-west-1`. The uploaded source was the locally validated `infra/security-bootstrap.yaml`. The review used the existing bootstrap value, set `EnableSimulatorAccess=true`, and pinned the API and CloudFront identifiers from the separately deployed `neighborgear-network` stack. Account-specific identifiers are deliberately not recorded here.

CloudFormation reported `CREATE_COMPLETE` and `AVAILABLE`. Deployment validations were enabled, Express mode was disabled, rollback-on-failure remained enabled, and resource auto-import was disabled. The console reported that all supported deployment validations passed.

The generated change set contains exactly three resource changes:

| Logical resource | Action | Type | Replacement |
|---|---|---|---|
| `CloudFormation` | Modify | `AWS::IAM::Role` | False |
| `Deployer` | Modify | `AWS::IAM::Role` | False |
| `OperatorAssumeDeployer` | Add | `AWS::IAM::Policy` | Not applicable |

The JSON review confirms that the two role changes replace their inline deny-all quarantine policies with the reviewed simulator deployment policies. The role trust policies and one-hour maximum sessions are unchanged. The new user policy allows only `sts:AssumeRole` to `NeighborGearDeployer` and requires MFA. The Deployer grant remains limited to the project artifact prefix, private frontend publication target, the one existing distribution, change-set operations for `neighborgear-demo`, and passing only `NeighborGearCloudFormation` to CloudFormation. The service-role policy contains no Bedrock or AgentCore access in simulator mode.

No bucket, table, managed policy, network resource, application compute resource or model runtime appears in the change set. No resource replacement is proposed. The change set has not been executed, so both deployed roles remain quarantined and the operator has not gained the new assume-role permission. Execution is a separate live IAM change and requires a fresh action-time owner approval.
