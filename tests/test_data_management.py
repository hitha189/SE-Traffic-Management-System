"""FR-19 Data Management: every category is stored and can be retrieved."""
import app as tms
from helpers import make_client, login, report


def test_every_data_category_is_stored_and_retrievable(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    alice = login(client, "alice")
    amb = login(client, "amb1", "emergency")

    client.get("/api/traffic", headers=alice)                       # traffic
    iid = report(client, alice, "Accident", "MG Road", "Crash"
                 ).get_json()["id"]                                  # incidents
    client.get("/api/route?source=Majestic&destination=Whitefield",
               headers=alice)                                        # routes
    client.get("/api/parking", headers=alice)                        # parking
    sig = client.get("/api/signals", headers=admin).get_json()["signals"][0]
    changed = client.put("/api/signals/%d" % sig["id"], headers=admin, json={
        "state": "Red" if sig["state"] != "Red" else "Green"})       # signals
    assert changed.get_json()["signal"]["updated_by"] == "boss"
    client.post("/api/admin/reports", headers=admin, json={})        # reports
    client.post("/api/emergency/priority", headers=amb, json={
        "vehicle_id": "AMB-1", "source": "Majestic",
        "destination": "Whitefield"})

    # retrieve each category through its own endpoint
    assert len(client.get("/api/traffic", headers=alice
                          ).get_json()["roads"]) == 6
    assert client.get("/api/incidents", headers=alice
                      ).get_json()["incidents"][0]["id"] == iid
    assert len(client.get("/api/alerts", headers=alice
                          ).get_json()["alerts"]) >= 1
    assert len(client.get("/api/routes/history", headers=alice
                          ).get_json()["routes"]) == 1
    assert len(client.get("/api/parking", headers=alice
                          ).get_json()["parking"]) == 6
    assert len(client.get("/api/signals", headers=admin
                          ).get_json()["signals"]) == 6
    assert len(client.get("/api/admin/reports", headers=admin
                          ).get_json()["reports"]) == 1
    assert len(client.get("/api/emergency/requests", headers=admin
                          ).get_json()["requests"]) == 1

    # and the admin summary counts every table
    records = client.get("/api/admin/summary", headers=admin
                         ).get_json()["records"]
    for table in ("users", "roads", "incidents", "routes", "signals",
                  "alerts", "emergency_requests", "audit_log",
                  "parking_areas", "reports", "traffic_history"):
        assert records[table] >= 1, table


def test_data_survives_a_restart_and_seeds_are_not_duplicated(tmp_path):
    client = make_client(tmp_path)
    alice = login(client, "alice")
    report(client, alice, "Hazard", "Majestic", "Oil")
    tms.init_db()                                   # simulate a restart
    tms.init_db()
    conn = tms.get_db()
    counts = {t: conn.execute("SELECT COUNT(*) FROM %s" % t).fetchone()[0]
              for t in ("users", "roads", "signals", "parking_areas",
                        "road_links", "incidents")}
    conn.close()
    assert counts == {"users": 1, "roads": 6, "signals": 6,
                      "parking_areas": 6, "road_links": 8, "incidents": 1}
    assert len(client.get("/api/incidents", headers=alice
                          ).get_json()["incidents"]) == 1
