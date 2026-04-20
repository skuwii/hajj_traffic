import mesa
import heapq
import math

class VehicleAgent(mesa.Agent):
    def __init__(self, model, start, destination):
        super().__init__(model)
        self.belief_map = {}
        for u, v, data in model.graph.edges(data=True):
            self.belief_map[(u, v)] = {
                "occupancy": data["occupancy"],
                "capacity":  data["capacity"],
                "distance":  data["distance"]
            }

        self.destination = destination
        self.position       = start
        self.arrived        = False
        self.yielding_ticks = 0          
        self.current_route = self._plan_route()

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
        key  = (u, v) if (u, v) in self.belief_map else (v, u)
        data = self.belief_map[key]
        congestion = data["occupancy"] / max(data["capacity"], 1)
        return data["distance"] * (1 + 2 * congestion)

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
        messages       = self.model.bus.receive(self.unique_id)
        belief_changed = False

        for msg in messages:
            performative = msg["performative"]
            content      = msg["content"]

            if performative == "INFORM":
                road_state = content.get("road_state", {})
                for key, new_occupancy in road_state.items():
                    if key in self.belief_map:
                        old = self.belief_map[key]["occupancy"]
                        self.belief_map[key]["occupancy"] = (
                            0.4 * new_occupancy + 0.6 * old
                        )
                belief_changed = True

            elif performative == "REROUTE":
                congested_segments = content.get("congested_segments", [])
                for seg in congested_segments:
                    key = tuple(seg)
                    if key not in self.belief_map:
                        key = (seg[1], seg[0])
                    if key in self.belief_map:
                        cap = self.belief_map[key]["capacity"]
                        self.belief_map[key]["occupancy"] = 0.95 * cap
                belief_changed = True

            elif performative == "CLEAR":
                self.yielding_ticks = 3   
        return belief_changed

    def _update_real_occupancy(self, u, v, delta):
        if self.model.graph.has_edge(u, v):
            self.model.graph[u][v]['occupancy'] = max(
                0, self.model.graph[u][v]['occupancy'] + delta
            )
        elif self.model.graph.has_edge(v, u):
            self.model.graph[v][u]['occupancy'] = max(
                0, self.model.graph[v][u]['occupancy'] + delta
            )

    def step(self):
        if self.arrived:
            return
        belief_changed = self._read_messages()

        if belief_changed:
            new_route = self._plan_route()
            if new_route and new_route != self.current_route:
                print(
                    f"[Vehicle {self.unique_id}] Replanning: "
                    f"{self.current_route} → {new_route}"
                )
                self.current_route = new_route

        if self.yielding_ticks > 0:
            self.yielding_ticks -= 1
            return   

        if len(self.current_route) > 1:
            next_node = self.current_route[1]

            self._update_real_occupancy(self.position, next_node, delta=-1)

            self.position      = next_node
            self.current_route = self.current_route[1:]   

            if len(self.current_route) > 1:
                self._update_real_occupancy(
                    self.position, self.current_route[1], delta=+1
                )

        if self.position == self.destination:
            self.arrived = True
            print(f"[Vehicle {self.unique_id}] Arrived at {self.destination}!")
