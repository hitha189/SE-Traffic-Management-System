# Non-functional requirements: how each one is met and how to show it

This page is for the final demo. For each requirement it gives the SRS pass
condition, what was built, the automated tests that prove it, and a short
live demonstration.

| ID | Requirement | Where | Tests |
|---|---|---|---|
| NFR-03 | Availability | `health.py`, `health_api.py` | `test_availability.py` |
| NFR-06 | Scalability | `network.py`, `routing.py`, indexes | `test_scalability.py` |
| NFR-07 | Modularity | `*_api.py` blueprints, `deps` | `test_modularity.py` |
| NFR-08 | Browsers and devices | `index.html` | `test_compat_static.py`, `tests/browser/` |
| NFR-09 | Data consistency | `consistency.py` | `test_consistency.py` |
| NFR-10 | Data privacy | `privacy.py`, `privacy_api.py` | `test_privacy.py` |
| NFR-11 | Future integration | `datasources.py`, `integrations_api.py` | `test_integration_ready.py` |

---

## NFR-03 Availability

**SRS pass:** the system remains available during normal operating periods
when its network and services are available.

**Our definition.** The SRS gives no number, so we set one: at least **99% of
requests** during normal operation finish without a server error (5xx), and
the system recovers on its own when the database comes back. Network or
hosting outages are outside the system's control, as the SRS says.

**Built**
- `GET /api/health` works without logging in, so an uptime monitor or load
  balancer can call it. It returns 200 when the database answers and 503
  when it does not.
- Every request is counted; every 5xx is counted separately. Admins see the
  availability percentage at `GET /api/admin/status` and in the interface.
- A new database connection is opened for each request, so nothing needs a
  restart after a database outage.
- Unexpected errors return a clean JSON 500 and the server keeps serving
  (NFR-05).

**Show it:** log in as `admin1`, click **Check system** (Availability 100%).
Open `/api/health` in a new tab (no login needed).

**Limits:** the prototype runs one Flask process. For real use, run it under
a production server (for example `gunicorn -w 2 app:app`) and monitor
`/api/health`.

---

## NFR-06 Scalability

**SRS pass:** more roads, users, sensors, parking areas and traffic data can
be added without redesigning the system.

**Built**
- **Roads are data, not code.** The road network moved from a Python list
  into the `road_links` table. An admin adds a road with
  `POST /api/admin/roads` (or the **Grow the network** panel). It joins
  the map, route planning, emergency routing, signals, alerts,
  notifications and analytics at once.
- **Parking areas** are added with `POST /api/admin/parking`.
- **Sensors** push readings through the ingest API (NFR-11).
- **Traffic data** history is capped (newest 20,000 readings) so storage
  stays bounded; incident lists return the newest 500.
- **Indexes** on the busy columns (incident status and location, alert
  state, notification owner, audit action and actor, traffic history road,
  route owner, parking location).

**Tests:** adds 60 roads and 30 parking areas through the API, then checks
that every main endpoint is still under the 1-second target; loads 5,000
incidents, 20,000 audit rows, 10,000 history rows and 5,000 users and checks
the same; checks the indexes exist.

**Show it:** as `admin1`, add a road ("Hebbal", connects to Majestic, 7.5 km).
It appears on the map, in the From/To lists, and in the signals table.

**Limits:** SQLite handles this prototype load. A larger deployment would
move to a server database; only `get_db()` and the SQL would change.

---

## NFR-07 Modularity

**SRS pass:** features are organised in modules and one can change with
minimal impact on the others.

**Built**
- Every Sprint 2 member-B feature is a **Flask Blueprint** in its own file
  (`parking_api.py`, `reporting_api.py`, `integrations_api.py`,
  `network_api.py`, `health_api.py`, `privacy_api.py`).
- A blueprint never imports `app.py`. It receives login checks, the database
  and the current user as an argument (`create_blueprint(deps)`). So it can
  run anywhere, even in a different app.
- Business logic (`parking.py`, `analytics.py`, `reports.py`, ...) contains
  no web code.

**Tests (`test_modularity.py`) work as architecture rules and fail if the
design is damaged:** no module imports `app.py`; no circular imports; logic
modules do not import Flask; blueprints do not import each other; each new
module may depend only on the modules listed in the test; importing
`parking_api` loads almost nothing else; the parking feature runs inside a
brand-new Flask app with stand-in dependencies.

**Show it:** run `python3 -m pytest tests/test_modularity.py -v`.

**Limits:** the Sprint 1 and member-A routes are still in `app.py`. They can
be moved into blueprints the same way; this was not done to avoid breaking
working, tested code.

---

## NFR-08 Browser and device compatibility

**SRS pass:** the application works on the modern browsers and standard
computing devices chosen for testing.

**Supported (our test selection):** the latest versions of **Chrome**,
**Edge**, **Firefox** and **Safari** on desktop; **Chrome on Android** and
**Safari on iPhone and iPad**; screens from 360 px wide phones to 1920 px
desktops.

**Built**
- Responsive layout (viewport tag, percentage widths, a small-screen rule,
  tables scroll inside their own box).
- Large text and tap targets (16 px text, buttons at least 24 px tall).
- Every form field has a label.
- **The map never blocks the app.** If the map library cannot load (blocked
  network, old device), a message replaces the map and everything else
  (routes, parking, alerts, reports) still works.

**Tests**
- `test_compat_static.py`: checks the page itself (standard HTML, viewport,
  labels, tap sizes, secure resources, map guard). Runs everywhere.
- `tests/browser/test_browsers.py`: drives real browsers through login, route
  planning, incident reporting, parking, the admin tools and a report
  download at six screen sizes (1920, 1366, 1024, 768, 390, 360 px) and with
  Pixel 7, iPhone 13 and iPad emulation. It also checks that nothing scrolls
  sideways and that the app works with the map blocked.

**Honest status:** in the build environment only **Chromium** (the Chrome and
Edge engine) could be installed, so those tests were run there and passed.
The Firefox and WebKit (Safari) versions are written and skip themselves when
the engine is missing. To run them on your own computer:

    pip install playwright
    python -m playwright install
    python3 -m pytest tests/browser -v

Before the demo, also open the app once by hand in Safari or Firefox and on a
real phone, and tick this list: log in, map or map message shown, plan a
route, report an incident, open Parking, nothing cut off at the screen edge.

---

## NFR-09 Data consistency

**SRS pass:** records for traffic events, incidents, users and administrative
actions stay consistent and accurate through all supported operations.

**Built, in two layers**
1. **The database refuses impossible records** (`consistency.install_triggers`):
   an unknown incident type or status; a closed incident being edited; a
   verified incident going back to "Reported"; a signal colour that does not
   exist; a road whose congestion level disagrees with its density; a bad
   role; an alert of an unknown kind; a notification for an alert that does
   not exist; an invalid emergency status; parking with more free spaces than
   capacity (table constraint). The audit log already rejects any edit or
   delete (NFR-12).
2. **A consistency check** (`GET /api/admin/consistency`, or the **Check data
   consistency** button) compares tables with each other: alerts against
   incidents and roads, roads against signals, parking against roads, orphan
   records left by a deleted user, and whether every alert was logged.
- Operations are already all-or-nothing (one transaction per request, NFR-05).

**Tests:** 12 kinds of bad write are refused; a long workflow (reports,
edits, closing, emergency, new road, sensor data, parking) ends with a clean
check; 7 kinds of deliberately damaged data are all found.

**Show it:** click **Check data consistency** ("All records agree").

**Note:** one Sprint 1 test wrote density 100 but left congestion "Low", a
record the new rules rightly refuse. The test now writes "High" as well.

---

## NFR-10 Data privacy

**SRS pass:** only necessary user information is collected, and personal and
location-related data is protected.

**What we collect, and why**

| Data | Why | Kept for |
|---|---|---|
| Username, email, password hash, role | account (FR-01, FR-02) | until the user deletes the account |
| Route history (place names) | route history | 30 days, then deleted automatically at start-up |
| Areas followed | notifications (FR-11) | until changed or the account is deleted |
| Incident reports (who, what, where) | FR-08 | the report stays; the name is removed on deletion |

Not collected: phone number, address, GPS position, device details. Locations
are named areas, never a person's coordinates. A test checks that no table
has such a column, and that extra fields sent at registration are ignored.

**Protection**
- Passwords are stored as hashes and never returned.
- Email addresses never appear in admin pages, reports, the audit log or
  shared lists (checked across 18 endpoints).
- Only admins can see who reported an incident.
- Route history, subscriptions and notifications are private to their owner.
- **Download my data** (`GET /api/me/export`) and **Delete my account**
  (`DELETE /api/me`, password required). Deletion removes the account,
  routes, subscriptions, notifications and emergency requests, strips the
  name from incidents already reported, and the user's old login stops
  working at once.

**Trade-off to explain in the demo:** the audit log is append-only (NFR-12),
so it keeps the **username** of actions already taken, for accountability.
It holds no email, route or location history. Admin accounts cannot be
deleted through this screen, to prevent locking everyone out.

**Show it:** log in as `driver1`, click **Download my data**.

---

## NFR-11 Future integration

**SRS pass:** the architecture allows future integration with traffic
sensors, IoT devices, public transport systems and smart-city
infrastructure without major redesign.

**Built (`datasources.py`)**
- **Everything that supplies outside data goes through one layer.** Today the
  sources are simulators. The rest of the system asks for fresh data and does
  not know where it comes from.
- **Pull:** register a `DataSource` subclass (for example one that calls a
  city API). It replaces the simulator with no other change. Tested.
- **Push:** devices send readings to `POST /api/admin/integrations/ingest`
  (traffic densities, parking spaces). Batches are checked and are
  all-or-nothing, every push is logged, and heavy readings raise congestion
  alerts like any other data.
- **New data types:** `register_ingester("public_transport", fn)` adds a type
  with no edits to existing code. Tested with a bus-arrival example.
- **Roadmap shown to admins:** `GET /api/admin/integrations` lists current
  sources, accepted types, and the planned integrations with how each plugs
  in.

**Honest limits.** Public transport and smart-city integration are
extension points, not working integrations. The ingest API uses an admin
login; a real deployment would give each device its own key.

**Show it:** run `python3 -m pytest tests/test_integration_ready.py -v` and
point out the sensor push raising an alert, the simulator being swapped for
another source, and the new "public_transport" data type being added.
