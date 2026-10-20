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


def build_graph():
    graph = {}
    for a, b, km in EDGES:
        graph.setdefault(a, []).append((b, km))
        graph.setdefault(b, []).append((a, km))
    return graph


def known_places():
    return sorted(build_graph().keys())


def find_route(source, destination):
    """Shortest route by distance (Dijkstra). Returns None if no route."""
    graph = build_graph()
    if source not in graph or destination not in graph:
        return None

    queue = [(0.0, source, [source])]
    seen = set()
    while queue:
        cost, node, path = heapq.heappop(queue)
        if node in seen:
            continue
        seen.add(node)
        if node == destination:
            minutes = round(cost / AVG_SPEED_KMPH * 60)
            return {"path": path, "distance_km": round(cost, 1),
                    "eta_minutes": minutes}
        for nxt, km in graph[node]:
            if nxt not in seen:
                heapq.heappush(queue, (cost + km, nxt, path + [nxt]))
    return None