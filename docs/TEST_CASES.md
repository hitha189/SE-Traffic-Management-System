# Test Case Document (updated after Sprint 1 and Sprint 2)

Traffic Management System · Deliverable 3 · test run of 10 Nov 2026

This document replaces the test case table in
`Traffic_Management_System_Test_Plan.pdf`. That plan was written before
development and lists 9 cases, all marked "Not Run". During the two sprints
the system changed, so the cases were updated and every case is now an
automated pytest test with a recorded result.

**How to run every case**

    python3 -m pip install -r requirements.txt
    python3 -m pytest -q

**Result of this run:** 276 tests collected, 275 passed, 0 failed,
1 skipped. The skip is the Playwright browser module
(`tests/browser/test_browsers.py`), which only runs where Playwright and its
browsers are installed (see `docs/NFR_EVIDENCE.md`, NFR-08).

## 1. What changed since the original Test Plan

| Change | Why |
|---|---|
| All 9 original cases (UT-01 to ST-03) are now automated in `tests/test_test_plan.py` and were run | The plan said "Not executed — manual testing required" |
| UT-02 now also checks a valid username with a wrong password, not only an unknown user | Both must be refused with the same message, so the error does not reveal which accounts exist (NFR-01) |
| IT-01 checks the data behind the map (road levels, coordinates, incident and congestion alerts) | The live map draws whatever `/api/traffic` and `/api/alerts` return; the drawing itself is checked by the Playwright tests |
| IT-02 "High on Route A" is made concrete: every road on the normal route is set to High, and the new route must avoid all of them | Gives a pass/fail rule instead of "a suitable route" |
| IT-03 "Road closure" uses incident type **Roadblock**, which raises a **Closure** alert; a second user in an unrelated area must get nothing | FR-11 says only relevant users are notified |
| ST-02 "Junction-01" is the **Majestic** signal; setting a signal to the state it already has is refused (400); a non-admin is refused (403) | Signals in the prototype are named after the junction they control |
| ST-03 "City Hospital" is replaced by **Whitefield**; "optimised" means an emergency route that uses live traffic and is no slower than the normal route, with route signals cleared | Destinations must be places on the simulated road network; the emergency route uses a smaller congestion penalty because its signals turn green, so it may still use a busy road |
| About 200 new cases were added for the Sprint 1 and Sprint 2 features (section 3) | Every FR-01 to FR-20 and NFR-01 to NFR-12 has at least one automated case |

## 2. Original Test Plan cases, updated and executed

| ID | Module | Description | Pre-conditions | Steps | Test data | Expected result | Actual result | Result | Automated test |
|---|---|---|---|---|---|---|---|---|---|
| UT-01 | Authentication | Login with valid credentials | Registered account | 1. Register 2. POST /api/login 3. Use the token on /api/traffic | valid_user / Valid@123 | User authenticated; dashboard data opens | 200 "Login successful", role user, token accepted by /api/traffic | Pass | `test_ut01_login_with_valid_credentials` |
| UT-02 | Authentication | Login refused with invalid credentials | Registered account exists | 1. Login with unknown user 2. Login with real user and wrong password | invalid_user / wrong123; valid_user / wrong123 | Login rejected with a clear error | 401 "Invalid credentials" both times, no token | Pass | `test_ut02_login_rejected_with_invalid_credentials` |
| UT-03 | Incident reporting | Submit a valid incident | User logged in | 1. POST /api/incidents 2. GET /api/incidents | Accident, MG Road, "Two vehicles blocking lane" | Stored, success message | 201 "Incident reported"; stored with the same type, place, description | Pass | `test_ut03_valid_incident_report_is_stored` |
| IT-01 | Traffic data and live map | Traffic data and incidents reach the map | User logged in; simulator held still | 1. Set MG Road High 2. Report accident 3. GET /api/traffic and /api/alerts | MG Road, High, Accident | Map data shows congestion and incident | MG Road "High" with lat/lng; Accident and Congestion alerts at MG Road | Pass | `test_it01_traffic_data_and_incidents_reach_the_map` |
| IT-02 | Route planning | Route uses traffic data | User logged in | 1. Plan Majestic to Whitefield 2. Set every road on that route High 3. Plan again | Majestic to Whitefield; High on route A | A least-congested route is shown | Second route is congestion-aware and shares no middle road with the first | Pass | `test_it02_route_planning_avoids_high_traffic` |
| IT-03 | Alerts and notifications | Traffic event alerts relevant users | Two users subscribed to different areas | 1. Report Roadblock at MG Road 2. Check alerts and both users' notifications | Road closure, MG Road | Relevant users get the alert | Closure alert at MG Road; MG Road subscriber notified; Silk Board subscriber not | Pass | `test_it03_road_closure_notifies_relevant_users` |
| ST-01 | Traffic Management System | End-to-end monitoring and route planning | Fresh system | 1. Login 2. Live map 3. Report accident 4. Route 5. Alerts 6. History | Majestic to Whitefield, Accident | Authenticated, map data, route, alerts shown | All steps succeed; route saved in history | Pass | `test_st01_end_to_end_monitoring_and_route_planning` |
| ST-02 | Traffic administration | Admin signal change is authorised, stored and audited | Admin and normal user | 1. Open signals 2. Majestic signal to Red 3. Non-admin and invalid state tried 4. Red to Green 5. Audit log | Junction Majestic, Red to Green | Change validated, stored, shown, audited | 403 for non-admin, 400 for "Blue", 200 for Green; audit entry by admin1 | Pass | `test_st02_admin_signal_change_is_authorised_stored_and_audited` |
| ST-03 | Emergency vehicle priority | Priority and optimised route | Emergency user; MG Road and Indiranagar High | 1. Request priority 2. Check route 3. Check request list and audit log | Ambulance-01, Majestic to Whitefield, High | Request accepted, optimised route, action logged | 201; emergency, congestion-aware route no slower than normal; signals cleared; request and audit entry recorded | Pass | `test_st03_emergency_priority_and_optimised_route` |

## 3. Test cases added during the sprints

IDs are `<requirement>-<number>`. Each row is one automated test function;
"Pass (n runs)" means the test runs once per parameter. Sprint 2 (A) is
Member A's work (PR #47), Sprint 2 (B) is Member B's work (PR #49).

**Totals:** 208 test functions in this section plus the 9 in section 2:
202 pass here, 6 are the Playwright browser functions that were skipped.

NFR-04 (usability) has no test file of its own. It is covered by the
automated checks in `test_compat_static.py` (form labels, tap-size buttons,
layout that fits a phone). All testing in this document is automated.

### FR-01: Registration

File `tests/test_register.py` · added in Sprint 1 · 3 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| FR-01-01 | Register valid | `test_register_valid` | Pass |
| FR-01-02 | Register missing details | `test_register_missing_details` | Pass |
| FR-01-03 | Register duplicate | `test_register_duplicate` | Pass |

### FR-02: Authentication

File `tests/test_login.py` · added in Sprint 1 · 3 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| FR-02-01 | Login valid | `test_login_valid` | Pass |
| FR-02-02 | Login wrong password | `test_login_wrong_password` | Pass |
| FR-02-03 | Login unknown user | `test_login_unknown_user` | Pass |

### FR-03: Role-based access

File `tests/test_roles.py` · added in Sprint 1 · 4 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| FR-03-01 | No token is rejected | `test_no_token_is_rejected` | Pass |
| FR-03-02 | Normal user cannot access admin | `test_normal_user_cannot_access_admin` | Pass |
| FR-03-03 | Admin can access admin | `test_admin_can_access_admin` | Pass |
| FR-03-04 | Emergency role access | `test_emergency_role_access` | Pass |

### FR-04: Traffic monitoring

File `tests/test_traffic.py` · added in Sprint 1 · 3 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| FR-04-01 | Traffic requires login | `test_traffic_requires_login` | Pass |
| FR-04-02 | Traffic returns roads with levels | `test_traffic_returns_roads_with_levels` | Pass |
| FR-04-03 | Traffic includes mg road | `test_traffic_includes_mg_road` | Pass |

### FR-05: Live traffic map

File `tests/test_home.py` · added in Sprint 1 · 1 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| FR-05-01 | Home page loads | `test_home_page_loads` | Pass |

### FR-06, FR-07: Signal monitoring and control

File `tests/test_signals.py` · added in Sprint 2 (A) · 9 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| FR-06-01 | Signals require login | `test_signals_require_login` | Pass |
| FR-06-02 | Normal user cannot view signals | `test_normal_user_cannot_view_signals` | Pass |
| FR-06-03 | Admin can view all signals | `test_admin_can_view_all_signals` | Pass |
| FR-06-04 | Admin can change signal and it is logged | `test_admin_can_change_signal_and_it_is_logged` | Pass |
| FR-06-05 | Invalid state is rejected and not applied | `test_invalid_state_is_rejected_and_not_applied` | Pass |
| FR-06-06 | Unchanged state is rejected | `test_unchanged_state_is_rejected` | Pass |
| FR-06-07 | Unknown signal is 404 | `test_unknown_signal_is_404` | Pass |
| FR-06-08 | Non admin cannot change signal | `test_non_admin_cannot_change_signal` | Pass |
| FR-06-09 | Missing body is 400 | `test_missing_body_is_400` | Pass |

### FR-08: Incident reporting

File `tests/test_incidents.py` · added in Sprint 1 · 3 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| FR-08-01 | Report incident valid | `test_report_incident_valid` | Pass |
| FR-08-02 | Report incident invalid | `test_report_incident_invalid` | Pass |
| FR-08-03 | Report incident requires login | `test_report_incident_requires_login` | Pass |

### FR-09: Incident management

File `tests/test_incident_management.py` · added in Sprint 2 (A) · 8 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| FR-09-01 | Admin can verify incident | `test_admin_can_verify_incident` | Pass |
| FR-09-02 | Admin can update incident | `test_admin_can_update_incident` | Pass |
| FR-09-03 | Admin can close incident | `test_admin_can_close_incident` | Pass |
| FR-09-04 | Closed incident cannot change | `test_closed_incident_cannot_change` | Pass |
| FR-09-05 | Cannot verify twice | `test_cannot_verify_twice` | Pass |
| FR-09-06 | Normal user cannot manage incidents | `test_normal_user_cannot_manage_incidents` | Pass |
| FR-09-07 | Invalid requests | `test_invalid_requests` | Pass |
| FR-09-08 | Updates are logged | `test_updates_are_logged` | Pass |

### FR-10: Traffic alerts

File `tests/test_alerts.py` · added in Sprint 2 (A) · 9 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| FR-10-01 | Alerts require login | `test_alerts_require_login` | Pass |
| FR-10-02 | Accident creates alert | `test_accident_creates_alert` | Pass |
| FR-10-03 | Roadblock is a closure and hazard is a hazard | `test_roadblock_is_a_closure_and_hazard_is_a_hazard` | Pass |
| FR-10-04 | Other incidents raise no alert | `test_other_incidents_raise_no_alert` | Pass |
| FR-10-05 | Heavy congestion raises alert without duplicates | `test_heavy_congestion_raises_alert_without_duplicates` | Pass |
| FR-10-06 | Congestion alert clears when traffic recovers | `test_congestion_alert_clears_when_traffic_recovers` | Pass |
| FR-10-07 | Light traffic raises no alert | `test_light_traffic_raises_no_alert` | Pass |
| FR-10-08 | Closing incident clears its alert | `test_closing_incident_clears_its_alert` | Pass |
| FR-10-09 | Editing incident updates its alert | `test_editing_incident_updates_its_alert` | Pass |

### FR-11: Notifications

File `tests/test_notifications.py` · added in Sprint 2 (A) · 8 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| FR-11-01 | User can choose areas | `test_user_can_choose_areas` | Pass |
| FR-11-02 | Invalid areas rejected | `test_invalid_areas_rejected` | Pass |
| FR-11-03 | Subscriber is notified for selected area | `test_subscriber_is_notified_for_selected_area` | Pass |
| FR-11-04 | Subscriber is notified for nearby area | `test_subscriber_is_notified_for_nearby_area` | Pass |
| FR-11-05 | Unrelated user is not notified | `test_unrelated_user_is_not_notified` | Pass |
| FR-11-06 | Other incident does not notify | `test_other_incident_does_not_notify` | Pass |
| FR-11-07 | Mark read and ownership | `test_mark_read_and_ownership` | Pass |
| FR-11-08 | Notifications require login | `test_notifications_require_login` | Pass |

### FR-12: Route planning

File `tests/test_routing.py` · added in Sprint 1 · 5 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| FR-12-01 | Find route majestic to whitefield | `test_find_route_majestic_to_whitefield` | Pass |
| FR-12-02 | Unknown place returns none | `test_unknown_place_returns_none` | Pass |
| FR-12-03 | Route api valid | `test_route_api_valid` | Pass |
| FR-12-04 | Route api invalid | `test_route_api_invalid` | Pass |
| FR-12-05 | Route requires login | `test_route_requires_login` | Pass |

### FR-13: Congestion-aware routing

File `tests/test_congestion_routing.py` · added in Sprint 1 · 3 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| FR-13-01 | Quiet roads keep shortest route | `test_quiet_roads_keep_shortest_route` | Pass |
| FR-13-02 | Heavy congestion changes route | `test_heavy_congestion_changes_route` | Pass |
| FR-13-03 | Route api uses congestion data | `test_route_api_uses_congestion_data` | Pass |

### FR-14, FR-15: Emergency priority and route

File `tests/test_emergency.py` · added in Sprint 2 (A) · 12 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| FR-14-01 | Emergency vehicle can request priority | `test_emergency_vehicle_can_request_priority` | Pass |
| FR-14-02 | Unauthorized users cannot request priority | `test_unauthorized_users_cannot_request_priority` | Pass |
| FR-14-03 | Priority rejects bad input | `test_priority_rejects_bad_input` | Pass |
| FR-14-04 | Priority turns route signals green and logs | `test_priority_turns_route_signals_green_and_logs` | Pass |
| FR-14-05 | Completing request restores signals | `test_completing_request_restores_signals` | Pass |
| FR-14-06 | Only owner or admin can complete | `test_only_owner_or_admin_can_complete` | Pass |
| FR-14-07 | Request lists are scoped | `test_request_lists_are_scoped` | Pass |
| FR-14-08 | Emergency route is faster than normal route | `test_emergency_route_is_faster_than_normal_route` | Pass |
| FR-14-09 | Emergency route uses traffic data | `test_emergency_route_uses_traffic_data` | Pass |
| FR-14-10 | Emergency route avoids roadblock when it can | `test_emergency_route_avoids_roadblock_when_it_can` | Pass |
| FR-14-11 | Emergency route falls back when roadblock is unavoidable | `test_emergency_route_falls_back_when_roadblock_is_unavoidable` | Pass |
| FR-14-12 | Emergency route access and validation | `test_emergency_route_access_and_validation` | Pass |

### FR-16: Parking availability

File `tests/test_parking.py` · added in Sprint 2 (B) · 12 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| FR-16-01 | Parking requires login | `test_parking_requires_login` | Pass |
| FR-16-02 | Every role can view parking | `test_every_role_can_view_parking` | Pass |
| FR-16-03 | Each area shows what drivers need | `test_each_area_shows_what_drivers_need` | Pass |
| FR-16-04 | Spaces always stay within capacity | `test_spaces_always_stay_within_capacity` | Pass |
| FR-16-05 | Filter by location | `test_filter_by_location` | Pass |
| FR-16-06 | Summary matches the areas | `test_summary_matches_the_areas` | Pass |
| FR-16-07 | Status labels | `test_status_labels` | Pass |
| FR-16-08 | Admin can add a parking area | `test_admin_can_add_a_parking_area` | Pass |
| FR-16-09 | Bad parking area is rejected | `test_bad_parking_area_is_rejected` | Pass (9 runs) |
| FR-16-10 | Duplicate area is 409 | `test_duplicate_area_is_409` | Pass |
| FR-16-11 | Only admin can add areas | `test_only_admin_can_add_areas` | Pass |
| FR-16-12 | Database refuses impossible parking numbers | `test_database_refuses_impossible_parking_numbers` | Pass |

### FR-17: Traffic analytics

File `tests/test_analytics.py` · added in Sprint 2 (B) · 8 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| FR-17-01 | Analytics is admin only | `test_analytics_is_admin_only` | Pass |
| FR-17-02 | All four areas are always present | `test_all_four_areas_are_always_present` | Pass |
| FR-17-03 | Empty history is explained not an error | `test_empty_history_is_explained_not_an_error` | Pass |
| FR-17-04 | Traffic flow reflects current conditions | `test_traffic_flow_reflects_current_conditions` | Pass |
| FR-17-05 | Congestion ranking uses history | `test_congestion_ranking_uses_history` | Pass |
| FR-17-06 | Patterns find peak hour and trends | `test_patterns_find_peak_hour_and_trends` | Pass |
| FR-17-07 | Incident statistics | `test_incident_statistics` | Pass |
| FR-17-08 | Every refresh adds history and it stays bounded | `test_every_refresh_adds_history_and_it_stays_bounded` | Pass |

### FR-18: Report generation

File `tests/test_reports.py` · added in Sprint 2 (B) · 9 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| FR-18-01 | Admin can generate a report | `test_admin_can_generate_a_report` | Pass |
| FR-18-02 | Report is stored and listed | `test_report_is_stored_and_listed` | Pass |
| FR-18-03 | Report is a snapshot that does not change | `test_report_is_a_snapshot_that_does_not_change` | Pass |
| FR-18-04 | Report gathers data from every feature | `test_report_gathers_data_from_every_feature` | Pass |
| FR-18-05 | Report can be downloaded as text | `test_report_can_be_downloaded_as_text` | Pass |
| FR-18-06 | Generating a report is logged | `test_generating_a_report_is_logged` | Pass |
| FR-18-07 | Reports are closed to everyone but admins | `test_reports_are_closed_to_everyone_but_admins` | Pass |
| FR-18-08 | Bad title is rejected | `test_bad_title_is_rejected` | Pass (3 runs) |
| FR-18-09 | Unknown report and bad format | `test_unknown_report_and_bad_format` | Pass |

### FR-19: Data management

File `tests/test_storage.py` · added in Sprint 1 · 4 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| FR-19-01 | Route is saved in history | `test_route_is_saved_in_history` | Pass |
| FR-19-02 | History requires login | `test_history_requires_login` | Pass |
| FR-19-03 | Summary blocked for normal user | `test_summary_blocked_for_normal_user` | Pass |
| FR-19-04 | Summary for admin | `test_summary_for_admin` | Pass |

### FR-19: Data management

File `tests/test_data_management.py` · added in Sprint 2 (B) · 2 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| FR-19b-01 | Every data category is stored and retrievable | `test_every_data_category_is_stored_and_retrievable` | Pass |
| FR-19b-02 | Data survives a restart and seeds are not duplicated | `test_data_survives_a_restart_and_seeds_are_not_duplicated` | Pass |

### FR-20, NFR-12: Audit logging and traceability

File `tests/test_audit.py` · added in Sprint 2 (A) · 8 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| FR-20-01 | Audit log is admin only | `test_audit_log_is_admin_only` | Pass |
| FR-20-02 | Important admin actions are recorded | `test_important_admin_actions_are_recorded` | Pass |
| FR-20-03 | Entries show who what and when | `test_entries_show_who_what_and_when` | Pass |
| FR-20-04 | System generated alerts are attributed to system | `test_system_generated_alerts_are_attributed_to_system` | Pass |
| FR-20-05 | Log can be filtered and limited | `test_log_can_be_filtered_and_limited` | Pass |
| FR-20-06 | Newest entry first | `test_newest_entry_first` | Pass |
| FR-20-07 | Bad limit is rejected | `test_bad_limit_is_rejected` | Pass (5 runs) |
| FR-20-08 | Audit log cannot be edited or deleted | `test_audit_log_cannot_be_edited_or_deleted` | Pass |

### NFR-01: Security controls

File `tests/test_security.py` · added in Sprint 1 · 3 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| NFR-01-01 | Security headers present | `test_security_headers_present` | Pass |
| NFR-01-02 | Account locks after repeated failures | `test_account_locks_after_repeated_failures` | Pass |
| NFR-01-03 | Successful login resets failures | `test_successful_login_resets_failures` | Pass |

### NFR-02: Response time

File `tests/test_performance.py` · added in Sprint 2 (A) · 4 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| NFR-02-01 | Target is defined | `test_target_is_defined` | Pass |
| NFR-02-02 | Responses carry timing header | `test_responses_carry_timing_header` | Pass |
| NFR-02-03 | Normal requests meet the target | `test_normal_requests_meet_the_target` | Pass |
| NFR-02-04 | Expected load stays within target | `test_expected_load_stays_within_target` | Pass |

### NFR-03: Availability

File `tests/test_availability.py` · added in Sprint 2 (B) · 6 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| NFR-03-01 | Health check needs no login | `test_health_check_needs_no_login` | Pass |
| NFR-03-02 | Health reports an outage and recovers without restart | `test_health_reports_an_outage_and_recovers_without_restart` | Pass |
| NFR-03-03 | Other requests fail cleanly during an outage | `test_other_requests_fail_cleanly_during_an_outage` | Pass |
| NFR-03-04 | Status shows availability to admins only | `test_status_shows_availability_to_admins_only` | Pass |
| NFR-03-05 | Normal operation has no server errors | `test_normal_operation_has_no_server_errors` | Pass |
| NFR-03-06 | Server errors are counted and service continues | `test_server_errors_are_counted_and_service_continues` | Pass |

### NFR-05: Input validation and errors

File `tests/test_validation.py` · added in Sprint 2 (A) · 7 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| NFR-05-01 | Wrong types in register and login give 400 not 500 | `test_wrong_types_in_register_and_login_give_400_not_500` | Pass |
| NFR-05-02 | Non object json is rejected cleanly | `test_non_object_json_is_rejected_cleanly` | Pass |
| NFR-05-03 | Incident field types and lengths | `test_incident_field_types_and_lengths` | Pass |
| NFR-05-04 | Errors are json not html | `test_errors_are_json_not_html` | Pass |
| NFR-05-05 | Oversized request is rejected | `test_oversized_request_is_rejected` | Pass |
| NFR-05-06 | Failed action leaves data unchanged | `test_failed_action_leaves_data_unchanged` | Pass |
| NFR-05-07 | Failed incident report creates no orphan record | `test_failed_incident_report_creates_no_orphan_record` | Pass |

### NFR-06: Scalability

File `tests/test_scalability.py` · added in Sprint 2 (B) · 11 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| NFR-06-01 | A new road appears everywhere | `test_a_new_road_appears_everywhere` | Pass |
| NFR-06-02 | Alerts and notifications work on a new road | `test_alerts_and_notifications_work_on_a_new_road` | Pass |
| NFR-06-03 | Emergency routing uses a new road | `test_emergency_routing_uses_a_new_road` | Pass |
| NFR-06-04 | New road is saved and logged | `test_new_road_is_saved_and_logged` | Pass |
| NFR-06-05 | Bad roads are rejected | `test_bad_roads_are_rejected` | Pass |
| NFR-06-06 | Only admins can add roads | `test_only_admins_can_add_roads` | Pass |
| NFR-06-07 | Database network matches the built in one | `test_database_network_matches_the_built_in_one` | Pass |
| NFR-06-08 | Sixty more roads still respond within the target | `test_sixty_more_roads_still_respond_within_the_target` | Pass |
| NFR-06-09 | Large amounts of data stay fast | `test_large_amounts_of_data_stay_fast` | Pass |
| NFR-06-10 | Thousands of users do not slow login | `test_thousands_of_users_do_not_slow_login` | Pass |
| NFR-06-11 | Indexes exist for the busy tables | `test_indexes_exist_for_the_busy_tables` | Pass |

### NFR-07: Modularity

File `tests/test_modularity.py` · added in Sprint 2 (B) · 10 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| NFR-07-01 | No feature module imports the main app file | `test_no_feature_module_imports_the_main_app_file` | Pass |
| NFR-07-02 | No circular dependencies | `test_no_circular_dependencies` | Pass |
| NFR-07-03 | Business logic does not depend on the web framework | `test_business_logic_does_not_depend_on_the_web_framework` | Pass |
| NFR-07-04 | Blueprints do not depend on each other | `test_blueprints_do_not_depend_on_each_other` | Pass |
| NFR-07-05 | There is one blueprint per feature group | `test_there_is_one_blueprint_per_feature_group` | Pass |
| NFR-07-06 | Each blueprint is built from injected dependencies | `test_each_blueprint_is_built_from_injected_dependencies` | Pass (6 runs) |
| NFR-07-07 | Blueprint names are unique | `test_blueprint_names_are_unique` | Pass |
| NFR-07-08 | Dependencies stay within the agreed limits | `test_dependencies_stay_within_the_agreed_limits` | Pass (9 runs) |
| NFR-07-09 | Importing a feature does not load the rest of the system | `test_importing_a_feature_does_not_load_the_rest_of_the_system` | Pass |
| NFR-07-10 | A feature runs on its own with stand in dependencies | `test_a_feature_runs_on_its_own_with_stand_in_dependencies` | Pass |

### NFR-04, NFR-08: Usability and browser support

File `tests/test_compat_static.py` · added in Sprint 2 (B) · 10 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| NFR-04-01 | Page declares standard html and encoding | `test_page_declares_standard_html_and_encoding` | Pass |
| NFR-04-02 | Page scales to phones and tablets | `test_page_scales_to_phones_and_tablets` | Pass |
| NFR-04-03 | Layout has no fixed wide elements | `test_layout_has_no_fixed_wide_elements` | Pass |
| NFR-04-04 | Form fields have labels | `test_form_fields_have_labels` | Pass |
| NFR-04-05 | Text and buttons are big enough to tap | `test_text_and_buttons_are_big_enough_to_tap` | Pass |
| NFR-04-06 | Only secure external resources are used | `test_only_secure_external_resources_are_used` | Pass |
| NFR-04-07 | Page works without modern only tricks | `test_page_works_without_modern_only_tricks` | Pass |
| NFR-04-08 | A broken map library does not stop the app | `test_a_broken_map_library_does_not_stop_the_app` | Pass |
| NFR-04-09 | Server sends the page as html utf8 | `test_server_sends_the_page_as_html_utf8` | Pass |
| NFR-04-10 | Supported browsers are documented | `test_supported_browsers_are_documented` | Pass |

### NFR-08: Real-browser checks (Playwright)

File `tests/browser/test_browsers.py` · added in Sprint 2 (B) · 6 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| NFR-08-01 | Pages fit the screen and the user journey works | `test_pages_fit_the_screen_and_the_user_journey_works` | Skipped |
| NFR-08-02 | Buttons are big enough to tap | `test_buttons_are_big_enough_to_tap` | Skipped |
| NFR-08-03 | Everything but the map works if the map cannot load | `test_everything_but_the_map_works_if_the_map_cannot_load` | Skipped |
| NFR-08-04 | Admin tools work and a report downloads | `test_admin_tools_work_and_a_report_downloads` | Skipped |
| NFR-08-05 | Phone and tablet emulation | `test_phone_and_tablet_emulation` | Skipped |
| NFR-08-06 | The real interactive map loads | `test_the_real_interactive_map_loads` | Skipped |

### NFR-09: Data consistency

File `tests/test_consistency.py` · added in Sprint 2 (B) · 9 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| NFR-09-01 | Database refuses bad records | `test_database_refuses_bad_records` | Pass (12 runs) |
| NFR-09-02 | Closed incidents are frozen but the reporter can be erased | `test_closed_incidents_are_frozen_but_the_reporter_can_be_erased` | Pass |
| NFR-09-03 | A verified incident cannot go back to reported | `test_a_verified_incident_cannot_go_back_to_reported` | Pass |
| NFR-09-04 | Triggers are installed once and on every restart | `test_triggers_are_installed_once_and_on_every_restart` | Pass |
| NFR-09-05 | A fresh system is consistent | `test_a_fresh_system_is_consistent` | Pass |
| NFR-09-06 | Everyday operations keep the records consistent | `test_everyday_operations_keep_the_records_consistent` | Pass |
| NFR-09-07 | The check finds records that disagree | `test_the_check_finds_records_that_disagree` | Pass (6 runs) |
| NFR-09-08 | Congestion alert mismatch is found | `test_congestion_alert_mismatch_is_found` | Pass |
| NFR-09-09 | The check is admin only | `test_the_check_is_admin_only` | Pass |

### NFR-10: Data privacy

File `tests/test_privacy.py` · added in Sprint 2 (B) · 16 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| NFR-10-01 | Accounts hold only the details the srs needs | `test_accounts_hold_only_the_details_the_srs_needs` | Pass |
| NFR-10-02 | No table stores phone address or gps | `test_no_table_stores_phone_address_or_gps` | Pass |
| NFR-10-03 | User locations are named areas not coordinates | `test_user_locations_are_named_areas_not_coordinates` | Pass |
| NFR-10-04 | Registration does not ask for anything extra | `test_registration_does_not_ask_for_anything_extra` | Pass |
| NFR-10-05 | Passwords are stored as hashes | `test_passwords_are_stored_as_hashes` | Pass |
| NFR-10-06 | Email and hash never appear in admin or shared data | `test_email_and_hash_never_appear_in_admin_or_shared_data` | Pass |
| NFR-10-07 | Only admins see who reported an incident | `test_only_admins_see_who_reported_an_incident` | Pass |
| NFR-10-08 | Route history is private to its owner | `test_route_history_is_private_to_its_owner` | Pass |
| NFR-10-09 | Location data is not kept forever | `test_location_data_is_not_kept_forever` | Pass |
| NFR-10-10 | Old routes are removed automatically at startup | `test_old_routes_are_removed_automatically_at_startup` | Pass |
| NFR-10-11 | User can download all their data | `test_user_can_download_all_their_data` | Pass |
| NFR-10-12 | Export needs login | `test_export_needs_login` | Pass |
| NFR-10-13 | Deleting an account removes personal data | `test_deleting_an_account_removes_personal_data` | Pass |
| NFR-10-14 | Deleting needs the right password | `test_deleting_needs_the_right_password` | Pass |
| NFR-10-15 | Admins cannot delete themselves by accident | `test_admins_cannot_delete_themselves_by_accident` | Pass |
| NFR-10-16 | Emergency users data is erased too | `test_emergency_users_data_is_erased_too` | Pass |

### NFR-11: Future integration

File `tests/test_integration_ready.py` · added in Sprint 2 (B) · 12 cases

| ID | Test case | Automated test | Result |
|---|---|---|---|
| NFR-11-01 | Admin can see sources and what is planned | `test_admin_can_see_sources_and_what_is_planned` | Pass |
| NFR-11-02 | Integration routes are admin only | `test_integration_routes_are_admin_only` | Pass |
| NFR-11-03 | A sensor can push traffic readings | `test_a_sensor_can_push_traffic_readings` | Pass |
| NFR-11-04 | Heavy sensor readings raise alerts like any other data | `test_heavy_sensor_readings_raise_alerts_like_any_other_data` | Pass |
| NFR-11-05 | A sensor can push parking readings | `test_a_sensor_can_push_parking_readings` | Pass |
| NFR-11-06 | Real sensors switch the simulator off | `test_real_sensors_switch_the_simulator_off` | Pass |
| NFR-11-07 | A different source can replace the simulator without other changes | `test_a_different_source_can_replace_the_simulator_without_other_changes` | Pass |
| NFR-11-08 | A new data type can be added without editing existing code | `test_a_new_data_type_can_be_added_without_editing_existing_code` | Pass |
| NFR-11-09 | Bad readings are rejected | `test_bad_readings_are_rejected` | Pass (16 runs) |
| NFR-11-10 | Source id must be clean | `test_source_id_must_be_clean` | Pass (7 runs) |
| NFR-11-11 | A batch is all or nothing | `test_a_batch_is_all_or_nothing` | Pass |
| NFR-11-12 | Every push is logged with its source | `test_every_push_is_logged_with_its_source` | Pass |
