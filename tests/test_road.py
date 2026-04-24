import sys
sys.path.insert(0, '.')
from utils.probabilistic import bayesian_update
from core.road_graph import build_mecca_graph

def test_bayesian_update():
    result = bayesian_update(70, 90, alpha=0.3)
    assert result == 76.0
    print("test_bayesian_update passed")

def test_bayesian_low_alpha():
    result = bayesian_update(70, 90, alpha=0.1)
    assert result == 72.0
    print("test_bayesian_low_alpha passed")

def test_graph_built():
    G = build_mecca_graph()
    assert 'haram' in G.nodes
    assert 'arafat' in G.nodes
    assert G.has_edge('haram', 'aziziyah')
    print("test_graph_built passed")

def test_congestion_threshold():
    G = build_mecca_graph()
    G['haram']['aziziyah']['occupancy'] = 160  # 80% of 200
    cap = G['haram']['aziziyah']['capacity']
    occ = G['haram']['aziziyah']['occupancy']
    assert occ / cap >= 0.75
    print("test_congestion_threshold passed")

if __name__ == '__main__':
    test_bayesian_update()
    test_bayesian_low_alpha()
    test_graph_built()
    test_congestion_threshold()