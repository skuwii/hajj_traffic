import mesa, random
class RoadAgent(mesa.Agent):
    def __init__(self, unique_id, model, graph, bus):
        super().__init__(unique_id, model)
        self.graph = graph
        self.bus = bus
        self.belief = {(u,v): 0 for u,v in graph.edges()}

    def get_noisy_reading(self, u, v):
        real = self.graph[u][v]['occupancy']
        noise = random.gauss(0, 5) # std dev = 5 cars
        return max(0, real + noise)

    def update_belief(self):
        alpha = 0.3
        for u, v in self.graph.edges():
            reading = self.get_noisy_reading(u, v)
            old = self.belief[(u, v)]
            self.belief[(u, v)] = alpha * reading + (1 - alpha) * old

    def find_congested(self):
        return [(u,v) for u,v in self.graph.edges()
        if self.belief[(u,v)] > 0.75 * self.graph[u][v]['capacity']]

    def step(self):
        self.update_belief()
        saturated = self.find_congested()
        if saturated:
            self.bus.broadcast('REROUTE',
                {'congested_segments': saturated}, self.unique_id,self.model.all_agent_ids())
        self.bus.broadcast('INFORM',{'road_state': dict(self.belief)}, self.unique_id,self.model.all_agent_ids())