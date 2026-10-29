"""Traffic analytics (FR-17).

Four areas, always present in the result:
  traffic_flow - current density and congestion per road
  congestion   - how often each road has been heavily congested
  incidents    - counts by type and status, and hotspots
  patterns     - hourly averages, peak hour and per-road trends
"""
from collections import defaultdict

import traffic

TREND_MIN_READINGS = 4
TREND_THRESHOLD = 5  # density points between first and second half


def _avg(values):
    return round(sum(values) / len(values), 1) if values else 0.0


def _traffic_flow(conn):
    roads = traffic.list_roads(conn)
    levels = {level: 0 for level in traffic.LEVELS}
    for road in roads:
        levels[road["congestion"]] += 1
    busiest = max(roads, key=lambda r: r["density"], default=None)
    quietest = min(roads, key=lambda r: r["density"], default=None)

    def brief(road):
        return ({"name": road["name"], "density": road["density"]}
                if road else None)
    return {
        "roads": [{"name": r["name"], "density": r["density"],
                   "congestion": r["congestion"]} for r in roads],
        "average_density": _avg([r["density"] for r in roads]),
        "busiest": brief(busiest),
        "quietest": brief(quietest),
        "levels": levels,
    }


def _history_by_road(conn):
    rows = conn.execute(
        "SELECT road, density, congestion FROM traffic_history ORDER BY id"
    ).fetchall()
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["road"]].append((row["density"], row["congestion"]))
    return grouped, len(rows)


def _congestion(history, total):
    ranking = []
    for road, readings in history.items():
        high = sum(1 for _d, level in readings if level == "High")
        ranking.append({
            "name": road,
            "readings": len(readings),
            "high_readings": high,
            "high_percent": round(100 * high / len(readings)),
        })
    ranking.sort(key=lambda r: (-r["high_percent"], r["name"]))
    return {
        "readings_analysed": total,
        "most_congested": ranking[:3],
    }


def _incidents(conn):
    def counts(column):
        rows = conn.execute(
            "SELECT %s AS k, COUNT(*) AS n FROM incidents GROUP BY %s "
            "ORDER BY n DESC, k" % (column, column)).fetchall()
        return {r["k"]: r["n"] for r in rows}
    by_status = counts("status")
    hotspots = conn.execute(
        "SELECT location, COUNT(*) AS n FROM incidents GROUP BY location "
        "ORDER BY n DESC, location LIMIT 3").fetchall()
    return {
        "total": sum(by_status.values()),
        "open": sum(n for s, n in by_status.items() if s != "Closed"),
        "by_type": counts("type"),
        "by_status": by_status,
        "hotspots": [{"location": h["location"], "incidents": h["n"]}
                     for h in hotspots],
    }


def _patterns(conn, history):
    hourly = conn.execute(
        "SELECT strftime('%H', recorded_at) AS hour, AVG(density) AS avg "
        "FROM traffic_history GROUP BY hour ORDER BY hour").fetchall()
    hours = [{"hour": h["hour"], "average_density": round(h["avg"], 1)}
             for h in hourly]
    trends = []
    for road, readings in sorted(history.items()):
        if len(readings) < TREND_MIN_READINGS:
            continue
        densities = [d for d, _level in readings]
        half = len(densities) // 2
        first, second = _avg(densities[:half]), _avg(densities[half:])
        if second - first >= TREND_THRESHOLD:
            trend = "Rising"
        elif first - second >= TREND_THRESHOLD:
            trend = "Falling"
        else:
            trend = "Stable"
        trends.append({"road": road, "trend": trend,
                       "earlier_average": first, "recent_average": second})
    result = {
        "hourly_average_density": hours,
        "peak_hour": max(hours, key=lambda h: h["average_density"])["hour"]
        if hours else None,
        "quietest_hour": min(hours, key=lambda h: h["average_density"])["hour"]
        if hours else None,
        "road_trends": trends,
    }
    if not hours:
        result["note"] = "Not enough history yet; refresh traffic a few times."
    return result


def analyze(conn):
    history, total = _history_by_road(conn)
    return {
        "generated_at": conn.execute("SELECT CURRENT_TIMESTAMP").fetchone()[0],
        "traffic_flow": _traffic_flow(conn),
        "congestion": _congestion(history, total),
        "incidents": _incidents(conn),
        "patterns": _patterns(conn, history),
    }
