"""NFR-11 Future integration: sensors, IoT, public transport, smart city."""
import pytest

import app as tms
import datasources
import traffic
from helpers import make_client, login, audit_entries


@pytest.fixture(autouse=True)
def keep_registry_clean():
    sources, ingesters = dict(datasources._sources), dict(
        datasources._ingesters)
    yield
    datasources._sources.clear()
    datasources._sources.update(sources)
    datasources._ingesters.clear()
    datasources._ingesters.update(ingesters)


def push(client, admin, kind, readings, source_id="sensor-1"):
    return client.post("/api/admin/integrations/ingest", headers=admin,
                       json={"source_id": source_id, "type": kind,
                             "readings": readings})


def density_of(road):
    conn = tms.get_db()
    value = conn.execute("SELECT density FROM roads WHERE name = ?",
                         (road,)).fetchone()[0]
    conn.close()
    return value


def test_admin_can_see_sources_and_what_is_planned(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    data = client.get("/api/admin/integrations", headers=admin).get_json()
    assert {s["kind"] for s in data["sources"]} == {"traffic", "parking"}
    assert data["ingest_types"] == ["parking", "traffic"]
    planned = " ".join(p["name"] for p in data["planned"])
    for word in ("sensors", "IoT", "Public transport", "Smart-city"):
        assert word in planned


def test_integration_routes_are_admin_only(tmp_path):
    client = make_client(tmp_path)
    assert client.get("/api/admin/integrations").status_code == 401
    assert push(client, {}, "traffic", [{"road": "MG Road", "density": 5}]
                ).status_code == 401
    for name, role in (("alice", None), ("amb1", "emergency")):
        h = login(client, name, role)
        assert client.get("/api/admin/integrations",
                          headers=h).status_code == 403
        assert push(client, h, "traffic", [{"road": "MG Road",
                                            "density": 5}]).status_code == 403


def test_a_sensor_can_push_traffic_readings(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    r = push(client, admin, "traffic", [{"road": "MG Road", "density": 91},
                                        {"road": "Majestic", "density": 12}])
    assert r.status_code == 200 and r.get_json()["accepted"] == 2
    assert density_of("MG Road") == 91 and density_of("Majestic") == 12
    conn = tms.get_db()
    level = conn.execute("SELECT congestion FROM roads WHERE name = "
                         "'MG Road'").fetchone()[0]
    history = conn.execute("SELECT COUNT(*) FROM traffic_history WHERE road "
                           "= 'MG Road'").fetchone()[0]
    conn.close()
    assert level == "High" and history == 1


def test_heavy_sensor_readings_raise_alerts_like_any_other_data(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    push(client, admin, "traffic", [{"road": "MG Road", "density": 95}])
    alerts = client.get("/api/alerts", headers=admin).get_json()["alerts"]
    assert [(a["kind"], a["location"]) for a in alerts] == [
        ("Congestion", "MG Road")]
    push(client, admin, "traffic", [{"road": "MG Road", "density": 10}])
    assert client.get("/api/alerts", headers=admin
                      ).get_json()["alerts"] == []


def test_a_sensor_can_push_parking_readings(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    datasources.register(datasources.PushSource("parking"))   # sensors only
    r = push(client, admin, "parking", [
        {"area": "MG Road Parking", "available": 7}], "lot-sensor-3")
    assert r.status_code == 200
    areas = client.get("/api/parking", headers=admin).get_json()["parking"]
    mg = next(a for a in areas if a["name"] == "MG Road Parking")
    assert mg["available"] == 7 and mg["status"] == "Limited"


def test_real_sensors_switch_the_simulator_off(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    datasources.register(datasources.PushSource("traffic"))
    push(client, admin, "traffic", [{"road": "MG Road", "density": 42}])
    for _ in range(5):
        roads = client.get("/api/traffic", headers=admin).get_json()["roads"]
    assert next(r for r in roads if r["name"] == "MG Road")["density"] == 42


def test_a_different_source_can_replace_the_simulator_without_other_changes(
        tmp_path):
    class CityApiSource(datasources.DataSource):
        kind = "traffic"
        description = "Pretend smart-city feed"

        def refresh(self, conn):
            for road in traffic.list_roads(conn):
                traffic.set_reading(conn, road["name"], 77)

    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    datasources.register(CityApiSource())
    roads = client.get("/api/traffic", headers=admin).get_json()["roads"]
    assert {r["density"] for r in roads} == {77}
    assert {r["congestion"] for r in roads} == {"High"}
    listed = client.get("/api/admin/integrations",
                        headers=admin).get_json()["sources"]
    assert {"kind": "traffic", "source": "CityApiSource",
            "description": "Pretend smart-city feed"} in listed


def test_a_new_data_type_can_be_added_without_editing_existing_code(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    conn = tms.get_db()
    conn.execute("CREATE TABLE bus_arrivals (stop TEXT, minutes INTEGER)")
    conn.commit()
    conn.close()

    def ingest_bus(conn, reading):
        stop, minutes = reading.get("stop"), reading.get("minutes")
        if not isinstance(stop, str) or not isinstance(minutes, int):
            raise ValueError("stop and minutes are required")
        conn.execute("INSERT INTO bus_arrivals VALUES (?, ?)", (stop, minutes))

    datasources.register_ingester("public_transport", ingest_bus)
    assert "public_transport" in client.get(
        "/api/admin/integrations", headers=admin).get_json()["ingest_types"]
    r = push(client, admin, "public_transport",
             [{"stop": "Majestic", "minutes": 4}], "bus-feed")
    assert r.status_code == 200
    conn = tms.get_db()
    assert conn.execute("SELECT * FROM bus_arrivals").fetchall()[0][:] == (
        "Majestic", 4)
    conn.close()
    assert push(client, admin, "public_transport",
                [{"stop": 5}]).status_code == 400


@pytest.mark.parametrize("kind, readings", [
    ("traffic", [{"road": "MG Road", "density": 101}]),
    ("traffic", [{"road": "MG Road", "density": -1}]),
    ("traffic", [{"road": "MG Road", "density": "50"}]),
    ("traffic", [{"road": "MG Road", "density": True}]),
    ("traffic", [{"road": "MG Road", "density": 50.5}]),
    ("traffic", [{"road": "Atlantis", "density": 50}]),
    ("traffic", [{"density": 50}]),
    ("traffic", ["MG Road"]),
    ("traffic", []),
    ("traffic", "MG Road"),
    ("traffic", [{"road": "MG Road", "density": 5}] * 101),
    ("parking", [{"area": "MG Road Parking", "available": 121}]),
    ("parking", [{"area": "MG Road Parking", "available": -1}]),
    ("parking", [{"area": "Nowhere", "available": 5}]),
    ("weather", [{"x": 1}]),
    ("", [{"x": 1}]),
])
def test_bad_readings_are_rejected(tmp_path, kind, readings):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    assert push(client, admin, kind, readings).status_code == 400
    assert audit_entries(client, admin, action="data_ingested") == []


@pytest.mark.parametrize("source_id", ["", "has space", "a/b", "x" * 51,
                                       None, 12, "semi;colon"])
def test_source_id_must_be_clean(tmp_path, source_id):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    r = client.post("/api/admin/integrations/ingest", headers=admin, json={
        "source_id": source_id, "type": "traffic",
        "readings": [{"road": "MG Road", "density": 5}]})
    assert r.status_code == 400


def test_a_batch_is_all_or_nothing(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    before = density_of("MG Road"), density_of("Majestic")
    r = push(client, admin, "traffic", [
        {"road": "MG Road", "density": 99},
        {"road": "Majestic", "density": 98},
        {"road": "Atlantis", "density": 97}])           # third is bad
    assert r.status_code == 400 and "Reading 3" in r.get_json()["error"]
    assert (density_of("MG Road"), density_of("Majestic")) == before
    conn = tms.get_db()
    assert conn.execute("SELECT COUNT(*) FROM traffic_history"
                        ).fetchone()[0] == 0
    conn.close()


def test_every_push_is_logged_with_its_source(tmp_path):
    client = make_client(tmp_path)
    admin = login(client, "boss", "admin")
    push(client, admin, "traffic", [{"road": "MG Road", "density": 20},
                                    {"road": "Majestic", "density": 30}],
         "camera-12")
    entry = audit_entries(client, admin, action="data_ingested")[0]
    assert entry["target"] == "source:camera-12"
    assert entry["details"] == "traffic: 2 reading(s)"
