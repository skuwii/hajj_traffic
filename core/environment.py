import random

def simulate_sensors(graph):
    for u, v in graph.edges():
        current = graph[u][v]['occupancy']
        cap = graph[u][v]['capacity']
        delta = random.randint(-5, 10)
        graph[u][v]['occupancy'] = max(0, min(cap, current + delta))