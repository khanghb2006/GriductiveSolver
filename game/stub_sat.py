"""Temporary SAT solver used until the team's instrumented DPLL lands."""
from collections import namedtuple

Result = namedtuple('Result', 'sat model')


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
