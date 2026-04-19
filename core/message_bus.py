from collections import defaultdict, deque

class MessageBus:
    def __init__(self):
        self.queues = defaultdict(deque) # agent_id → messages

    def send(self, to, performative, content, sender):
        self.queues[to].append({
        'performative': performative, # e.g. 'REROUTE'
        'content': content, # actual data payload
        'sender': sender # who sent it
    })
        
    def receive(self, agent_id):
        msgs = list(self.queues[agent_id])
        self.queues[agent_id].clear()
        return msgs
    
    def broadcast(self, performative, content, sender, all_ids):
        for aid in all_ids:
        self.send(aid, performative, content, sender)