"""Area subscriptions and notifications (FR-11).

A user chooses the areas they care about. When an alert is raised, only users
subscribed to that area or to a directly connected (nearby) area are
notified, so unrelated users are never targeted.
"""
import routing


def init_notifications(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS subscriptions (
            username TEXT NOT NULL,
            area TEXT NOT NULL,
            PRIMARY KEY (username, area)
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_area "
                 "ON subscriptions (area)")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            alert_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user "
                 "ON notifications (username)")
    conn.commit()


def nearby_areas(conn, area):
    """The area itself plus the places directly connected to it by road."""
    graph = routing.build_graph(conn)
    near = {area}
    for neighbour, _km in graph.get(area, []):
        near.add(neighbour)
    return near


def set_subscriptions(conn, username, areas):
    """Replace the user's areas. Does not commit."""
    conn.execute("DELETE FROM subscriptions WHERE username = ?", (username,))
    for area in sorted(set(areas)):
        conn.execute(
            "INSERT INTO subscriptions (username, area) VALUES (?, ?)",
            (username, area))


def get_subscriptions(conn, username):
    rows = conn.execute(
        "SELECT area FROM subscriptions WHERE username = ? ORDER BY area",
        (username,)).fetchall()
    return [r["area"] for r in rows]


def notify_for_alert(conn, alert_id, location, message):
    """Create a notification for every user subscribed to the alert's area or
    a nearby area. Does not commit. Returns the usernames notified."""
    near = sorted(nearby_areas(conn, location))
    marks = ",".join("?" for _ in near)
    rows = conn.execute(
        "SELECT DISTINCT username FROM subscriptions WHERE area IN (" +
        marks + ")", near).fetchall()
    users = [r["username"] for r in rows]
    for username in users:
        conn.execute(
            "INSERT INTO notifications (username, alert_id, message) "
            "VALUES (?, ?, ?)", (username, alert_id, message))
    return users


def list_notifications(conn, username):
    rows = conn.execute(
        "SELECT id, alert_id, message, is_read, created_at "
        "FROM notifications WHERE username = ? ORDER BY id DESC LIMIT 50",
        (username,)).fetchall()
    return [dict(r) for r in rows]


def mark_read(conn, username, notification_id):
    """Only the owner can mark a notification. Returns True if it changed."""
    cur = conn.execute(
        "UPDATE notifications SET is_read = 1 "
        "WHERE id = ? AND username = ?", (notification_id, username))
    return cur.rowcount > 0
