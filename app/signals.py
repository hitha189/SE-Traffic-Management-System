"""Traffic signal status and control (FR-06, FR-07).

One signal per simulated junction (the same places as the road network).
Changes are validated here; the caller writes the audit entry in the same
transaction (FR-20).
"""
import traffic

SIGNAL_STATES = ["Red", "Yellow", "Green"]
INITIAL_CYCLE = ["Green", "Red", "Yellow"]


def init_signals(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location TEXT UNIQUE NOT NULL,
            state TEXT NOT NULL DEFAULT 'Red',
            updated_by TEXT NOT NULL DEFAULT 'system',
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    for i, (name, _lat, _lng) in enumerate(traffic.SEED_ROADS):
        conn.execute(
            "INSERT OR IGNORE INTO signals (location, state) VALUES (?, ?)",
            (name, INITIAL_CYCLE[i % len(INITIAL_CYCLE)]),
        )
    conn.commit()


def list_signals(conn):
    rows = conn.execute(
        "SELECT id, location, state, updated_by, updated_at "
        "FROM signals ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def get_signal(conn, signal_id):
    row = conn.execute(
        "SELECT id, location, state, updated_by, updated_at "
        "FROM signals WHERE id = ?", (signal_id,)).fetchone()
    return dict(row) if row else None


def get_signal_by_location(conn, location):
    row = conn.execute(
        "SELECT id, location, state, updated_by, updated_at "
        "FROM signals WHERE location = ?", (location,)).fetchone()
    return dict(row) if row else None


def set_state(conn, signal_id, new_state, actor):
    """Change a signal. Does not commit. Returns the old state."""
    signal = get_signal(conn, signal_id)
    old = signal["state"]
    conn.execute(
        "UPDATE signals SET state = ?, updated_by = ?, "
        "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (new_state, actor, signal_id),
    )
    return old
