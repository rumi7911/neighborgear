# Conditional AWS deployment

Status: initial application implementation and offline validation complete; the separately approved network prerequisite and deny-all-quarantined security scaffold are `CREATE_COMPLETE` in Ireland, while the **application itself is not deployed or tested end-to-end in AWS**. The ARM64 archive was built locally. Issued credits, core service coverage and Lambda quota compatibility were verified. The CloudFront endpoint currently has no frontend assets or application route. Deployment-policy completion, workload-boundary creation, controlled role activation, Scheduler coverage and live stop-control verification remain gates. See `credits-preflight.md`.

## Cost-alert preparation

Security update, 12 September: after local lint, structural tests, selected AWS Guard rules, AWS deployment validation and separate action-time owner approvals, the security scaffold and workload boundary reached `CREATE_COMPLETE`. The deployed roles remain deny-all quarantined and provide no deployment capability. The source template now contains a separately gated simulator-only activation branch; it has not been uploaded, reviewed as a change set or executed. Do not apply the policy components independently or attempt application deployment with root. Lambda's applied quota is verified at 1,000.

Simulator separation update: `Mode=simulator` executes deterministic queued work inside the worker Lambda. The AgentCore runtime, runtime role, runtime invocation environment variable and invocation grant are all conditioned on live mode. This allows the protected cloud lifecycle and shutdown controls to be tested before AgentCore provisioning or any model call. Live mode remains a later, separately reviewed deployment.

`infra/cost-controls.yaml` is a separate, opt-in monitoring template for us-east-1. It creates only an account-wide monthly $20 COST budget: actual dollar alerts above $1, $5, $10 and $20, and a forecast alert above $20. Credits/refunds are excluded so they cannot hide service consumption. The budget is not a hard cap, is not cumulative across months, and does not replace the model-attempt counter or shutdown controls. New-account forecasts may be unavailable.

The `AlertEmail` parameter has no default and is masked; obtain the owner's chosen recipient privately. `EnableAlerts` defaults to false. Do not embed the address in repository files or shell history.

Operational update, 7 September 2026: after the owner supplied a recipient, the notification-only budget `NeighborGear-gross-account-spend` was created directly through the AWS Budgets API, not CloudFormation. Read-back verified HEALTHY status, all five thresholds and the chosen subscriber, credit/refund exclusion and no budget actions. Email delivery itself has not been tested. The address and account identifiers are deliberately omitted here. Do not deploy this template as a duplicate budget; reuse/update the existing API-managed budget, or separately review migration to CloudFormation. Application deployment and model invocation remain disabled; no IAM permissions were changed.

Offline checks: `uv run --extra cloud pytest -q infra/tests/test_cost_controls.py` and `uv run cfn-lint --regions us-east-1 --template infra/cost-controls.yaml`.

## Before doing anything billable

Application stop checks and the dry-run-first `scripts/stop-demo.py` tool are now implemented locally; see [stop-control.md](stop-control.md) for commands, required access and limitations. The owner bootstrap includes a retained, initially empty control table. Every cloud entry path fails closed until an owner-approved `CONTROL` record enables a UTC window of at most six hours. Workload access is read-only. The template and runtime now enforce a maximum of ten live run admissions. Live permissions and cloud shutdown verification remain unfinished; expiry alone does not stop all AWS charges.

Network ownership is separate: after review and explicit owner approval, `infra/network-bootstrap.yaml` was deployed as stack `neighborgear-network` in Ireland on 12 September 2026. It created the HTTP API/default stage, private web bucket and CloudFront resources; all seven resources reached `CREATE_COMPLETE`. No compute, application route or model invocation was created. The verified outputs are stored in a gitignored local environment file. The application stack receives `NetworkApiId` and `NetworkDomainName` from those outputs, and its service-role API policy must be privately rendered with the exact API ID before application, not an API wildcard. The app role has no network-stack or CloudFront management grant.

Local security integration: all five workload roles are now explicit and reference the fixed `NeighborGearWorkloadBoundary`. The owner-only definition is `infra/workload-boundary.yaml`, disabled by default and not applied. Deploy only as `neighborgear-demo` in `eu-west-1`; boundary resource scopes and PassRole names depend on that reviewed naming. The full deployment service-role policy and bootstrap assembly are still incomplete. See `infra/iam-review/README.md`; passing local tests is not deployment authorization.

Complete `credits-preflight.md`. All resources in `infra/template.yaml` are conditional on `EnableResources=true`; a template rule additionally requires `CreditsVerified=true`. The flag is an operator attestation, not a billing lookup. Even simulator mode has AWS infrastructure costs if deployed. Do not enable resources with unverified service coverage.

This template targets **eu-west-1** with the EU Nova Lite inference profile `eu.amazon.nova-lite-v1:0`. Verify regional availability and model access in your account before deployment. Changing model/provider requires reviewing IAM, credits and evaluation, not just editing a string.

## Offline preparation

```sh
uv sync --frozen --all-extras --python 3.12
uv run --extra cloud pytest -q
uv run cfn-lint infra/template.yaml
uv run cfn-lint infra/workload-boundary.yaml infra/security-bootstrap.yaml
uv run cfn-lint infra/network-bootstrap.yaml
npm --prefix frontend ci
npm --prefix frontend run build
bash scripts/package-cloud.sh
```

Packaging installs locked Linux ARM64 wheels into `output/cloud-package/`, and creates `output/neighborgear-agent.zip`. It downloads packages but does not access AWS. It refuses to overwrite an existing package directory: move that generated directory/archive aside before rebuilding. `agentcore_entry.py` is the archive entrypoint. The local macOS process cannot validate execution of Linux native wheels.

The SAM template uses the prepared package directly (`CodeUri`), so **do not run a build that replaces it with host-native dependencies**. `sam validate --lint --template-file infra/template.yaml` is an optional additional check when the SAM CLI is installed. The existing `cfn-lint` check passed without warnings/errors.

## Deployment procedure — participant-owned account required

1. Establish a short-lived AWS session locally, not through chat. Verify the account, region, issued credits, service eligibility and cost reserve.
2. After approval, upload the archive to the private, user-owned artifact bucket in eu-west-1, using an immutable key under `agent/`. Verify bucket ownership and set `CodeBucket` / `CodeKey` to that object. The template does not create this prerequisite bucket; use the same bucket in the boundary's `ArtifactBucketName` parameter.
3. Do not run the application deployment yet: first complete and approve the dedicated CloudFormation service-role policy and owner security setup. The separately reviewed owner network change set is complete, and its outputs are recorded privately. Pin the verified API ID in the app route policy and repeat live policy validation before application deployment. Subsequent SAM change sets must use the app service role, stack `neighborgear-demo`, region `eu-west-1`, both code parameters, `NetworkApiId`, `NetworkDomainName`, a private judge key (at least 24 characters), `CreditsVerified=true`, `EnableResources=true`, `Mode=simulator` and `MaxLiveRuns=10` for the first approved test. Ten is now the template default and maximum as well as the runtime hard ceiling. Review the transformed changes before execution. No application deploy command has been run here.
4. Upload `frontend/dist/` to the stack's `WebBucket` output using the participant's account. Set short caching for index.html and long immutable caching for hashed assets. Do not make the bucket public. Open the `DemoUrl` output; enter the judge creation key in the app. CloudFront forwards API calls and private sandbox headers without caching them.
5. Test sandbox creation, isolation, queue processing, reset fencing and the full simulator lifecycle in the deployed stack. Verify AgentCore permissions, direct-code execution, runtime response format, S3 artifacts and logs; offline tests cannot prove these service integrations.
6. Recheck credits and limits, then update `Mode=live` and create a **new** sandbox. Existing sessions retain their own mode. Evaluate with `scripts/evaluate.py --url https://YOUR-DEMO/api --live` and a private `NEIGHBORGEAR_JUDGE_KEY` in the local shell. Require the live release gate before recording or claiming an AI demonstration.

Deployment follows AWS's [Python direct-code packaging](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-code-deploy-python.html) and uses the [CloudFormation runtime code configuration](https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-properties-bedrockagentcore-runtime-codeconfiguration.html). SAM manages application resources and the direct-code AgentCore resource from the supplied archive.

## Recovery, bounds and limitations

- A DynamoDB document contains operational state, internal queue and idempotency metadata. Business outcomes and queue intake are conditional atomic writes. Updates larger than 340KB or a sandbox with 60 runs are rejected; reset the fictional sandbox when full.
- API intake responds without waiting for a model. SQS publish failures retain the accepted command; a five-minute sweep repairs them. The sweep uses scenario dates, never replaces them with wall time.
- SQS FIFO orders wake-ups by sandbox. Repository checks enforce predecessor order; a 75-second lease limits duplicate computation. After three automatic attempts the run fails with a retry action. Failed domain commands are not automatically replayed forever.
- API writes during a model call can invalidate its conditional commit. That computation can be billed despite having no committed effect. Model computation is not transactionally reversible.
- A persistent deployment-wide counter limits live **run attempts**, including failed attempts, to `MaxLiveRuns`, now defaulting to ten and hard-capped at ten in both the template and runtime. Each run is separately bounded to 12 tool calls / 60 seconds / 2,048 output tokens per model response. This is not a dollar cap and does not cap infrastructure costs. Never delete/reset the counter to evade the agreed allowance.
- The API is throttled to two requests/second with burst five; function concurrency is bounded. These are small-demo settings and may require coordination for multiple judges. The judge creation key is a bearer secret, not full staff authentication.
- The repository uses paginated scans for queue discovery and run lookup. This is unsuitable for public high-volume use. Keep the judge URL/key private and expire the demonstration promptly after judging.
- Sessions expire after seven days. DynamoDB TTL deletion is asynchronous, but auth and reads reject expired records. S3 business-session artifacts expire after seven days. Model conversation/private reasoning is not stored. Lambda logs retain seven days; verify/set AgentCore log retention after deployment.
- SDK Strands handoff is application-level persisted state, not native interrupt/resume. CloudFormation/runtime IAM and transport response behavior still need real AWS testing. No final independent cloud review was obtained because the delegated reviewer hit a workspace quota.

## Operator shutdown

Use the [stop-control procedure](stop-control.md) for the implemented dry-run-first CLI. Its permissions are still under [shutdown access review](../infra/iam-review/shutdown-review.md); do not attach the broad generated baseline. The instructions below describe separately approved teardown, not actions performed automatically by the CLI.

The owner network stack has a separate lifecycle. Removing the application leaves its API/stage, CloudFront distribution and retained web bucket in place. Include the network stack's exact outputs in the owner shutdown review; do not assume deleting `neighborgear-demo` disables the distribution or ends all storage/network charges. The app role deliberately cannot perform network teardown.

Disable the EventBridge schedule and SQS event source mapping; set runtime credit verification false to block further model calls; restrict/disable the judge API. Inspect pending runs and DLQ before removal. Then remove only the named stack after reviewing its resources. DynamoDB and S3 buckets use Retain policies to avoid accidental data loss and **can continue storage charges** after stack deletion. Inspect and explicitly clean those retained fictional artifacts when no longer needed. Billing alerts are supplementary, not guaranteed charge prevention.
