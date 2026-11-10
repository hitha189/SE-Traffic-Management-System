# Branch Coverage Report

Traffic Management System · Deliverable 3

Branch coverage checks that both outcomes of every decision (`if`, `for`, `while`, `try`) were taken by some test, for example that a check is seen both passing and failing. It is stricter than statement coverage: an `if` with no `else` can have every line run while the "condition false" path is never tried.

| Item | Value |
|---|---|
| Run at | 2026-11-10 23:47 IST |
| Command | `python3 -m pytest --cov --cov-branch --cov-report=term-missing` (`branch = True` is also set in `.coveragerc`) |
| Tool | coverage.py 7.17.1 via pytest-cov |
| Branch outcomes in the code | 346 |
| Taken by the tests | 318 |
| Not taken | 28 |
| **Branch coverage** | **91.9%** |
| Combined statement + branch coverage | 96.8% |
| Target | The Test Plan sets no number; we used 80%, a common minimum, and it is met |

## Branch coverage by module

| Module | Branches | Taken | Partial decisions | Branch coverage | Branches not taken (line -> target) |
|---|---|---|---|---|---|
| `app/alerts.py` | 14 | 13 | 1 | 92.9% | 115->117 |
| `app/analytics.py` | 16 | 16 | 0 | 100.0% | none |
| `app/app.py` | 100 | 92 | 8 | 92.0% | 157->158, 166->167, 192->198, 195->196, 442->443, 551->552, 572->573, 649->650 |
| `app/audit.py` | 6 | 6 | 0 | 100.0% | none |
| `app/consistency.py` | 44 | 36 | 8 | 81.8% | 117->118, 119->120, 133->134, 142->143, 158->159, 168->170, 181->182, 186->189 |
| `app/datasources.py` | 14 | 13 | 1 | 92.9% | 69->exit |
| `app/emergency.py` | 10 | 9 | 1 | 90.0% | 112->110 |
| `app/health.py` | 2 | 2 | 0 | 100.0% | none |
| `app/incidents.py` | 6 | 5 | 1 | 83.3% | 30->31 |
| `app/integrations_api.py` | 4 | 4 | 0 | 100.0% | none |
| `app/network.py` | 18 | 18 | 0 | 100.0% | none |
| `app/notifications.py` | 6 | 6 | 0 | 100.0% | none |
| `app/parking.py` | 22 | 22 | 0 | 100.0% | none |
| `app/privacy.py` | 2 | 1 | 1 | 50.0% | 24->25 |
| `app/privacy_api.py` | 4 | 4 | 0 | 100.0% | none |
| `app/reporting_api.py` | 8 | 8 | 0 | 100.0% | none |
| `app/reports.py` | 20 | 15 | 5 | 75.0% | 117->122, 124->125, 135->138, 140->141, 155->160 |
| `app/routing.py` | 22 | 21 | 1 | 95.5% | 106->107 |
| `app/signals.py` | 2 | 2 | 0 | 100.0% | none |
| `app/storage.py` | 4 | 4 | 0 | 100.0% | none |
| `app/traffic.py` | 10 | 10 | 0 | 100.0% | none |
| `app/validation.py` | 12 | 11 | 1 | 91.7% | 21->22 |
| **Total** | **346** | **318** | **28** | **91.9%** | |

Modules with no decisions to test: `app/health_api.py`, `app/network_api.py`, `app/parking_api.py`.

## Branches not taken, explained

| Module | Branch not taken |
|---|---|
| `app/alerts.py` | `list_alerts(active_only=False)`: nothing in the app asks this function for cleared alerts (the alerts route and reports both list active alerts only) |
| `app/app.py` | Lockout expiry (157, 166), slow-request warning (195), the timing header when a request has no start time (192), empty description on edit (442), no emergency route (551, 572), start-up block (649) |
| `app/consistency.py` | Eight 'problem found' branches, one per kind of fault the tests do not create one by one |
| `app/datasources.py` | `refresh()` for a data kind with no registered source |
| `app/emergency.py` | Ending priority when a route signal is no longer Green (an admin changed it during the trip) |
| `app/incidents.py` | `commit=True` path, unused by the app |
| `app/privacy.py` | Export for a missing user |
| `app/reports.py` | Text report with traffic history (ranking, peak hour, trends) and with no busiest road |
| `app/routing.py` | No emergency route even through roadblocks |
| `app/validation.py` | Boolean passed where a number is expected |

## Reading the results

- Every access-control decision (`require_role`) is covered in both directions: allowed and refused.
- Every input check in `validation.py` and the API routes is covered both accepting and rejecting, except the boolean case above and the empty description on incident edit.
- The weakest module is `consistency.py` (NFR-09). Its checker is tested on a consistent system and on several faults, but not on every kind of fault one by one. The database triggers that stop those faults from being stored are tested in `test_consistency.py::test_database_refuses_bad_records`.
- The two "no route" branches cannot be reached on the prototype network because every place is connected.

## How to reproduce

    python3 -m pytest --cov --cov-branch --cov-report=term-missing
