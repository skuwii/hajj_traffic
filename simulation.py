import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mesa
import matplotlib.pyplot as plt
from core.message_bus          import MessageBus
from core.road_graph           import build_mecca_graph
from core.environment          import simulate_sensors
from agents.road_agent         import RoadAgent
from agents.intersection_agent import IntersectionAgent
from agents.vehicle_agent      import VehicleAgent
from agents.emergency_agent    import EmergencyAgent
from visualize                 import SimVisualizer

VEHICLE_SPAWNS = [
    ("arafat",     "haram"),
    ("muzdalifah", "haram"),
    ("mina_gate",  "haram"),
    ("arafat",     "mina_gate"),
    ("muzdalifah", "jamarat"),
    ("arafat",     "jamarat"),
    ("mina_gate",  "arafat"),
    ("haram",      "arafat"),
    ("jamarat",    "haram"),
    ("tunnel",     "arafat"),
]

EMERGENCY_SPAWNS = [
    ("arafat",    "haram"),
    ("muzdalifah","haram"),
    ("mina_gate", "haram"),
]

INTERSECTION_NODES = ["aziziyah", "muzdalifah", "jamarat", "tunnel"]

class HajjModel(mesa.Model):
    def __init__(self, n_vehicles=30, n_emergency=5):
        super().__init__()
        self.graph = build_mecca_graph()
        self.bus   = MessageBus()
        self.tick  = 0

        self.n_vehicles  = n_vehicles
        self.n_emergency = n_emergency

        self.road_agent = RoadAgent(self, self.graph, self.bus)

        self.intersection_agents = [
            IntersectionAgent(self, self.bus, node_id)
            for node_id in INTERSECTION_NODES
        ]

        # Spawn first batch of vehicles immediately
        self.vehicle_agents = []
        self._vehicle_spawn_queue = list(range(n_vehicles))
        self._spawn_batch(5)  # spawn 5 at tick 0

        # Emergency agents spawn on a timer — none at tick 0
        self.emergency_agents = []
        self._emergency_spawn_queue = list(range(n_emergency))
        self._emergency_timer = 0

        self.emergency_agent = None  # set after first emergency spawns

        self.datacollector = mesa.DataCollector(model_reporters={
            "Congested Roads":   self._count_congested,
            "Avg Occupancy (%)": self._avg_occupancy_pct,
            "Vehicles Arrived":  self._count_arrived,
            "Emergency Arrived": self._count_emergency_arrived,
        })

    def _spawn_batch(self, count):
        vehicle_types = [("ambulance", 1), ("fire_truck", 2), ("police", 3)]
        for _ in range(min(count, len(self._vehicle_spawn_queue))):
            i = self._vehicle_spawn_queue.pop(0)
            start, dest = VEHICLE_SPAWNS[i % len(VEHICLE_SPAWNS)]
            agent = VehicleAgent(self, start, dest)
            self.vehicle_agents.append(agent)

    def _spawn_emergency(self):
        vehicle_types = [("ambulance", 1), ("fire_truck", 2), ("police", 3)]
        if self._emergency_spawn_queue:
            i = self._emergency_spawn_queue.pop(0)
            start, dest = EMERGENCY_SPAWNS[i % len(EMERGENCY_SPAWNS)]
            vtype, priority = vehicle_types[i % len(vehicle_types)]
            agent = EmergencyAgent(self, start, dest, vtype, priority)
            self.emergency_agents.append(agent)
            self.emergency_agent = self.emergency_agents[0]
            print(f"  [Tick {self.tick}] Emergency spawned: {vtype} {start} → {dest}")

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

        # Stagger vehicle spawns — 3 every 5 ticks
        if self.tick > 0 and self.tick % 5 == 0 and self._vehicle_spawn_queue:
            self._spawn_batch(3)

        # Stagger emergency spawns — one every 15 ticks
        self._emergency_timer += 1
        if self._emergency_timer >= 15 and self._emergency_spawn_queue:
            self._spawn_emergency()
            self._emergency_timer = 0

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

    N_VEHICLES  = 50
    N_EMERGENCY = 8
    N_TICKS     = 150

    model = HajjModel(n_vehicles=N_VEHICLES, n_emergency=N_EMERGENCY)
    viz   = SimVisualizer(model)

    print(f"\nIntersections: {INTERSECTION_NODES}")
    print(f"Vehicles: {N_VEHICLES} (staggered) | Emergency: {N_EMERGENCY} (one per 15 ticks)")
    print(f"Running {N_TICKS} ticks...\n")

    for tick in range(N_TICKS):
        model.step()
        viz.render(tick)
        if (tick + 1) % 10 == 0:
            print(f"  Tick {tick+1:3d} | Congested: {model._count_congested()} | "
                  f"Avg occ: {model._avg_occupancy_pct()}% | "
                  f"Vehicles: {model._count_arrived()}/{len(model.vehicle_agents)} arrived | "
                  f"Emergency: {model._count_emergency_arrived()}/{len(model.emergency_agents)}")

    print("\nDone.")
    plot_results(model)