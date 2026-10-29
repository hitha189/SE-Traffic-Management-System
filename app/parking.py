"""Parking areas and available spaces (FR-16)."""
import random

SEED_AREAS = [
    # name, road it is on, capacity, spaces free at start
    ("MG Road Parking", "MG Road", 120, 45),
    ("Majestic Bus Stand Parking", "Majestic", 200, 80),
    ("Whitefield Tech Park Parking", "Whitefield", 300, 150),
    ("Silk Board Parking", "Silk Board", 80, 12),
    ("Indiranagar 100ft Road Parking", "Indiranagar", 100, 38),
    ("Koramangala Forum Parking", "Koramangala", 150, 60),
]


class Conflict(Exception):
    """The parking area already exists (HTTP 409)."""


def init_parking(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS parking_areas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            location TEXT NOT NULL,
            capacity INTEGER NOT NULL CHECK (capacity > 0),
            available INTEGER NOT NULL CHECK (available >= 0),
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            CHECK (available <= capacity)
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_parking_location "
                 "ON parking_areas (location)")
    for name, location, capacity, available in SEED_AREAS:
        conn.execute(
            "INSERT OR IGNORE INTO parking_areas "
            "(name, location, capacity, available) VALUES (?, ?, ?, ?)",
            (name, location, capacity, available))
    conn.commit()


def _status(available, capacity):
    if available == 0:
        return "Full"
    if available * 5 <= capacity:   # 20% or less free
        return "Limited"
    return "Available"


def _to_dict(row):
    item = dict(row)
    occupied = item["capacity"] - item["available"]
    item["occupancy_percent"] = round(100 * occupied / item["capacity"])
    item["status"] = _status(item["available"], item["capacity"])
    return item


def list_areas(conn, location=None):
    query = ("SELECT id, name, location, capacity, available, updated_at "
             "FROM parking_areas")
    params = []
    if location:
        query += " WHERE location = ?"
        params.append(location)
    query += " ORDER BY location, name"
    return [_to_dict(r) for r in conn.execute(query, params).fetchall()]


def summary(conn):
    areas = list_areas(conn)
    return {
        "areas": len(areas),
        "total_capacity": sum(a["capacity"] for a in areas),
        "total_available": sum(a["available"] for a in areas),
        "full_areas": [a["name"] for a in areas if a["status"] == "Full"],
        "limited_areas": [a["name"] for a in areas
                          if a["status"] == "Limited"],
    }


def refresh_simulated(conn):
    """Simulate cars arriving and leaving. Does not commit."""
    for row in conn.execute(
            "SELECT id, capacity, available FROM parking_areas").fetchall():
        step = random.randint(-8, 8)
        new = min(row["capacity"], max(0, row["available"] + step))
        conn.execute(
            "UPDATE parking_areas SET available = ?, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new, row["id"]))


def set_available(conn, area_name, available):
    """Set the free spaces of one area (used by real sensors). Does not
    commit. Raises ValueError if the number is impossible."""
    row = conn.execute("SELECT id, capacity FROM parking_areas WHERE name = ?",
                       (area_name,)).fetchone()
    if row is None:
        raise ValueError("Unknown parking area: %s" % area_name)
    if (isinstance(available, bool) or not isinstance(available, int)
            or not 0 <= available <= row["capacity"]):
        raise ValueError("Available spaces must be 0-%d" % row["capacity"])
    conn.execute(
        "UPDATE parking_areas SET available = ?, "
        "updated_at = CURRENT_TIMESTAMP WHERE id = ?", (available, row["id"]))


def add_area(conn, name, location, capacity):
    """Add a new parking area (NFR-06). Does not commit."""
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
        raise ValueError("Name must be 1-80 characters")
    name = name.strip()
    if (not isinstance(location, str) or conn.execute(
            "SELECT 1 FROM roads WHERE name = ?",
            (location,)).fetchone() is None):
        raise ValueError("Location must be an existing road")
    if (isinstance(capacity, bool) or not isinstance(capacity, int)
            or not 1 <= capacity <= 10000):
        raise ValueError("Capacity must be a whole number from 1 to 10000")
    if conn.execute("SELECT 1 FROM parking_areas WHERE name = ?",
                    (name,)).fetchone():
        raise Conflict("A parking area with this name already exists")
    cur = conn.execute(
        "INSERT INTO parking_areas (name, location, capacity, available) "
        "VALUES (?, ?, ?, ?)", (name, location, capacity, capacity))
    return cur.lastrowid
