# Deviations from the Submitted Documents (Sprint 1)

| Area | Submitted design (SAD / SRS) | Sprint 1 implementation | Reason |
|---|---|---|---|
| Architecture | Event-driven microservices with API Gateway and Event Bus | Single Flask application split into modules (`traffic.py`, `incidents.py`, `routing.py`, `storage.py`) | Faster for a solo one-week prototype; module boundaries keep the design ready to split into services (NFR-07) |
| Data stores | Each service owns its own data store | One shared SQLite database | Simplicity for the prototype |
| Traffic data | Traffic Data Ingestion Service with simulated feed | Simulated readings generated inside `traffic.py` | SRS allows simulated data (FR-04); real sensors are future work (NFR-11) |
| Route planning | Congestion-aware routes using ITrafficData | Dijkstra over a small simulated road graph, using the same density values as the map | Prototype scope (FR-12, FR-13) |
| Sessions | Token issued by User & Auth Service | Signed, expiring tokens (1 hour) checked in the same app | Same security goal (NFR-01) without a gateway |
| Sprint 1 scope | All FR/NFR planned across two sprints | Sprint 1 covers FR-01 to FR-05, FR-08, FR-12, FR-13, FR-19 (partial: users, roads, incidents, route history), NFR-01, NFR-04 | FR-19 is completed in Sprint 2 as alerts, parking, signals and reports are added |

---

# Sprint 2 additions and deviations (items FR-06, FR-07, FR-09, FR-10, FR-11, FR-14, FR-15, FR-20, NFR-02, NFR-05, NFR-12)

| Area | Submitted design (SRS / SAD) | Sprint 2 implementation | Reason |
|---|---|---|---|
| Event Bus / alert service | Alerts and notifications delivered through an event bus between services | `alerts.py` and `notifications.py` are called directly from the Flask routes that cause the event, inside one database transaction | Same single-app deviation as Sprint 1; the modules keep the service boundary, so an event bus can replace the direct calls later (NFR-07, NFR-11) |
| Congestion alerts (FR-10) | Alert on congestion | An alert is raised when a road's simulated congestion is High (density 70% or more) and cleared when it drops below | The SRS gives no threshold; this reuses the "High" level already shown on the map |
| Incident alerts (FR-10) | Alerts for accidents, closures, hazards | Raised **when the incident is reported** (not after verification), so drivers see it immediately. Roadblock = Closure alert. "Other" incidents raise no alert. Closing an incident clears its alert; editing it updates the alert | Faster warning to users; the admin can still verify, edit or close |
| "Nearby area" (FR-11) | Notify users in selected or nearby areas | Nearby = the area itself plus places directly connected to it in the simulated road graph. Users choose areas with tick boxes | There is no real GPS data in the prototype; this also avoids collecting location data (NFR-10) |
| Signal control (FR-07) | Prototype-level signal change with validation and logging | Signal state is stored in the database only (Red / Yellow / Green). Invalid states and "no change" requests are rejected. Each change is logged in the same transaction | No real signal hardware; matches the SRS wording "in the prototype" |
| Emergency priority (FR-14) | Authorized emergency vehicles request priority | Only the `emergency` role can request it. Admins can view all requests and end them, but cannot create one. The vehicle's route signals turn green and are restored when the trip ends | The SRS fail condition says an unauthorized requester must not be able to submit |
| Emergency route (FR-15) | Optimized route using available traffic information | Same road graph and live densities as normal routing, with a smaller congestion penalty, a higher assumed speed (50 km/h vs 30 km/h) and a detour around places with an open roadblock; falls back to the direct route if no detour exists | Prototype scope; the response also shows the normal route time for comparison |
| Response time (NFR-02) | "Acceptable time" (no number in SRS) | Project target set to **1 second** per request. Every response carries an `X-Response-Time-ms` header, slow requests are logged, and tests check the target | The SRS says the target is not specified, so we defined one |
| Audit log (FR-20, NFR-12) | Log important administrative actions with time | Table `audit_log` stores actor, action, target, details and UTC time. Database triggers reject UPDATE and DELETE, so entries cannot be changed. Admins can filter by action or actor | Traceability; in a production system the log would also be shipped to separate storage |
| Error handling (NFR-05) | Validate input, handle errors without corrupting data | Wrong types, bad JSON and oversized requests give a clear 400 / 413. Unexpected errors give a safe 500 message with no internals. Each request is one transaction that rolls back fully on error | Covers all routes, including the Sprint 1 ones |

## Sprint 1 code that was touched in Sprint 2

| File | Change | Why |
|---|---|---|
| `app/routing.py` | `find_route` got optional `penalty`, `speed`, `avoid` arguments (defaults keep old behaviour) | Reused for emergency routing instead of copying the algorithm |
| `app/incidents.py` | `add_incident` got `commit=True` argument | Lets the incident, its alert and its audit entry be saved together |
| `app/app.py` | Register, login and incident routes now read fields through `clean_str` / `json_body`; error handlers and request timer added | NFR-05 and NFR-02 apply to the whole system |
| `app/storage.py` | New tables added to the summary counts | FR-19 data categories |
| `app/static/index.html` | New panels for alerts, notifications, admin and emergency | FR-06 to FR-20 user interface |

## Known limitations

- Two emergency requests that overlap on the same junction restore signals independently; the last one to finish decides the final colour.
- Cleared alerts are kept in the database but the interface shows only active ones.
- `app/seed_demo.py` creates demo accounts (admin, emergency, user) because the prototype has no screen for creating privileged accounts. Its passwords are for demos only.
