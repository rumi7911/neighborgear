# AgentCore access component — review only

Prepared locally, 9 September 2026. **Not attached; not first-deployment-ready.**

`cloudformation-agentcore.json` covers these operations for the existing direct-code design:

- CreateAgentRuntime: AWS requires `Resource: *`. The grant requires Ireland and `Project=NeighborGear` on the request. The template now supplies that tag. This does **not** enforce a runtime-name prefix, a one-runtime limit, authentication type or a dollar cap at creation. Approval must account for that exception; never describe it as exact-name-scoped creation.
- Get/update/delete runtime and create endpoint: scoped to the configured `NeighborGear_${AccountId}` name with ten generated suffix characters. AWS's CreateAgentRuntime response schema documents this ARN format. The question marks match single characters, not arbitrary trailing paths.
- Get/delete endpoints and runtime/endpoint tag management: restricted to that runtime family. The current application uses the default endpoint; these grants do not permit unrelated runtimes or global endpoint administration.
- DeleteWorkloadIdentity: requires a separately resolved **exact** `${WorkloadIdentityArn}`. GetAgentRuntime/CreateAgentRuntime responses expose the associated identity; do not infer its name from the runtime name and do not substitute the default directory or a wildcard.
- PassCapacityProvider: explicitly denied. AWS documents capacityProviderConfiguration as optional and specific to Instances compute. The template has no such configuration. This is a deliberate exclusion of that feature, not proof that AWS's generic operation mapping is satisfied for every runtime variant. Validate the configured serverless path live.

The existing role-management component supplies PassRole for only the bounded Runtime role and the AgentCore service. The provisioning component grants no model/runtime invocation, IAM administration, identity-directory management, OAuth credentials, VPC management or service-linked-role creation. Source-account trust and workload execution permissions remain separate from provisioning rights.

## Important first-creation limitation

The workload identity does not exist yet. An exact-identity deletion policy cannot be completed before AWS returns its ARN. Therefore this lifecycle component is **not a ready first-create/rollback policy**, even though its JSON and local tests pass. Before creating the first runtime, review a staged owner-authorized creation/recovery procedure that captures the runtime and identity ARNs and provisions exact cleanup rights. Do not execute a normal CloudFormation first-create with unresolved placeholders, assume rollback will work, broaden identity deletion, or silently retain a failed billable runtime. Runtime replacement may similarly require an explicitly reviewed set of old/new identity ARNs; the assembler intentionally accepts only one today.

## Offline assembly

`scripts/build_access_review.py` combines the four CloudFormation components: bounded role management, named resources, exact-API routes and AgentCore. It reads a private JSON file containing `AccountId`, `ApiId`, `ArtifactBucketName`, and `WorkloadIdentityArn`, and prints a **review wrapper** with `policy`, its compact character count, and remaining gates. It makes no AWS calls, creates no files, and always reports `application_ready=false`.

It rejects missing identifiers, scope wildcards, a directory ARN, foreign-account/region identities, unknown substitutions and a policy exceeding 10,240 compact characters. Format checks cannot prove ownership or runtime association; verify inputs against AWS responses. The size check covers the assembled document only: all other inline policies on the role, including quarantine, count toward the aggregate AWS limit. Do not treat this as a managed policy, whose individual limit is smaller. The existing deny-all quarantine is untouched.

After verified identifiers exist, run locally with a private values file outside Git:

```sh
uv run python scripts/build_access_review.py /absolute/private/path/neighborgear-review-values.json
```

The output contains account/resource identifiers; do not publish or paste it into the public repository. The wrapper itself is not an IAM policy to attach. Passing local assembly does not resolve remaining named-resource handler dependencies, prove live authorization, approve the owner network setup, fix the Lambda quota, verify Scheduler credit coverage, or implement the six-hour stop control.

## Sources

- [AgentCore service authorization data](https://servicereference.us-east-1.amazonaws.com/v1/bedrock-agentcore/bedrock-agentcore.json): operations, dependencies and resource/condition support.
- [CreateAgentRuntime](https://docs.aws.amazon.com/bedrock-agentcore-control/latest/APIReference/API_CreateAgentRuntime.html): optional Instances capacity configuration, runtime ARN format and associated identity response.
- [DeleteAgentRuntime](https://docs.aws.amazon.com/bedrock-agentcore-control/latest/APIReference/API_DeleteAgentRuntime.html): runtime versus version deletion.
- [CloudFormation runtime schema](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-bedrockagentcore-runtime.html): Tags map and direct-code runtime properties.
- [IAM policy-size limits](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_iam-quotas.html): aggregate role inline limit 10,240 characters; individual managed-policy limit 6,144; whitespace excluded.
