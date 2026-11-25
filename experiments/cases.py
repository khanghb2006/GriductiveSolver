"""Extra benchmark-only puzzles needed for balanced 3x3/4x4 experiments."""
from game.logic import CRIMINAL, INNOCENT
from game.puzzles import JOBS, NAMES, PUZZLES, case, cells, count, different, fact, same


def _benchmark_case(pid, title, size, labels, offset):
    """Create a deterministic reveal chain using relational/counting clues.

    These cases stay outside the UI's authored corpus. Every clue is validated
    by ``game.puzzles.case`` against the supplied solution.
    """
    ids = [f'{chr(65 + column)}{row}'
           for row in range(1, size + 1) for column in range(size)]
    authored = {}
    for index, owner in enumerate(ids):
        if index + 2 >= len(ids):
            target = ids[index % 2]
            authored[owner] = fact(
                target, CRIMINAL if labels[index % 2] else INNOCENT)
            continue

        anchor, target = ids[index + 1], ids[index + 2]
        anchor_value, target_value = labels[index + 1], labels[index + 2]
        mode = index % 3
        if mode == 0:
            authored[owner] = (same(anchor, target) if anchor_value == target_value
                               else different(anchor, target))
        elif mode == 1:
            authored[owner] = count(
                'EXACTLY', int(anchor_value) + int(target_value), cells(anchor, target))
        elif target_value:
            authored[owner] = count(
                'AT_LEAST', int(anchor_value) + 1, cells(anchor, target))
        else:
            authored[owner] = count(
                'AT_MOST', int(anchor_value), cells(anchor, target))

    rotated_names = NAMES[offset:] + NAMES[:offset]
    rotated_jobs = JOBS[offset:] + JOBS[:offset]
    return case(pid, title, size, rotated_names, rotated_jobs, labels,
                authored, ids[:2])


EXTRA_PUZZLES = (
    _benchmark_case(
        'benchmark-3-river', 'Dấu chân bên sông', 3,
        [False, True, True, False, True, False, False, True, False], 2),
    _benchmark_case(
        'benchmark-3-market', 'Phiên chợ cuối ngày', 3,
        [True, False, True, True, False, False, True, False, True], 4),
    _benchmark_case(
        'benchmark-4-tower', 'Bóng tối trên tháp canh', 4,
        [False, True, False, True, True, False, True, False,
         False, False, True, True, True, False, False, True], 1),
    _benchmark_case(
        'benchmark-4-bridge', 'Lời thề dưới chân cầu', 4,
        [True, False, False, True, False, True, True, False,
         True, True, False, False, False, True, False, True], 3),
)

BENCHMARK_PUZZLES = dict(PUZZLES)
BENCHMARK_PUZZLES.update((puzzle['id'], puzzle) for puzzle in EXTRA_PUZZLES)
