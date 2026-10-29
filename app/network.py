"""Road network growth (NFR-06).

Roads, junction signals and road links are all data, not code. An admin can
add a road with its connections and it immediately appears on the map, in
route planning, in alerts and in analytics, with no change to the program.
"""
import routing
import signals


class Conflict(Exception):
    """The thing being added already exists (HTTP 409)."""


MAX_NAME = 50
MAX_LINKS = 10


def init_network(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS road_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            a TEXT NOT NULL,
            b TEXT NOT NULL,
            km REAL NOT NULL CHECK (km > 0),
            UNIQUE (a, b)
        )"""
    )
    if conn.execute("SELECT COUNT(*) FROM road_links").fetchone()[0] == 0:
        for a, b, km in routing.EDGES:
            conn.execute("INSERT INTO road_links (a, b, km) VALUES (?, ?, ?)",
                         (a, b, km))
    conn.commit()


def road_exists(conn, name):
    return conn.execute("SELECT 1 FROM roads WHERE name = ?",
                        (name,)).fetchone() is not None


def add_road(conn, name, lat, lng, links):
    """Add a road, its signal and its links. Does not commit.

    `links` is a list of (existing_road_name, distance_km). At least one link
    is required so the new road is reachable by route planning.
    Raises ValueError for bad input and Conflict for a duplicate name.
    """
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= MAX_NAME:
        raise ValueError("Road name must be 1-%d characters" % MAX_NAME)
    name = name.strip()
    if (isinstance(lat, bool) or isinstance(lng, bool)
            or not isinstance(lat, (int, float))
            or not isinstance(lng, (int, float))
            or not -90 <= lat <= 90 or not -180 <= lng <= 180):
        raise ValueError("Latitude and longitude are not valid")
    if not isinstance(links, list) or not 1 <= len(links) <= MAX_LINKS:
        raise ValueError("Connect the new road to 1-%d existing roads"
                         % MAX_LINKS)
    clean = []
    for link in links:
        to = link.get("to") if isinstance(link, dict) else None
        km = link.get("km") if isinstance(link, dict) else None
        if (not isinstance(to, str) or not road_exists(conn, to)
                or isinstance(km, bool)
                or not isinstance(km, (int, float)) or not 0.1 <= km <= 100):
            raise ValueError("Each link needs an existing road and a "
                             "distance of 0.1-100 km")
        clean.append((to, float(km)))
    if road_exists(conn, name):
        raise Conflict("A road with this name already exists")

    conn.execute("INSERT INTO roads (name, lat, lng) VALUES (?, ?, ?)",
                 (name, float(lat), float(lng)))
    signals.add_signal(conn, name)
    for to, km in clean:
        conn.execute("INSERT OR IGNORE INTO road_links (a, b, km) "
                     "VALUES (?, ?, ?)", (name, to, km))
    return {"name": name, "lat": lat, "lng": lng,
            "links": [{"to": to, "km": km} for to, km in clean]}
