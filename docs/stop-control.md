# Application stop gate and shutdown tool — locally verified

All deployed entry paths now read one owner-controlled DynamoDB record using a strongly consistent read: API intake, SQS worker, scheduled sweep and AgentCore entry. Queue publishing and live-attempt admission recheck it too. There is no cached enabled state and no automatic initialization.

The separate `neighborgear-demo-controls` table belongs to the disabled owner security bootstrap. Workload roles and their boundary permit **GetItem only** on it; the application service-role draft cannot create or modify it. The record has key `pk=CONTROL`, `enabled` as a boolean, and `starts_at` / `expires_at` as UTC Unix seconds. Enabling and choosing timestamps are owner actions requiring explicit approval, not sandbox controls.

Access is allowed only when enabled is exactly true, the timestamps are finite, the duration is positive and at most 21,600 seconds, and current wall-clock time is within `[starts_at, expires_at)`. Missing configuration, missing records, read errors, invalid windows and expiry all stop new work. Scenario-clock controls cannot extend this window. The table has no TTL deletion: a stopped record must not disappear and trigger accidental reinitialization. Sandbox reset and process restart neither rewrite nor extend the record.

Stopped API requests receive HTTP 503 before intake. Sweep returns without scanning/publishing. The SQS worker acknowledges wake-ups without invoking AgentCore; durable commands remain in DynamoDB for an explicitly approved recovery. AgentCore returns `stopped` before claiming work. A stop is not a claim that every pending command failed or was deleted.

## Ten-attempt admission limit

The existing deployment-wide `BUDGET` record uses a conditional atomic update. Both the template default/maximum and runtime code now cap admissions at ten. A caller requesting a larger value cannot raise that ceiling. Invalid limits issue no ticket. A lower configured allowance remains supported.

The counter is consumed before live model work, never refunded on failure, and never reset by another sandbox, sandbox reset, process restart or retry. It has no automatic expiry. Concurrent admission tests accept ten tickets total. This is an upper bound on admitted live **run attempts**, not ten model API calls and not ten successful outcomes. Ambiguous infrastructure failures may consume allowance without useful work. Existing 60-second, 12-tool-call and per-response output limits remain unchanged.

## Dry-run-first shutdown command

`scripts/stop-demo.py` is implemented and tested offline. It requires an explicit expected account, exact application and owner-security **stack ARNs** (including stack IDs), and an approved non-root profile. Ireland is fixed. Default execution performs reads only; `--apply` is the only mutation switch. No live execution has been performed.

```sh
uv run python scripts/stop-demo.py --help
uv run python scripts/stop-demo.py \
  --profile APPROVED_NON_ROOT_PROFILE \
  --account-id VERIFIED_ACCOUNT_ID \
  --app-stack-arn VERIFIED_APPLICATION_STACK_ARN \
  --owner-stack-arn VERIFIED_SECURITY_STACK_ARN
```

These are placeholders, not deployable identifiers. Keep the resulting report private. Only after owner authorization and inspection of the dry-run targets, repeat the same command with `--apply`.

The tool checks STS identity, stable CloudFormation stacks and paginated resource ownership, the exact control table, reminder group/target/role, and queue mapping's function/source. Missing or ambiguous resources, root credentials, mismatched accounts and stacks being updated cause refusal before writes. All targets are rechecked before apply. A missing CONTROL record already fails closed in the app; this tool refuses to initialize it.

Apply closes `CONTROL.enabled` first with a conditional update and consistent read-back, preserving the window and all other records. It then disables the schedule while preserving its configuration and requests mapping disablement. Scheduler updates replace configuration, so copying writable fields from GetSchedule is essential. [AWS UpdateSchedule reference](https://docs.aws.amazon.com/scheduler/latest/APIReference/API_UpdateSchedule.html)

The final read-back distinguishes `stopped` (gate and both triggers observed disabled) from `pending` (including Lambda's asynchronous `Disabling` state). Exit codes: 0 for a successful read-only preview or confirmed stop, 1 for refusal/error, 2 for pending. Re-run read-only to inspect; repeat apply when appropriate. Repeated stops do not rewrite disabled resources. Partial failures report confirmed progress and never reopen the gate; a timed-out write may have applied even when its confirmation is absent. No automatic rollback, permission expansion, resource deletion or model invocation occurs.

This is not an atomic lock against a concurrent owner/deployment changing configuration. Do not deploy, edit schedules or re-enable controls during shutdown. Stable-state checks reduce but cannot eliminate that race. The script intentionally refuses failed/transitioning stacks rather than guessing recovery targets; those require owner inspection.

Access review remains required: STS identity and CloudFormation stack/resource reads; GetItem/UpdateItem on the exact owner control key; GetSchedule/UpdateSchedule on the exact schedule; GetEventSourceMapping/UpdateEventSourceMapping on the exact mapping; and any required Scheduler PassRole authorization restricted to the existing role/service. No new grants are attached by this tool, and the app's read-only control grants are unchanged. Live permission and shutdown validation remain deployment gates.

## What is not complete

- This is an application stop gate, **not physical AWS resource shutdown**. Lambda invocations and control reads, EventBridge schedules, CloudFront requests and retained storage can continue to incur charges after expiry.
- A call already admitted may finish; the check cannot atomically cancel distributed in-flight computation. Expiry is not an instantaneous cancellation or guaranteed dollar cap.
- The shutdown tool has only been exercised against fake clients and Moto DynamoDB. Actual AWS permissions, trigger transitions and residual-cost observations are unverified. No live shutdown command has been run.
- Owner-only control initialization/update permissions and the first approved six-hour UTC window must be reviewed before deployment. The scaffold creates an empty table; it does not seed an enabled record. Until the owner configures it, the cloud application fails closed.
- Live IAM enforcement, concurrent admission against real DynamoDB, actual stop/recovery and residual-cost observations remain untested in AWS. No billing balance was refreshed by these local tests.

The existing API/Runtime record-table grants are not an IAM-level immutability guarantee for BUDGET against compromised deployment/runtime code. Normal sandbox operations cannot replenish it, but the complete access review must also consider protection of that counter. No general record-edit endpoint is exposed.

Verification: `uv run --extra cloud pytest -q infra/tests/test_stop_controls.py` exercises disabled/expired/invalid/missing/unreadable controls, API/worker/sweep/runtime gates, restart/reset persistence, concurrent admission, failed-attempt consumption and invalid limits. These use mocked AWS infrastructure, never a real model.

`uv run --extra cloud pytest -q infra/tests/test_stop_demo.py` covers dry-run, ownership rejection, idempotency, preserved configuration/data, partial failures, asynchronous disablement and CLI behavior. Full Python suite on 9 September 2026: **131 passed**, three existing dependency deprecation warnings. No frontend or infrastructure templates changed in this step.
