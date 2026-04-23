from interfaces import SEGMENT_TO_APPROACH

def solve_csp(queues, cycle=120, min_green=10):
    total = sum(queues.values()) or 1
    schedule = {a: max(min_green, round((q / total) * cycle)) for a, q in queues.items()}
    diff = cycle - sum(schedule.values())
    biggest = max(schedule, key=schedule.get)
    schedule[biggest] += diff
    return schedule