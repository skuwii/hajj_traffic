import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mesa
import matplotlib.pyplot as plt
import networkx as nx

from core.message_bus          import MessageBus
from core.road_graph           import build_mecca_graph
from core.environment          import simulate_sensors
from agents.road_agent         import RoadAgent
from agents.intersection_agent import IntersectionAgent
from agents.vehicle_agent      import VehicleAgent
from agents.emergency_agent    import EmergencyAgent


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

        # ── Road Agent ────────────────────────────────────────────────────
        self.road_agent = RoadAgent(self, self.graph, self.bus)

        # ── Intersection Agents ───────────────────────────────────────────
        # IntersectionAgent still uses Mesa 2.x constructor (unique_id first)
        # until Zed updates it to Mesa 3.x
        self.intersection_agents = []
        for i, node_id in enumerate(INTERSECTION_NODES):
            agent = IntersectionAgent(
                model   = self,
                bus     = self.bus,
                node_id = node_id
            )
            self.intersection_agents.append(agent)

        # ── Vehicle Agents ────────────────────────────────────────────────
        self.vehicle_agents = []
        for i in range(n_vehicles):
            start, destination = VEHICLE_SPAWNS[i % len(VEHICLE_SPAWNS)]
            agent = VehicleAgent(self, start=start, destination=destination)
            self.vehicle_agents.append(agent)

        # ── Emergency Agents ──────────────────────────────────────────────
        vehicle_types = [
            ("ambulance",  1),
            ("fire_truck", 2),
            ("police",     3),
        ]
        self.emergency_agents = []
        for i in range(n_emergency):
            vtype, priority = vehicle_types[i % len(vehicle_types)]
            agent = EmergencyAgent(
                model        = self,
                start        = "mina_gate",
                destination  = "haram",
                vehicle_type = vtype,
                priority     = priority
            )
            self.emergency_agents.append(agent)

        # ── Mesa 3.x — no scheduler needed ───────────────────────────────
        # SimultaneousActivation was removed in Mesa 3.x.
        # We call each agent's step() manually in HajjModel.step().

        # ── Data collector ────────────────────────────────────────────────
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Congested Roads":   self._count_congested,
                "Avg Occupancy (%)": self._avg_occupancy_pct,
                "Vehicles Arrived":  self._count_arrived,
                "Emergency Arrived": self._count_emergency_arrived,
            }
        )

    def all_agent_ids(self):
        ids  = [self.road_agent.unique_id]
        ids += [a.unique_id for a in self.intersection_agents]
        ids += [a.unique_id for a in self.vehicle_agents]
        ids += [a.unique_id for a in self.emergency_agents]
        return ids

    def _count_congested(self):
        return sum(
            1 for u, v in self.graph.edges()
            if self.graph[u][v]["occupancy"] >
               0.75 * self.graph[u][v]["capacity"]
        )

    def _avg_occupancy_pct(self):
        edges = list(self.graph.edges())
        if not edges:
            return 0
        return round(
            sum(
                self.graph[u][v]["occupancy"] /
                max(self.graph[u][v]["capacity"], 1) * 100
                for u, v in edges
            ) / len(edges), 2
        )

    def _count_arrived(self):
        return sum(1 for a in self.vehicle_agents if a.arrived)

    def _count_emergency_arrived(self):
        return sum(1 for a in self.emergency_agents if a.arrived)

    def step(self):
        self.datacollector.collect(self)
        simulate_sensors(self.graph)         # uses core/environment.py

        # Mesa 3.x — call each agent's step() manually in order:
        # 1. Road Agent reads sensors and broadcasts INFORM/REROUTE
        # 2. Intersection Agents process signals and PREEMPT requests
        # 3. Vehicle Agents update beliefs and move
        # 4. Emergency Agents preempt, clear, and move
        self.road_agent.step()
        for agent in self.intersection_agents:
            agent.step()
        for agent in self.vehicle_agents:
            agent.step()
        for agent in self.emergency_agents:
            agent.step()

        self.tick += 1


def visualize(model):
    G   = model.graph
    pos = nx.get_node_attributes(G, "pos")

    edge_colors = []
    for u, v in G.edges():
        ratio = G[u][v]["occupancy"] / max(G[u][v]["capacity"], 1)
        if ratio > 0.75:
            edge_colors.append("red")
        elif ratio > 0.5:
            edge_colors.append("orange")
        else:
            edge_colors.append("green")

    intersection_nodes = {a.node_id for a in model.intersection_agents}
    node_colors = [
        "gold" if n in intersection_nodes else "lightblue"
        for n in G.nodes()
    ]

    plt.figure(figsize=(10, 7))
    nx.draw(
        G, pos,
        edge_color  = edge_colors,
        node_color  = node_colors,
        with_labels = True,
        node_size   = 800,
        font_size   = 9,
        width       = 3
    )
    plt.title(f"Hajj Traffic — Tick {model.tick}")
    plt.legend(
        handles=[
            plt.Line2D([0], [0], color="green",  lw=2, label="Clear  (< 50%)"),
            plt.Line2D([0], [0], color="orange", lw=2, label="Moderate (50–75%)"),
            plt.Line2D([0], [0], color="red",    lw=2, label="Congested (> 75%)"),
            plt.scatter([], [], color="gold",      label="Intersection Agent"),
            plt.scatter([], [], color="lightblue", label="Normal Node"),
        ],
        loc="lower left"
    )
    plt.tight_layout()
    plt.show()


def plot_results(model):
    data = model.datacollector.get_model_vars_dataframe()

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle("Hajj Traffic Simulation Results", fontsize=14)

    data["Congested Roads"].plot(
        ax     = axes[0][0],
        title  = "Congested Roads per Tick",
        color  = "red",
        ylabel = "Count",
        xlabel = "Tick"
    )
    data["Avg Occupancy (%)"].plot(
        ax     = axes[0][1],
        title  = "Average Road Occupancy (%)",
        color  = "orange",
        ylabel = "%",
        xlabel = "Tick"
    )
    data["Vehicles Arrived"].plot(
        ax     = axes[1][0],
        title  = "Vehicles Arrived at Destination",
        color  = "green",
        ylabel = "Count",
        xlabel = "Tick"
    )
    data["Emergency Arrived"].plot(
        ax     = axes[1][1],
        title  = "Emergency Vehicles Arrived",
        color  = "blue",
        ylabel = "Count",
        xlabel = "Tick"
    )

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":

    print("=" * 55)
    print("  Hajj Traffic Management System — Simulation")
    print("=" * 55)

    N_VEHICLES  = 30
    N_EMERGENCY = 3
    N_TICKS     = 100

    model = HajjModel(n_vehicles=N_VEHICLES, n_emergency=N_EMERGENCY)

    print(f"\nAgents created:")
    print(f"  Road Agent:           1")
    print(f"  Intersection Agents:  {len(model.intersection_agents)}")
    print(f"  Vehicle Agents:       {len(model.vehicle_agents)}")
    print(f"  Emergency Agents:     {len(model.emergency_agents)}")
    print(f"\nRunning {N_TICKS} ticks...\n")

    for tick in range(N_TICKS):
        model.step()

        if (tick + 1) % 10 == 0:
            print(f"  Tick {tick+1:3d} | "
                  f"Congested: {model._count_congested()} roads | "
                  f"Avg occupancy: {model._avg_occupancy_pct()}% | "
                  f"Arrived: {model._count_arrived()}/{N_VEHICLES} vehicles")

    print("\nSimulation complete.")
    print(f"  Vehicles arrived:   {model._count_arrived()} / {N_VEHICLES}")
    print(f"  Emergency arrived:  {model._count_emergency_arrived()} / {N_EMERGENCY}")

    visualize(model)
    plot_results(model)