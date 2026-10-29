"""Pluggable data sources (NFR-11 Future Integration).

Everything that supplies outside data - today a simulator, later real traffic
sensors, IoT devices, public-transport feeds or smart-city systems - plugs in
here. The rest of the system only asks `refresh(conn, kind)` and never knows
where the data came from, so a real source replaces a simulated one without
touching routes, alerts, analytics or the interface.

Two ways in:
  * PULL: register a `DataSource`; the system calls its `refresh()`.
  * PUSH: devices send readings to the ingest API; each data type has an
    ingester (a function that validates and stores one reading).
New data types are added with `register_ingester()`, with no edits here.
"""
import parking
import traffic


class DataSource:
    """Base class. Subclass it and register an instance."""
    kind = None
    description = ""

    def refresh(self, conn):
        """Bring the database up to date. Must not commit."""


class SimulatedTrafficSource(DataSource):
    kind = "traffic"
    description = "Simulated traffic readings (prototype)"

    def refresh(self, conn):
        traffic.refresh_simulated(conn)


class SimulatedParkingSource(DataSource):
    kind = "parking"
    description = "Simulated parking occupancy (prototype)"

    def refresh(self, conn):
        parking.refresh_simulated(conn)


class PushSource(DataSource):
    """Use when devices push data through the ingest API: nothing to pull,
    and the simulator is switched off for that kind."""

    def __init__(self, kind, description="Readings pushed by devices"):
        self.kind = kind
        self.description = description


_sources = {}
_ingesters = {}

MAX_READINGS_PER_REQUEST = 100


def register(source):
    _sources[source.kind] = source


def get(kind):
    return _sources.get(kind)


def refresh(conn, kind):
    source = _sources.get(kind)
    if source is not None:
        source.refresh(conn)


def describe():
    return [{"kind": kind, "source": type(src).__name__,
             "description": src.description}
            for kind, src in sorted(_sources.items())]


# ---- push ingestion ---------------------------------------------------------
def register_ingester(kind, function):
    """`function(conn, reading)` stores one reading or raises ValueError."""
    _ingesters[kind] = function


def ingest_kinds():
    return sorted(_ingesters)


def ingest(conn, kind, readings):
    """Store a batch of readings. Does not commit; the caller's transaction
    makes the batch all-or-nothing. Raises ValueError on the first bad one."""
    handler = _ingesters.get(kind)
    if handler is None:
        raise ValueError("Unsupported data type: %s" % kind)
    if (not isinstance(readings, list) or not readings
            or len(readings) > MAX_READINGS_PER_REQUEST):
        raise ValueError("Send 1-%d readings" % MAX_READINGS_PER_REQUEST)
    for i, reading in enumerate(readings, 1):
        if not isinstance(reading, dict):
            raise ValueError("Reading %d is not an object" % i)
        try:
            handler(conn, reading)
        except ValueError as e:
            raise ValueError("Reading %d: %s" % (i, e))
    return len(readings)


def _ingest_traffic(conn, reading):
    road, density = reading.get("road"), reading.get("density")
    if (isinstance(density, bool) or not isinstance(density, int)
            or not 0 <= density <= 100):
        raise ValueError("density must be a whole number from 0 to 100")
    if not isinstance(road, str) or not traffic.set_reading(conn, road,
                                                            density):
        raise ValueError("unknown road")


def _ingest_parking(conn, reading):
    parking.set_available(conn, reading.get("area"), reading.get("available"))


register(SimulatedTrafficSource())
register(SimulatedParkingSource())
register_ingester("traffic", _ingest_traffic)
register_ingester("parking", _ingest_parking)

# Integrations the architecture is ready for but the prototype does not yet
# have. Shown to admins so the roadmap is visible. (NFR-11)
PLANNED = [
    {"name": "Traffic sensors", "how": "push readings to the ingest API "
     "(type 'traffic') or register a PushSource"},
    {"name": "IoT devices (parking sensors, cameras)", "how": "push readings "
     "to the ingest API (type 'parking')"},
    {"name": "Public transport feeds", "how": "register_ingester("
     "'public_transport', function) and a table for the data"},
    {"name": "Smart-city infrastructure", "how": "register a DataSource "
     "subclass that calls the city API in refresh()"},
]
