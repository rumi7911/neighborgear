# AWS Safe First Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish non-root deployment access and verifiable usage controls, then run one bounded real-model case without authorizing personal spending.

**Architecture:** Separate owner-controlled security bootstrap, a deployment role, a CloudFormation service role, and workload execution roles. Deploy the existing SAM application in simulator mode first; enable real Nova Lite only after security, cost and shutdown checks pass.

**Tech Stack:** Existing Python/FastAPI/Strands, SAM/CloudFormation, IAM/STS, AWS Budgets, DynamoDB, Lambda/SQS, AgentCore, S3/CloudFront, EventBridge Scheduler.

**Spec:** User-approved NeighborGear MVP in this task; `docs/implementation.md`, `docs/deployment.md`, and `docs/credits-preflight.md`. This plan supersedes those documents' historical claims that no credits/account have been verified; it does not supersede their deployment gates.

## Global Constraints

- Planning only until execution is authorized. Do not create roles, send alerts, upgrade plans, deploy, or invoke models while writing this plan.
- AWS credits only. No personal spending, paid-plan upgrade, Organization/Control Tower setup, subscriptions, paid support, or third-party models.
- Region: eu-west-1; model: `eu.amazon.nova-lite-v1:0`. Its current EU routing destinations are Ireland, Paris, Frankfurt and Stockholm. Scope model permissions to those verified destinations; recheck before applying.
- Fictional data only. Private judge key; no credentials or billing screenshots in Git, frontend assets or chat.
- Confirmed 7 September 2026: $100 active Free Tier credit, $0 reported usage, credit expiry 5 September 2027; Free plan active until 5 March 2027. Console balances are delayed estimates. Root is the plugin's current identity.
- Credit list explicitly includes Bedrock, AgentCore, Lambda, API Gateway, DynamoDB, S3, SQS, CloudFront, CloudWatch and CloudFormation. It lists CloudWatch Events; verify EventBridge Scheduler's billing coverage specifically before deployment rather than assuming a legacy name proves coverage.
- Nova Lite availability and EU inference profile were verified; AgentCore listing succeeded. These checks do not prove Create/Invoke permissions or usable quotas.
- No automatic delegation is required. Independent review is desirable before IAM application; never claim it occurred if unavailable.

## Proposed allowance and gates

| Stage | Allowance / stop rule |
|---|---|
| First deployment and smoke test | $5 gross-cost planning ceiling, not an AWS-enforced dollar cap |
| Initial development and evaluation | $20 cumulative project target; stop and request approval before expanding |
| Credit reserve | Target at least $80 remaining; stop if observed balance falls below it or usage is unexplained |
| First live case | At most 10 deployment-wide live attempts, including failures and retries |
| Individual run | Existing 60-second deadline, 12 tool calls, 2,048 output tokens per model response |
| First deployment lifetime | Six-hour test window, then disable new work unless an extension is approved |

The $5 stage allowance sits inside the $20 target. Neither is a guaranteed bill limit. Do not equate 10 run attempts with 10 model calls: each tool loop can cause several model responses. Infrastructure, retries, scans, transfer and logging cost money even with simulator mode enabled.

## Task 1: Confirm prerequisites and prepare the non-root access design

**Files:** Update `docs/credits-preflight.md`; create `infra/security-bootstrap.yaml`; update `docs/deployment.md`. Keep account-specific values outside source control.

**Interfaces:** Bootstrap outputs `DeployerRoleArn`, `CloudFormationRoleArn`, `WorkloadBoundaryArn`, `ArtifactBucketName`. Application deployment consumes these rather than a root session.

- [ ] Recheck plan/balance with `GetAccountPlanState`; inspect the credit details if eligibility changed. Resolve Scheduler credit coverage and Free-plan availability using official AWS documentation/support before enabling it. Do not substitute paid access.
- [ ] Read-only inventory existing human/federated identities and MFA status. Prefer an existing suitable non-root identity; never assume one exists. If absent, present the exact new identity/trust setup for owner approval. Do not create an AWS Organization to obtain sign-in.
- [ ] Propose owner-controlled bootstrap of `NeighborGearDeployer` and `NeighborGearCloudFormation`. Use a named human/federated principal and short-lived sessions with MFA appropriate to that identity type; no new static access keys. Do not claim a root session assuming a role solves the underlying root-credential risk.
- [ ] Limit Deployer to this project's artifact uploads, CloudFormation change sets/stack operations, diagnostics, and passing only the CloudFormation role. No generic IAM administration, role creation, billing upgrades, or direct model invocation.
- [ ] Limit CloudFormation to this project's supported resources. Require a fixed permissions boundary on all roles it can create; prevent changing/removing the boundary or altering the deployer/bootstrap roles. Restrict `iam:PassRole` to the relevant workload roles and receiving services. Scope global-service exceptions separately from eu-west-1 permissions.
- [ ] Review the complete trust and identity policies before any bootstrap. Owner approval is required to create security-sensitive access. If plugin role switching is unsupported, plan an approved short-lived local CLI session instead; verify `GetCallerIdentity` is non-root before deployment.
- [ ] **Gate:** no execution until the sign-in path, exact principals and policies are reviewed. Verify both permitted project actions and denied out-of-project/admin/other-model actions; policy simulation is supporting evidence, not proof of all service behavior.

## Task 2: Generate and review workload policy baselines offline

**Files:** Review `infra/template.yaml`; create reviewed baseline artifacts under `infra/iam/` and `infra/tests/test_security_controls.py`.

**Interfaces:** Application roles consume `WorkloadBoundaryArn`; explicit API, worker, sweep, scheduler and AgentCore roles replace or constrain SAM-generated roles. Outputs preserve `DemoUrl`, `WebBucket`, `RuntimeArn`.

- [ ] Use the AWS IAM skill's Autopilot path for Python source, not hand-generated runtime policy guesses. During implementation, verify the tool version and record/pin the version used. Proposed baseline command (not run during planning):

```sh
uvx iam-policy-autopilot@latest --version
uvx iam-policy-autopilot@latest generate-policies \
  'backend/agent.py' \
  'infra/repository.py' \
  'infra/dispatch.py' \
  'infra/handlers.py' \
  'infra/runtime.py' \
  --region eu-west-1 --account "$NEIGHBORGEAR_ACCOUNT_ID" \
  --service-hints dynamodb s3 sqs bedrock bedrock-agentcore \
  --pretty
```

Set `NEIGHBORGEAR_ACCOUNT_ID` privately from verified STS output, never an invented value. Do not use `--upload-policies`. Review SDK wrappers/Strands dependencies that static analysis cannot resolve; follow the tool's explain workflow and document unresolved calls before applying policies.

- [ ] For bootstrap and deployment APIs, use the current AWS Service Authorization Reference to derive deployment permissions. Do not confuse API operation names with IAM action names or copy broad generated runtime policies to the deployer.
- [ ] Scope model permissions to Nova Lite's verified EU profile and destination model ARNs. Scope data/log resources to the project. Validate trust conditions against the specific service's supported context keys; do not indiscriminately add unsupported conditions.
- [ ] Write failing structural policy tests rejecting `AdministratorAccess`, unrestricted `iam:PassRole`, a missing boundary on any created role, and model ARNs outside the approved profile/destinations. Implement the template changes, rerun until passing, and inspect the transformed SAM template for generated roles as well as handwritten roles.
- [ ] Run `uv run --extra cloud pytest -q` and `uv run cfn-lint infra/template.yaml infra/security-bootstrap.yaml`; commit only reviewed local source changes. Never commit credentials, generated account-specific evidence or package archives.

## Task 3: Install cost visibility and a tested application stop control

**Files:** Create `infra/cost-controls.yaml`, `infra/tests/test_cost_controls.py`, `scripts/stop-demo.py`; modify `infra/template.yaml`, `infra/runtime.py`, `infra/repository.py`, `infra/handlers.py`, and their existing tests as necessary for the shared controls.

**Interfaces:** Cost stack requires an owner-approved `AlertEmail`. A protected control record has `enabled: bool` and `expires_at: UTC timestamp`. Every intake, sweep and runtime entry checks it. `scripts/stop-demo.py` defaults to read-only reporting; an explicit apply option affects only the verified named stack and control record.

- [ ] Propose account-wide $20 monthly COST budget to catch untagged costs, with actual dollar alerts at $1, $5, $10 and $20, plus forecast $20. Configure `IncludeCredit=false`, `IncludeRefund=false`, and unblended/non-amortized costs. Include support/tax/recurring costs rather than hiding them. Monthly alerts do not implement the cumulative project target; maintain a separate cumulative ledger across months.
- [ ] Obtain the alert email before creating subscribers. No inferred email, budget reports, automatic Budget Actions, or scheduled assistant monitoring. Forecasting may be unavailable on a new account; actual alerts and app controls must stand independently.
- [ ] Unit-test the budget template: USD20 amount, credits/refunds excluded, four ACTUAL absolute thresholds and one FORECASTED threshold, owner-supplied subscriber. Validate the template before applying it.
- [ ] Add tests proving disabled/expired controls reject new work and model calls, cannot be changed by sandbox APIs, survive sandbox resets, and cannot be bypassed by creating another session. Fail closed if the control cannot be read. A runtime check alone is insufficient because API/Sweep activity can still accrue costs.
- [ ] Add concurrency tests proving the existing shared attempt counter accepts no more than 10 live attempts across concurrent sandboxes, counts failed attempts, and is not replenished by retries/reset. Preserve the current per-run bounds. Do not delete the counter to replenish the allowance.
- [ ] Implement the expiry/stop checks and a dry-run-first shutdown command that verifies account, stack ownership and exact resource IDs. Its apply mode disables the reminder schedule and SQS mapping, closes intake and disables new model work. Report in-flight work and retained storage; do not promise instantaneous cancellation or zero residual charges.
- [ ] Test the shutdown command with fake AWS clients, including wrong-account/foreign-stack rejection and idempotent repeated stop. Make the six-hour expiry explicit before provisioning. Owner must be present for the initial test window; no unattended deployment until shutdown is verified.
- [ ] **Gate:** review all-service projected costs using current eu-west-1 pricing, six-hour duration, 10 live attempts and pessimistic loop/token/retry assumptions. Account for retained storage, the external artifact bucket and delayed billing. If projected first-stage costs exceed $5 or coverage is uncertain, stop before deploying.

## Task 4: Deploy the protected simulator and prove shutdown

**Files:** Update `docs/deployment.md`; deployment parameters remain private. No production data.

- [ ] Request execution approval for the exact bootstrap policies, email alerts, public HTTPS/static demo endpoint protected by the judge key, and the $5 initial test allowance. Public assets are not secret; judge credentials and data must remain protected. Never silently upgrade the Free plan if deployment is denied.
- [ ] Bootstrap approved access/cost controls, confirm non-root identity, and verify read-back of roles, boundaries and budget configuration. Do not create unrelated resources or use administrator policies to work around denied operations.
- [ ] Rebuild the immutable Linux ARM64 artifact; create the private project artifact bucket through the bootstrap template if needed. Tag project resources `Project=NeighborGear` where supported. Explicitly account for resources outside the application stack.
- [ ] Create/review the SAM change set with the dedicated CloudFormation role. Start `Mode=simulator`, `MaxLiveRuns=10`; keep model execution disabled separately until Task 5. Review resource replacements, generated IAM and deletion policies before applying.
- [ ] Verify real cloud simulator lifecycle, queue response handling, AgentCore packaging, isolated sessions and seven-day log/data retention. Inspect Lambda quotas before assuming reserved concurrency is available. No model calls during this stage.
- [ ] Exercise disable/expiry in the cloud; verify new work is refused and schedules/mappings are stopped. Verify re-enabling requires the operator and preserves the attempt counter. Re-enable only within the approved test window for Task 5.

## Task 5: One live case, then pause for measured review

**Files:** Use `scripts/evaluate.py` as the scenario reference; do not run its ten-scenario live suite yet. Save private observations outside Git; update `docs/evaluation.md` with redacted measured results after testing.

- [ ] Recheck credits/plan and current costs; verify model access under the actual runtime role, not root. Confirm 10 is the total global live-attempt allowance and inspect its current consumption.
- [ ] Enable live mode and the model gate for one new fictional sandbox. Exercise request intake, staff approval, reservation/transport, cancellation/reassignment, delivery, reminder, return and inspection. Stop after this one case or the first unexpected failure; no automatic operator retries.
- [ ] Record per-run latency, actual model usage where available, failures, immutable approval/reservation/inspection records, and remaining attempt allowance. Model usage estimates must be labelled separately from posted AWS billing.
- [ ] Disable new work immediately after the smoke test and verify the stop state. Wait for billing to post before expanding; do not interpret $0 immediately after testing as free usage.
- [ ] Report result and seek approval for a revised total attempt allowance before running the ten live evaluation scenarios. Retain the original release requirement: at least 9/10 successes, zero invariant violations and all three main-demo repeats successful.
- [ ] Choose the judge-access expiry from the official judging schedule before public submission. Do not use submission day as a guessed shutdown date. Retained DynamoDB/S3 data and artifact storage require a separately reviewed cleanup after judging; no automatic destructive cleanup.

## Self-review and execution handoff

### Execution checkpoint — 7 September 2026

Read-only account discovery is complete: credits remain $100, root MFA is enabled, no root access keys, no IAM users or suitable deployment roles. Lambda concurrency is 10; current positive reservations require quota/architecture review. No security identities, budgets, resource stacks or model calls have been created.

The independent offline cost-template portion of Task 3 is implemented: `infra/cost-controls.yaml`, three regression tests and CI lint coverage. All three tests were observed failing before the template existed, then passed; cfn-lint reported no errors/warnings. Alert enablement stays false and no email is assumed. Shared stop/expiry controls and shutdown tooling are not implemented yet.

Task 1's external access gate remains closed. Stop before applying IAM or deploying. Required user input: alert recipient. Required reviewed design: a new non-root human sign-in path and scoped deployment policies; no automatic Organization setup or paid-plan upgrade. Independent offline cost preparation did not require this missing identity.

Subsequent checkpoint: the owner supplied the alert recipient. Created the notification-only `NeighborGear-gross-account-spend` budget through the AWS Budgets API and verified its configuration, HEALTHY state, all five subscribers and absence of actions. This account-level billing operation used the existing connection without changing its permissions; application deployment still requires non-root access. The local cost template is not the live resource's manager: avoid deploying a duplicate. Recipient details remain outside Git. No paid model or application infrastructure was enabled, and no email-delivery test was performed.

- [x] Covers credit evidence, non-root access, role boundaries, model/service eligibility, gross-cost alerts, cumulative allowance, application limits, expiry, simulator deployment, one live test and shutdown.
- [x] Separates proposed dollar allowances from enforced attempt controls and delayed billing.
- [x] No AWS mutation, model invocation, new identity or notification was authorized by this planning request.
- [ ] Execution input: alert email and approval of the exact access bootstrap after read-only identity discovery.
- [ ] Remaining technical gates: Scheduler coverage, Free-plan deployment/quotas, scoped policy validation, complete cost estimate, cloud integration and shutdown tests.

Recommended execution: inline checkpoints in this task; optional independent reviewer if available. Stop after each security/cost approval gate instead of treating the plan as blanket authorization.

Execution checkpoint — 9 September 2026: implemented the dry-run-first `scripts/stop-demo.py` tool after observing failing tests. It verifies same-account Ireland stack/resource ownership and non-root identity, closes the owner control gate, preserves schedule configuration while disabling it, disables the queue mapping and reports partial/asynchronous outcomes. Repeated stops are idempotent. Sixteen new offline tests pass; full Python suite 131 passed with three existing warnings. No live AWS calls or mutations were made in this step. Task 3 remains open for scoped shutdown permissions, the approved UTC window and real shutdown/cost validation; this is not authorization to provision resources.

## Sources verified while planning

Execution checkpoint — 8 September 2026: Safari access restored; plugin still reports reauthentication required, so no API quota refresh succeeded. Created `NeighborGearOperator` in the verified account through Safari, without console credentials, policies, groups or access keys. Left its Security credentials page open for owner password/MFA setup. No deployment role, quota increase, model invocation or application resource was created. This is only the human identity bootstrap; it does not satisfy the non-root deployment-access gate yet.

- [Budget credit inclusion defaults](https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_budgets_CostTypes.html): credits are included by default; exclude them for gross-spend visibility.
- [Budget update delays](https://docs.aws.amazon.com/cost-management/latest/userguide/bcm-lite-use-budget.html): alerts are delayed and cannot guarantee cost containment.
- [CloudFormation service roles](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-iam-servicerole.html): scope both the service role and who may operate the stack.
- [Scoped PassRole permissions](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_passrole.html): do not permit passing arbitrary roles.
