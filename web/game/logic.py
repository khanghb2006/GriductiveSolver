"""Public-only semantic oracle. Replace ExhaustiveAgent with the team's SAT agent."""
from dataclasses import dataclass
from math import prod
from typing import Protocol

CRIMINAL, INNOCENT, UNKNOWN = 'CRIMINAL', 'INNOCENT', 'UNKNOWN'


def region_cells(region, layout):
    ids = [c['id'] for c in layout]
    kind = region['kind']
    if kind == 'LIST':
        cells = region['cells']
        if len(set(cells)) != len(cells) or not set(cells) <= set(ids):
            raise ValueError('Invalid explicit region')
        return list(cells)
    if kind == 'ROW':
        return [c['id'] for c in layout if c['row'] == region['row']]
    if kind == 'COLUMN':
        return [c['id'] for c in layout if c['column'] == region['column']]
    if kind == 'NEIGHBORS':
        center = next(c for c in layout if c['id'] == region['cell'])
        return [c['id'] for c in layout if c != center and
                max(abs(c['row']-center['row']), abs(c['column']-center['column'])) == 1]
    raise ValueError('Unknown region')


def referenced_cells(clue, layout):
    return region_cells(clue['region'], layout) if 'region' in clue else list(clue['cells'])


def evaluate(clue, assignment, layout):
    cells = referenced_cells(clue, layout)
    values = [assignment[c] for c in cells]
    kind = clue['type']
    if kind == 'FACT':
        return values[0] == (clue['status'] == CRIMINAL)
    if kind == 'SAME':
        return values[0] == values[1]
    if kind == 'DIFFERENT':
        return values[0] != values[1]
    k = clue['k']
    if type(k) is not int or not 0 <= k <= len(cells):
        raise ValueError('Invalid count')
    count = sum(values)
    if kind == 'EXACTLY':
        return count == k
    if kind == 'AT_LEAST':
        return count >= k
    if kind == 'AT_MOST':
        return count <= k
    raise ValueError('Unknown clue type')


@dataclass
class Inference:
    statuses: dict
    model_count: int


class LogicAgent(Protocol):
    def classify(self, public_state: dict) -> Inference: ...


class ExhaustiveAgent:
    """Exact public-model search with propagation, pruning and component factoring.

    The historical class name/interface stays stable for engine and SAT adapters.
    This remains a semantic constraint oracle, not a CNF/DPLL implementation.
    """
    def classify(self, public_state):
        layout = public_state['layout']
        known = public_state['known']
        unresolved = [c['id'] for c in layout if c['id'] not in known]
        base = {c: s == CRIMINAL for c, s in known.items()}
        # Compile public constraints once, then propagate and prune partial models.
        constraints = []
        for clue in public_state['clues']:
            cells = tuple(referenced_cells(clue, layout))
            kind = clue['type']
            value = clue.get('k') if 'region' in clue or kind in ('EXACTLY','AT_LEAST','AT_MOST') else clue.get('status')
            if kind in ('EXACTLY','AT_LEAST','AT_MOST'):
                if type(value) is not int or not 0 <= value <= len(cells):
                    raise ValueError('Invalid count')
            elif kind not in ('FACT','SAME','DIFFERENT'):
                raise ValueError('Unknown clue type')
            constraints.append((kind, cells, value))

        def bounds(constraint, assignment):
            """Return (still possible, already true for every extension)."""
            kind, cells, value = constraint
            if kind == 'FACT':
                if cells[0] not in assignment:
                    return True, False
                valid = assignment[cells[0]] == (value == CRIMINAL)
                return valid, valid
            if kind in ('SAME', 'DIFFERENT'):
                if cells[0] == cells[1]:
                    return (kind == 'SAME', kind == 'SAME')
                if not all(c in assignment for c in cells):
                    return True, False
                valid = (assignment[cells[0]] == assignment[cells[1]]) == (kind == 'SAME')
                return valid, valid
            lower = sum(assignment.get(c, False) for c in cells)
            upper = lower + sum(c not in assignment for c in cells)
            if kind == 'EXACTLY':
                return lower <= value <= upper, lower == upper == value
            if kind == 'AT_LEAST':
                return upper >= value, lower >= value
            return lower <= value, upper <= value

        if any(not bounds(c, base)[0] for c in constraints):
            return Inference({}, 0)
        # Satisfied constraints impose no more dependencies. Disconnected groups
        # factor exactly: count their models separately, multiply their counts.
        active = [c for c in constraints if not bounds(c, base)[1]]
        parent = {c:c for c in unresolved}
        def root(c):
            while parent[c] != c:
                parent[c] = parent[parent[c]]
                c = parent[c]
            return c
        for _, cells, _ in active:
            variables = [c for c in cells if c in parent]
            for c in variables[1:]:
                parent[root(c)] = root(variables[0])
        groups = {}
        for c in unresolved:
            groups.setdefault(root(c), []).append(c)

        def solve(variables, rules, assignment):
            assignment = dict(assignment)
            while True:
                if any(not bounds(c, assignment)[0] for c in rules):
                    return 0, set(), set()
                pending = [c for c in variables if c not in assignment]
                # Free remaining variables contribute 2^n models without enumeration.
                if all(bounds(c, assignment)[1] for c in rules):
                    yes = {c for c in variables if assignment.get(c, True)}
                    no = {c for c in variables if not assignment.get(c, False)}
                    return 1 << len(pending), yes, no
                domains = {}
                changed = False
                for cell in pending:
                    incident = [c for c in rules if cell in c[1]]
                    allowed = [v for v in (False, True) if all(
                        bounds(c, assignment | {cell:v})[0] for c in incident)]
                    if not allowed:
                        return 0, set(), set()
                    if len(allowed) == 1:
                        assignment[cell] = allowed[0]
                        changed = True
                    domains[cell] = allowed
                if not changed:
                    break
            # Deterministic constrained-variable choice; only explore feasible branches.
            cell = max(pending, key=lambda v: sum(v in c[1] for c in rules))
            count, yes, no = 0, set(), set()
            for value in domains[cell]:
                n, y, f = solve(variables, rules, assignment | {cell:value})
                count += n
                yes.update(y)
                no.update(f)
            return count, yes, no

        counts, seen_true, seen_false = [], set(), set()
        for variables in groups.values():
            variables_set = set(variables)
            rules = [c for c in active if variables_set.intersection(c[1])]
            count, yes, no = solve(variables, rules, base)
            if not count:
                return Inference({}, 0)
            counts.append(count)
            seen_true.update(yes)
            seen_false.update(no)
        count = prod(counts)
        statuses = {c: (UNKNOWN if c in seen_true and c in seen_false else
                        CRIMINAL if c in seen_true else INNOCENT) for c in unresolved}
        return Inference(statuses if count else {}, count)


def proof_support(agent, state, target, verdict):
    """Deletion-minimal set of opened clues sufficient for an actual deduction."""
    clues = list(state['clues'])
    for clue in list(clues):
        trial = [c for c in clues if c['id'] != clue['id']]
        result = agent.classify(state | {'clues': trial})
        if result.model_count and result.statuses.get(target) == verdict:
            clues = trial
    return clues
