# Code Coverage Report (statement coverage)

Traffic Management System · Deliverable 3

| Item | Value |
|---|---|
| Run at | 2026-11-10 23:32 IST |
| Command | `python3 -m pytest --cov --cov-report=term-missing` |
| Tool | coverage.py 7.17.1 via pytest-cov; settings in `.coveragerc` |
| Code measured | every module in `app/` (25 files); `seed_demo.py` is left out because it is a demo script, not part of the system |
| Statements | 1414 |
| Statements run by the tests | 1385 |
| **Statement coverage** | **97.9%** |
| Target | The Test Plan sets no number; we used 80%, a common minimum, and it is met |

Branch coverage is reported separately in [`BRANCH_COVERAGE_REPORT.md`](BRANCH_COVERAGE_REPORT.md). The machine-readable data for both is in [`coverage.json`](coverage.json).

## Coverage by module

| Module | Statements | Missed | Coverage | Lines not run |
|---|---|---|---|---|
| `app/alerts.py` | 47 | 0 | 100.0% | none |
| `app/analytics.py` | 59 | 0 | 100.0% | none |
| `app/app.py` | 455 | 11 | 97.6% | 127-128, 158-159, 167, 196, 443, 552, 573, 650-651 |
| `app/audit.py` | 23 | 0 | 100.0% | none |
| `app/consistency.py` | 79 | 8 | 89.9% | 118, 120, 134, 143, 159, 170, 182, 189 |
| `app/datasources.py` | 64 | 1 | 98.4% | 64 |
| `app/emergency.py` | 55 | 0 | 100.0% | none |
| `app/health.py` | 32 | 0 | 100.0% | none |
| `app/health_api.py` | 26 | 0 | 100.0% | none |
| `app/incidents.py` | 25 | 1 | 96.0% | 31 |
| `app/integrations_api.py` | 36 | 0 | 100.0% | none |
| `app/network.py` | 35 | 0 | 100.0% | none |
| `app/network_api.py` | 20 | 0 | 100.0% | none |
| `app/notifications.py` | 34 | 0 | 100.0% | none |
| `app/parking.py` | 56 | 0 | 100.0% | none |
| `app/parking_api.py` | 34 | 0 | 100.0% | none |
| `app/privacy.py` | 18 | 1 | 94.4% | 25 |
| `app/privacy_api.py` | 29 | 0 | 100.0% | none |
| `app/reporting_api.py` | 55 | 0 | 100.0% | none |
| `app/reports.py` | 67 | 3 | 95.5% | 125, 138, 141 |
| `app/routing.py` | 53 | 1 | 98.1% | 107 |
| `app/signals.py` | 24 | 0 | 100.0% | none |
| `app/storage.py` | 25 | 0 | 100.0% | none |
| `app/traffic.py` | 40 | 2 | 95.0% | 99, 102 |
| `app/validation.py` | 23 | 1 | 95.7% | 22 |
| **Total** | **1414** | **29** | **97.9%** | |

## Why the remaining lines are not run

| Module | Lines | What the code does, and why no test reaches it |
|---|---|---|
| `app/app.py` | 127-128 | Expired or tampered login token is refused. Not reached: no test sends a forged or expired token (gap, see below) |
| `app/app.py` | 158-159 | Lockout ends after `LOCKOUT_SECONDS`. Not reached: the tests do not wait out the lockout period |
| `app/app.py` | 167 | Failure counter restarts after the lockout window. Same reason |
| `app/app.py` | 196 | Slow-request warning in the log. Not reached: every test request is faster than the 1 s target (NFR-02), which is the desired result |
| `app/app.py` | 443 | Incident edit with an empty description is refused. Not reached: the tests try empty type and location, not empty description |
| `app/app.py` | 552 | 404 when no emergency route exists. Not reached: every pair of places on the network is connected |
| `app/app.py` | 573 | Same 404 for an emergency priority request |
| `app/app.py` | 650-651 | `python3 app.py` start-up block. Runs only when the server is started by hand, not under pytest |
| `app/consistency.py` | 118, 120, 134, 143, 159, 170, 182, 189 | Individual problem messages in the consistency checker (NFR-09) for faults the tests do not create one by one (alert of the wrong kind, signal without a road, parking on an unknown road, invalid role, orphan notification, unlogged alert). The database triggers stop most of these faults from being written at all, which `test_consistency.py` does test |
| `app/datasources.py` | 64 | `get()` helper is not called by the tests |
| `app/incidents.py` | 31 | `add_incident(..., commit=True)`. The app always passes `commit=False` inside a transaction |
| `app/privacy.py` | 25 | Data export for a user who no longer exists. The route checks the login first, so it cannot happen through the API |
| `app/reports.py` | 125, 138, 141 | Text-report lines for a road ranking, a peak hour and road trends. Not reached: the text-download test uses a fresh database with no traffic history |
| `app/routing.py` | 107 | No emergency route at all. Not reached: the network is connected |
| `app/traffic.py` | 99-102 | `list_history()` helper. Analytics reads the history with its own query |
| `app/validation.py` | 22 | `parse_int(True)` is refused because JSON `true` is a bool in Python. No test sends a boolean as a number |

## Gaps worth closing

Most missed lines are defensive paths that cannot happen through the API on the prototype's connected road network. Three are worth a test in a later round:

1. **Forged or expired token** (`app.py` 127-128): security relevant (NFR-01). A test can send a token signed with a different key and expect 401.
2. **Lockout expiry** (`app.py` 158-159, 167): can be tested by moving the stored failure time back by `LOCKOUT_SECONDS`.
3. **Empty description on incident edit** (`app.py` 443): one more case in `test_incident_management.py`.

## How to reproduce

    python3 -m pip install -r requirements.txt
    python3 -m pytest --cov --cov-report=term-missing
    python3 -m pytest --cov --cov-report=html   # opens as htmlcov/index.html
