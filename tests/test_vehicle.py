import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mesa
from core.message_bus     import MessageBus
from core.road_graph      import build_mecca_graph
from agents.vehicle_agent import VehicleAgent

class MockModel(mesa.Model):
    def __init__(self):
        super().__init__()
        self.graph = build_mecca_graph()
        self.bus   = MessageBus()

    def all_agent_ids(self):
        return [a.unique_id for a in self.agents]

def test_basic_navigation():
    print("TEST 1: Basic navigation (no messages)\n")

    model   = MockModel()
    vehicle = VehicleAgent(model, start="mina_gate", destination="haram")

    print(f"Start:         {vehicle.position}")
    print(f"Destination:   {vehicle.destination}")
    print(f"Planned route: {vehicle.current_route}")

    assert vehicle.current_route[0]  == "mina_gate", "Route should start at mina_gate"
    assert vehicle.current_route[-1] == "haram",     "Route should end at haram"
    assert len(vehicle.current_route) > 1,           "Route should have more than 1 node"

    for tick in range(20):
        vehicle.step()
        print(f"  Tick {tick:2d}: position = {vehicle.position}")
        if vehicle.arrived:
            break

    assert vehicle.arrived,             "Vehicle should have arrived"
    assert vehicle.position == "haram", "Final position should be haram"
    print("PASSED")

def test_reroute_replanning():
    print("\n" + "-"*60)
    print("TEST 2: REROUTE message triggers replanning\n")

    model   = MockModel()
    vehicle = VehicleAgent(model, start="mina_gate", destination="haram")

    print(f"Original route: {vehicle.current_route}")

    model.bus.send(
        to           = vehicle.unique_id,
        performative = "REROUTE",
        content      = {"congested_segments": [("mina_gate", "muzdalifah")]},
        sender       = 0   # Road Agent is agent 0
    )

    belief_changed = vehicle._read_messages()

    assert belief_changed, "REROUTE should mark beliefs as changed"
    assert vehicle.belief_map[("mina_gate", "muzdalifah")]["occupancy"] > 100, \
        "Congested segment should be set to 95% of capacity (~114)"

    new_route = vehicle._plan_route()
    print(f"Replanned route: {new_route}")

    assert new_route[0]  == "mina_gate", "Route should still start at mina_gate"
    assert new_route[-1] == "haram",     "Route should still end at haram"
    print("PASSED")

def test_inform_updates_belief():
    print("\n" + "-"*60)
    print("TEST 3: INFORM message updates belief map\n")

    model   = MockModel()
    vehicle = VehicleAgent(model, start="mina_gate", destination="haram")

    key = ('haram', 'aziziyah')
    if key not in vehicle.belief_map:
        key = ('aziziyah', 'haram')

    old_belief = vehicle.belief_map[key]["occupancy"]
    print(f"Belief before INFORM: {old_belief}")

    road_state = {
        ('haram',      'aziziyah'):   80.0,
        ('aziziyah',   'mina_gate'):  60.0,
        ('mina_gate',  'muzdalifah'): 30.0,
        ('muzdalifah', 'arafat'):     10.0
    }
    model.bus.send(
        to           = vehicle.unique_id,
        performative = "INFORM",
        content      = {"road_state": road_state},
        sender       = 0
    )

    vehicle._read_messages()
    new_belief = vehicle.belief_map[key]["occupancy"]
    print(f"Belief after INFORM:  {new_belief}")

    assert new_belief > old_belief,        "Belief should increase after INFORM"
    assert abs(new_belief - 32.0) < 0.01, f"Expected ~32.0, got {new_belief}"
    print("PASSED")

def test_clear_yields():
    print("\n" + "-"*60)
    print("TEST 4: CLEAR message pauses movement for 3 ticks\n")

    model   = MockModel()
    vehicle = VehicleAgent(model, start="mina_gate", destination="haram")

    model.bus.send(
        to           = vehicle.unique_id,
        performative = "CLEAR",
        content      = {"route_ahead": ["mina_gate", "muzdalifah", "aziziyah"]},
        sender       = 999   # Emergency Agent is 999
    )

    pos_before = vehicle.position

    vehicle.step()  # reads CLEAR → sets yielding_ticks=3, no movement
    assert vehicle.position       == pos_before, "Should not move on tick of CLEAR"
    assert vehicle.yielding_ticks == 2,          "Should have 2 ticks remaining"
    print(f"  Tick 1 (yield): position = {vehicle.position}")

    vehicle.step()  # yield tick 2
    assert vehicle.position       == pos_before, "Should not move on yield tick 2"
    assert vehicle.yielding_ticks == 1,          "Should have 1 tick remaining"
    print(f"  Tick 2 (yield): position = {vehicle.position}")

    vehicle.step()  # yield tick 3
    assert vehicle.yielding_ticks == 0,          "Yield should now be over"
    print(f"  Tick 3 (yield): position = {vehicle.position}")

    vehicle.step()  # now free to move
    print(f"  Tick 4 (free):  position = {vehicle.position}")
    assert vehicle.position != pos_before,       "Vehicle should move after yield ends"
    print("PASSED")

def test_already_arrived():
    print("\n" + "-"*60)
    print("TEST 5: Vehicle already at destination does nothing\n")

    model   = MockModel()
    vehicle = VehicleAgent(model, start="haram", destination="haram")

    vehicle.step()
    print(f"Position: {vehicle.position}  |  Route: {vehicle.current_route}")
    assert vehicle.position == "haram", "Should stay at haram"
    print("PASSED\n")

if __name__ == "__main__":
    test_basic_navigation()
    test_reroute_replanning()
    test_inform_updates_belief()
    test_clear_yields()
    test_already_arrived()

    print("ALL TESTS PASSED")
