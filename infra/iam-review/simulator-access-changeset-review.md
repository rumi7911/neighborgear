# Simulator access change-set review — 13 September 2026

Status: **executed successfully after a separate action-time owner approval**.

CloudFormation created the standard update change set `neighborgear-simulator-access-review-20260913` for the existing `neighborgear-security` stack in `eu-west-1`. The uploaded source was the locally validated `infra/security-bootstrap.yaml`. The review used the existing bootstrap value, set `EnableSimulatorAccess=true`, and pinned the API and CloudFront identifiers from the separately deployed `neighborgear-network` stack. Account-specific identifiers are deliberately not recorded here.

CloudFormation reported `CREATE_COMPLETE` and `AVAILABLE`. Deployment validations were enabled, Express mode was disabled, rollback-on-failure remained enabled, and resource auto-import was disabled. The console reported that all supported deployment validations passed.

The generated change set contains exactly three resource changes:

| Logical resource | Action | Type | Replacement |
|---|---|---|---|
| `CloudFormation` | Modify | `AWS::IAM::Role` | False |
| `Deployer` | Modify | `AWS::IAM::Role` | False |
| `OperatorAssumeDeployer` | Add | `AWS::IAM::Policy` | Not applicable |

The JSON review confirms that the two role changes replace their inline deny-all quarantine policies with the reviewed simulator deployment policies. The role trust policies and one-hour maximum sessions are unchanged. The new user policy allows only `sts:AssumeRole` to `NeighborGearDeployer` and requires MFA. The Deployer grant remains limited to the project artifact prefix, private frontend publication target, the one existing distribution, change-set operations for `neighborgear-demo`, and passing only `NeighborGearCloudFormation` to CloudFormation. The service-role policy contains no Bedrock or AgentCore access in simulator mode.

No bucket, table, managed policy, network resource, application compute resource or model runtime appeared in the change set. No resource replacement was proposed.

After a separate action-time owner approval, the exact reviewed change set was executed with rollback-all and deletion of newly created resources on failure. At 10:27 UK time, the stack reached `UPDATE_COMPLETE`. `CloudFormation` and `Deployer` each reached `UPDATE_COMPLETE`, and `OperatorAssumeDeployer` reached `CREATE_COMPLETE`. Read-back confirmed `EnableBootstrap=true` and `EnableSimulatorAccess=true` with the two pinned network identifiers. The roles now carry the reviewed simulator-only grants, and the operator can assume the deployer role only with MFA. No application stack or model invocation was started by this update.
