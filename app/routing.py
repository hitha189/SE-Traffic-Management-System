import heapq

# Road network between the simulated locations: (from, to, distance in km)
EDGES = [
    ("Majestic", "MG Road", 4.0),
    ("MG Road", "Indiranagar", 4.5),
    ("MG Road", "Koramangala", 6.0),
    ("Majestic", "Koramangala", 8.0),
    ("Indiranagar", "Whitefield", 15.0),
    ("Koramangala", "Silk Board", 5.0),
    ("Silk Board", "Whitefield", 20.0),
    ("Indiranagar", "Koramangala", 5.5),
]

AVG_SPEED_KMPH = 30.0
CONGESTION_PENALTY = 1.5  # a road at 100% density costs 2.5x its distance


def build_graph():
    graph = {}
    for a, b, km in EDGES:
        graph.setdefault(a, []).append((b, km))
        graph.setdefault(b, []).append((a, km))
    return graph


def known_places():
    return sorted(build_graph().keys())


def edge_cost(km, a, b, density, penalty=CONGESTION_PENALTY):
    """Distance made 'longer' by traffic at both ends of the segment."""
    if not density:
        return km
    avg = (density.get(a, 0) + density.get(b, 0)) / 2
    return km * (1 + penalty * avg / 100)


def find_route(source, destination, density=None, penalty=CONGESTION_PENALTY,
               speed=AVG_SPEED_KMPH, avoid=None):
    """Least-cost route (Dijkstra). `density` maps place name -> 0..100.
    `avoid` is a set of places to stay away from (never the source or
    destination). Returns None if no route."""
    graph = build_graph()
    avoid = set(avoid or ()) - {source, destination}
    if source not in graph or destination not in graph:
        return None

    queue = [(0.0, 0.0, source, [source])]
    seen = set()
    while queue:
        cost, dist, node, path = heapq.heappop(queue)
        if node in seen:
            continue
        seen.add(node)
        if node == destination:
            return {
                "path": path,
                "distance_km": round(dist, 1),
                "eta_minutes": round(cost / speed * 60),
                "free_flow_minutes": round(dist / speed * 60),
                "congestion_aware": bool(density),
            }
        for nxt, km in graph[node]:
            if nxt not in seen and nxt not in avoid:
                heapq.heappush(queue, (
                    cost + edge_cost(km, node, nxt, density, penalty),
                    dist + km,
                    nxt,
                    path + [nxt],
                ))
    return None


# ---- Emergency routing (FR-15) ---------------------------------------------
EMERGENCY_SPEED_KMPH = 50.0   # emergency vehicles travel faster
EMERGENCY_PENALTY = 0.4       # and are slowed far less by traffic


def find_emergency_route(source, destination, density=None, blocked=None):
    """Fastest route for an emergency vehicle.

    Uses the same live congestion data as normal routing, but with a smaller
    congestion penalty and higher speed, and steers around places that have
    an open roadblock (`blocked`). If avoiding them leaves no route, it falls
    back to a route through them rather than returning nothing.
    """
    route = find_route(source, destination, density,
                       penalty=EMERGENCY_PENALTY, speed=EMERGENCY_SPEED_KMPH,
                       avoid=blocked)
    if route is None and blocked:
        route = find_route(source, destination, density,
                           penalty=EMERGENCY_PENALTY,
                           speed=EMERGENCY_SPEED_KMPH)
    if route is None:
        return None
    normal = find_route(source, destination, density)
    route["emergency"] = True
    route["normal_eta_minutes"] = normal["eta_minutes"] if normal else None
    route["avoided"] = sorted(set(blocked or ()) - set(route["path"]))
    return route
