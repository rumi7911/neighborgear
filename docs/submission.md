# NeighborGear

**Tagline:** From an equipment request to a confirmed delivery—with the follow-up handled.

**Track:** Good Neighbor Agents

**Public source:** https://github.com/rumi7911/neighborgear

## Inspiration
Community equipment reuse depends on many small handoffs: finding the right item, confirming suitability, arranging collection, responding to cancellations, and bringing equipment back into circulation. NeighborGear explores how an agent can help a coordinator carry those handoffs through to completion.

## What it does
A coordinator enters an equipment request. NeighborGear asks for missing specifications, compares stock across three fictional depots, presents matches for staff review, and coordinates a loan. When a driver cancels, the system looks for a feasible replacement. It records the delivery, schedules a return reminder, and keeps returned equipment unavailable until staff record an inspection pass.

## How it is built
React and TypeScript provide the coordinator interface. Python, FastAPI, and Pydantic implement the API and domain constraints. The Strands Agents SDK provides the live agent integration, with focused tools operating on persisted records. A deterministic simulator supports development and clearly identifies itself throughout the interface.

## Demonstration boundaries
All people, equipment records, depots, dates, and messages are fictional. Correspondence is stored in an internal outbox; no external recipient is contacted. The system does not prescribe equipment or certify inspection. Staff decisions are modelled explicitly. Cloud deployment and live-model evaluation depend on verified AWS credits. Do not describe them as completed until the recorded deployment and evaluation evidence confirms completion.

## What we learned
Reliable coordination requires more than a plausible answer: reservations must remain consistent, repeat events must be harmless, and a handoff must survive an interruption. The demo is designed to make those properties visible.

## Evaluation and impact
The evaluation suite measures workflow completion, errors, and latency. Time savings, financial savings, and improvements to real equipment access remain hypotheses until tested with an actual charity. Do not substitute simulated counts for real-world impact.

## Submission checklist
- [x] Verify entrant eligibility and registration; obtain AWS Builder ID.
- [x] Publish repository, README, MIT licence, architecture diagram, and reproducible setup.
- [ ] Verify live model execution and retain evaluation evidence.
- [ ] Make a public video of at most five minutes showing the working project.
- [ ] Supply testing instructions and the verified demo URL if deployed.
- [ ] Publish the build article and include its actual URL.
- [ ] Confirm every required Devpost field before submitting.

## Status on 12 September 2026

- Devpost project `NeighborGear` exists as a **draft**. It has not been submitted or published.
- The local MVP is complete and the Python suite has passed 131 tests.
- The public repository, MIT licence, README and architecture diagram are available.
- AWS credits and gross-cost alerts are verified. The network and quarantined security scaffolds are deployed in `eu-west-1`; no application compute or model run has been enabled.
- The approved change set `neighborgear-workload-boundary-review-20260912` was executed. Stack `neighborgear-workload-boundary` and its sole resource, the unattached `AWS::IAM::ManagedPolicy`, reached `CREATE_COMPLETE`.
- The critical path is: finish and review exact deployment policies; deploy the protected simulator; prove shutdown; run one bounded live case; complete the ten-scenario evaluation; publish the demo/video/article; complete the Devpost fields; then run final preflight and submit.
- Submission closes at **15 September 2026, 01:00 Europe/London**. The internal target remains **14 September 2026, 20:00 Europe/London**.

Nothing in this document is a submission or a claim that publication has occurred.
