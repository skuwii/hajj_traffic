PERFORMATIVES = {'INFORM', 'REROUTE', 'PREEMPT', 'ACCEPT', 'REJECT', 'CLEAR'}

NODES = ['haram', 'mina_gate', 'arafat', 'muzdalifah', 'aziziyah', 'jamarat', 'tunnel']

MESSAGE_SCHEMA = {
    'performative': str,
    'sender': str,
    'content': dict,
    'tick': int
}

SEGMENT_TO_APPROACH = {
    ('haram',      'aziziyah'):  'S',
    ('mina_gate',  'aziziyah'):  'N',
    ('haram',      'tunnel'):    'E',
    ('aziziyah',   'tunnel'):    'S',
    ('mina_gate',  'tunnel'):    'W',
    ('aziziyah',   'jamarat'):   'E',
    ('mina_gate',  'jamarat'):   'W',
    ('muzdalifah', 'haram'):     'W',
}