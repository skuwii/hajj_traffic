import mesa
from interfaces import SEGMENT_TO_APPROACH
from utils.csp_solver import solve_csp

class IntersectionAgent(mesa.Agent):
    def __init__(self, model, bus, node_id):
        super().__init__(model)
        self.bus = bus
        self.node_id = node_id
        self.queue_lengths = {'N': 0, 'S': 0}
        self.current_phase = 'N'
        self.phase_schedule = {'N': 60, 'S': 60}
        self.preempted = False
        self.emergency_approach = None

    def process_messages(self):
        messages = self.bus.receive(self.unique_id)
        for msg in messages:
            if msg['performative'] == 'INFORM':
                road_state = msg['content'].get('road_state', {})
                for segment, occupancy in road_state.items():
                    if segment in SEGMENT_TO_APPROACH:
                        approach = SEGMENT_TO_APPROACH[segment]
                        self.queue_lengths[approach] = occupancy
            elif msg['performative'] == 'PREEMPT':
                if not self.preempted:
                    self.preempted = True
                    self.emergency_approach = msg['content']['approach']
                    self.bus.send(msg['sender'], 'ACCEPT',
                        {'intersection_id': self.node_id,
                         'granted_approach': self.emergency_approach},
                        self.unique_id)
                else:
                    self.bus.send(msg['sender'], 'REJECT',
                        {'intersection_id': self.node_id},
                        self.unique_id)
            elif msg['performative'] == 'CLEAR':
                self.preempted = False
                self.emergency_approach = None

    def step(self):
        self.process_messages()
        if self.preempted:
            self.current_phase = self.emergency_approach
            return
        self.phase_schedule = solve_csp(self.queue_lengths)
        self.current_phase = max(self.phase_schedule, key=self.phase_schedule.get)
        self.bus.broadcast('INFORM',
            {'intersection_id': self.node_id,
             'current_phase': self.current_phase,
             'phase_schedule': self.phase_schedule},
            self.unique_id,
            self.model.all_agent_ids())