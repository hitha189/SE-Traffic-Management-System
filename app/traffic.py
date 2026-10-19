import random
import sqlite3

SEED_ROADS = [
    ("MG Road", 12.9756, 77.6068),
    ("Majestic", 12.9767, 77.5713),
    ("Whitefield", 12.9698, 77.7500),
    ("Silk Board", 12.9176, 77.6233),
    ("Indiranagar", 12.9784, 77.6408),
    ("Koramangala", 12.9352, 77.6245),
]

LEVELS = ["Low", "Medium", "High"]


def init_traffic(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS roads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            congestion TEXT NOT NULL DEFAULT 'Low',
            density INTEGER NOT NULL DEFAULT 0
        )"""
    )
    for name, lat, lng in SEED_ROADS:
        conn.execute(
            "INSERT OR IGNORE INTO roads (name, lat, lng) VALUES (?, ?, ?)",
            (name, lat, lng),
        )
    conn.commit()


def refresh_simulated(conn):
    """Simulate a new traffic reading for every road."""
    for row in conn.execute("SELECT id FROM roads").fetchall():
        density = random.randint(5, 100)
        if density < 35:
            level = "Low"
        elif density < 70:
            level = "Medium"
        else:
            level = "High"
        conn.execute(
            "UPDATE roads SET density = ?, congestion = ? WHERE id = ?",
            (density, level, row["id"]),
        )
    conn.commit()


def list_roads(conn):
    rows = conn.execute(
        "SELECT name, lat, lng, congestion, density FROM roads ORDER BY name"
    ).fetchall()
    return [dict(r) for r in rows]