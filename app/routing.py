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


def edge_cost(km, a, b, density):
    """Distance made 'longer' by traffic at both ends of the segment."""
    if not density:
        return km
    avg = (density.get(a, 0) + density.get(b, 0)) / 2
    return km * (1 + CONGESTION_PENALTY * avg / 100)


def find_route(source, destination, density=None):
    """Least-cost route (Dijkstra). `density` maps place name -> 0..100.
    Returns None if no route."""
    graph = build_graph()
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
                "eta_minutes": round(cost / AVG_SPEED_KMPH * 60),
                "free_flow_minutes": round(dist / AVG_SPEED_KMPH * 60),
                "congestion_aware": bool(density),
            }
        for nxt, km in graph[node]:
            if nxt not in seen:
                heapq.heappush(queue, (
                    cost + edge_cost(km, node, nxt, density),
                    dist + km,
                    nxt,
                    path + [nxt],
                ))
    return None