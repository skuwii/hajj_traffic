# interfaces.py — all agents import from this file
PERFORMATIVES = {'INFORM', 'REROUTE', 'PREEMPT', 'ACCEPT', 'REJECT', 'CLEAR'}
# Agreed node names — everyone must use these exact strings
NODES = ['haram', 'mina_gate', 'arafat', 'muzdalifah', 'aziziyah']
# Message schema — all fields required
MESSAGE_SCHEMA = {
'performative': str, # one of PERFORMATIVES above
'sender': str, # agent unique_id
'content': dict, # payload (route, segment_id, phase, etc.)
'tick': int # simulation timestamp
}