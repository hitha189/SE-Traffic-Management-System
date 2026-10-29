import pytest

from helpers import make_client, login, report, audit_entries


def make_report(client, admin, **body):
    return client.post("/api/admin/reports", headers=admin, json=body)


def test_admin_can_generate_a_report(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    r = make_report(client, admin)
    assert r.status_code == 201
    rep = r.get_json()["report"]
    assert rep["id"] >= 1 and rep["generated_by"] == "boss"
    assert rep["title"] == "Traffic management report"
    content = rep["content"]
    for section in ("analytics", "signals", "alerts", "parking",
                    "emergency", "open_incidents"):
        assert section in content
    for area in ("traffic_flow", "congestion", "incidents", "patterns"):
        assert area in content["analytics"]


def test_report_is_stored_and_listed(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    rid = make_report(client, admin, title="Weekly").get_json()["report"]["id"]
    listed = client.get("/api/admin/reports", headers=admin).get_json()
    assert [r["id"] for r in listed["reports"]] == [rid]
    assert listed["reports"][0]["title"] == "Weekly"
    assert "content" not in listed["reports"][0]
    got = client.get("/api/admin/reports/%d" % rid, headers=admin).get_json()
    assert got["report"]["content"]["title"] == "Weekly"


def test_report_is_a_snapshot_that_does_not_change(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    user = login(client, "alice")
    rid = make_report(client, admin).get_json()["report"]["id"]
    report(client, user, "Accident", "MG Road", "Crash")
    old = client.get("/api/admin/reports/%d" % rid,
                     headers=admin).get_json()["report"]["content"]
    assert old["analytics"]["incidents"]["total"] == 0
    new = make_report(client, admin).get_json()["report"]["content"]
    assert new["analytics"]["incidents"]["total"] == 1
    assert new["alerts"]["by_kind"] == {"Accident": 1}
    assert new["open_incidents"][0]["location"] == "MG Road"


def test_report_gathers_data_from_every_feature(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    content = make_report(client, admin).get_json()["report"]["content"]
    assert content["signals"]["total"] == 6
    assert sum(content["signals"]["by_state"].values()) == 6
    assert content["parking"]["areas"] == 6
    assert content["parking"]["total_capacity"] == 950


def test_report_can_be_downloaded_as_text(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    user = login(client, "alice")
    report(client, user, "Hazard", "Majestic", "Oil on road")
    rid = make_report(client, admin, title="Morning report"
                      ).get_json()["report"]["id"]
    r = client.get("/api/admin/reports/%d?format=text" % rid, headers=admin)
    assert r.status_code == 200
    assert r.mimetype == "text/plain"
    assert "attachment" in r.headers["Content-Disposition"]
    text = r.get_data(as_text=True)
    for heading in ("MORNING REPORT", "1. TRAFFIC FLOW", "2. CONGESTION",
                    "3. INCIDENTS", "4. TRAFFIC PATTERNS", "5. SYSTEM STATE",
                    "OPEN INCIDENTS"):
        assert heading in text
    assert "Hazard at Majestic" in text


def test_generating_a_report_is_logged(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    make_report(client, admin, title="Audit me")
    log = audit_entries(client, admin, action="report_generated")
    assert len(log) == 1
    assert log[0]["actor"] == "boss" and log[0]["details"] == "Audit me"


def test_reports_are_closed_to_everyone_but_admins(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    rid = make_report(client, admin).get_json()["report"]["id"]
    for name, role in (("alice", None), ("amb1", "emergency")):
        h = login(client, name, role)
        assert make_report(client, h).status_code == 403
        assert client.get("/api/admin/reports", headers=h).status_code == 403
        assert client.get("/api/admin/reports/%d" % rid,
                          headers=h).status_code == 403
        assert client.get("/api/admin/reports/%d?format=text" % rid,
                          headers=h).status_code == 403
    assert client.post("/api/admin/reports").status_code == 401
    assert client.get("/api/admin/reports/%d" % rid).status_code == 401


@pytest.mark.parametrize("body", [{"title": "T" * 101}, {"title": 42},
                                  {"title": ["x"]}])
def test_bad_title_is_rejected(tmp_path, body):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    assert make_report(client, admin, **body).status_code == 400
    assert client.get("/api/admin/reports",
                      headers=admin).get_json()["reports"] == []


def test_unknown_report_and_bad_format(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    rid = make_report(client, admin).get_json()["report"]["id"]
    assert client.get("/api/admin/reports/999",
                      headers=admin).status_code == 404
    assert client.get("/api/admin/reports/%d?format=pdf" % rid,
                      headers=admin).status_code == 400
