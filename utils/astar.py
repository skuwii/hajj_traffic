import heapq, math
def edge_weight(graph, u, v):
    data = graph[u][v]
    congestion_factor = data['occupancy'] / data['capacity']
    # At 0% full → cost = distance * 1.0 (normal speed)
    # At 60% full → cost = distance * 2.6 (very expensive, avoid)
    #At 75% full→ cost = distance * 3.0 (maximum avoidance)
    return data['distance'] * (1 + 2 * congestion_factor)

def heuristic(graph, node, goal):
    x1, y1 = graph.nodes[node]['pos']
    x2, y2 = graph.nodes[goal]['pos']
    return math.sqrt((x1-x2)**2 + (y1-y2)**2)

def astar(graph, start, goal):
    queue = [(0, start, [start])] # (f_cost, node, path)
    visited = set()
    while queue:
    f, current, path = heapq.heappop(queue)
    if current == goal: return path
    if current in visited: continue
    visited.add(current)
    for nb in graph.neighbors(current):
        if nb not in visited:
            g = sum(edge_weight(graph, path[i], path[i+1])
                for i in range(len(path)-1))
            g += edge_weight(graph, current, nb)
        h = heuristic(graph, nb, goal)
        heapq.heappush(queue, (g+h, nb, path+[nb]))
    return [] # no route found