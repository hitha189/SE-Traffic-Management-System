# Deviations from the Submitted Documents (Sprint 1)

| Area | Submitted design (SAD / SRS) | Sprint 1 implementation | Reason |
|---|---|---|---|
| Architecture | Event-driven microservices with API Gateway and Event Bus | Single Flask application split into modules (`traffic.py`, `incidents.py`, `routing.py`, `storage.py`) | Faster for a solo one-week prototype; module boundaries keep the design ready to split into services (NFR-07) |
| Data stores | Each service owns its own data store | One shared SQLite database | Simplicity for the prototype |
| Traffic data | Traffic Data Ingestion Service with simulated feed | Simulated readings generated inside `traffic.py` | SRS allows simulated data (FR-04); real sensors are future work (NFR-11) |
| Route planning | Congestion-aware routes using ITrafficData | Dijkstra over a small simulated road graph, using the same density values as the map | Prototype scope (FR-12, FR-13) |
| Sessions | Token issued by User & Auth Service | Signed, expiring tokens (1 hour) checked in the same app | Same security goal (NFR-01) without a gateway |
| Sprint 1 scope | All FR/NFR planned across two sprints | Sprint 1 covers FR-01 to FR-05, FR-08, FR-12, FR-13, FR-19 (partial: users, roads, incidents, route history), NFR-01, NFR-04 | FR-19 is completed in Sprint 2 as alerts, parking, signals and reports are added |