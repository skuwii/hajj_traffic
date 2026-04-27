import networkx as nx

def build_mecca_graph():
    G = nx.Graph()

    # Nodes
    G.add_node('haram',      pos=(21.4225, 39.8262))
    G.add_node('aziziyah',   pos=(21.4050, 39.8600))
    G.add_node('mina_gate',  pos=(21.4133, 39.8936))
    G.add_node('muzdalifah', pos=(21.3800, 39.9367))
    G.add_node('arafat',     pos=(21.3547, 39.9845))
    G.add_node('jamarat',    pos=(21.4214, 39.8728))
    G.add_node('tunnel',     pos=(21.4190, 39.8500))

    # Edges
    G.add_edge('haram',      'aziziyah',   distance=3.0, capacity=200, occupancy=0)
    G.add_edge('aziziyah',   'mina_gate',  distance=4.5, capacity=150, occupancy=0)
    G.add_edge('mina_gate',  'muzdalifah', distance=3.2, capacity=120, occupancy=0)
    G.add_edge('muzdalifah', 'arafat',     distance=5.0, capacity=100, occupancy=0)
    G.add_edge('haram',      'tunnel',     distance=2.5, capacity=160, occupancy=0)
    G.add_edge('tunnel',     'aziziyah',   distance=1.8, capacity=140, occupancy=0)
    G.add_edge('tunnel',     'mina_gate',  distance=2.2, capacity=160, occupancy=0)
    G.add_edge('aziziyah',   'jamarat',    distance=3.5, capacity=130, occupancy=0)
    G.add_edge('jamarat',    'mina_gate',  distance=1.5, capacity=180, occupancy=0)
    G.add_edge('jamarat', 'tunnel', distance=1.0, capacity=180, occupancy=0)
    return G