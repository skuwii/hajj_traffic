import networkx as nx

def build_mecca_graph():
    G = nx.Graph()
    # Nodes: key pilgrimage locations with lat/lon coordinates
    G.add_node('haram', pos=(21.4225, 39.8262))
    G.add_node('mina_gate', pos=(21.4133, 39.8936))
    G.add_node('arafat', pos=(21.3547, 39.9845))
    G.add_node('muzdalifah', pos=(21.3800, 39.9367))
    G.add_node('aziziyah', pos=(21.4050, 39.8600))

    # Edges: roads with capacity, occupancy and distance
    G.add_edge('haram', 'aziziyah', distance=3.0, capacity=200, occupancy=0)
    G.add_edge('aziziyah', 'mina_gate', distance=4.5, capacity=150, occupancy=0)
    G.add_edge('mina_gate', 'muzdalifah', distance=3.2, capacity=120, occupancy=0)
    G.add_edge('muzdalifah', 'arafat', distance=5.0, capacity=100, occupancy=0)
    return G

