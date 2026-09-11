# Agents for Humans: Building NeighborGear

Draft for builder.aws.com. Update with actual screenshots and verified results before publication.

Community equipment reuse is a coordination problem. A request arrives, staff identify what is needed, somebody searches the stock, another person arranges delivery, and a cancellation starts the work again. We chose to explore this through NeighborGear, a coordinator workspace for a fictional network of three equipment depots.

The core design choice was to make each handoff concrete. A proposed match is different from a reservation. A reservation is different from a confirmed delivery. A returned walking aid cannot quietly become available again: a staff inspection result must change its state. Those distinctions guide both the interface and the tools exposed to the agent.

We use the Strands Agents SDK for the live agent integration. Its tools work with typed requests and persisted operational records. Model output helps interpret requests and coordinate next actions; ordinary application logic checks availability, dimensions, capacity, approval, and duplicate events.

Local development uses a clearly labelled deterministic simulator. That lets us exercise cancellations and returns repeatedly without pretending that a fixture is an AI result. The planned AWS runtime uses AgentCore, with asynchronous work and persisted state. Deployment and real-model evaluation are credit-gated; this draft must be updated with the actual status before being published.

The most revealing demo moment is a driver cancellation. A successful system must either arrange a replacement that fits the constraints or explain the remaining decision to the coordinator. It should never manufacture an assignment simply to keep the story moving.

Our prototype uses fictional people and inventory, with all messages kept in a simulated outbox. Real-world benefit requires validation with the staff and communities doing this work. That is the next research step after demonstrating a reliable workflow.
