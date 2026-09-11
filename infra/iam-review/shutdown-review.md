# Shutdown access review — 9 September 2026

**Result: not ready to attach or deploy.** The shutdown implementation is locally tested. No account API was called in this review; earlier account evidence has not been refreshed. No permissions, quotas, billing settings, stacks or model calls were changed.

## Reproducible source scan

The AWS IAM skill requires source-policy Autopilot for Python SDK code. `uvx iam-policy-autopilot@latest --version` resolved to **0.3.0**, then pinned for reproduction. The scan completed with telemetry disabled and no upload flag. Ireland comes from the approved template. The account flag is omitted because the current connection has not been freshly verified; wildcard account output is not deployment-ready.

```sh
DISABLE_IAM_POLICY_AUTOPILOT_TELEMETRY=true uvx iam-policy-autopilot@0.3.0 generate-policies \
  'scripts/stop_demo.py' \
  --region eu-west-1 \
  --service-hints sts cloudformation scheduler lambda dynamodb \
  --pretty
```

The same command can use `@latest`; record any version change before comparing results. Replace the source path when using a different checkout. Never add `--upload-policies` to this review command.

Result: one identity-policy baseline, eight statements and three explicit wildcard-resource warnings. All shutdown operation families were detected, including paginated CloudFormation resource listing. No manually constructed replacement policy was produced or attached.

## Findings requiring scoped review

| Generated access | Finding / required boundary |
| --- | --- |
| CloudFormation DescribeStacks, ListStackResources | Baseline matches every Ireland stack in any account. Scope must be the two verified stack ARNs. |
| CloudFormation ListStacks | Scanner associates this with DescribeStacks. The script always supplies StackName; review the dependency rather than granting account-wide listing automatically. |
| DynamoDB GetItem, UpdateItem, ReadDataForReplication | Baseline matches every Ireland table. Target only the owner controls table and CONTROL key. Replication access needs justification; the script does not implement replication. |
| KMS Decrypt | Scanner attributes this to DynamoDB forward-access sessions. Resolve actual encryption configuration; do not grant every key. |
| Scheduler GetSchedule, UpdateSchedule | Target the single verified schedule ARN, not all groups/schedules. |
| IAM PassRole | Generated Resource is `*`, with Scheduler service condition. Only the verified existing Scheduler role is in scope. |
| Lambda GetEventSourceMapping, UpdateEventSourceMapping | Target the single verified mapping ARN. |
| STS GetCallerIdentity | Verifies identity, not sufficient deployment permissions. |

Reproduce dependency explanations with the generation command plus `--explain 'cloudformation:ListStacks' 'dynamodb:ReadDataForReplication' 'kms:Decrypt'`. Static analysis is not live authorization evidence. Exact schedule/mapping IDs do not exist until provisioning through an approved path. Do not invent IDs or grant broad access to bypass this sequencing issue.

## Safe script versus disable-only permissions

The script only closes the gate and disables triggers. General update access to those exact resources is broader than the script's behavior. DynamoDB item/attribute restrictions do not establish that a written boolean must be false. Do not describe eventual maintenance credentials as IAM-enforced “stop only.” This is an inference from the documented item/attribute condition model. [AWS fine-grained DynamoDB access](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/specifying-conditions.html)

Treat eventual credentials as trusted, short-lived owner maintenance access, not workload access. Keep control writes out of application roles. A mediated disable-only service would be a design expansion requiring review.

## Deployment gates in execution order

1. **Access:** reconnect the AWS plugin to the intended non-root identity and verify STS. Console sign-in alone does not reconnect it. No static keys or root workaround.
2. **Account feasibility:** refresh Lambda quota, Free-plan constraints, Scheduler credit eligibility and balance. Last observed concurrency was 10. Reservations total four; AWS requires 100 units unreserved, so the recorded configuration needs at least 104. No quota request, plan upgrade or removal of limits is authorized. [AWS reserved concurrency](https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html)
3. **Cost and access approval:** finish the six-hour simulator cost estimate, approve bootstrap/provisioning access and resolve AgentCore first-creation/rollback permissions. Deny-all quarantine remains unchanged.
4. **Owner-reviewed window:** choose explicit UTC start/end times, at most six hours, protect judge access and establish scoped maintenance access. No automatic enabled-control initialization.
5. **Protected simulator:** after the above gates, provision approved resources, resolve shutdown IDs and validate permissions. Preview shutdown before opening intake; test apply/read-back with the owner present. Partial/pending results are not completion.
6. **Live model:** after simulator lifecycle and shutdown validation, refresh credits and approve bounded real-model evaluation. Fixtures are not live AI evidence.

Next external action: the owner reconnects the AWS plugin to the intended non-root session. Current credentials and service access remain unverified.
