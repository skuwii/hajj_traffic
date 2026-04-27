import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.animation as animation

BG        = "#111316"
SURFACE   = "#161a1f"
ACCENT    = "#4a9eff"
RED       = "#e74c3c"
WHITE     = "#e8eaed"
DIM       = "#5a6070"
GREEN     = "#2ecc71"
YELLOW    = "#f1c40f"
PURPLE    = "#9b59b6"
FONT      = "monospace"

NODE_POS = {
    'haram':      (0.18, 0.82),
    'tunnel':     (0.35, 0.72),
    'aziziyah':   (0.40, 0.55),
    'jamarat':    (0.62, 0.72),
    'mina_gate':  (0.65, 0.55),
    'muzdalifah': (0.72, 0.32),
    'arafat':     (0.88, 0.12),
}

NODE_LABELS = {
    'haram':      'Al-Haram',
    'tunnel':     'Tunnel',
    'aziziyah':   'Aziziyah',
    'jamarat':    'Jamarat',
    'mina_gate':  'Mina Gate',
    'muzdalifah': 'Muzdalifah',
    'arafat':     'Arafat',
}

INTERSECTION_NODES = {'aziziyah', 'muzdalifah', 'jamarat', 'tunnel'}

EDGES = [
    ('haram',      'aziziyah'),
    ('haram',      'tunnel'),
    ('tunnel',     'aziziyah'),
    ('tunnel',     'mina_gate'),
    ('tunnel',     'jamarat'),
    ('aziziyah',   'mina_gate'),
    ('aziziyah',   'jamarat'),
    ('jamarat',    'mina_gate'),
    ('mina_gate',  'muzdalifah'),
    ('muzdalifah', 'arafat'),
]

def congestion_color(ratio):
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

        self.ax_map   = self.fig.add_axes([0.01, 0.05, 0.62, 0.90])
        self.ax_stats = self.fig.add_axes([0.65, 0.05, 0.34, 0.90])

        for ax in (self.ax_map, self.ax_stats):
            ax.set_facecolor(SURFACE)
            for spine in ax.spines.values():
                spine.set_edgecolor(DIM)

        self._draw_static_frame()

    def _draw_static_frame(self):
        self.fig.text(0.01, 0.97,
                      "HAJJ TRAFFIC MANAGEMENT SYSTEM",
                      fontsize=13, fontweight='bold',
                      color=WHITE, fontfamily=FONT, va='top')
        self.fig.text(0.01, 0.955,
                      "Multi-Agent Simulation  ·  CS3081  ·  Effat University  ·  Spring 2026",
                      fontsize=7.5, color=DIM, fontfamily=FONT, va='top')

        legend_items = [
            mpatches.Patch(color=GREEN,  label='Clear  (< 60%)'),
            mpatches.Patch(color=YELLOW, label='Warning (60-75%)'),
            mpatches.Patch(color=RED,    label='Critical (> 75%)'),
            mpatches.Patch(color=ACCENT, label='Intersection Agent'),
            mpatches.Patch(color=PURPLE, label='Emergency Vehicle'),
        ]
        self.fig.legend(handles=legend_items,
                        loc='lower left', bbox_to_anchor=(0.01, 0.01),
                        framealpha=0.15, facecolor=SURFACE,
                        edgecolor=DIM, fontsize=8,
                        labelcolor=WHITE)

    def render(self, tick):
        self.ax_map.clear()
        self.ax_stats.clear()
        self._render_map(tick)
        self._render_stats(tick)
        plt.draw()
        plt.pause(0.4)

    def _get_active_emergency(self):
        ea = next((a for a in self.model.emergency_agents if not a.arrived), None)
        if ea is None and self.model.emergency_agents:
            ea = self.model.emergency_agents[-1]
        return ea

    def _render_map(self, tick):
        ax = self.ax_map
        ax.set_facecolor(BG)
        ax.set_xlim(-0.05, 1.05)
        ax.set_ylim(-0.05, 1.05)
        ax.axis('off')

        ax.text(0.98, 0.98, f"TICK  {tick:04d}",
                transform=ax.transAxes,
                fontsize=11, fontfamily=FONT,
                color=ACCENT, fontweight='bold',
                ha='right', va='top',
                bbox=dict(boxstyle='round,pad=0.4',
                          facecolor=SURFACE, edgecolor=ACCENT, linewidth=1.2))

        graph = self.model.graph

        for u, v in EDGES:
            if not graph.has_edge(u, v):
                continue
            x0, y0 = NODE_POS[u]
            x1, y1 = NODE_POS[v]
            occ   = graph[u][v]['occupancy']
            cap   = graph[u][v]['capacity']
            ratio = occ / cap if cap else 0
            color = congestion_color(ratio)

            ax.plot([x0, x1], [y0, y1], color='black', linewidth=8,
                    solid_capstyle='round', alpha=0.5, zorder=1)
            ax.plot([x0, x1], [y0, y1], color=color, linewidth=4.5,
                    solid_capstyle='round', zorder=2)

            mx, my = (x0+x1)/2, (y0+y1)/2
            ax.text(mx, my + 0.025, f"{int(occ)}/{cap}",
                    fontsize=7, fontfamily=FONT,
                    color=WHITE, ha='center', va='bottom',
                    bbox=dict(boxstyle='round,pad=0.2',
                              facecolor=SURFACE, edgecolor=color,
                              linewidth=0.8, alpha=0.85),
                    zorder=5)

            dx, dy = x1-x0, y1-y0
            ax.annotate('', xy=(x0+dx*0.65, y0+dy*0.65),
                        xytext=(x0+dx*0.35, y0+dy*0.35),
                        arrowprops=dict(arrowstyle='->', color=color, lw=1.5),
                        zorder=3)

        for node, (x, y) in NODE_POS.items():
            is_intersection = node in INTERSECTION_NODES

            glow_color = ACCENT if is_intersection else DIM
            glow = plt.Circle((x, y), 0.038, color=glow_color, alpha=0.18, zorder=3)
            ax.add_patch(glow)

            body_color = ACCENT if is_intersection else "#2c3e50"
            body = plt.Circle((x, y), 0.026, color=body_color,
                               zorder=4, linewidth=1.8,
                               ec=WHITE if is_intersection else DIM)
            ax.add_patch(body)

            ax.text(x, y - 0.055, NODE_LABELS[node],
                    fontsize=8.5, fontfamily=FONT,
                    color=WHITE if is_intersection else DIM,
                    fontweight='bold' if is_intersection else 'normal',
                    ha='center', va='top', zorder=6)

            if is_intersection:
                matching = [ia for ia in self.model.intersection_agents
                            if ia.node_id == node]
                if matching:
                    ia = matching[0]
                    phase_color = RED if ia.preempted else GREEN
                    ax.text(x + 0.04, y + 0.04, f">> {ia.current_phase}",
                            fontsize=7, fontfamily=FONT,
                            color=phase_color, fontweight='bold',
                            ha='left', va='bottom', zorder=7)

        ea = self._get_active_emergency()
        if ea is not None and hasattr(ea, 'position') and ea.position in NODE_POS:
            ex, ey = NODE_POS[ea.position]
            emerg = plt.Circle((ex, ey), 0.035, color=PURPLE,
                                zorder=8, alpha=0.85, ec=WHITE, linewidth=1.5)
            ax.add_patch(emerg)
            ax.text(ex, ey + 0.058, "EMERGENCY",
                    fontsize=7.5, fontfamily=FONT,
                    color=PURPLE, fontweight='bold',
                    ha='center', va='bottom', zorder=9)

        vehicle_counts = {}
        for va in self.model.vehicle_agents:
            if hasattr(va, 'position') and va.position in NODE_POS and not va.arrived:
                vehicle_counts[va.position] = vehicle_counts.get(va.position, 0) + 1

        for node, count in vehicle_counts.items():
            x, y = NODE_POS[node]
            ax.text(x + 0.042, y - 0.01, f"[{count}] vehicles",
                    fontsize=7, fontfamily=FONT,
                    color=YELLOW, ha='left', va='center', zorder=7)

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
                    fontsize=7.5, fontfamily=FONT,
                    color=ACCENT, fontweight='bold', va='top')
            y -= 0.018
            ax.axhline(y, color=DIM, linewidth=0.6, xmin=0, xmax=1)
            y -= 0.010

        def row(label, value, color=WHITE):
            nonlocal y
            ax.text(0.02, y, label,
                    fontsize=7, fontfamily=FONT, color=DIM, va='top')
            ax.text(0.98, y, str(value),
                    fontsize=7, fontfamily=FONT,
                    color=color, va='top', ha='right', fontweight='bold')
            y -= 0.028

        ax.text(0.5, y, "SYSTEM STATUS",
                fontsize=10, fontfamily=FONT,
                color=WHITE, fontweight='bold',
                ha='center', va='top')
        y -= 0.038

        section("ROAD SEGMENTS")
        graph = self.model.graph
        for u, v in EDGES:
            if not graph.has_edge(u, v):
                continue
            occ   = graph[u][v]['occupancy']
            cap   = graph[u][v]['capacity']
            ratio = occ / cap if cap else 0
            status = "CRIT" if ratio > 0.75 else ("WARN" if ratio > 0.60 else "OK")
            color  = RED if ratio > 0.75 else (YELLOW if ratio > 0.60 else GREEN)
            label  = f"{NODE_LABELS[u][:5]}>{NODE_LABELS[v][:5]}"
            row(label, f"{int(ratio*100)}% {status}", color)

        y -= 0.005
        section("INTERSECTIONS")
        for ia in self.model.intersection_agents:
            color = RED if ia.preempted else GREEN
            mode  = f"PREEMPT [{ia.current_phase}]" if ia.preempted else f"CSP [{ia.current_phase}]"
            row(ia.node_id.capitalize(), mode, color)

        y -= 0.005
        section("ROAD AGENT")
        ra = self.model.road_agent
        saturated = [(u, v) for (u, v), b in ra.belief.items()
                     if b > 0.75 * graph[u][v]['capacity']]
        row("Segments monitored", len(list(graph.edges())))
        row("Saturated", len(saturated), RED if saturated else GREEN)

        y -= 0.005
        section("EMERGENCY AGENT")
        ea = self._get_active_emergency()
        if ea is not None:
            pos    = getattr(ea, 'position', 'unknown')
            active = getattr(ea, 'preemption_active', False)
            vtype  = getattr(ea, 'vehicle_type', 'unknown')
            row("Type",       vtype.replace('_', ' ').title())
            row("Position",   pos)
            row("Preemption", "ACTIVE" if active else "INACTIVE",
                RED if active else DIM)
            total_ea   = len(self.model.emergency_agents)
            arrived_ea = sum(1 for a in self.model.emergency_agents if a.arrived)
            row("Arrived", f"{arrived_ea}/{total_ea}", GREEN)
        else:
            row("Status", "none spawned yet", DIM)

        y -= 0.005
        section("VEHICLE AGENTS")
        total   = len(self.model.vehicle_agents)
        arrived = sum(1 for v in self.model.vehicle_agents if getattr(v, 'arrived', False))
        pending = len(getattr(self.model, '_vehicle_spawn_queue', []))
        row("Spawned",  total)
        row("Arrived",  arrived, GREEN)
        row("En route", total - arrived, ACCENT)
        row("Pending",  pending, DIM)

        y -= 0.005
        section("MESSAGE BUS")
        total_msgs = sum(len(q) for q in self.model.bus.queues.values())
        row("Queued messages", total_msgs, ACCENT if total_msgs else DIM)

        ax.text(0.5, 0.02,
                f"Effat University  ·  Dr. Naila Marir  ·  Tick {tick}",
                fontsize=6.5, fontfamily=FONT,
                color=DIM, ha='center', va='bottom')
