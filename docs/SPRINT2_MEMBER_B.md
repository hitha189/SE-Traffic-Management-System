# Sprint 2: member B (26 Oct to 30 Oct 2026)

Issues: #16 FR-16, #17 FR-17, #18 FR-18, #23 NFR-03, #26 NFR-06, #27 NFR-07,
#28 NFR-08, #29 NFR-09, #30 NFR-10, #31 NFR-11. Story points are the ones
already on the project board.

## What was built

| Issue | Item | What it does | Main files | Tests |
|---|---|---|---|---|
| #16 | FR-16 Parking Availability | Everyone sees parking areas, free spaces, status and a fill bar; admins can add areas | `parking.py`, `parking_api.py` | `test_parking.py` |
| #17 | FR-17 Traffic Analytics | Admins see flow, congestion, incidents and patterns (peak hour, trends) | `analytics.py`, `reporting_api.py` | `test_analytics.py` |
| #18 | FR-18 Report Generation | Admins generate a saved report snapshot and download it as text | `reports.py`, `reporting_api.py` | `test_reports.py` |
| #23 | NFR-03 Availability | Public health check, measured availability, recovery after outage | `health.py`, `health_api.py` | `test_availability.py` |
| #26 | NFR-06 Scalability | Roads and parking added without code changes; indexes; capped history | `network.py`, `routing.py`, `network_api.py` | `test_scalability.py` |
| #27 | NFR-07 Modularity | Blueprint features with injected dependencies; architecture rules as tests | `*_api.py` | `test_modularity.py` |
| #28 | NFR-08 Browsers and devices | Responsive page, map optional, real-browser tests | `index.html` | `test_compat_static.py`, `tests/browser/` |
| #29 | NFR-09 Data consistency | Database refuses impossible records; admin consistency check | `consistency.py` | `test_consistency.py` |
| #30 | NFR-10 Data privacy | Minimal data, hidden reporter names, download and delete my data, 30-day route history | `privacy.py`, `privacy_api.py` | `test_privacy.py` |
| #31 | NFR-11 Future integration | Replaceable data sources and a sensor ingest API | `datasources.py`, `integrations_api.py` | `test_integration_ready.py` |

`test_data_management.py` also completes FR-19 (every data category stored and retrievable).

**Test result:** 266 tests pass on a normal computer (the 101 from before plus
165 new), 1 skipped (the browser tests, which need Playwright). With
Playwright and Chromium installed, 10 browser tests also pass.

How each non-functional requirement is met and shown:
`docs/NFR_EVIDENCE.md`. Differences from the submitted documents:
`docs/DEVIATIONS.md` (member B section).

## Two-minute video script (member B)

Start fresh: stop the server, then
`rm -f app/tms.db && cd app && python3 seed_demo.py && python3 app.py`.
Use a private browser window so no saved passwords appear.

| Time | Do | Say |
|---|---|---|
| 0:00 | Log in as `driver1` / `Driver@123`. Scroll to **Parking** | "Drivers see parking areas, free spaces and whether each is Available, Limited or Full." |
| 0:15 | Click **Refresh parking** twice | "The numbers update as cars come and go." |
| 0:25 | Scroll to **My data**, click **Download my data** | "Users can download all their data. We keep only what we need." Log out |
| 0:35 | Log in as `admin1` / `Admin@123`. Click **Refresh traffic** 3 times at the top | "This stores traffic readings for analysis." |
| 0:45 | Click **Show analytics** | "Analytics covers flow, congestion, incidents and patterns." |
| 1:00 | Type a title, **Generate report**, then **Download** | "A report is a saved snapshot that admins can download." |
| 1:15 | **Check system**, then **Check data consistency** | "We measure availability, and the system checks its own records agree." |
| 1:30 | In **Grow the network**: name `Hebbal`, lat `13.0358`, lng `77.597`, connects to `Majestic`, `7.5`, **Add road** | "A new road needs no code change. It joins the map, routes and signals." |
| 1:45 | Show `Hebbal` in the **From** list or the signals table | "Scalability: the system grows through data." |
| 1:55 | Terminal: `python3 -m pytest -q` | "266 tests pass." |

## Likely questions in the final demo

- **Why Blueprints?** Each feature is its own file and receives what it needs
  as an argument, so one can change without touching the others (NFR-07).
- **How do real sensors connect?** Through the ingest API or by registering a
  data source; nothing else changes (NFR-11).
- **What happens if the database is down?** `/api/health` says degraded, other
  requests return a clean error, and it works again as soon as the database
  is back (NFR-03).
- **How do you protect privacy but keep an audit log?** The log keeps only
  usernames; email and routes are deleted with the account (NFR-10, NFR-12).
- **Was it tested in Safari and Firefox?** Chromium was tested automatically;
  the Firefox and WebKit tests are written and run once Playwright is
  installed. Say plainly which you ran.
