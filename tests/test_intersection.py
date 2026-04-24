import sys
sys.path.insert(0, '.')
from utils.csp_solver import solve_csp

def test_normal_queues():
    result = solve_csp({'N': 5, 'S': 20, 'E': 3, 'W': 12})
    assert sum(result.values()) == 120
    assert max(result, key=result.get) == 'S'
    print("test_normal_queues passed")

def test_equal_queues():
    result = solve_csp({'N': 10, 'S': 10, 'E': 10, 'W': 10})
    assert sum(result.values()) == 120
    print("test_equal_queues passed")

def test_one_approach():
    result = solve_csp({'N': 0, 'S': 30, 'E': 0, 'W': 0})
    assert sum(result.values()) == 120
    assert max(result, key=result.get) == 'S'
    print("test_one_approach passed")

if __name__ == '__main__':
    test_normal_queues()
    test_equal_queues()
    test_one_approach()