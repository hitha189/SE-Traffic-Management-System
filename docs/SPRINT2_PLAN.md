# Sprint 2 Plan: 26 Oct to 30 Oct 2026

Team member A (this document): 11 items, 38 story points.
Team member B: FR-16, FR-17, FR-18, NFR-03, NFR-06, NFR-07, NFR-08, NFR-09, NFR-10, NFR-11.

## Backlog for member A

| Issue | Item | Points | What was built | Files | Tests |
|---|---|---|---|---|---|
| #6 | FR-06 Signal Monitoring | 2 | Admin sees every signal's state, who changed it and when | `signals.py`, `GET /api/signals` | `test_signals.py` |
| #7 | FR-07 Signal Control | 3 | Admin sets Red/Yellow/Green; validated and logged | `signals.py`, `PUT /api/signals/<id>` | `test_signals.py` |
| #9 | FR-09 Incident Management | 5 | Admin verifies, edits and closes incidents; closed ones are locked | `incidents.py`, `PATCH /api/incidents/<id>` | `test_incident_management.py` |
| #10 | FR-10 Traffic Alerts | 5 | Alerts for congestion, accidents, closures, hazards; no duplicates; cleared when over | `alerts.py`, `GET /api/alerts` | `test_alerts.py` |
| #11 | FR-11 Notifications | 5 | Users pick areas; only users in or next to the event area are notified | `notifications.py`, `/api/subscriptions`, `/api/notifications` | `test_notifications.py` |
| #14 | FR-14 Emergency Priority | 5 | Emergency role requests priority; route signals go green; restored at trip end | `emergency.py`, `/api/emergency/priority`, `/api/emergency/requests` | `test_emergency.py` |
| #15 | FR-15 Emergency Route | 3 | Faster, traffic-aware route that avoids roadblocks | `routing.py`, `GET /api/emergency/route` | `test_emergency.py` |
| #20 | FR-20 Audit Logging | 3 | Signal changes, incident updates, alert creation, emergency actions recorded | `audit.py`, `GET /api/admin/audit` | `test_audit.py` |
| #32 | NFR-12 Audit Traceability | 2 | Entries hold actor, action, target, details, UTC time; cannot be edited or deleted | `audit.py` (triggers) | `test_audit.py` |
| #25 | NFR-05 Input Validation and Error Handling | 3 | Type and length checks everywhere, JSON errors, rollback on failure | `validation.py`, `app.py` | `test_validation.py` |
| #22 | NFR-02 Response Time | 2 | 1 second target, timing header, slow-request log | `app.py` | `test_performance.py` |

**Result:** 101 automated tests pass (32 from Sprint 1, 69 new).

## Suggested sprint board (Todo / In progress / Done)

Day 1: NFR-05, FR-20, NFR-12 (foundation: validation and audit) · Day 2: FR-06, FR-07, FR-09 · Day 3: FR-10, FR-11 · Day 4: FR-14, FR-15 · Day 5: NFR-02, video, documentation, freeze.

## Pull request

Branch `sprint2-member-a`. In the PR description write:

    Closes #6, closes #7, closes #9, closes #10, closes #11, closes #14,
    closes #15, closes #20, closes #22, closes #25, closes #32

GitHub then closes all 11 issues when the repo owner merges it. `app.py` and `index.html` hold several features each, so they cannot be split into one clean PR per issue.

## Merge notes for member B

Member B's code will touch the same files, so expect small conflicts. They are easy to fix:

- `app/app.py`: put your new routes in your own block at the end, above `if __name__ == "__main__":`. Also add your `init_` call in `init_db()`.
- `app/storage.py`: the `COUNTED_TABLES` list. Keep both people's table names.
- `app/static/index.html`: add your panels after the admin panel.
- `docs/DEVIATIONS.md`: add your own section at the end.

Data you can read for analytics (FR-17) and reports (FR-18), all in a `conn` from `get_db()`:

| Need | Call |
|---|---|
| Incidents | `incidents.list_incidents(conn)` |
| Signals | `signals.list_signals(conn)` |
| Alerts, including cleared | `alerts.list_alerts(conn, active_only=False)` |
| Roads and congestion | `traffic.list_roads(conn)` |
| Admin actions | `audit.list_logs(conn, limit=500)` |
| Role check on a route | `@require_role("admin")` |

For NFR-07, every feature is a module (`signals.py`, `alerts.py`, `notifications.py`, `emergency.py`, `audit.py`) with its own `init_` function and no imports of `app.py`.

## 2-minute video script (Sprint 2)

Run once: `cd app`, `python seed_demo.py`, `python app.py`, open http://127.0.0.1:5000

| Time | Do | Say |
|---|---|---|
| 0:00 | Log in as `driver1` / `Driver@123`. Tick **MG Road**, click **Save my areas** | "A driver chooses the areas to follow." |
| 0:15 | Report an Accident at **Majestic** | "Reporting an accident raises an alert and notifies users in or next to that area." |
| 0:30 | Show **Traffic alerts** and **Notifications**. Log out | "The alert is visible to everyone, and the subscribed user gets a notification." |
| 0:40 | Log in as `admin1` / `Admin@123`. Click **Verify** on the incident | "The admin reviews and verifies the report." |
| 0:55 | In the signals table, change one signal to Red and click **Set** | "The admin controls signals; every change is validated and logged." |
| 1:10 | Scroll to **audit log** | "Who, what, and when. Entries cannot be edited or deleted." |
| 1:20 | Click **Close** on the incident, then **Refresh alerts** at the top | "Closing the incident clears its alert." Log out |
| 1:30 | Log in as `ambulance1` / `Ambulance@123`. Vehicle `AMB-101`, Majestic to Whitefield, **Preview route** | "The emergency route is faster than the normal one." |
| 1:45 | Click **Request priority**, then **Trip finished** | "Signals along the route turn green, then are restored." |
| 1:55 | Show the terminal: `python -m pytest -q` | "101 automated tests pass." |

## Before you submit

1. Record the video and put it in `docs/sprint2-demo.mp4`.
2. Update story points and assignees on the GitHub Project board.
3. Tick off the documentation: `docs/DEVIATIONS.md` is already updated.
4. Freeze: no new features after the PR is merged.
