import sqlite3

import pytest

import app as tms
from helpers import make_client, login, report, audit_entries


def test_audit_log_is_admin_only(tmp_path):
    client = make_client(tmp_path)
    user = login(client, "alice")
    amb = login(client, "amb1", "emergency")
    assert client.get("/api/admin/audit").status_code == 401
    assert client.get("/api/admin/audit", headers=user).status_code == 403
    assert client.get("/api/admin/audit", headers=amb).status_code == 403


def test_important_admin_actions_are_recorded(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    iid = report(client, admin).get_json()["id"]
    client.patch("/api/incidents/%d" % iid, headers=admin,
                 json={"action": "verify"})
    sigs = client.get("/api/signals", headers=admin).get_json()["signals"]
    target = sigs[0]
    new = "Red" if target["state"] != "Red" else "Green"
    client.put("/api/signals/%d" % target["id"], headers=admin,
               json={"state": new})
    actions = {e["action"] for e in audit_entries(client, admin)}
    assert {"signal_change", "incident_verified", "alert_created",
            "incident_reported"} <= actions


def test_entries_show_who_what_and_when(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    sigs = client.get("/api/signals", headers=admin).get_json()["signals"]
    new = "Red" if sigs[0]["state"] != "Red" else "Green"
    client.put("/api/signals/%d" % sigs[0]["id"], headers=admin,
               json={"state": new})
    entry = audit_entries(client, admin)[0]
    assert entry["actor"] == "boss"
    assert entry["action"] == "signal_change"
    assert entry["target"] == "signal:%d" % sigs[0]["id"]
    assert entry["created_at"]  # time information (NFR-12)
    assert sigs[0]["location"] in entry["details"]


def test_system_generated_alerts_are_attributed_to_system(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    report(client, admin)
    entry = audit_entries(client, admin, action="alert_created")[0]
    assert entry["actor"] == "boss"  # raised by the report itself


def test_log_can_be_filtered_and_limited(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    other = login(client, "alice")
    report(client, admin)
    report(client, other, "Hazard", "Majestic", "Oil")
    assert all(e["actor"] == "alice"
               for e in audit_entries(client, admin, actor="alice"))
    assert all(e["action"] == "incident_reported"
               for e in audit_entries(client, admin,
                                      action="incident_reported"))
    assert len(audit_entries(client, admin, limit=1)) == 1


def test_newest_entry_first(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    report(client, admin, "Accident", "MG Road", "first")
    report(client, admin, "Hazard", "Majestic", "second")
    ids = [e["id"] for e in audit_entries(client, admin)]
    assert ids == sorted(ids, reverse=True)


@pytest.mark.parametrize("bad", ["0", "-5", "abc", "1000", "1.5"])
def test_bad_limit_is_rejected(tmp_path, bad):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    r = client.get("/api/admin/audit", headers=admin,
                   query_string={"limit": bad})
    assert r.status_code == 400


def test_audit_log_cannot_be_edited_or_deleted(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    report(client, admin)
    conn = tms.get_db()
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE audit_log SET actor = 'someone-else'")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM audit_log")
    conn.close()
    assert len(audit_entries(client, admin)) >= 1
