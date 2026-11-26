"""Deterministic DPLL SAT solver with metrics used by the experiments."""
from dataclasses import dataclass
from time import perf_counter


@dataclass(frozen=True)
class SolveStats:
    decisions: int
    propagations: int
    backtracks: int
    runtime_ms: float


@dataclass(frozen=True)
class SolveResult:
    sat: bool
    model: dict[int, bool] | None
    stats: SolveStats


def solve(clauses, n_vars, assumptions=(), *, use_pure_literals=False):
    """Solve a CNF formula and return a complete model or UNSAT.

    Variables are positive integers in ``1..n_vars``. Branching always picks
    the smallest unassigned variable, which keeps runs reproducible.
    """
    started = perf_counter()
    decisions = propagations = backtracks = 0
    formula = tuple(tuple(clause) for clause in clauses)

    if n_vars < 0:
        raise ValueError('n_vars must be non-negative')
    if any(lit == 0 or abs(lit) > n_vars for clause in formula for lit in clause):
        raise ValueError('literal outside 1..n_vars')

    def result(model):
        return SolveResult(
            model is not None,
            model,
            SolveStats(decisions, propagations, backtracks,
                       (perf_counter() - started) * 1000),
        )

    initial = {}
    for literal in assumptions:
        if literal == 0 or abs(literal) > n_vars:
            raise ValueError('assumption outside 1..n_vars')
        variable, value = abs(literal), literal > 0
        if variable in initial and initial[variable] != value:
            return result(None)
        initial[variable] = value

    def inspect_clause(clause, assignment):
        free = []
        for literal in clause:
            variable = abs(literal)
            if variable in assignment:
                if assignment[variable] == (literal > 0):
                    return True, ()
            else:
                free.append(literal)
        return False, tuple(free)

    def propagate(assignment):
        nonlocal propagations
        assignment = dict(assignment)
        while True:
            changed = False
            for clause in formula:
                satisfied, free = inspect_clause(clause, assignment)
                if satisfied:
                    continue
                if not free:
                    return None
                if len(free) == 1:
                    literal = free[0]
                    variable, value = abs(literal), literal > 0
                    if variable in assignment and assignment[variable] != value:
                        return None
                    if variable not in assignment:
                        assignment[variable] = value
                        propagations += 1
                        changed = True
            if changed:
                continue

            if use_pure_literals:
                polarities = {}
                for clause in formula:
                    satisfied, free = inspect_clause(clause, assignment)
                    if satisfied:
                        continue
                    for literal in free:
                        polarities.setdefault(abs(literal), set()).add(literal > 0)
                pure = [(variable, next(iter(values)))
                        for variable, values in polarities.items() if len(values) == 1]
                if pure:
                    for variable, value in sorted(pure):
                        assignment[variable] = value
                        propagations += 1
                    continue
            return assignment

    def search(assignment):
        nonlocal decisions, backtracks
        assignment = propagate(assignment)
        if assignment is None:
            return None

        unresolved = []
        for clause in formula:
            satisfied, free = inspect_clause(clause, assignment)
            if not satisfied:
                unresolved.extend(free)
        if not unresolved:
            return {variable: assignment.get(variable, False)
                    for variable in range(1, n_vars + 1)}

        variable = next(variable for variable in range(1, n_vars + 1)
                        if variable not in assignment)
        for value in (True, False):
            decisions += 1
            model = search(assignment | {variable: value})
            if model is not None:
                return model
            backtracks += 1
        return None

    return result(search(initial))
