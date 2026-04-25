import sys, os 
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mesa
from core.message_bus          import MessageBus
from core.road_graph           import build_mecca_graph
from core.environment          import simulate_sensors
from agents.road_agent         import RoadAgent
from agents.intersection_agent import IntersectionAgent
from agents.vehicle_agent      import VehicleAgent
from agents.emergency_agent    import EmergencyAgent
from visualize                 import SimVisualizer
import matplotlib.pyplot as plt

VEHICLE_SPAWNS = [
    ("mina_gate",  "haram"),
    ("arafat",     "haram"),
    ("muzdalifah", "haram"),
    ("mina_gate",  "arafat"),
    ("haram",      "mina_gate"),
]

INTERSECTION_NODES = ["aziziyah", "muzdalifah"]

class HajjModel(mesa.Model):
    def __init__(self, n_vehicles=10, n_emergency=1):
        super().__init__()
        self.graph = build_mecca_graph()
        self.bus   = MessageBus()
        self.tick  = 0

        self.road_agent = RoadAgent(self, self.graph, self.bus)

        self.intersection_agents = [
            IntersectionAgent(self, self.bus, node_id)
            for node_id in INTERSECTION_NODES
        ]

        self.vehicle_agents = [
            VehicleAgent(self, VEHICLE_SPAWNS[i % len(VEHICLE_SPAWNS)][0],
                         VEHICLE_SPAWNS[i % len(VEHICLE_SPAWNS)][1])
            for i in range(n_vehicles)
        ]

        vehicle_types = [("ambulance", 1), ("fire_truck", 2), ("police", 3)]
        self.emergency_agents = [
            EmergencyAgent(self, "mina_gate", "haram",
                           *vehicle_types[i % len(vehicle_types)])
            for i in range(n_emergency)
        ]

        # For visualize.py compatibility (expects singular)
        self.emergency_agent = self.emergency_agents[0]

        self.datacollector = mesa.DataCollector(model_reporters={
            "Congested Roads":   self._count_congested,
            "Avg Occupancy (%)": self._avg_occupancy_pct,
            "Vehicles Arrived":  self._count_arrived,
            "Emergency Arrived": self._count_emergency_arrived,
        })

    def all_agent_ids(self):
        ids  = [self.road_agent.unique_id]
        ids += [a.unique_id for a in self.intersection_agents]
        ids += [a.unique_id for a in self.vehicle_agents]
        ids += [a.unique_id for a in self.emergency_agents]
        return ids

    def _count_congested(self):
        return sum(1 for u, v in self.graph.edges()
                   if self.graph[u][v]["occupancy"] > 0.75 * self.graph[u][v]["capacity"])

    def _avg_occupancy_pct(self):
        edges = list(self.graph.edges())
        if not edges: return 0
        return round(sum(self.graph[u][v]["occupancy"] /
                         max(self.graph[u][v]["capacity"], 1) * 100
                         for u, v in edges) / len(edges), 2)

    def _count_arrived(self):
        return sum(1 for a in self.vehicle_agents if a.arrived)

    def _count_emergency_arrived(self):
        return sum(1 for a in self.emergency_agents if a.arrived)

    def step(self):
        self.datacollector.collect(self)
        simulate_sensors(self.graph)
        self.road_agent.step()
        for agent in self.intersection_agents:
            agent.step()
        for agent in self.vehicle_agents:
            agent.step()
        for agent in self.emergency_agents:
            agent.step()
        self.tick += 1

def plot_results(model):
    data = model.datacollector.get_model_vars_dataframe()
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.patch.set_facecolor('#111316')
    fig.suptitle("Hajj Traffic Simulation — Results Summary", 
                 fontsize=13, color='white', fontfamily='monospace')

    for ax in axes.flat:
        ax.set_facecolor('#161a1f')
        ax.tick_params(colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.title.set_color('white')
        for spine in ax.spines.values():
            spine.set_edgecolor('#5a6070')

    data["Congested Roads"].plot(ax=axes[0][0], title="Congested Roads per Tick",
        color="#e74c3c", ylabel="Count", xlabel="Tick")
    data["Avg Occupancy (%)"].plot(ax=axes[0][1], title="Average Road Occupancy (%)",
        color="#f1c40f", ylabel="%", xlabel="Tick")
    data["Vehicles Arrived"].plot(ax=axes[1][0], title="Vehicles Arrived",
        color="#2ecc71", ylabel="Count", xlabel="Tick")
    data["Emergency Arrived"].plot(ax=axes[1][1], title="Emergency Vehicles Arrived",
        color="#9b59b6", ylabel="Count", xlabel="Tick")

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    print("=" * 55)
    print("  Hajj Traffic Management System — Simulation")
    print("=" * 55)

    N_VEHICLES  = 10
    N_EMERGENCY = 1
    N_TICKS     = 100

    model = HajjModel(n_vehicles=N_VEHICLES, n_emergency=N_EMERGENCY)
    viz   = SimVisualizer(model)

    print(f"\nAgents: 1 Road | {len(model.intersection_agents)} Intersection | "
          f"{len(model.vehicle_agents)} Vehicle | {len(model.emergency_agents)} Emergency")
    print(f"Running {N_TICKS} ticks...\n")

    for tick in range(N_TICKS):
        model.step()
        viz.render(tick)
        if (tick + 1) % 10 == 0:
            print(f"  Tick {tick+1:3d} | Congested: {model._count_congested()} | "
              f"Avg occ: {model._avg_occupancy_pct()}% | "
              f"Arrived: {model._count_arrived()}/{N_VEHICLES}")
        # if model._count_arrived() >= N_VEHICLES:
        #     print(f"\nAll vehicles arrived at tick {tick+1}.")
        #     break

    print("\nDone.")
    plot_results(model)