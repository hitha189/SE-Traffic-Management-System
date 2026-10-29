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


---

# Sprint 2, member B: additions and deviations
(items FR-16, FR-17, FR-18, NFR-03, NFR-06, NFR-07, NFR-08, NFR-09, NFR-10, NFR-11;
how each non-functional requirement is shown is in `docs/NFR_EVIDENCE.md`)

| Area | Submitted design (SRS / SAD) | Sprint 2 implementation | Reason |
|---|---|---|---|
| Parking data (FR-16) | Parking data from a data service | Six simulated parking areas, one per road. Free spaces drift by up to 8 on each refresh to imitate cars coming and going. Status is Available, Limited (20% or less free) or Full | The SRS allows simulated data where real data is not available; real sensors can push data instead (NFR-11) |
| Analytics (FR-17) | Analysis of flow, congestion, incidents and patterns | Admin only. Every traffic reading is now stored (`traffic_history`, newest 20,000 kept). Flow and congestion use current and stored readings, incidents use counts and hotspots, patterns use hourly averages (UTC) and a rising / falling / stable trend per road | The SRS names the four areas but not the method; this is the simplest honest method on simulated data. With simulated random data the patterns are noise, with real sensors they become meaningful |
| Reports (FR-18) | Administrators generate management reports | A report is a saved snapshot (stored in the new `reports` table) of analytics, signals, alerts, parking, emergency requests and open incidents. It can be downloaded as plain text | Text keeps the prototype simple; PDF export is future work |
| Availability (NFR-03) | "Remain available during normal operating periods" | Measured: every request and every server error is counted, target 99% of requests without a server error. Public health check at `/api/health`. The system recovers by itself after a database outage | The SRS gives no number, so we defined one (same approach as the 1-second target in NFR-02) |
| Scalability (NFR-06) | Design permits more roads, users, sensors, parking areas, data | The road network moved from a fixed list in `routing.py` into the `road_links` table. Admins add roads and parking areas through the API or interface with no code change. Indexes added. History capped at 20,000 readings and the incident list returns the newest 500 | Without this, "more roads" would need a code change, which fails the SRS pass condition |
| Modularity (NFR-07) | Modular components; the SAD shows separate services | Member-B features are Flask Blueprints in their own files that never import `app.py`; dependencies are passed in. `test_modularity.py` enforces the rules | Single-app deviation from Sprint 1 remains; the blueprint pattern is the step towards separate services |
| Browsers and devices (NFR-08) | "Modern browsers and standard devices selected for testing" | Selection: latest Chrome, Edge, Firefox, Safari; Chrome on Android; Safari on iPhone and iPad; 360 px to 1920 px. Automated browser tests exist for Chromium, Firefox and WebKit. The map no longer blocks the app if it cannot load | Only Chromium could be run when the tests were written; Firefox and WebKit must be run once on a computer with them installed (`docs/NFR_EVIDENCE.md`) |
| Data consistency (NFR-09) | Consistent, accurate records | The database refuses impossible records (triggers) and an admin consistency check compares tables with each other | Triggers also protect databases created in Sprint 1 |
| Data privacy (NFR-10) | Collect only necessary data, protect personal and location data | Reporter names are hidden from non-admins. Users can download their data and delete their account (password required). Route history is deleted after 30 days. A deleted account's login stops working immediately | Right to access and erasure. The audit log keeps the username only (append-only by NFR-12); admin accounts cannot be deleted through the screen |
| Future integration (NFR-11) | Architecture allows sensors, IoT, public transport, smart-city | `datasources.py`: simulators are replaceable sources; devices can push traffic and parking readings to an admin-only ingest API; new data types are added with one function | Public transport and smart-city feeds are extension points only, not working integrations. The ingest API uses an admin login; a real deployment would use a key per device |

## Existing code touched in member B's work

| File | Change | Why |
|---|---|---|
| `app/app.py` | Imports and registers six blueprints; reads the road network from the database; `require_role` also checks the account still exists; the traffic route asks the data-source layer for fresh data; non-admins no longer see who reported an incident; availability counter added | NFR-03, 06, 07, 10, 11 |
| `app/routing.py` | `build_graph`, `known_places`, `find_route`, `find_emergency_route` accept the database graph (optional arguments; old calls still work) | NFR-06 |
| `app/traffic.py` | Readings go through `set_reading` and are stored in `traffic_history`; density levels are named constants | FR-17, NFR-09, NFR-11 |
| `app/signals.py`, `emergency.py`, `notifications.py`, `incidents.py`, `alerts.py`, `audit.py`, `storage.py` | `add_signal`; graph passed in; indexes; `LIST_LIMIT`; `purge_old_routes`; more tables counted | NFR-06, 10, FR-19 |
| `app/static/index.html` | New panels (parking, analytics, reports, system health, grow the network, my data); the map is optional | FR-16 to FR-18, NFR-03, 06, 08, 09, 10 |
| `tests/test_congestion_routing.py` | One test wrote a road density of 100 but left the level "Low". It now also writes "High" | The new consistency rule (NFR-09) rightly refuses that record |

FR-19 (Data Management) is now complete: users, traffic updates, incidents,
alerts, routes, parking data, signal states and reports are all stored and
retrievable (`tests/test_data_management.py`).

## Known limitations (member B)

- Firefox and Safari (WebKit) browser tests are written but were not run in the build environment; see `docs/NFR_EVIDENCE.md`.
- Parking numbers and traffic patterns come from a simulator; they show the features work, not real traffic behaviour.
- The Sprint 1 and member-A routes are still in `app.py`, not blueprints.
- SQLite is enough for the prototype; a large deployment would need a server database.
