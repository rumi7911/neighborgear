# Access-policy review checkpoint

## Live access update — 11 September 2026

Latest: the plugin is freshly verified as NeighborGearOperator, not root. Lambda reports 1,000 concurrent and 1,000 unreserved executions, zero functions and zero code storage. After separate exact owner approval, the preflight inline policy now also permits only `access-analyzer:ValidatePolicy` and `iam:SimulateCustomPolicy`. Access Analyzer returned zero findings for the operator, deployer, runtime-Bedrock, preflight and assembled CloudFormation service-role identity policies. Positive and negative simulations allowed the exact intended paths while denying missing MFA, a wrong CloudFormation role, another passable role, another table, a missing inference-profile context and another model. AgentCore Instances capacity remained explicitly denied. The API-ID and workload-identity values used for syntax/simulation were review-only placeholders because those resources do not exist yet; they must be replaced and revalidated after owner prerequisite creation. No deployment or model invocation occurred.

### Historical 10 September checkpoint

Latest: the owner approved attaching NeighborGearPreflightReadOnly; IAM confirmed creation and the saved two-statement JSON matched the reviewed scope. All four reads then succeeded via NeighborGearOperator. Lambda Ireland concurrency/unreserved remain 10/10 with zero functions. See [the updated verification record](operator-preflight-readonly.md). Earlier statements below about this policy being unattached and these four reads being denied are historical; no deployment grants were activated.

[operator-preflight-readonly.json](operator-preflight-readonly.json) and its [scope review](operator-preflight-readonly.md) now mirror the six approved non-mutating operations. This does not activate deployment access.

Supersedes older reauthentication/root-identity blockers below: after explicit owner approval, attached only the AWS-managed `AWSMCPSignInOAuthAccessPolicy` directly to NeighborGearOperator through the owner console. Read-back showed one attached policy and console access Enabled with MFA. The reconnected plugin successfully executed STS GetCallerIdentity as NeighborGearOperator in the expected account, not root. No static keys, deployment roles or application resources were created.

The subsequent read-only preflight attempted ListAttachedUserPolicies, ListUserPolicies and ListGroupsForUser on that same user, plus Lambda GetAccountSettings in Ireland. All four returned AccessDenied with no identity-based allow. This is an authorization gap, not failed MFA or expired plugin authentication. Current quota and the complete API-visible permission inventory therefore remain unverified. A narrowly scoped read-only preflight grant requires owner approval before attachment; do not attach AdministratorAccess or broad account-wide ReadOnlyAccess to bypass this gate. Historical statements about no attached policies refer to the state before the OAuth attachment.

Latest: [shutdown access review](shutdown-review.md) records the successful source scan, rejected broad baseline and ordered deployment gates. No shutdown policy was attached; the next external prerequisite is a freshly verified non-root AWS connection.

**Drafts only. Not attached, not a complete deployment bootstrap.** Prepared 9 September 2026. Do not paste these directly into IAM: `${AccountId}` is a review placeholder, not an IAM policy variable. Resolve it privately from verified STS identity before validation/application. No account identifiers, email addresses or secrets are stored here.

## Documents and scope

### Provisioning checkpoint

Stop-control update: the disabled owner security template now also defines `neighborgear-demo-controls`, retained without TTL and initially empty. Api/Worker/Sweep/Runtime roles and the boundary receive only GetItem on that exact table. Source-policy Autopilot 0.3.0 was rerun offline after the read path was added; its broad baseline was not attached. Owner control-write authorization and stronger IAM protection for the separate BUDGET record remain review items. See `docs/stop-control.md`; the shutdown CLI is now implemented with offline tests, but its operator permissions and actual cloud shutdown remain unverified. No shutdown grants have been added to these policy drafts.

AgentCore follow-up: [the AgentCore review](agentcore-review.md) now accompanies `cloudformation-agentcore.json` and the offline `scripts/build_access_review.py` assembler. Tagged Ireland creation, runtime/endpoint management and exact-identity cleanup are drafted; Instances capacity-provider selection is explicitly denied. The critical first-create/rollback identity dependency is not solved by placeholders. The assembler refuses unresolved scopes and oversized policies and always labels the result review-only. Quarantine remains unchanged; initial creation/recovery, live IAM validation and other deployment gates remain open.

Network refinement: CloudFront, the HTTP API/default stage and web bucket now live in the separate disabled `infra/network-bootstrap.yaml`. The app consumes verified network outputs and manages only routes/integrations inside that API through `cloudformation-api-routes.json`. Web-bucket administration has been removed from the app's named-resource component. This avoids an account-wide CloudFront grant to the app role; owner network approval/execution and AgentCore provisioning remain pending. See the provisioning review for cross-stack setup and shutdown implications.

The [provisioning review](provisioning-review.md) now explains the named-resource policy component, all of its scope exceptions, and the remaining API Gateway, CloudFront, AgentCore and dependency gaps. `cloudformation-named-resources.json` covers named infrastructure configuration, not a complete deployment service role. `infra/security-bootstrap.yaml` is an owner-only, disabled scaffold: even when creation is enabled, both deployment roles retain explicit deny-all quarantine and no operator attachment is made. No executable unlock or deployment path is claimed. This remains preparation only, with no AWS mutation.

### Template integration completed locally

`infra/template.yaml` now declares ApiRole, WorkerRole, SweepRole, SchedulerRole and RuntimeRole explicitly. All use the fixed owner-managed `NeighborGearWorkloadBoundary`, inline policies, project IAM paths and stack-prefixed role names. The corresponding PassRole draft has been aligned with those names. SAM expansion is tested using pinned aws-sam-translator 1.113.0; it produces exactly those five roles, with no extra generated role or managed-policy attachment. This is offline template verification, not live authorization proof.

`infra/workload-boundary.yaml` defines the separate owner-only boundary policy and defaults `EnableBoundary=false`. It grants no permissions by itself and creates no application infrastructure. Its ceiling covers the project's records, work queue, artifact reads under `agent/`, fictional session writes, runtime invocation, reminder sweep, logs and the reviewed EU model profile. IAM administration and unrestricted resource grants are absent. The managed policy is retained on stack deletion so workload boundaries are not accidentally removed.

The deployable application name must be `neighborgear-demo` in `eu-west-1` to match this reviewed access design. Table, work queue, session bucket, Lambda functions and roles now have deterministic stack-prefixed names to match the boundary. Artifact `CodeKey` must start with `agent/`; immutable suffixes are still required. The boundary and artifact bucket must be provisioned only after complete bootstrap approval, and do not exist yet.

Lambda roles trust the documented Lambda service principal; unsupported source-context conditions were not invented for Lambda role assumption. Scheduler trust requires the owning account and the dedicated project **schedule group** ARN, not a schedule ARN. Log groups are created before the functions, which only receive stream-create/write access to their individual groups. AgentCore's existing source-account trust remains; its runtime-prefix logging scope is narrowed. Cloud service trust and actual runtime log naming still require live validation before deployment.

The deployer draft now includes object upload, verification and multipart-upload cleanup under the owner bucket's `agent/` prefix, plus bucket-location lookup. It cannot delete objects, change bucket policies or write outside that prefix. `${ArtifactBucketName}` must be privately resolved to the same reviewed bucket supplied to the workload boundary. Uploads must use content-addressed keys; PutObject alone does not enforce immutability, and reusing a key could overwrite code, so deployment procedures must reject existing keys with different content. Package Lambda artifacts under the same prefix. Frontend publication needs separately scoped WebAssets permissions and is not included in this artifact grant.

**Still unfinished:** the complete CloudFormation infrastructure-provisioning policy and activation of the owner-controlled bootstrap. The locked scaffold is now defined, but its final permission assembly is not complete. The work above does not make task 1 or AWS deployment complete. AWS plugin reauthentication is still required for live policy validation; no remote mutation was performed.

- `runtime-bedrock.json`: complete Bedrock-only identity-policy draft for the runtime, now integrated in `infra/template.yaml`. The first statement allows the two inference actions on the exact Ireland EU Nova Lite profile. The second permits its four previously verified EU foundation-model destinations only when `bedrock:InferenceProfileArn` equals that profile. No wildcard region/model, profile management, bearer-token access, hosted tool invocation or guardrail permissions are granted. This is not the runtime's complete data/log policy or a permissions boundary.

- `cloudformation-role-management.json`: the IAM-only portion of the future CloudFormation service-role policy. Role creation requires the exact owner-managed `NeighborGearWorkloadBoundary`; creation and inline-role management are restricted to `/neighborgear-demo/`. PassRole lists five exact role names matching the integrated application template, separated by receiving service. Explicit denials prohibit boundary removal/replacement and managed-policy administration/attachment. This file alone grants no infrastructure provisioning and is not a finished service role.

  The management grant includes trust-policy updates inside the workload path. It cannot inspect or constrain the contents of a submitted trust/inline policy. Safety therefore also requires that this path contain only boundary-protected project roles, that owners never insert unbounded roles into it, and that resource policies do not grant broader access directly to workload sessions. Boundary changes remain owner-only; role deletion with a boundary needs validation during rollback testing.

- `operator.json`: the operator's sole grant is `sts:AssumeRole` for `NeighborGearDeployer`, with MFA required. No account administration or direct resource access.
- `deployer-trust.json`: only the exact `NeighborGearOperator` IAM user may assume the deployer role, with MFA. No root, account-wide principal, session tags or external principals. Set the role's maximum session duration to one hour in the eventual bootstrap.
- `deployer.json`: CloudFormation change-set preparation, review and execution for exactly `neighborgear-demo` in Ireland, plus the artifact operations described above. Creation must specify `NeighborGearCloudFormation`; PassRole is limited to that role and the CloudFormation service. Stack discovery is account-wide metadata within Ireland because ListStacks has no resource-level scope. Template validation is also unscoped by resource. No IAM administration, direct model invocation, stack deletion or security-bootstrap modification is granted by this draft.

These policies grant only their listed permissions; omission is not an explicit deny against grants from other policies. Audit the user's groups, attached/inline policies, role policies and resource policies before application.

CloudFormation execution delegates the power of its service role, including to people who can operate an existing stack. Therefore the deployer policy **must not be applied in isolation** or used with an administrator CloudFormation role. The separate bounded service-role policy and workload boundaries are still required. ExecuteChangeSet does not support the RoleArn condition used by CreateChangeSet; do not add an ineffective condition to pretend it does.

## Verified evidence and limitations

- 8 September read-only AWS calls succeeded: plugin identity is still **root**; Lambda Ireland account concurrency and unreserved concurrency are both **10**, with zero functions. Service Quotas marks concurrent executions adjustable. This does not prove an increase will be approved or is available on the Free plan.
- User reported successful IAM console login after MFA resynchronization. That does not change the plugin's credential identity. A non-root programmatic session is still required before app deployment; do not create static access keys as a shortcut.
- AWS's published rule leaves 100 concurrency units unreserved. The existing template reserves 2 + 1 + 1, so the documented minimum quota for that arrangement is **104**, assuming no other reservations. No quota request was submitted; no concurrency controls were removed. Ask for approval before submitting a quota request, and do not upgrade the account to resolve it.
- Local IAM Policy Autopilot **0.3.0** completed successfully on all five runtime-source files below. It found DynamoDB, SQS, S3 and AgentCore operations. The output included wildcard table/runtime/queue/object resources, optional KMS, S3 ACL/retention/Object Lambda and replication permissions. It did not resolve Bedrock calls inside Strands. **Do not attach its raw output or interpret it as complete least privilege.** Source results were inspected in the tool output, not uploaded to IAM.

Reproduce the source scan with the verified account ID supplied privately:

```sh
DISABLE_IAM_POLICY_AUTOPILOT_TELEMETRY=true uvx iam-policy-autopilot@0.3.0 generate-policies \
  'backend/agent.py' \
  'infra/repository.py' \
  'infra/dispatch.py' \
  'infra/handlers.py' \
  'infra/runtime.py' \
  --region eu-west-1 --account "$NEIGHBORGEAR_ACCOUNT_ID" \
  --service-hints dynamodb s3 sqs bedrock bedrock-agentcore --pretty
```

The initial invocation displayed the tool's command-usage telemetry notice; the completed reproduction explicitly disabled telemetry. No `--upload-policies` was used.

## Remaining work before an application approval request

### Current task-1 finding

An additional Autopilot 0.3.0 run included the installed `strands/models/bedrock.py` and `--explain 'bedrock:*'`. It still produced no Bedrock invocation actions. The installed dependency chooses `self.client.converse_stream` or `self.client.converse` into `converse_method` before invoking it (lines 1397–1416), which the scan does not resolve. No dependency code was modified. The user subsequently explicitly approved manually verifying these missing permissions against official AWS documentation; that exception does not authorize attachment or deployment.

Manual verification resolves the action mapping: Converse requires `bedrock:InvokeModel`; ConverseStream requires `bedrock:InvokeModelWithResponseStream`. AWS's inference-profile documentation requires the profile plus every destination model and demonstrates restricting foundation-model access with `bedrock:InferenceProfileArn`. The service authorization data confirms this key has ARN type and is supported by both actions. Its generic operation mapping also lists optional guardrail, bearer-token and hosted-tool permissions; none of those features is used by the configured IAM-authenticated, application-tool workflow, so they are not added. Do not confuse local Strands tools with Bedrock-hosted InvokeTool operations.

The documentation prose contains `aws:InferenceProfileArn` in one sentence, but its policy example and the service authorization data use `bedrock:InferenceProfileArn`; this draft uses the verified service-specific key.

The new API attempt to recheck identity and the routing profile returned `UNAUTHORIZED` before calls executed. The four destinations therefore remain based on the earlier verified profile, not a fresh account check. Live Access Analyzer validation and IAM positive/negative simulation have not run. Reconnect the plugin, recheck the profile, and test both actions against: the exact profile, all four destinations with correct context, missing/wrong context, another model, another region and unrelated IAM actions. Expected results are allows only for the first two groups. These are pending verification cases, not measured results.

The user-approved manual-verification blocker is resolved. Full task 1 remains incomplete until the boundary, service-role provisioning permissions, artifact access, template integration and live validation are finished.

CloudFront creation also has explicit scoping exceptions: the current service reference lists no resource scope or action-specific condition keys for CreateOriginAccessControl and CreateOriginRequestPolicy. Updates/deletes support resource ARNs. The eventual bootstrap review must disclose these creation exceptions and scope later management to the actual created IDs, rather than claiming every CloudFront operation is name-scoped.

1. Finish the owner-controlled bootstrap and CloudFormation service role. The boundary definition and scoped artifact-upload draft are now prepared locally. Do not substitute broad managed policies.
2. Trace unresolved Strands/dependency calls with Autopilot's explain workflow; separate workload roles and scope the results to actual project resources and approved EU Nova Lite destinations.
3. Completed locally: all five explicit roles reference the fixed boundary; tests inspect the SAM-expanded template. Live enforcement remains unverified until the owner bootstrap is approved, applied and inspected.
4. Resolve the Lambda quota and Scheduler credit-coverage questions; implement and verify the six-hour stop control and ten-attempt global allowance.
5. Render private policy copies, perform AWS policy validation and positive/negative simulations, and obtain review of the complete bootstrap. Current tests are structural guardrails, **not** live IAM authorization tests.
6. Establish and verify non-root tooling, then request approval for the exact bootstrap and bounded simulator deployment. No paid resources or model calls were enabled during this checkpoint.

## References checked

- [Converse API permissions](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html).
- [ConverseStream API permissions](https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ConverseStream.html).
- [Inference-profile permissions and profile-only access](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-prereq.html).
- [Bedrock service authorization data](https://servicereference.us-east-1.amazonaws.com/v1/bedrock/bedrock.json): operation/action mapping and `bedrock:InferenceProfileArn` condition type.

- [CloudFormation service authorization data](https://servicereference.us-east-1.amazonaws.com/v1/cloudformation/cloudformation.json): operation mappings, stack ARNs, RoleArn condition support and global read exceptions.
- [IAM service authorization data](https://servicereference.us-east-1.amazonaws.com/v1/iam/iam.json): PassRole action and receiving-service condition.
- [STS service authorization data](https://servicereference.us-east-1.amazonaws.com/v1/sts/sts.json): AssumeRole action. This design deliberately grants only plain role assumption, not session tagging, source identity or supplied contexts.
- [Lambda reserved concurrency](https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html): 100-unit unreserved pool requirement; reservations themselves have no additional charge.
