import random as rndm

def simulate_sensors(graph):
    for u, v in graph.edges():
        graph[u][v]['occupancy'] = rndm.randint(0, graph[u][v]['capacity'])