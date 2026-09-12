# Provisioning review — updated 12 September 2026

**The owner network prerequisite is deployed. The application policies and security bootstrap remain review-only drafts: do not attach or deploy them yet.**

## Prepared artifacts

### Network ownership split

The design separates `infra/network-bootstrap.yaml` (owner-managed stack `neighborgear-network`) from `infra/template.yaml` (application stack `neighborgear-demo`). After exact owner approval, the reviewed network change set was executed in Ireland on 12 September 2026. Its HTTP API and auto-deploying throttled default stage, CloudFront distribution/origin policies, private web bucket and distribution-scoped bucket policy all reached `CREATE_COMPLETE`. Five outputs were captured in a gitignored local environment file; account-specific identifiers are not committed. No existing resource was migrated.

The application template now creates only the Lambda integration, `/api/{proxy+}` route and API-scoped Lambda permission inside the supplied `NetworkApiId`. `NetworkDomainName` supplies its demo URL output. Both values must be verified outputs from the same account's Ireland network stack; neither parameter has a default. The app's web-bucket output remains derived from the reviewed application stack name, which must match the network's `ApplicationStackName`.

`cloudformation-api-routes.json` grants POST on the exact API's route/integration collections and GET/PATCH/DELETE on their children. `${ApiId}` must be the verified network output, **never `*`**. There is no API creation, API deletion, stage configuration, import/reimport, CloudFront management or API-Gateway PassRole grant. The integration deliberately omits CredentialsArn and uses a Lambda resource permission, as documented by AWS. The generic CreateIntegration/UpdateIntegration mapping also lists PassRole for role-backed integrations; that configuration is not used here.

This moves the unscopable network-creation operations out of the application deployer's remit; it does not make them narrowly scoped AWS operations. The initial owner-reviewed network change set is complete. Future network updates and teardown still require separate owner review and an owner-authorized execution path. Do not give the application role a broad network role or permission to operate the network stack. Its current CloudFormation stack scope remains only `neighborgear-demo`.

API Gateway stage throttles stay owner-controlled. Route/integration management can still redirect traffic or add routes within this one API, so its change sets remain security-sensitive. There are no routes or compute in the network template alone: it is not a working demo until app/frontend deployment. Removing the app does not remove the owner network, and shutdown must cover both stacks.

`cloudformation-named-resources.json` is a valid identity-policy document, but only a **component** of the future CloudFormation service role. It is not a complete authorization policy for the application. Combine nothing until the remaining dependencies below have been reviewed. Account and artifact bucket placeholders must be resolved privately; they are not IAM variables.

Its statements cover:

| Statement group | Scope and limits |
| --- | --- |
| Table configuration | One Ireland `neighborgear-demo-records` table, its TTL and tags; no item-level permissions. Table deletion is destructive despite the absence of item actions. |
| Queue configuration | Exactly the work FIFO and dead-letter FIFO; no send/receive grant. `SetQueueAttributes` can change queue policies and retention, so changes still need review. |
| Bucket creation/configuration | Only the deterministic session bucket; creation requires Ireland, existing-bucket management requires the owning account. No bucket or object deletion grant. The owner-managed web bucket has no grant here. |
| Session expiry | Lifecycle configuration on the fictional-session bucket only; changing expiry can delete data later. |
| Web-origin policy | Removed from the app's provisioning component; managed only by the owner network template. |
| Artifact reads | Owner bucket's `agent/` objects only, not upload or bucket administration. |
| Lambda configuration | Exactly api, worker and sweep functions; no invocation grant. Function reads expose configuration, including the private judge key, to this privileged deployment role. |
| API invocation permission | AddPermission only for the API function and API Gateway principal. Source ARN must still be checked in the expanded template; this condition does not constrain it. |
| Event source mapping | Creation uses AWS's required `Resource: *`, constrained to Ireland and the exact worker function. Existing mapping get/update/delete requires that worker. This does not independently constrain the source queue. |
| Logs | Three Lambda log groups only. Modern tagging actions use the ARN without `:*`; other log-group actions use the documented suffixed ARN. DescribeLogGroups is Ireland-wide metadata because AWS does not offer resource-level scope. No log-event reads. |
| Scheduler | One reminder group and schedules inside it. PassRole remains in the separately reviewed IAM component. |

The dead-letter queue and web bucket now have deterministic names in the application template so these grants do not need account-wide queue/bucket patterns. Nothing is deployed, so this does not rename an existing AWS resource. Future replacement of named resources needs an explicit migration review.

All action names and supported resource types in this component were checked against AWS's programmatic service references. Lambda's FunctionArn (ARN) and Principal (String) condition types were checked too. This verifies vocabulary and scoping support, **not** successful CloudFormation execution.

## Owner scaffold, deliberately locked

`infra/security-bootstrap.yaml` creates nothing by default. If separately approved and enabled by an owner in Ireland, it would create a private, encrypted, versioned artifact bucket and two one-hour deployment roles. Both roles have an explicit **deny-all quarantine** policy. There are no user attachments, credentials, broad managed policies or application resources. The Deployer trust retains the exact existing operator and MFA requirement. The CloudFormation trust uses AWS's documented service principal; no unsupported stack SourceArn condition is assumed.

The workload boundary remains in the separate disabled `infra/workload-boundary.yaml`. Its ArtifactBucketName must match the scaffold output. These are account-global named IAM resources: do not create duplicate security stacks in other regions. The artifact bucket retains current versions on stack deletion; obsolete noncurrent versions expire after seven days and incomplete multipart uploads after one day. Retained storage is not a zero-cost guarantee.

Do not create even the locked scaffold until credits/costs and its exact change set have been approved. The quarantine has **no enable parameter**: replacing it requires an owner-reviewed template change after complete permission validation. Attaching an Allow policy alongside the quarantine will not unlock a role.

## Unresolved before a complete deployment policy

1. **API Gateway HTTP API:** the deployed API ID is captured privately. The exact-ID route/integration policy produced zero findings in the AWS policy editor. API Gateway V2 simulation allowed its exact collection/child operations and denied unrelated-API POST/PATCH cases while exact-API controls remained allowed. The remaining gate is CloudFormation route/integration create, update and rollback verification after application-deployment approval. API and stage creation belong to the owner network setup; no tag inheritance assumption is needed for app grants.
2. **CloudFront:** the initial owner-reviewed network change set completed successfully. The ownership split avoids granting generated-ID creation/management operations to the app role, and no application CloudFront grant has been added. Future updates and teardown remain owner-controlled.
3. **AgentCore:** creation/deletion mappings include runtime endpoints, capacity-provider and workload-identity dependencies. Verify the actual direct-code, IAM-authenticated handler path and applicable resource scope before granting them. No AgentCore provisioning grant has been added.
4. **API dependency completeness:** the service reference maps some operations to permissions for variants not configured here, including DynamoDB replication/resource policies, Lambda layers/capacity providers and S3 ACL/object-lock/versioning writes. This component does not resolve those prerequisites and is deliberately not represented as a complete operation-derived policy. Reconcile them with authoritative handler/API evidence before assembly; do not blindly attach all reported permissions. Event-mapping tag permissions also need resolution if SAM/CloudFormation supplies tags.
5. **Assembly and live validation:** merge the resolved provisioning component with bounded workload-role management, validate aggregate policy size and IAM semantics, run positive/negative simulations, inspect actual generated IDs/trust/boundaries, and test create/update/rollback. Only then prepare an owner-reviewed replacement for quarantine and the operator's assume-role attachment. Frontend publication permissions remain separate.

None of these reviews authorizes account-wide grants. Exact deployed-API editor validation and simulation are complete; the AWS connector was unavailable for that checkpoint, so the simulation was run as a custom, unattached policy in the authenticated owner console. Lambda quota and credit/cost planning gates are recorded separately; Scheduler credit coverage, usage-stop controls and the remaining application permissions still require final review.

AgentCore follow-up evidence: AWS documents an automatically managed identity directory, but the checked identity examples do not establish a reliable runtime-to-workload-identity naming rule for our deployment. Do not grant deletion of the whole default directory to bridge that gap. Its runtime identity service-linked role documentation describes OAuth/JWT token flows, which this IAM-authenticated application does not use; no service-linked role was added on that basis. Runtime endpoint, identity-deletion and capacity-provider dependencies remain unresolved rather than being converted to wildcard grants.

## Sources

- Programmatic action/resource references: [DynamoDB](https://servicereference.us-east-1.amazonaws.com/v1/dynamodb/dynamodb.json), [SQS](https://servicereference.us-east-1.amazonaws.com/v1/sqs/sqs.json), [S3](https://servicereference.us-east-1.amazonaws.com/v1/s3/s3.json), [Lambda](https://servicereference.us-east-1.amazonaws.com/v1/lambda/lambda.json), [Logs](https://servicereference.us-east-1.amazonaws.com/v1/logs/logs.json), [Scheduler](https://servicereference.us-east-1.amazonaws.com/v1/scheduler/scheduler.json).
- Remaining service references: [API Gateway](https://servicereference.us-east-1.amazonaws.com/v1/apigateway/apigateway.json), [CloudFront](https://servicereference.us-east-1.amazonaws.com/v1/cloudfront/cloudfront.json), [AgentCore](https://servicereference.us-east-1.amazonaws.com/v1/bedrock-agentcore/bedrock-agentcore.json).
- [API Gateway tag support and V1 inheritance](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-tagging-supported-resources.html).
- [CloudFormation service-role trust and delegation](https://docs.aws.amazon.com/prescriptive-guidance/latest/least-privilege-cloudformation/service-roles-for-cloudformation.html).
- [CloudWatch log-group ARN variants](https://docs.aws.amazon.com/AmazonCloudWatchLogs/latest/APIReference/API_LogGroup.html).
- [API Gateway integration schema and role-free resource permissions](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-apigatewayv2-integration.html), [route schema](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-apigatewayv2-route.html), [stage schema](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-apigatewayv2-stage.html).
- [AgentCore identity directory](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agent-identity-directory.html), [service-linked role use cases](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/service-linked-roles.html).
