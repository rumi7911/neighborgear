# NeighborGear

From an equipment request to a confirmed delivery—with the follow-up handled.

A coordinator-facing hackathon sandbox for a fictional network of equipment-reuse charities. **Not a medical service.** Three depots, 24 walking frames and rollators, six volunteer drivers and six example cases. Every identity, location and event is fictional. Messages remain in an internal simulated outbox.

## Run locally

Requirements: Python 3.12 through [uv](https://docs.astral.sh/uv/), Node.js 22.12+ and npm. Dependencies are pinned in `uv.lock` and `frontend/package-lock.json`.

```sh
bash scripts/dev.sh
```

Open **http://127.0.0.1:5173**. API documentation: http://127.0.0.1:8000/docs. Stop with Ctrl-C. SQLite data survives process restarts in `backend/data/neighborgear.sqlite3` (git-ignored). Each browser has an isolated sandbox identified by a private bearer token in local storage. Use Demo controls → Reset sandbox to reset only that sandbox.

To run components separately:

```sh
uv sync --frozen --python 3.12
uv run uvicorn backend.app:app --host 127.0.0.1 --port 8000
# In another terminal:
npm --prefix frontend ci
npm --prefix frontend run dev
```

The default **simulator** parses explicitly stated supported facts and runs the real safety/lifecycle rules without a model. It is a development aid, **not evidence of a working AI demonstration**. Live Strands/Bedrock evaluation and cloud deployment require verified credits and account access; neither is claimed here.

## Try the workflow

1. Create a new request with fictional name and paste:

   > Please lend a rollator in North, handle height 80-95 cm, weight 85 kg. Delivery 2026-09-06 and return 2026-09-12. Available 10:00 to 16:00.

2. Review the eligible items and the exclusion reasons. Tick the staff suitability confirmation and approve a match. Availability is rechecked inside the reservation transaction.
3. Simulate driver cancellation. Inspect the replacement assignment and correspondence in Activity.
4. Confirm delivery, advance the scenario clock 14 days, and inspect the return reminder.
5. Record return. Equipment is quarantined; only an inspection pass restores availability. A failure retires it.

The sandbox intentionally starts on **5 September 2026**, regardless of the actual date. Reset before repeating this script. Arthur's seeded case demonstrates missing weight; Theo's demonstrates no compatible inventory.

## Verification

```sh
uv run --extra cloud pytest -q
npm --prefix frontend test
npm --prefix frontend run build
uv run cfn-lint infra/template.yaml
```

Tests cover the main lifecycle, missing specs, safety/approval gates, competing reservations and capacity, idempotence, isolation and worker recovery. Automated fixture tests do not measure live model quality. The release gate is ten fixed real-model scenarios, at least nine successful outcomes and zero approval/reservation/inspection violations.

## Boundaries and operations

- Equipment suitability is a staff decision based on supplied specifications. The model cannot approve itself, waive inspection or select medical equipment on clinical grounds.
- Mutations enqueue durable work and return a run/event ID. The browser polls for persisted outcomes. Closing the page does not cancel a run.
- The SQLite reference implementation serializes writes. This is a small demonstration, not a production clinical or logistics system.
- No NHS connection, live messages, payments, routes, real recipients or charity partnership.
- Never expose the development server publicly. A judge-facing deployment needs a private creation key, HTTPS, request limits and verified credit coverage.
- Environment variables are not automatically loaded from `.env`; export them in your shell or configure the deployment environment. Never commit credentials.

## Project guide

| Area | Files |
|---|---|
| Interface | `frontend/src/` — Requests, Request detail, Equipment |
| API and background worker | `backend/app.py`, `backend/worker.py` |
| Safety rules and fictional data | `backend/domain.py` |
| Persistence | `backend/store.py` |
| Model adapter | `backend/agent.py` |
| Capability-bound Strands tools | `backend/coordinator.py` |
| Conditional AWS implementation | `infra/`, `docs/deployment.md` |
| Architecture and live evaluation | `docs/architecture.md`, `docs/evaluation.md` |
| Tests | `backend/tests/` |
| Implementation record | `docs/implementation.md` |
| Submission draft / video script / article | `docs/submission.md`, `docs/demo-script.md`, `docs/build-story.md` |

MIT licensed. No real-world time-savings claims have been validated. Public repository publication, the final live-model video and submission must be completed using the participant's own accounts.
