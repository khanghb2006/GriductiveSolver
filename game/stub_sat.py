"""Temporary stand-ins for build_kb (encoder) and solve (DPLL). Delete once the real modules land."""
from collections import namedtuple
from itertools import combinations
from .logic import CRIMINAL, referenced_cells

KB = namedtuple('KB', 'clauses n_primary n_aux')
Result = namedtuple('Result', 'sat model')


def build_kb(state):
    layout = state['layout']
    var = {cell['id']: i for i, cell in enumerate(layout, start=1)}  # row-major: C_i = i
    clauses = [[var[c] if s == CRIMINAL else -var[c]] for c, s in state['known'].items()]
    for clue in state['clues']:
        vs = [var[c] for c in referenced_cells(clue, layout)]
        kind = clue['type']
        if kind == 'FACT':
            clauses.append([vs[0] if clue['status'] == CRIMINAL else -vs[0]])
        elif kind in ('SAME', 'DIFFERENT'):
            a, b = vs[0], (vs[1] if kind == 'SAME' else -vs[1])
            clauses += [[-a, b], [a, -b]]                      # a <-> b
        else:                                                   # counting, direct combinations
            k, size = clue['k'], len(vs)
            if kind in ('EXACTLY', 'AT_MOST'):                  # no (k+1) cells all criminal
                clauses += [[-v for v in group] for group in combinations(vs, k + 1)]
            if kind in ('EXACTLY', 'AT_LEAST'):                 # among any (size-k+1) cells, one criminal
                clauses += [list(group) for group in combinations(vs, size - k + 1)]
    return KB(clauses, len(layout), 0)


def solve(clauses, n_vars, assumptions=()):
    def search(assignment):
        while True:                                             # unit propagation
            unit = None
            for clause in clauses:
                if any(assignment.get(abs(l)) == (l > 0) for l in clause):
                    continue                                    # clause already true
                free = [l for l in clause if abs(l) not in assignment]
                if not free:
                    return None                                 # clause false: conflict
                if len(free) == 1:
                    unit = free[0]
                    break
            if unit is None:
                break
            assignment = assignment | {abs(unit): unit > 0}
        var = next((v for v in range(1, n_vars + 1) if v not in assignment), None)
        if var is None:
            return assignment                                   # every variable assigned
        return search(assignment | {var: True}) or search(assignment | {var: False})

    assignment = {}
    for lit in assumptions:
        if assignment.setdefault(abs(lit), lit > 0) != (lit > 0):
            return Result(False, None)                          # contradictory assumptions
    model = search(assignment)
    return Result(model is not None, model)