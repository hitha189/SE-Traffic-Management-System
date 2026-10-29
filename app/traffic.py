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
LOW_MAX = 35      # density below this is "Low"
MEDIUM_MAX = 70   # density below this is "Medium", otherwise "High"
HISTORY_LIMIT = 20000  # newest readings kept for analytics (NFR-06)


def level_for_density(density):
    if density < LOW_MAX:
        return "Low"
    if density < MEDIUM_MAX:
        return "Medium"
    return "High"


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
    # Every reading is kept so traffic patterns can be analysed (FR-17).
    conn.execute(
        """CREATE TABLE IF NOT EXISTS traffic_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            road TEXT NOT NULL,
            density INTEGER NOT NULL,
            congestion TEXT NOT NULL,
            recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_history_road "
                 "ON traffic_history (road)")
    conn.commit()


def set_reading(conn, road_name, density):
    """Store one reading for a road and add it to the history. Used by the
    simulator and by real sensors. Does not commit. Returns False if the
    road does not exist."""
    level = level_for_density(density)
    cur = conn.execute(
        "UPDATE roads SET density = ?, congestion = ? WHERE name = ?",
        (density, level, road_name),
    )
    if cur.rowcount == 0:
        return False
    conn.execute(
        "INSERT INTO traffic_history (road, density, congestion) "
        "VALUES (?, ?, ?)", (road_name, density, level))
    return True


def prune_history(conn):
    """Keep only the newest HISTORY_LIMIT readings so storage stays bounded."""
    conn.execute(
        "DELETE FROM traffic_history WHERE id <= "
        "(SELECT COALESCE(MAX(id), 0) FROM traffic_history) - ?",
        (HISTORY_LIMIT,))


def refresh_simulated(conn):
    """Simulate a new traffic reading for every road."""
    for row in conn.execute("SELECT name FROM roads").fetchall():
        set_reading(conn, row["name"], random.randint(5, 100))
    prune_history(conn)
    conn.commit()


def list_roads(conn):
    rows = conn.execute(
        "SELECT name, lat, lng, congestion, density FROM roads ORDER BY name"
    ).fetchall()
    return [dict(r) for r in rows]


def list_history(conn, limit=1000):
    rows = conn.execute(
        "SELECT road, density, congestion, recorded_at FROM traffic_history "
        "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]
