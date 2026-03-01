# MARG

## Multi-Agent Adaptive Routing Grid

MARG is a deterministic, distributed simulation engine that models emergency vehicle coordination across an urban traffic grid. It explores decentralized reservation protocols, conflict resolution strategies, and fairness under contention using autonomous signal and ambulance agents.

The system is designed as a research-grade coordination framework rather than a simple visualization. It emphasizes architectural clarity, reproducibility, and systems engineering rigor.

---

## Overview

Urban emergency response systems must balance speed, safety, and coordination across constrained infrastructure. MARG models this problem as a distributed resource allocation challenge:

* Intersections act as autonomous signal agents.
* Ambulances act as autonomous routing agents.
* Communication occurs exclusively via structured message passing.
* Corridors emerge dynamically through negotiated reservations.

There is no centralized routing authority controlling all signals. Instead, coordination arises from local decision-making combined with deterministic global safeguards.

---

## Core Objectives

MARG is built to explore:

* Distributed resource reservation under real-time constraints
* Sliding-window corridor formation
* Priority aging and fairness mechanisms
* Conflict resolution with hysteresis
* Deadlock prevention and deterministic recovery
* Deterministic replay through seeded execution

The system is structured to be testable, reproducible, and extensible.

---

## System Architecture

The system follows a strict separation of responsibilities:

Ambulance Agents <-> Signal Agents
            |
         Message Bus
            |
        Simulation Engine

### Simulation Engine

* Advances discrete time steps
* Delivers messages deterministically
* Updates congestion state
* Records metrics
* Performs deadlock detection
* Produces full system snapshots

The engine does not override agent decisions. It remains a passive orchestrator of time and message flow.

### SignalAgent

* Maintains local reservation queue
* Applies priority hysteresis
* Enforces minimum reservation hold duration
* Activates and revokes reservations deterministically
* Exposes local state for observability

### AmbulanceAgent

* Computes shortest path over weighted graph
* Requests reservations using sliding window depth
* Applies priority aging
* Handles revocations and cooldown
* Releases reservations upon traversal

### Message Bus

* Ensures deterministic delivery order
* Prevents direct agent-to-agent invocation
* Maintains isolation between decision-makers

---

## Reservation Protocol

MARG uses a sliding-window reservation mechanism:

1. An ambulance computes its shortest path.
2. It requests reservations for upcoming intersections.
3. Each signal evaluates requests using:

   * Current phase
   * Existing active reservation
   * Queue ordering
   * Priority and hysteresis margin
4. Reservations are approved, queued, or denied.
5. Corridors form as consecutive approvals accumulate.

Ambulances cannot force signal state changes.
Signals cannot directly command ambulance movement.

Coordination is emergent but bounded.

---

## Deadlock Handling

The system implements both prevention and recovery.

### Prevention

* Sliding-window depth reduces circular hold
* Priority aging mitigates starvation
* Reservation timeout releases stale holds
* Hysteresis reduces flip-flop displacement

### Recovery

* Periodic cycle detection in reservation graph
* Deterministic tie-break logic
* Forced release of selected reservation
* Deadlock counter metric increment

This ensures the system remains stable even under high contention.

---

## Metrics

MARG tracks cumulative performance metrics per simulation run:

* Average response time
* Reservation success rate
* Fairness index (Jain’s fairness metric)
* Deadlock count
* Queue length statistics

All metrics reset upon engine reset and are exported via REST and WebSocket endpoints.

---

## Chaos Mode

Chaos Mode enables stress testing by spawning large numbers of ambulances simultaneously with randomized, valid start and destination pairs.

Constraints:

* Start and destination must differ
* Deterministic seeded generation
* No duplicate route pairs within batch
* Spawn count bounded by grid size

Chaos Mode exposes:

* Reservation competition dynamics
* Fairness shifts under load
* Congestion amplification
* Deadlock resilience

---

## Backend Stack

* Python
* FastAPI
* Background simulation thread
* Deterministic seeded randomness
* WebSocket snapshot streaming
* Atomic engine replacement
* Full unit test coverage

The backend guarantees:

* Deterministic replay under identical seed and configuration
* Thread-safe reset operations
* JSON-serializable full system state
* Clean separation between API and simulation logic

---

## Frontend Visualization

The frontend renders a structured city grid using HTML5 Canvas.

Key characteristics:

* Deterministic grid-based layout
* Smooth ambulance interpolation
* Phase-based signal coloring
* Congestion-weighted road tinting
* Reservation corridor highlighting
* Optimized rendering using requestAnimationFrame
* Snapshot-driven rendering loop
* Offscreen caching for static road network

The layout includes:

* Sticky navigation bar
* Full-width simulation canvas
* Live metrics panel
* Runtime configuration controls
* Chaos Mode trigger

---

## Configuration

All simulation parameters are configurable at runtime via API:

* Grid rows and columns
* Corridor depth
* Tick interval
* Reservation timeout
* Hysteresis margin
* Priority weights (alpha, beta, wait_alpha)
* Phase durations
* Congestion multipliers
* Snapshot broadcast interval

Configuration updates rebuild the engine atomically while preserving determinism.

---

## Determinism

MARG enforces strict determinism:

* All randomness derived from seeded generator
* Identical seed + configuration produces identical state
* Message delivery order is deterministic
* No hidden non-seeded randomness
* Engine replacement is atomic under lock

This enables reproducible experimentation and controlled stress testing.

---

## Running the System

### Backend

Run the API server:

uvicorn backend.app.main:app --reload

Available endpoints:

GET /state
GET /metrics
POST /spawn_ambulance
POST /reset
POST /reset_with_config
POST /chaos
WebSocket: /ws

---

### Frontend

Start the React frontend:

npm run dev

Ensure backend is running before connecting.

---

## Design Principles

* No centralized decision authority
* Strict message-based coordination
* Deterministic execution
* Reproducibility over randomness
* Architectural separation of concerns
* Observability as a first-class feature

---

## Use Cases

* Distributed systems experimentation
* Resource allocation modeling
* Deadlock research
* Fairness analysis under contention
* Systems engineering portfolio demonstration
* Coordination protocol prototyping

---

## Future Extensions

* Real-world map integration
* Adaptive congestion modeling
* Formal deadlock verification
* Hybrid centralized/decentralized experimentation
* Multi-class vehicle priority modeling

---

## License

MIT License
