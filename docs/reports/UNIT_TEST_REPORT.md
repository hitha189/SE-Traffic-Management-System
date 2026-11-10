# Unit Test Report

Traffic Management System · Deliverable 3

| Item | Value |
|---|---|
| Run at | 2026-11-10 23:15 IST |
| Command | `python3 -m pytest -q --junitxml=docs/reports/unit-test-results.xml` |
| Environment | macOS 27.0.1, Python 3.13.7, pytest 9.1.1, Flask 3.1.3 |
| Tests collected | 276 |
| Passed | **275** |
| Failed | **0** |
| Skipped | 1 |
| Pass rate (of tests run) | 100.0% |
| Total time | 31.7 s |

Raw result file: [`unit-test-results.xml`](unit-test-results.xml) (JUnit format, opens in any CI tool).

## What counts as a unit test here

Each test starts the Flask app against a fresh, empty SQLite file in a temporary folder (`tests/helpers.py: make_client`), so no test depends on another or on `tms.db`. Most tests exercise one module through its API route; some (`test_routing.py`, `test_congestion_routing.py`, `test_modularity.py`) call module functions directly. The Test Plan's integration and system cases (IT-01 to ST-03) are in the same run and are reported again in `SYSTEM_VALIDATION_REPORT.md`.

## Results by test file

| Test file | Passed | Failed | Skipped | Time (s) |
|---|---|---|---|---|
| `browser/test_browsers.py` | 0 | 0 | 1 | 0.00 |
| `test_alerts.py` | 9 | 0 | 0 | 0.90 |
| `test_analytics.py` | 8 | 0 | 0 | 1.57 |
| `test_audit.py` | 12 | 0 | 0 | 1.61 |
| `test_availability.py` | 6 | 0 | 0 | 0.85 |
| `test_compat_static.py` | 10 | 0 | 0 | 0.02 |
| `test_congestion_routing.py` | 3 | 0 | 0 | 0.11 |
| `test_consistency.py` | 25 | 0 | 0 | 2.75 |
| `test_data_management.py` | 2 | 0 | 0 | 0.42 |
| `test_emergency.py` | 12 | 0 | 0 | 1.97 |
| `test_home.py` | 1 | 0 | 0 | 0.00 |
| `test_incident_management.py` | 8 | 0 | 0 | 1.81 |
| `test_incidents.py` | 3 | 0 | 0 | 0.25 |
| `test_integration_ready.py` | 33 | 0 | 0 | 3.80 |
| `test_login.py` | 3 | 0 | 0 | 0.28 |
| `test_modularity.py` | 23 | 0 | 0 | 0.16 |
| `test_notifications.py` | 8 | 0 | 0 | 1.30 |
| `test_parking.py` | 20 | 0 | 0 | 2.34 |
| `test_performance.py` | 4 | 0 | 0 | 0.42 |
| `test_privacy.py` | 16 | 0 | 0 | 2.21 |
| `test_register.py` | 3 | 0 | 0 | 0.18 |
| `test_reports.py` | 11 | 0 | 0 | 1.64 |
| `test_roles.py` | 4 | 0 | 0 | 0.46 |
| `test_routing.py` | 5 | 0 | 0 | 0.23 |
| `test_scalability.py` | 11 | 0 | 0 | 1.78 |
| `test_security.py` | 3 | 0 | 0 | 0.72 |
| `test_signals.py` | 9 | 0 | 0 | 1.10 |
| `test_storage.py` | 4 | 0 | 0 | 0.35 |
| `test_test_plan.py` | 9 | 0 | 0 | 1.42 |
| `test_traffic.py` | 3 | 0 | 0 | 0.23 |
| `test_validation.py` | 7 | 0 | 0 | 0.59 |
| **Total** | **275** | **0** | **1** | **31.46** |

## Skipped tests

- `browser/test_browsers.py` (whole module): Playwright is not installed

The browser tests need Playwright and its browser engines (`pip install playwright` and `playwright install`). They are skipped, not failed, when those are missing. This is a known deviation in `docs/DEVIATIONS.md`.

## Failed tests

None.

## Ten slowest tests

| Test | Time (s) |
|---|---|
| `test_analytics::test_traffic_flow_reflects_current_conditions` | 0.39 |
| `test_availability::test_normal_operation_has_no_server_errors` | 0.39 |
| `test_consistency::test_everyday_operations_keep_the_records_consistent` | 0.37 |
| `test_notifications::test_unrelated_user_is_not_notified` | 0.32 |
| `test_test_plan::test_it03_road_closure_notifies_relevant_users` | 0.32 |
| `test_data_management::test_every_data_category_is_stored_and_retrievable` | 0.31 |
| `test_emergency::test_only_owner_or_admin_can_complete` | 0.31 |
| `test_signals::test_non_admin_cannot_change_signal` | 0.31 |
| `test_reports::test_reports_are_closed_to_everyone_but_admins` | 0.31 |
| `test_parking::test_every_role_can_view_parking` | 0.31 |

No single test takes more than about a third of a second.

## Defects found during this testing round

No defects were found in the application code. Two of the newly automated Test Plan cases failed on their first run because the test expected behaviour the system deliberately does not have; the tests were corrected, not the code:

| Case | First expectation | Actual (correct) behaviour |
|---|---|---|
| ST-02 | Setting a signal to Red always succeeds | A signal that is already Red is refused with 400 "Signal is already Red" (FR-07: only real changes are applied and logged) |
| ST-03 | The emergency route avoids every High road | Emergency routing uses a smaller congestion penalty because its own signals turn green; it must be no slower than the normal route (FR-15) |
