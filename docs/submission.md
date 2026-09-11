# NeighborGear

**Tagline:** From an equipment request to a confirmed delivery—with the follow-up handled.

**Track:** Good Neighbor Agents

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
- [ ] Verify entrant eligibility and registration; obtain AWS Builder ID.
- [ ] Publish repository, README, MIT licence, architecture diagram, and reproducible setup.
- [ ] Verify live model execution and retain evaluation evidence.
- [ ] Make a public video of at most five minutes showing the working project.
- [ ] Supply testing instructions and the verified demo URL if deployed.
- [ ] Publish the build article and include its actual URL.
- [ ] Confirm every required Devpost field before submitting.

Nothing in this document is a submission or a claim that publication has occurred.
