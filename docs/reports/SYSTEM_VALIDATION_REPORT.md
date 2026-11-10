# System Validation Report

Traffic Management System · Deliverable 3

This report checks the finished system against the Software Requirements Specification (`Traffic_Management_System_SRS.pdf`): every functional requirement (FR-01 to FR-20) and non-functional requirement (NFR-01 to NFR-12), plus the end-to-end system tests from the Test Plan.

| Item | Value |
|---|---|
| Run at | 2026-11-11 00:03 IST |
| Build | branch `deliverable3-testing`, on top of `main` after PR #49 |
| Tests run | 276 collected, 275 passed, 0 failed, 1 skipped |
| Method | Automated only: pytest with the Flask test client; no manual steps |
| Requirements validated | 32 of 32 have passing automated tests (see notes for NFR-04 and NFR-08) |

## 1. End-to-end system tests (Test Plan ST-01 to ST-03)

| ID | Scenario | Requirements exercised | Result |
|---|---|---|---|
| ST-01 | Login, live traffic data, report an accident, plan Majestic to Whitefield, see alerts, route saved in history | FR-02, FR-04, FR-05, FR-08, FR-10, FR-12, FR-13, FR-19 | **Passed** |
| ST-02 | Admin changes the Majestic signal Red to Green; non-admin and invalid state refused; change shown and audited | FR-03, FR-06, FR-07, FR-20, NFR-05, NFR-12 | **Passed** |
| ST-03 | Ambulance requests priority with heavy traffic; optimised emergency route, signals cleared, request and audit entry stored | FR-03, FR-14, FR-15, FR-20 | **Passed** |

The integration cases IT-01 to IT-03 also pass: IT-01 passed, IT-02 passed, IT-03 passed. Details of all nine cases are in `docs/TEST_CASES.md`.

## 2. Requirement-by-requirement validation

Counts are test runs in the named files (a file can serve more than one requirement, so the column does not add up to the total).

| Req | Requirement | Delivered | Test files | Passed | Failed | Skipped | Validated | Notes |
|---|---|---|---|---|---|---|---|---|
| FR-01 | User registration | Sprint 1 | `test_register`, `test_validation` | 10 | 0 | 0 | Yes |  |
| FR-02 | User login | Sprint 1 | `test_login`, `test_security` | 6 | 0 | 0 | Yes |  |
| FR-03 | Role-based access | Sprint 1 | `test_roles` | 4 | 0 | 0 | Yes |  |
| FR-04 | Traffic monitoring | Sprint 1 | `test_traffic` | 3 | 0 | 0 | Yes |  |
| FR-05 | Live traffic map | Sprint 1 | `test_home`, `test_traffic`, `test_compat_static` | 14 | 0 | 0 | Yes | The map data is tested; drawing the map in a browser is covered by the Playwright tests, skipped in this run |
| FR-06 | Signal monitoring | Sprint 2 (A) | `test_signals` | 9 | 0 | 0 | Yes |  |
| FR-07 | Signal control | Sprint 2 (A) | `test_signals` | 9 | 0 | 0 | Yes |  |
| FR-08 | Incident reporting | Sprint 1 | `test_incidents` | 3 | 0 | 0 | Yes |  |
| FR-09 | Incident management | Sprint 2 (A) | `test_incident_management` | 8 | 0 | 0 | Yes |  |
| FR-10 | Traffic alerts | Sprint 2 (A) | `test_alerts` | 9 | 0 | 0 | Yes |  |
| FR-11 | Notifications | Sprint 2 (A) | `test_notifications` | 8 | 0 | 0 | Yes |  |
| FR-12 | Route planning | Sprint 1 | `test_routing` | 5 | 0 | 0 | Yes |  |
| FR-13 | Congestion-aware routing | Sprint 1 | `test_congestion_routing` | 3 | 0 | 0 | Yes |  |
| FR-14 | Emergency priority | Sprint 2 (A) | `test_emergency` | 12 | 0 | 0 | Yes |  |
| FR-15 | Emergency route | Sprint 2 (A) | `test_emergency` | 12 | 0 | 0 | Yes |  |
| FR-16 | Parking availability | Sprint 2 (B) | `test_parking` | 20 | 0 | 0 | Yes |  |
| FR-17 | Traffic analytics | Sprint 2 (B) | `test_analytics` | 8 | 0 | 0 | Yes |  |
| FR-18 | Report generation | Sprint 2 (B) | `test_reports` | 11 | 0 | 0 | Yes |  |
| FR-19 | Data management | Sprint 1 + 2 | `test_storage`, `test_data_management` | 6 | 0 | 0 | Yes |  |
| FR-20 | Audit logging | Sprint 2 (A) | `test_audit` | 12 | 0 | 0 | Yes |  |
| NFR-01 | Security (hashed passwords, lockout, headers) | Sprint 1 | `test_security`, `test_privacy`, `test_roles` | 23 | 0 | 0 | Yes |  |
| NFR-02 | Response time | Sprint 2 (A) | `test_performance` | 4 | 0 | 0 | Yes | Target of 1 s is our own choice (the SRS gives no number) |
| NFR-03 | Availability | Sprint 2 (B) | `test_availability` | 6 | 0 | 0 | Yes | 99% target is our own choice; measured on one Flask process |
| NFR-04 | Usability | Sprint 1 | `test_compat_static`, `test_home` | 11 | 0 | 0 | Yes | Automated checks cover labels, tap sizes and phone layout; ease of use itself is not measured by a test |
| NFR-05 | Input validation and error handling | Sprint 2 (A) | `test_validation` | 7 | 0 | 0 | Yes |  |
| NFR-06 | Scalability | Sprint 2 (B) | `test_scalability` | 11 | 0 | 0 | Yes |  |
| NFR-07 | Modularity | Sprint 2 (B) | `test_modularity` | 23 | 0 | 0 | Yes |  |
| NFR-08 | Browser and device support | Sprint 2 (B) | `test_compat_static`, `test_browsers` | 10 | 0 | 1 | Yes | Static checks pass; real-browser tests (Chromium, Firefox, WebKit) skipped here because Playwright is not installed |
| NFR-09 | Data consistency | Sprint 2 (B) | `test_consistency` | 25 | 0 | 0 | Yes |  |
| NFR-10 | Data privacy | Sprint 2 (B) | `test_privacy` | 16 | 0 | 0 | Yes |  |
| NFR-11 | Future integration | Sprint 2 (B) | `test_integration_ready` | 33 | 0 | 0 | Yes |  |
| NFR-12 | Audit traceability | Sprint 2 (A) | `test_audit` | 12 | 0 | 0 | Yes |  |

## 3. Known limitations of this validation

These are documented deviations, not failures (see `docs/DEVIATIONS.md`):

- One Flask application instead of separate microservices; modules keep the service boundaries (NFR-07).
- Traffic and parking data come from a simulator, so the tests show the features work, not real-world traffic behaviour.
- Response-time (NFR-02) and availability (NFR-03) targets were set by the team because the SRS gives no numbers.
- Firefox and Safari (WebKit) are only validated where the Playwright tests are run; they were skipped in this run.
- The separate Security Requirements document (SR-01 onwards) was not validated item by item in this round.

## 4. Conclusion

All 275 automated tests that ran passed, including the Test Plan's three system tests. Every SRS requirement has passing automated evidence. For NFR-04 and NFR-08 that evidence is static checks of the page; real-browser runs were skipped. The system is validated against the SRS within the limitations above.
