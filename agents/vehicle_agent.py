import mesa
import heapq
import math

class VehicleAgent(mesa.Agent):
    """
    Vehicle Agent — BDI architecture with A* navigation.

    Belief  : personal copy of road congestion (updated via INFORM / REROUTE)
    Desire  : reach self.destination
    Intention: self.current_route  (list of node names, replanned when beliefs change)
    """

    def __init__(self, model, start, destination):
        super().__init__(model)

        # ── BDI: Belief ───────────────────────────────────────────────────────
        # Personal copy of road map. Starts identical to real graph,
        # but only updates when an INFORM or REROUTE message arrives —
        # intentionally lagging behind reality to simulate incomplete knowledge.
        self.belief_map = {}
        for u, v, data in model.graph.edges(data=True):
            self.belief_map[(u, v)] = {
                "occupancy": data["occupancy"],
                "capacity":  data["capacity"],
                "distance":  data["distance"]
            }

        # ── BDI: Desire ───────────────────────────────────────────────────────
        self.destination = destination

        # ── BDI: Intention ────────────────────────────────────────────────────
        self.position       = start
        self.arrived        = False
        self.yielding_ticks = 0          # nonzero = yielding for emergency vehicle

        # Plan the initial route right away using current beliefs
        self.current_route = self._plan_route()

    # ─────────────────────────────────────────────────────────────────────────
    # A* PLANNING  (uses belief_map, NOT the real graph)
    # ─────────────────────────────────────────────────────────────────────────

    def _plan_route(self):
        """
        A* from self.position to self.destination.
        Uses self.belief_map so routing is based on what the agent
        BELIEVES about congestion, not ground truth.
        Returns a list of node names, e.g. ['mina_gate', 'aziziyah', 'haram'].
        Returns [] if already at destination or no route exists.
        """
        start = self.position
        goal  = self.destination

        if start == goal:
            return []

        # Priority queue entries: (f_cost, node, path_so_far)
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

        return []   # no route found

    def _edge_cost(self, u, v):
        """
        Cost of travelling road (u, v) based on belief_map.
        Mirrors the same formula used in the Road Agent / astar.py:
            cost = distance * (1 + 2 * congestion_ratio)
        So at 0% full  → cost = distance * 1.0  (normal)
           at 75% full → cost = distance * 2.5  (expensive)
           at 100% full→ cost = distance * 3.0  (avoid)
        """
        # belief_map keys are stored as (u, v); try both directions
        key  = (u, v) if (u, v) in self.belief_map else (v, u)
        data = self.belief_map[key]
        congestion = data["occupancy"] / max(data["capacity"], 1)
        return data["distance"] * (1 + 2 * congestion)

    def _heuristic(self, node, goal):
        """
        Straight-line Euclidean distance between node and goal.
        Uses the pos=(lat, lon) attribute on each graph node.
        """
        x1, y1 = self.model.graph.nodes[node]["pos"]
        x2, y2 = self.model.graph.nodes[goal]["pos"]
        return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

    def _path_cost(self, path):
        """Total accumulated cost of a path already computed."""
        return sum(
            self._edge_cost(path[i], path[i + 1])
            for i in range(len(path) - 1)
        )

    # ─────────────────────────────────────────────────────────────────────────
    # MESSAGE HANDLING
    # ─────────────────────────────────────────────────────────────────────────

    def _read_messages(self):
        """
        Empty the inbox and process each message.
        Matches the message format sent by RoadAgent:
            {'performative': ..., 'content': ..., 'sender': ...}

        Returns True if beliefs changed (triggers replanning).
        """
        messages       = self.model.bus.receive(self.unique_id)
        belief_changed = False

        for msg in messages:
            performative = msg["performative"]
            content      = msg["content"]

            # ── INFORM: Road Agent sharing full road state ────────────────
            # content = {'road_state': {(u,v): occupancy_estimate, ...}}
            if performative == "INFORM":
                road_state = content.get("road_state", {})
                for key, new_occupancy in road_state.items():
                    # road_state keys from RoadAgent are tuples (u, v)
                    if key in self.belief_map:
                        old = self.belief_map[key]["occupancy"]
                        # Blend: trust new info 40%, keep prior 60%
                        # Intentionally less trusting than Road Agent (alpha=0.3)
                        # to simulate a driver who is cautious about sudden reports
                        self.belief_map[key]["occupancy"] = (
                            0.4 * new_occupancy + 0.6 * old
                        )
                belief_changed = True

            # ── REROUTE: Road Agent saying a specific segment is congested ─
            # content = {'congested_segments': [(u,v), (u,v), ...]}
            elif performative == "REROUTE":
                congested_segments = content.get("congested_segments", [])
                for seg in congested_segments:
                    key = tuple(seg)
                    # Try both directions since graph is undirected
                    if key not in self.belief_map:
                        key = (seg[1], seg[0])
                    if key in self.belief_map:
                        cap = self.belief_map[key]["capacity"]
                        # Mark as 95% full so A* strongly avoids it
                        self.belief_map[key]["occupancy"] = 0.95 * cap
                belief_changed = True

            # ── CLEAR: Emergency vehicle approaching — yield ───────────────
            # content = {'route_ahead': [...]}  (we don't need the route detail)
            elif performative == "CLEAR":
                self.yielding_ticks = 3   # pause movement for 3 ticks
                # No belief_changed — we don't replan, just pause

        return belief_changed

    # ─────────────────────────────────────────────────────────────────────────
    # MOVEMENT
    # ─────────────────────────────────────────────────────────────────────────

    def _update_real_occupancy(self, u, v, delta):
        """
        Update the REAL graph occupancy when this vehicle moves onto or off a road.
        This is what other agents (Road Agent sensors) will eventually detect.
        delta = +1 when vehicle enters a segment, -1 when it leaves.
        """
        if self.model.graph.has_edge(u, v):
            self.model.graph[u][v]['occupancy'] = max(
                0, self.model.graph[u][v]['occupancy'] + delta
            )
        elif self.model.graph.has_edge(v, u):
            self.model.graph[v][u]['occupancy'] = max(
                0, self.model.graph[v][u]['occupancy'] + delta
            )

    # ─────────────────────────────────────────────────────────────────────────
    # MAIN STEP — Mesa calls this every tick
    # ─────────────────────────────────────────────────────────────────────────

    def step(self):
        """
        BDI cycle every tick:
        1. Perceive  — read messages from message bus
        2. Update    — revise belief_map based on messages
        3. Deliberate— replan route if beliefs changed
        4. Yield     — if emergency vehicle is coming, wait
        5. Execute   — move one step along current_route
        6. Check     — have we arrived?
        """

        # Already at destination — do nothing
        if self.arrived:
            return

        # ── 1 & 2: Perceive and update beliefs ───────────────────────────────
        belief_changed = self._read_messages()

        # ── 3: Deliberate — replan if beliefs changed ─────────────────────────
        if belief_changed:
            new_route = self._plan_route()
            # Only switch if we found a valid new route AND it's different
            if new_route and new_route != self.current_route:
                print(
                    f"[Vehicle {self.unique_id}] Replanning: "
                    f"{self.current_route} → {new_route}"
                )
                self.current_route = new_route

        # ── 4: Yield for emergency vehicle ────────────────────────────────────
        if self.yielding_ticks > 0:
            self.yielding_ticks -= 1
            return   # skip movement this tick

        # ── 5: Execute — move one step forward ───────────────────────────────
        if len(self.current_route) > 1:
            next_node = self.current_route[1]

            # Leave current segment (reduce its real occupancy)
            self._update_real_occupancy(self.position, next_node, delta=-1)

            # Move to next node
            self.position      = next_node
            self.current_route = self.current_route[1:]   # consume one step

            # Enter the next segment ahead (increase its real occupancy)
            if len(self.current_route) > 1:
                self._update_real_occupancy(
                    self.position, self.current_route[1], delta=+1
                )

        # ── 6: Check arrival ──────────────────────────────────────────────────
        if self.position == self.destination:
            self.arrived = True
            print(f"[Vehicle {self.unique_id}] Arrived at {self.destination}!")
