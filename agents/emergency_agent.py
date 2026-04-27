import mesa
import heapq
import math
from interfaces import SEGMENT_TO_APPROACH
 
 
class EmergencyAgent(mesa.Agent):
 
    PREEMPT_HORIZON = 2
    REJECT_COOLDOWN = 2
 
    def __init__(self, model, start, destination,
                 vehicle_type="ambulance", priority=1):
        super().__init__(model)
 
        self.bus          = model.bus
        self.position     = start
        self.destination  = destination
        self.vehicle_type = vehicle_type
        self.priority     = priority
 
        self.current_route           = self._plan_route()
        self.preempted_intersections = set()
        self.accepted_intersections  = set()
        self.corridor_clear          = False
        self.arrived                 = False
        self.retry_ticks             = 0
 
    def _plan_route(self):
        start = self.position
        goal  = self.destination
 
        if start == goal:
            return []
 
        queue   = [(0, start, [start])]
        visited = set()
 
        while queue:
            f, current, path = heapq.heappop(queue)
 
            if current == goal:
                return path
 
            if current in visited:
                continue
            visited.add(current)
 
            for neighbor in self.model.graph.neighbors(current):
                if neighbor in visited:
                    continue
                g = self._path_cost(path) + self._edge_cost(current, neighbor)
                h = self._heuristic(neighbor, goal)
                heapq.heappush(queue, (g + h, neighbor, path + [neighbor]))
 
        return []
 
    def _edge_cost(self, u, v):
        return self.model.graph[u][v]["distance"]
 
    def _heuristic(self, node, goal):
        x1, y1 = self.model.graph.nodes[node]["pos"]
        x2, y2 = self.model.graph.nodes[goal]["pos"]
        return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
 
    def _path_cost(self, path):
        return sum(
            self._edge_cost(path[i], path[i + 1])
            for i in range(len(path) - 1)
        )
 
    def _read_messages(self):
        messages = self.bus.receive(self.unique_id)
 
        for msg in messages:
            performative = msg["performative"]
            content      = msg["content"]
 
            if performative == "ACCEPT":
                node_id = content.get("intersection_id")
                self.accepted_intersections.add(node_id)
                if len(self.current_route) > 1:
                    if self.current_route[1] in self.accepted_intersections:
                        self.corridor_clear = True
 
            elif performative == "REJECT":
                node_id = content.get("intersection_id")
                self.preempted_intersections.discard(node_id)
                self.corridor_clear = False
                self.retry_ticks    = self.REJECT_COOLDOWN
 
    def _rule_1_preempt_ahead(self):
        lookahead = self.current_route[1 : 1 + self.PREEMPT_HORIZON]
 
        for node in lookahead:
            if node in self.preempted_intersections:
                continue
 
            target_id = self._find_intersection_agent(node)
            if target_id is None:
                continue
 
            idx       = self.current_route.index(node)
            from_node = self.current_route[idx - 1] if idx > 0 else self.position
            approach  = self._get_approach_direction(from_node, node)
 
            self.bus.send(
                to           = target_id,
                performative = "PREEMPT",
                content      = {
                    "approach":     approach,
                    "priority":     self.priority,
                    "vehicle_type": self.vehicle_type,
                    "agent_id":     self.unique_id
                },
                sender = self.unique_id
            )
 
            self.preempted_intersections.add(node)
            print(f"[EmergencyAgent {self.unique_id}] "
                  f"PREEMPT sent to '{node}' "
                  f"(approach={approach}, priority={self.priority})")
 
    def _rule_2_broadcast_clear(self):
        if not self.corridor_clear:
            return
 
        route_ahead = self.current_route[1:]
 
        self.bus.broadcast(
            performative = "CLEAR",
            content      = {
                "route_ahead":  route_ahead,
                "priority":     self.priority,
                "vehicle_type": self.vehicle_type
            },
            sender  = self.unique_id,
            all_ids = self.model.all_agent_ids()
        )
 
        print(f"[EmergencyAgent {self.unique_id}] "
              f"CLEAR broadcast — route ahead: {route_ahead}")
 
        self.preemption_active = len(self.preempted_intersections) > 0
    def _rule_3_move(self):
        if not self.current_route or len(self.current_route) < 2:
            return
 
        next_node = self.current_route[1]
 
        if self.corridor_clear:
            steps = 2
        elif next_node not in self.preempted_intersections:
            steps = 1
        else:
            steps = 0
            print(f"[EmergencyAgent {self.unique_id}] "
                  f"Waiting for ACCEPT at '{next_node}'...")
 
        for _ in range(steps):
            if len(self.current_route) < 2:
                break
 
            next_node = self.current_route[1]
 
            self._update_real_occupancy(self.position, next_node, delta=-1)
            self.position      = next_node
            self.current_route = self.current_route[1:]
 
            if len(self.current_route) > 1:
                self._update_real_occupancy(
                    self.position, self.current_route[1], delta=+1
                )
 
            print(f"[EmergencyAgent {self.unique_id}] Moved to '{self.position}'")
 
            self.preempted_intersections.discard(self.position)
            self.accepted_intersections.discard(self.position)
            self.corridor_clear = False
 
    def _find_intersection_agent(self, node_id):
        if not hasattr(self.model, "intersection_agents"):
            return None
        for agent in self.model.intersection_agents:
            if agent.node_id == node_id:
                return agent.unique_id
        return None
 
    def _get_approach_direction(self, from_node, to_node):
        return SEGMENT_TO_APPROACH.get((from_node, to_node), "N")
 
    def _update_real_occupancy(self, u, v, delta):
        if self.model.graph.has_edge(u, v):
            self.model.graph[u][v]["occupancy"] = max(
                0, self.model.graph[u][v]["occupancy"] + delta
            )
        elif self.model.graph.has_edge(v, u):
            self.model.graph[v][u]["occupancy"] = max(
                0, self.model.graph[v][u]["occupancy"] + delta
            )
 
    def step(self):
        if self.arrived:
            return
 
        if self.retry_ticks > 0:
            self.retry_ticks -= 1
            print(f"[EmergencyAgent {self.unique_id}] "
                  f"Retry cooldown — {self.retry_ticks} ticks remaining")
            return
 
        self._read_messages()
        self._rule_1_preempt_ahead()
        self._rule_2_broadcast_clear()
        self._rule_3_move()
 
        if self.position == self.destination:
            self.arrived = True
            print(f"[EmergencyAgent {self.unique_id}] "
                  f"{self.vehicle_type.upper()} (priority {self.priority}) "
                  f"ARRIVED at '{self.destination}'!")
 