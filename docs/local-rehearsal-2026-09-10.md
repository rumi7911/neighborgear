# Local release rehearsal — 10 September 2026

> Update, 11 September 2026: AWS has applied the Ireland Lambda concurrent-execution quota of 1,000, with utilization still at zero. A fresh Billing check found $120 remaining and $0 used, and the AgentCore console showed no runtime resources. These clear the quota and planning-cost gates; they do not activate deployment. Non-root tooling, live IAM validation, explicit deployment approval and the first paid model-invocation approval remain outstanding.

Completed while the Ireland Lambda quota request is pending. No AWS deployment, account changes or model invocation was performed by this rehearsal.

## Fresh results

| Check | Result |
| --- | --- |
| `uv run --frozen --extra cloud pytest -q` | 131 passed, three dependency deprecation warnings |
| `npm --prefix frontend test` | Three transport tests passed |
| `npm --prefix frontend run build` | TypeScript and Vite production build passed |
| Ten API simulator scenarios | 10/10 passed, no detected invariant violations |
| Three main workflow repeats | All passed, 1.602–1.610 seconds locally |
| Live model release gate | False; not tested by this rehearsal |

The API evaluation used port 8011 and a new temporary SQLite database, with simulator mode explicitly selected and the credits gate explicitly false. Existing browser sessions and their database were not reset. The temporary API was stopped after evaluation.

Machine-readable local evidence: `output/evaluation-simulator-2026-09-10.json` (git-ignored). These timings measure deterministic simulator behavior, not model latency or coordinator time savings. No new browser/accessibility inspection or cloud integration test was performed.

## Remaining release gates

1. Resolve the quota request and verify the actual applied Lambda limit. A pending request is not an increase.
2. Finish reviewed deployment permissions, credit/service eligibility and cost checks, and verify cloud stop controls before enabling resources.
3. Run the ten fixed scenarios with the real model, retaining measured completion, latency and failures. Require at least 9/10, all three main repeats, and zero detected approval/reservation/inspection violations.
4. Rehearse the coordinator UI against the verified live deployment, then record the four-minute video using `docs/demo-script.md`.
5. Publish the repository, video and build article using owner-approved destinations; fill their real URLs into the submission. Existing documents are drafts, not evidence of publication.

Existing independent work can continue without quota approval: polish the recording script and testing instructions, review the repository for publication, and rehearse the explicitly labelled simulator. None substitutes for the real-model release gate.
