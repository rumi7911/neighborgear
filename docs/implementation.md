# NeighborGear implementation

Approved plan: a coordinator workspace for three fictional UK depots, 24 walking aids, six drivers, six example requests. React/TypeScript/Vite; Python 3.12 FastAPI/Pydantic/Strands; SQLite local, DynamoDB cloud; AgentCore conditional on verified credits. No real communications or personal data. All changes occur on codex/neighborgear in this new, empty project.

## Work ledger
- Backend domain/API/worker: implemented; Strands coordinator uses eight bound tools; 35 backend tests verified.
- Coordinator UI: implemented; three views, approval modal, status/activity, retry and sandbox controls.
- AWS infrastructure: implemented locally, SAM lint and ARM64 package build verified. 13 additional offline repository/runtime/handler tests. Not deployed; real service integration requires credited account validation.
- Evaluation: ten simulator cases passed including three main-demo repeats. Live gate remains false; no Bedrock calls made.
- Submission artifacts: MIT license, setup, architecture diagrams, article/write-up/video script drafted. Public repository, final live video, article publication and submission are not performed.
- Browser verification: full lifecycle, keyboard approval, reopen persistence, desktop and mobile, inventory filters verified. Mobile overflow fixed. No relevant browser console errors observed.

## Continuation notes — 7 September 2026

Independent backend review identified missing cancellation driver binding and missing request links on retries. Both reproduced in failing tests, fixed, and verified. UI now sends driver ID and offers failed-intake retry. Child workers later hit workspace quota; cloud implementation and regression verification completed in the main task. A final independent cloud review remains outstanding.

Ruling: persistent business-state handoff replaces native Strands interrupt/resume. Staff decisions still bind item/version and grant no model approval authority. Cost if wrong: implementing native interrupt/resume session management later.
Ruling: use bounded whole-sandbox DynamoDB documents and paginated recovery scans for the protected prototype. Conditional writes fence stale computations and resets. Cost if wrong: contention/repeated model computation and a future record/index migration for scale; three attempt and deployment-wide run limits bound model retries.
Ruling: after delegation became unavailable, continue safe implementation and regression testing locally; do not claim independent cloud review. Cost if wrong: defects that an additional reviewer could have caught; real AWS validation remains a release gate.

## Design fidelity and QA notes

The generated concept in `docs/design/workspace-concept.png` informed the warm-neutral/teal palette, left navigation, three metrics, request table and four-stage guide. Actual counts/statuses come from API data instead of the concept's placeholder values. The decorative walking-aid illustration is replaced by lightweight purpose-labelled icons; this does not affect workflows. Desktop inspected at 1440×1000; mobile at 390×844. Table rows scroll within their panel on mobile, not the page. An absolutely positioned accessibility label originally expanded page width to 650px; containing it within the table panel restored document width to 390px. Keyboard Tab/Space/Enter completed the staff-approval dialog; console inspection showed no relevant errors or warnings. Broader browser/screen-reader coverage is still unverified.

Ruling: use the existing empty project on a feature branch instead of creating another checkout of an unborn repository. No existing user code exists to isolate.
Ruling: do not perform account registration, agree to terms, publish, deploy or spend credits without verified user-owned account access and credits. Prepare reproducible artifacts locally.
Ruling: development mode uses an explicitly labelled deterministic simulator. Live mode requires Strands with Bedrock; live calls are disabled until credit verification. Never claim fixture output as model output.

## Shared HTTP contract (root /api)
JSON fields snake_case. Dates ISO yyyy-mm-dd. Requests authenticated with X-Sandbox-Token (opaque secret returned only on creation). Persist token locally in browser. No URL-supplied session IDs trusted.
- POST /sessions => {token, session_id, mode, now}; seed 3 depots, 24 items, 6 drivers, 6 requests.
- GET /snapshot => {session:{id,now,mode}, depots:[],equipment:[],drivers:[],requests:[],messages:[],events:[],runs:[]}.
- POST /requests {name,text,equipment_type?,min_height_cm?,max_height_cm?,user_weight_kg?,needed_by?,return_by?,area?,window_start?,window_end?} => {request_id,run_id,event_id}.
- POST /requests/{id}/clarify (same optional specification fields) => {run_id,event_id}.
- POST /requests/{id}/approve {equipment_id,proposal_version} => {run_id,event_id}.
- POST /requests/{id}/events {type:'cancel_driver'|'confirm_delivery'|'return_equipment'|'pass_inspection'|'fail_inspection',...} => {run_id,event_id}.
- POST /runs/{id}/retry => {run_id,event_id}.
- POST /clock {days:1..30} => {run_id,event_id}.
- POST /reset => reset caller's data, same token.
- GET /health => {status,mode}.
All writes accept Idempotency-Key. Snapshot can contain detail; UI derives request view from it. Poll every 1.5s while runs queued/running, otherwise 5s. Errors {detail:string}.

## Shared records
Equipment {id,name,type:'walking_frame'|'rollator',depot_id,min_height_cm,max_height_cm,max_weight_kg,status:'available'|'reserved'|'on_loan'|'inspection'|'retired',inspection_passed:boolean,inspected_at?,loan_until?}.
Depot {id,name,area,address}; Driver {id,name,capacity,areas:string[],window_start,window_end}.
Request {id,name,text,equipment_type,min_height_cm,max_height_cm,user_weight_kg,needed_by,return_by,area,window_start,window_end,status:'new'|'needs_information'|'awaiting_approval'|'reserved'|'delivery_scheduled'|'needs_attention'|'on_loan'|'inspection'|'completed',missing_fields:string[],candidates:[{equipment_id,eligible,reasons:string[]}],proposal_version:number,equipment_id?,driver_id?,delivery_date?,cancelled_driver_ids:[],created_at}.
Message {id,request_id,recipient,subject,body,created_at,simulated:true}; Event {id,request_id?,type,summary,created_at}; Run {id,request_id?,status:'queued'|'running'|'succeeded'|'failed',error?,created_at}.
Approvals, reservations, transport assignments and loans are persisted domain records in addition to visible request projection.

## Acceptance
Full request/clarify/match/approve/reserve/schedule/cancel/reassign/deliver/remind/return/inspect lifecycle; reject unsafe/incompatible inventory; concurrent reservations and transport capacity checks; duplicate events/messages; restart recovery; sandbox isolation; deadline/window constraints; live model time/tool bounds. Real evaluation separately records whether run used Bedrock and never silently falls back.

## Review boundaries
Backend owns backend/** and pyproject.toml, uv.lock. Frontend owns frontend/**. Cloud/docs own infra/**, docs except this ledger, scripts cloud/evaluation scaffolding; root integrates README and scripts/dev. Backend supplies repository transaction API for local SQLite and cloud adapter, and process_run entrypoint to cloud worker. Frontend consumes only shared HTTP contract above.
