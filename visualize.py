import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.animation as animation
import matplotlib.patheffects as pe
import networkx as nx
import numpy as np

# ── Colour palette (STR system) ─────────────────────────────────────────────
BG        = "#0e0f11"
SURFACE   = "#1c1e21"
AZURE     = "#2980d4"
RED       = "#c0392b"
WHITE     = "#e8eaed"
DIM       = "#4a4d52"
GREEN     = "#27ae60"
YELLOW    = "#f39c12"
FONT      = "monospace"

# ── Node positions (lat/lon → display coords) ───────────────────────────────
NODE_POS = {
    'haram':      (0.30, 0.82),
    'aziziyah':   (0.50, 0.62),
    'mina_gate':  (0.72, 0.50),
    'muzdalifah': (0.60, 0.28),
    'arafat':     (0.82, 0.12),
}

NODE_LABELS = {
    'haram':      'Al-Haram',
    'aziziyah':   'Aziziyah',
    'mina_gate':  'Mina Gate',
    'muzdalifah': 'Muzdalifah',
    'arafat':     'Arafat',
}

EDGES = [
    ('haram',      'aziziyah'),
    ('aziziyah',   'mina_gate'),
    ('mina_gate',  'muzdalifah'),
    ('muzdalifah', 'arafat'),
]

# ── Congestion colour ramp ───────────────────────────────────────────────────
def congestion_color(ratio):
    """0.0 = clear (green) → 0.6 = warning (yellow) → 1.0 = critical (red)"""
    if ratio < 0.60:
        t = ratio / 0.60
        r = int(39  + t * (243 - 39))
        g = int(174 + t * (156 - 174))
        b = int(96  + t * (18  - 96))
    else:
        t = (ratio - 0.60) / 0.40
        r = int(243 + t * (192 - 243))
        g = int(156 + t * (57  - 156))
        b = int(18  + t * (43  - 18))
    return f"#{r:02x}{g:02x}{b:02x}"

# ── Main visualiser class ────────────────────────────────────────────────────
class SimVisualizer:
    def __init__(self, model):
        self.model = model

        plt.rcParams.update({
            'font.family':      'monospace',
            'text.color':       WHITE,
            'axes.facecolor':   BG,
            'figure.facecolor': BG,
        })

        self.fig = plt.figure(figsize=(16, 9), facecolor=BG)
        self.fig.canvas.manager.set_window_title("Hajj Traffic Management System · CS3081")

        # Layout: main graph (left) + stats panel (right)
        self.ax_map   = self.fig.add_axes([0.01, 0.05, 0.64, 0.90])
        self.ax_stats = self.fig.add_axes([0.67, 0.05, 0.31, 0.90])

        for ax in (self.ax_map, self.ax_stats):
            ax.set_facecolor(SURFACE)
            for spine in ax.spines.values():
                spine.set_edgecolor(DIM)

        self._draw_static_frame()

    # ── Static chrome ────────────────────────────────────────────────────────
    def _draw_static_frame(self):
        self.fig.text(0.01, 0.97,
                      "HAJJ TRAFFIC MANAGEMENT SYSTEM",
                      fontsize=13, fontweight='bold',
                      color=AZURE, fontfamily=FONT, va='top')
        self.fig.text(0.01, 0.955,
                      "Multi-Agent Simulation  ·  CS3081  ·  Effat University  ·  Spring 2026",
                      fontsize=7.5, color=DIM, fontfamily=FONT, va='top')

        # Legend
        legend_items = [
            mpatches.Patch(color=GREEN,  label='Clear  (< 60%)'),
            mpatches.Patch(color=YELLOW, label='Warning (60–75%)'),
            mpatches.Patch(color=RED,    label='Critical (> 75%)'),
            mpatches.Patch(color=AZURE,  label='Intersection Agent'),
            mpatches.Patch(color='#8e44ad', label='Emergency Vehicle'),
        ]
        self.fig.legend(handles=legend_items,
                        loc='lower left', bbox_to_anchor=(0.01, 0.01),
                        framealpha=0.15, facecolor=SURFACE,
                        edgecolor=DIM, fontsize=8,
                        labelcolor=WHITE)

    # ── Per-tick render ──────────────────────────────────────────────────────
    def render(self, tick):
        self.ax_map.clear()
        self.ax_stats.clear()

        self._render_map(tick)
        self._render_stats(tick)

        plt.draw()
        plt.pause(0.05)

    # ── Road map ─────────────────────────────────────────────────────────────
    def _render_map(self, tick):
        ax = self.ax_map
        ax.set_facecolor(BG)
        ax.set_xlim(-0.05, 1.05)
        ax.set_ylim(-0.05, 1.05)
        ax.axis('off')

        # Tick badge
        ax.text(0.98, 0.98, f"TICK  {tick:04d}",
                transform=ax.transAxes,
                fontsize=11, fontfamily=FONT,
                color=AZURE, fontweight='bold',
                ha='right', va='top',
                bbox=dict(boxstyle='round,pad=0.4',
                          facecolor=SURFACE, edgecolor=AZURE, linewidth=1.2))

        graph = self.model.graph

        # ── Edges ────────────────────────────────────────────────────────────
        for u, v in EDGES:
            x0, y0 = NODE_POS[u]
            x1, y1 = NODE_POS[v]
            occ = graph[u][v]['occupancy']
            cap = graph[u][v]['capacity']
            ratio = occ / cap if cap else 0
            color = congestion_color(ratio)

            # Shadow
            ax.plot([x0, x1], [y0, y1], color='black', linewidth=8,
                    solid_capstyle='round', alpha=0.5, zorder=1)
            # Road
            ax.plot([x0, x1], [y0, y1], color=color, linewidth=4.5,
                    solid_capstyle='round', zorder=2)

            # Occupancy label
            mx, my = (x0+x1)/2, (y0+y1)/2
            ax.text(mx, my + 0.025,
                    f"{occ}/{cap}",
                    fontsize=7.5, fontfamily=FONT,
                    color=WHITE, ha='center', va='bottom',
                    bbox=dict(boxstyle='round,pad=0.2',
                              facecolor=SURFACE, edgecolor=color,
                              linewidth=0.8, alpha=0.85),
                    zorder=5)

            # Flow arrow
            dx, dy = x1-x0, y1-y0
            ax.annotate('', xy=(x0+dx*0.65, y0+dy*0.65),
                        xytext=(x0+dx*0.35, y0+dy*0.35),
                        arrowprops=dict(arrowstyle='->', color=color,
                                        lw=1.5), zorder=3)

        # ── Nodes ────────────────────────────────────────────────────────────
        for node, (x, y) in NODE_POS.items():
            is_intersection = (node == 'aziziyah')

            # Glow ring
            glow_color = AZURE if is_intersection else DIM
            glow = plt.Circle((x, y), 0.038, color=glow_color,
                               alpha=0.18, zorder=3)
            ax.add_patch(glow)

            # Node body
            body_color = AZURE if is_intersection else "#2c3e50"
            body = plt.Circle((x, y), 0.026, color=body_color,
                               zorder=4, linewidth=1.8,
                               ec=WHITE if is_intersection else DIM)
            ax.add_patch(body)

            # Node label
            ax.text(x, y - 0.055,
                    NODE_LABELS[node],
                    fontsize=8.5, fontfamily=FONT,
                    color=WHITE if is_intersection else DIM,
                    fontweight='bold' if is_intersection else 'normal',
                    ha='center', va='top', zorder=6)

            # Intersection phase badge
            if is_intersection:
                ia = self.model.intersection_agents[0]
                phase = ia.current_phase
                phase_color = GREEN if not ia.preempted else RED
                ax.text(x + 0.04, y + 0.04,
                        f"▶ {phase}",
                        fontsize=7.5, fontfamily=FONT,
                        color=phase_color, fontweight='bold',
                        ha='left', va='bottom', zorder=7)

        # ── Emergency vehicle ─────────────────────────────────────────────────
        ea = self.model.emergency_agent
        if hasattr(ea, 'current_node') and ea.current_node in NODE_POS:
            ex, ey = NODE_POS[ea.current_node]
            emerg = plt.Circle((ex, ey), 0.035, color='#8e44ad',
                                zorder=8, alpha=0.85, ec=WHITE, linewidth=1.5)
            ax.add_patch(emerg)
            ax.text(ex, ey + 0.055, "🚑 EMERGENCY",
                    fontsize=7.5, fontfamily=FONT,
                    color='#8e44ad', fontweight='bold',
                    ha='center', va='bottom', zorder=9)

        # ── Vehicle agents ────────────────────────────────────────────────────
        vehicle_counts = {}
        for va in self.model.vehicle_agents:
            if hasattr(va, 'current_node') and va.current_node in NODE_POS:
                vehicle_counts[va.current_node] = vehicle_counts.get(va.current_node, 0) + 1

        for node, count in vehicle_counts.items():
            x, y = NODE_POS[node]
            ax.text(x + 0.042, y - 0.01,
                    f"🚗 ×{count}",
                    fontsize=7, fontfamily=FONT,
                    color=YELLOW, ha='left', va='center', zorder=7)

    # ── Stats panel ───────────────────────────────────────────────────────────
    def _render_stats(self, tick):
        ax = self.ax_stats
        ax.set_facecolor(SURFACE)
        ax.axis('off')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

        y = 0.96

        def section(title):
            nonlocal y
            ax.text(0.0, y, title,
                    fontsize=8, fontfamily=FONT,
                    color=AZURE, fontweight='bold', va='top')
            y -= 0.025
            ax.axhline(y, color=DIM, linewidth=0.6, xmin=0, xmax=1)
            y -= 0.015

        def row(label, value, color=WHITE):
            nonlocal y
            ax.text(0.02, y, label,
                    fontsize=7.5, fontfamily=FONT,
                    color=DIM, va='top')
            ax.text(0.98, y, str(value),
                    fontsize=7.5, fontfamily=FONT,
                    color=color, va='top', ha='right', fontweight='bold')
            y -= 0.038

        # Header
        ax.text(0.5, y, "SYSTEM STATUS",
                fontsize=10, fontfamily=FONT,
                color=WHITE, fontweight='bold',
                ha='center', va='top')
        y -= 0.045

        # ── Road segments ─────────────────────────────────────────────────────
        section("ROAD SEGMENTS")
        graph = self.model.graph
        for u, v in EDGES:
            occ = graph[u][v]['occupancy']
            cap = graph[u][v]['capacity']
            ratio = occ / cap if cap else 0
            status = "CRITICAL" if ratio > 0.75 else ("WARNING" if ratio > 0.60 else "CLEAR")
            color  = RED if ratio > 0.75 else (YELLOW if ratio > 0.60 else GREEN)
            label = f"{NODE_LABELS[u][:6]}→{NODE_LABELS[v][:6]}"
            row(label, f"{int(ratio*100)}%  {status}", color)

        y -= 0.01
        # ── Intersection ──────────────────────────────────────────────────────
        section("INTERSECTION · AZIZIYAH")
        ia = self.model.intersection_agents[0]
        row("Mode",   "PREEMPTED" if ia.preempted else "CSP ACTIVE",
            RED if ia.preempted else GREEN)
        row("Green phase", ia.current_phase)
        for approach, t in ia.phase_schedule.items():
            row(f"  Phase {approach}", f"{t}s")

        y -= 0.01
        # ── Road agent ────────────────────────────────────────────────────────
        section("ROAD AGENT")
        ra = self.model.road_agent
        saturated = [(u, v) for (u, v), b in ra.belief.items()
                     if b > 0.75 * graph[u][v]['capacity']]
        row("Segments monitored", len(list(graph.edges())))
        row("Saturated segments", len(saturated),
            RED if saturated else GREEN)

        y -= 0.01
        # ── Emergency agent ───────────────────────────────────────────────────
        section("EMERGENCY AGENT")
        ea = self.model.emergency_agent
        pos = getattr(ea, 'current_node', 'inactive')
        active = getattr(ea, 'preemption_active', False)
        row("Position",  pos)
        row("Preemption", "ACTIVE" if active else "INACTIVE",
            RED if active else DIM)

        y -= 0.01
        # ── Vehicles ──────────────────────────────────────────────────────────
        section("VEHICLE AGENTS")
        total   = len(self.model.vehicle_agents)
        arrived = sum(1 for v in self.model.vehicle_agents
                      if getattr(v, 'arrived', False))
        row("Total vehicles", total)
        row("Arrived",        arrived, GREEN)
        row("En route",       total - arrived, AZURE)

        y -= 0.01
        # ── Message bus ───────────────────────────────────────────────────────
        section("MESSAGE BUS")
        total_msgs = sum(len(q) for q in self.model.bus.queues.values())
        row("Queued messages", total_msgs, AZURE if total_msgs else DIM)

        # Footer
        ax.text(0.5, 0.02,
                f"Effat University  ·  Dr. Naila Marir  ·  Tick {tick}",
                fontsize=6.5, fontfamily=FONT,
                color=DIM, ha='center', va='bottom')


# ── Standalone test (run: python visualize.py) ───────────────────────────────
if __name__ == '__main__':
    from core.road_graph import build_mecca_graph
    from core.message_bus import MessageBus

    class _FakeIntersection:
        current_phase    = 'N'
        preempted        = False
        phase_schedule   = {'N': 72, 'S': 48}

    class _FakeEmergency:
        current_node      = 'mina_gate'
        preemption_active = True

    class _FakeVehicle:
        def __init__(self, node, arrived=False):
            self.current_node = node
            self.arrived      = arrived

    class _FakeRoadAgent:
        def __init__(self, graph):
            self.belief = {(u, v): 0 for u, v in graph.edges()}

    class _FakeModel:
        def __init__(self):
            self.graph = build_mecca_graph()
            self.graph['haram']['aziziyah']['occupancy']    = 140
            self.graph['aziziyah']['mina_gate']['occupancy'] = 110
            self.graph['mina_gate']['muzdalifah']['occupancy'] = 60
            self.graph['muzdalifah']['arafat']['occupancy']  = 20
            self.bus                  = MessageBus()
            self.road_agent           = _FakeRoadAgent(self.graph)
            self.intersection_agents  = [_FakeIntersection()]
            self.emergency_agent      = _FakeEmergency()
            self.vehicle_agents       = [
                _FakeVehicle('haram'),
                _FakeVehicle('haram'),
                _FakeVehicle('aziziyah'),
                _FakeVehicle('mina_gate', arrived=True),
            ]

    model = _FakeModel()
    viz   = SimVisualizer(model)

    def animate(tick):
        # Wiggle occupancy slightly to show live update
        model.graph['haram']['aziziyah']['occupancy'] = min(200, 140 + tick * 2)
        viz.render(tick)

    ani = animation.FuncAnimation(viz.fig, animate, frames=50,
                                  interval=200, repeat=False)
    plt.show()
