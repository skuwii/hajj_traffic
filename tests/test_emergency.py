import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mesa
import networkx as nx
from core.message_bus       import MessageBus
from agents.emergency_agent import EmergencyAgent


class StubIntersectionAgent:
    def __init__(self, unique_id, node_id):
        self.unique_id = unique_id
        self.node_id   = node_id


def build_mecca_graph():
    G = nx.Graph()
    G.add_node("haram",      pos=(21.4225, 39.8262))
    G.add_node("mina_gate",  pos=(21.4133, 39.8936))
    G.add_node("arafat",     pos=(21.3547, 39.9845))
    G.add_node("muzdalifah", pos=(21.3800, 39.9367))
    G.add_node("aziziyah",   pos=(21.4050, 39.8600))
    G.add_edge("haram",      "aziziyah",   distance=3.0, capacity=200, occupancy=0)
    G.add_edge("aziziyah",   "mina_gate",  distance=4.5, capacity=150, occupancy=0)
    G.add_edge("mina_gate",  "muzdalifah", distance=3.2, capacity=120, occupancy=0)
    G.add_edge("muzdalifah", "arafat",     distance=5.0, capacity=100, occupancy=0)
    return G


class MockModel(mesa.Model):
    def __init__(self):
        super().__init__()
        self.graph = build_mecca_graph()
        self.bus   = MessageBus()
        self.intersection_agents = [
            StubIntersectionAgent(unique_id=10, node_id="aziziyah"),
            StubIntersectionAgent(unique_id=11, node_id="mina_gate"),
            StubIntersectionAgent(unique_id=12, node_id="muzdalifah"),
        ]

    def all_agent_ids(self):
        ids  = [a.unique_id for a in self.agents]
        ids += [ia.unique_id for ia in self.intersection_agents]
        return ids


def drain(bus, uid):
    return bus.receive(uid)


def test_initialisation():
    print("\n" + "="*60)
    print("TEST 1: Agent initialises correctly")
    print("="*60)

    model = MockModel()
    agent = EmergencyAgent(model,
                           start        = "mina_gate",
                           destination  = "haram",
                           vehicle_type = "ambulance",
                           priority     = 1)

    print(f"  unique_id:    {agent.unique_id}")
    print(f"  position:     {agent.position}")
    print(f"  destination:  {agent.destination}")
    print(f"  vehicle_type: {agent.vehicle_type}")
    print(f"  priority:     {agent.priority}")
    print(f"  route:        {agent.current_route}")
    print(f"  arrived:      {agent.arrived}")
    print(f"  retry_ticks:  {agent.retry_ticks}")

    assert agent.position               == "mina_gate"
    assert agent.destination            == "haram"
    assert agent.vehicle_type           == "ambulance"
    assert agent.priority               == 1
    assert agent.arrived                == False
    assert agent.retry_ticks            == 0
    assert agent.corridor_clear         == False
    assert agent.current_route[0]       == "mina_gate"
    assert agent.current_route[-1]      == "haram"
    assert len(agent.preempted_intersections) == 0
    assert len(agent.accepted_intersections)  == 0
    print("PASSED")


def test_astar_ignores_congestion():
    print("\n" + "="*60)
    print("TEST 2: A* plans by distance only — ignores congestion")
    print("="*60)

    model = MockModel()
    model.graph["mina_gate"]["muzdalifah"]["occupancy"] = 120

    agent_1 = EmergencyAgent(model, start="mina_gate", destination="haram")

    model.graph["mina_gate"]["muzdalifah"]["occupancy"] = 0
    agent_2 = EmergencyAgent(model, start="mina_gate", destination="haram")

    print(f"  Route (road at 100%): {agent_1.current_route}")
    print(f"  Route (road clear):   {agent_2.current_route}")

    assert agent_1.current_route == agent_2.current_route
    assert agent_1.current_route[0]  == "mina_gate"
    assert agent_1.current_route[-1] == "haram"
    print("PASSED")


def test_rule1_preempt_sent():
    print("\n" + "="*60)
    print("TEST 3: RULE 1 — PREEMPT sent to intersections ahead")
    print("="*60)

    model = MockModel()
    agent = EmergencyAgent(model,
                           start        = "mina_gate",
                           destination  = "haram",
                           vehicle_type = "ambulance",
                           priority     = 1)

    print(f"  Route:           {agent.current_route}")
    print(f"  PREEMPT_HORIZON: {agent.PREEMPT_HORIZON}")

    agent.step()

    print(f"  Preempted intersections: {agent.preempted_intersections}")

    assert len(agent.preempted_intersections) > 0

    preempt_found = False
    for ia in model.intersection_agents:
        msgs = drain(model.bus, ia.unique_id)
        for m in msgs:
            if m["performative"] == "PREEMPT":
                preempt_found = True
                c = m["content"]
                print(f"  Intersection '{ia.node_id}' received PREEMPT:")
                print(f"    approach:     {c['approach']}")
                print(f"    priority:     {c['priority']}")
                print(f"    vehicle_type: {c['vehicle_type']}")
                print(f"    agent_id:     {c['agent_id']}")
                assert c["priority"]     == 1
                assert c["vehicle_type"] == "ambulance"
                assert c["agent_id"]     == agent.unique_id
                assert "approach"        in c

    assert preempt_found
    print("PASSED")


def test_rule1_no_duplicate_preempt():
    print("\n" + "="*60)
    print("TEST 4: RULE 1 — PREEMPT not sent twice to same intersection")
    print("="*60)

    model = MockModel()
    agent = EmergencyAgent(model, start="mina_gate", destination="haram")

    agent.step()
    preempted_after_tick1 = set(agent.preempted_intersections)

    for ia in model.intersection_agents:
        drain(model.bus, ia.unique_id)

    agent.step()

    new_preempts = 0
    for ia in model.intersection_agents:
        msgs = drain(model.bus, ia.unique_id)
        new_preempts += sum(1 for m in msgs
                            if m["performative"] == "PREEMPT"
                            and m["content"].get("agent_id") == agent.unique_id)

    print(f"  Preempted after tick 1: {preempted_after_tick1}")
    print(f"  New PREEMPTs in tick 2: {new_preempts}")

    assert new_preempts == 0
    print("PASSED")


def test_accept_sets_corridor_clear():
    print("\n" + "="*60)
    print("TEST 5: ACCEPT message → corridor_clear = True")
    print("="*60)

    model     = MockModel()
    agent     = EmergencyAgent(model, start="mina_gate", destination="haram")
    next_node = agent.current_route[1]

    print(f"  Next node on route: {next_node}")
    print(f"  corridor_clear before ACCEPT: {agent.corridor_clear}")

    model.bus.send(
        to           = agent.unique_id,
        performative = "ACCEPT",
        content      = {"intersection_id": next_node, "granted_approach": "N"},
        sender       = 10
    )

    agent._read_messages()

    print(f"  corridor_clear after ACCEPT:  {agent.corridor_clear}")

    assert agent.corridor_clear == True
    assert next_node in agent.accepted_intersections
    print("PASSED")


def test_rule2_clear_broadcast():
    print("\n" + "="*60)
    print("TEST 6: RULE 2 — CLEAR broadcast sent after corridor secured")
    print("="*60)

    model     = MockModel()
    agent     = EmergencyAgent(model, start="mina_gate", destination="haram")
    next_node = agent.current_route[1]

    model.bus.send(
        to           = agent.unique_id,
        performative = "ACCEPT",
        content      = {"intersection_id": next_node, "granted_approach": "N"},
        sender       = 10
    )

    agent._read_messages()
    agent._rule_2_broadcast_clear()

    clear_found = False
    for ia in model.intersection_agents:
        msgs = drain(model.bus, ia.unique_id)
        for m in msgs:
            if m["performative"] == "CLEAR":
                clear_found = True
                c = m["content"]
                print(f"  CLEAR received by agent {ia.unique_id}:")
                print(f"    route_ahead:  {c['route_ahead']}")
                print(f"    priority:     {c['priority']}")
                print(f"    vehicle_type: {c['vehicle_type']}")
                assert isinstance(c["route_ahead"], list)
                assert c["priority"]     == 1
                assert c["vehicle_type"] == "ambulance"

    assert clear_found
    print("PASSED")


def test_reject_sets_cooldown():
    print("\n" + "="*60)
    print("TEST 7: REJECT message → retry cooldown set, no movement")
    print("="*60)

    model      = MockModel()
    agent      = EmergencyAgent(model, start="mina_gate", destination="haram")
    next_node  = agent.current_route[1]
    pos_before = agent.position

    agent.preempted_intersections.add(next_node)

    model.bus.send(
        to           = agent.unique_id,
        performative = "REJECT",
        content      = {"intersection_id": next_node},
        sender       = 10
    )

    agent.step()

    print(f"  retry_ticks after REJECT step: {agent.retry_ticks}")
    print(f"  position unchanged:            {agent.position == pos_before}")

    # retry_ticks is set to REJECT_COOLDOWN (2) inside _read_messages.
    # step() then returns early — the decrement happens on the NEXT step().
    # So after one step(), retry_ticks is still 2 (REJECT_COOLDOWN).
    assert agent.retry_ticks == agent.REJECT_COOLDOWN
    assert agent.position    == pos_before
    assert agent.corridor_clear == False

    # Second step confirms decrement works correctly
    agent.step()
    print(f"  retry_ticks after second step: {agent.retry_ticks}")
    assert agent.retry_ticks == agent.REJECT_COOLDOWN - 1
    print("PASSED")


def test_rule3_double_speed_when_clear():
    print("\n" + "="*60)
    print("TEST 8: RULE 3 — moves 2 steps when corridor is clear")
    print("="*60)

    model = MockModel()
    agent = EmergencyAgent(model, start="mina_gate", destination="haram")

    print(f"  Route:           {agent.current_route}")
    print(f"  Position before: {agent.position}")

    agent.corridor_clear = True
    agent._rule_3_move()

    print(f"  Position after:  {agent.position}")

    assert agent.position != "mina_gate"
    assert len(agent.current_route) <= len(["mina_gate", "aziziyah", "haram"]) - 1
    print("PASSED")


def test_rule3_waits_for_accept():
    print("\n" + "="*60)
    print("TEST 9: RULE 3 — waits when PREEMPT sent but no ACCEPT received")
    print("="*60)

    model      = MockModel()
    agent      = EmergencyAgent(model, start="mina_gate", destination="haram")
    next_node  = agent.current_route[1]
    pos_before = agent.position

    agent.preempted_intersections.add(next_node)
    agent.corridor_clear = False

    agent._rule_3_move()

    print(f"  Position unchanged: {agent.position == pos_before}")
    assert agent.position == pos_before
    print("PASSED")


def test_full_traversal():
    print("\n" + "="*60)
    print("TEST 10: Full traversal mina_gate → haram")
    print("="*60)

    model = MockModel()
    agent = EmergencyAgent(model,
                           start        = "mina_gate",
                           destination  = "haram",
                           vehicle_type = "ambulance",
                           priority     = 1)

    print(f"  Planned route: {agent.current_route}")

    for tick in range(20):
        for ia in model.intersection_agents:
            msgs = drain(model.bus, ia.unique_id)
            for m in msgs:
                if m["performative"] == "PREEMPT":
                    model.bus.send(
                        to           = agent.unique_id,
                        performative = "ACCEPT",
                        content      = {
                            "intersection_id":  ia.node_id,
                            "granted_approach": m["content"].get("approach", "N")
                        },
                        sender = ia.unique_id
                    )

        agent.step()
        print(f"  Tick {tick:2d}: position = {agent.position}")

        if agent.arrived:
            break

    assert agent.arrived
    assert agent.position == "haram"
    print("PASSED")


def test_priority_levels():
    print("\n" + "="*60)
    print("TEST 11: Different vehicle types have correct priority levels")
    print("="*60)

    model = MockModel()

    ambulance  = EmergencyAgent(model, start="mina_gate", destination="haram",
                                vehicle_type="ambulance",  priority=1)
    fire_truck = EmergencyAgent(model, start="mina_gate", destination="haram",
                                vehicle_type="fire_truck", priority=2)
    police     = EmergencyAgent(model, start="mina_gate", destination="haram",
                                vehicle_type="police",     priority=3)

    print(f"  ambulance  priority: {ambulance.priority}")
    print(f"  fire_truck priority: {fire_truck.priority}")
    print(f"  police     priority: {police.priority}")

    assert ambulance.priority  == 1
    assert fire_truck.priority == 2
    assert police.priority     == 3
    assert ambulance.priority < fire_truck.priority < police.priority
    print("PASSED")


def test_already_arrived():
    print("\n" + "="*60)
    print("TEST 12: Already at destination — does nothing")
    print("="*60)

    model = MockModel()
    agent = EmergencyAgent(model, start="haram", destination="haram")

    agent.step()

    print(f"  position: {agent.position} | route: {agent.current_route}")
    assert agent.position == "haram"
    print("PASSED")


if __name__ == "__main__":
    test_initialisation()
    test_astar_ignores_congestion()
    test_rule1_preempt_sent()
    test_rule1_no_duplicate_preempt()
    test_accept_sets_corridor_clear()
    test_rule2_clear_broadcast()
    test_reject_sets_cooldown()
    test_rule3_double_speed_when_clear()
    test_rule3_waits_for_accept()
    test_full_traversal()
    test_priority_levels()
    test_already_arrived()

    print("\n" + "="*60)
    print("ALL TESTS PASSED")
    print("="*60)
