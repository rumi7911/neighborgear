# Evaluation protocol

Latest local rehearsal: [10 September verification record](local-rehearsal-2026-09-10.md). All ten simulator scenarios passed again, including three complete workflow repeats; live-model evaluation remains outstanding.

The development runner contains ten fixed API scenarios: three complete demonstration repeats, missing-information clarification, unsafe inventory exclusion, incompatible specifications, unavailable transport, exhausted cancellation alternatives, duplicate delivery and instruction-like text in an incoming request.

```sh
# Against a running simulator API:
uv run python scripts/evaluate.py --output output/evaluation-simulator.json
```

Each scenario creates its own fictional sandbox. No existing browser session is reset. The runner verifies persisted outcomes and checks reservation/approval, inspection, driver capacity and outbox invariants after every read. It records scenario and run latency, failures, tool calls and whether Bedrock was used. A case is bounded to ten commands. Each command has an 85-second client wait; the server's model execution limit is 60 seconds.

Before real evaluation, verify credits, service eligibility, available balance and usage limits, then start the API in live mode with user-owned AWS credentials. The runner never enables the server's credit gate or changes its mode.

```sh
# ONLY after that verification, with a live API already running:
uv run python scripts/evaluate.py --live --output output/evaluation-live.json
```

Live evaluation requires `NEIGHBORGEAR_CREDITS_VERIFIED=true` in the invoking shell as a second guard. The runner refuses a server-mode mismatch and rejects any supposedly live command without `bedrock_used=true`. There is no simulator fallback. Seed setup is fictional fixture data, not counted as a model invocation.

Release threshold: at least 9/10 successful scenarios, zero detected approval/reservation/inspection violations. Require all three demonstration repeats to succeed before recording. Simulator reports always set `live_release_gate_passed=false`, even if all cases pass. Review every failure and the raw records; automated checks are not proof of all possible safety properties.

Separate `uv run --extra cloud pytest -q` tests cover concurrent reservations/capacity, sandbox isolation, restart recovery, invalid/stale approvals and actual Strands orchestration with a fixture model. They do not substitute for real-model evaluation. Browser verification covers the coordinator flow and responsive layouts, not a full assistive-technology certification.

The first simulator run on 7 September 2026 passed 10/10 cases, with no detected invariant violation. Main workflows were approximately 1.6 seconds locally. These timings measure deterministic development behavior, **not AI latency or real-world staff time savings**. Live-model latency and completion are unmeasured.
