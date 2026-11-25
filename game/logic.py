"""Public-only semantic oracle. Replace ExhaustiveAgent with the team's SAT agent."""
from collections.abc import Mapping
from dataclasses import dataclass
from math import prod
from typing import Protocol

CRIMINAL, INNOCENT, UNKNOWN = 'CRIMINAL', 'INNOCENT', 'UNKNOWN'


def region_cells(region, layout):
    if not isinstance(region, Mapping):
        raise ValueError('A region must be a mapping')
    kind = region.get('kind')
    if kind in ('LIST', 'CELLS'):
        return checked_cells(region.get('cells'), layout)
    if kind == 'ROW':
        row = region.get('row')
        cells = [c['id'] for c in layout if type(row) is int and c['row'] == row]
    elif kind in ('COLUMN', 'COL'):
        column = region.get('column', region.get('col'))
        if isinstance(column, str) and len(column) == 1 and 'A' <= column <= 'Z':
            column = ord(column) - ord('A') + 1
        cells = [c['id'] for c in layout if type(column) is int and c['column'] == column]
    elif kind == 'NEIGHBORS':
        center = next((c for c in layout if c['id'] == region.get('cell')), None)
        if center is None:
            raise ValueError('Invalid neighbor center')
        return [c['id'] for c in layout if
                max(abs(c['row'] - center['row']), abs(c['column'] - center['column'])) == 1]
    else:
        raise ValueError(f'Unknown region kind: {kind!r}')
    if not cells:
        raise ValueError(f'Invalid {kind} coordinate')
    return cells


def checked_cells(cells, layout, *, distinct=True):
    ids = {c['id'] for c in layout}
    if not isinstance(cells, (list, tuple)) or any(
        not isinstance(cell, str) or cell not in ids for cell in cells
    ):
        raise ValueError('Invalid cell references')
    if distinct and len(set(cells)) != len(cells):
        raise ValueError('Duplicate cells in explicit region')
    return list(cells)


def checked_role(status):
    if status not in (CRIMINAL, INNOCENT):
        raise ValueError(f'Invalid status: {status!r}')
    return status == CRIMINAL


def comparison(clue, layout):
    """Resolve both count operands and the comparison operator."""
    sides = []
    default_op = 'EQ'
    for key in ('left', 'right'):
        side = clue.get(key)
        if not isinstance(side, Mapping):
            raise ValueError(f'Invalid comparison operand: {key}')
        # The web branch explicitly supplies a center and the role to count.
        if 'kind' in side:
            sides.append((region_cells(side, layout), True))
            default_op = None
        else:
            region = dict(kind='NEIGHBORS', cell=side.get('cell'))
            sides.append((region_cells(region, layout), checked_role(side.get('status'))))
    op = clue.get('op', default_op)
    if op not in ('GT', 'EQ', 'LT'):
        raise ValueError(f'Invalid comparison operator: {op!r}')
    return sides[0], sides[1], op


def referenced_cells(clue, layout):
    kind = clue.get('type')
    if kind == 'COMPARE':
        left, right, _ = comparison(clue, layout)
        return list(dict.fromkeys(left[0] + right[0]))
    if kind in ('FACT', 'SAME', 'DIFFERENT'):
        cells = [clue['cell']] if kind == 'FACT' and 'cell' in clue else clue.get('cells')
        cells = checked_cells(cells, layout, distinct=False)
        expected = 1 if kind == 'FACT' else 2
        if len(cells) != expected:
            raise ValueError(f'{kind} requires {expected} cell(s)')
        return cells
    if kind == 'CONTIGUOUS':
        region = clue.get('region')
        if not isinstance(region, Mapping) or region.get('kind') != 'ROW':
            raise ValueError('CONTIGUOUS requires a row')
        return region_cells(region, sorted(layout, key=lambda cell: cell['column']))
    return (region_cells(clue['region'], layout) if 'region' in clue
            else checked_cells(clue.get('cells'), layout))


def checked_count(clue, region_size):
    k = clue.get('k')
    if type(k) is not int or not 0 <= k <= region_size:
        raise ValueError('Invalid count')
    return k


def checked_parity(clue):
    parity = clue.get('parity')
    if parity not in ('EVEN', 'ODD'):
        raise ValueError(f'Invalid parity: {parity!r}')
    return parity == 'ODD'


def evaluate(clue, assignment, layout):
    kind = clue.get('type')
    if kind == 'COMPARE':
        (left, left_role), (right, right_role), op = comparison(clue, layout)
        a = sum(assignment[c] == left_role for c in left)
        b = sum(assignment[c] == right_role for c in right)
        return {'GT': a > b, 'EQ': a == b, 'LT': a < b}[op]

    cells = referenced_cells(clue, layout)
    values = [assignment[c] for c in cells]
    if kind == 'FACT':
        return values[0] == checked_role(clue.get('status'))
    if kind == 'SAME':
        return values[0] == values[1]
    if kind == 'DIFFERENT':
        return values[0] != values[1]
    if kind == 'CONTIGUOUS':
        role = checked_role(clue.get('status'))
        positions = [i for i, value in enumerate(values) if value == role]
        return not positions or positions[-1] - positions[0] + 1 == len(positions)
    count = sum(values)
    if kind == 'PARITY':
        return count % 2 == checked_parity(clue)
    if kind not in ('EXACTLY', 'AT_LEAST', 'AT_MOST'):
        raise ValueError(f'Unknown clue type: {kind!r}')
    k = checked_count(clue, len(cells))
    return {'EXACTLY': count == k, 'AT_LEAST': count >= k, 'AT_MOST': count <= k}[kind]


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
            value = None
            if kind == 'COMPARE':
                left, right, op = comparison(clue, layout)
                # Combine coefficients for each cell shared by the two counts.
                coefficients, constant = {}, 0
                for sign, (side_cells, role) in zip((1, -1), (left, right)):
                    for cell in side_cells:
                        coefficients[cell] = coefficients.get(cell, 0) + sign * (1 if role else -1)
                        if not role:
                            constant += sign
                value = ({c: k for c, k in coefficients.items() if k}, -constant, op)
            elif kind == 'CONTIGUOUS':
                target = checked_role(clue.get('status'))
                # Empty, singleton and every longer interval are valid blocks.
                value = {tuple(not target for _ in cells)}
                for start in range(len(cells)):
                    for end in range(start + 1, len(cells) + 1):
                        value.add(tuple(target if start <= i < end else not target for i in range(len(cells))))
            elif kind in ('EXACTLY','AT_LEAST','AT_MOST'):
                value = checked_count(clue, len(cells))
            elif kind == 'PARITY':
                value = checked_parity(clue)
            elif kind == 'FACT':
                value = checked_role(clue.get('status'))
            elif kind not in ('SAME', 'DIFFERENT'):
                raise ValueError('Unknown clue type')
            constraints.append((kind, cells, value))

        def bounds(constraint, assignment):
            """Return (still possible, already true for every extension)."""
            kind, cells, value = constraint
            if kind == 'COMPARE':
                coefficients, target, op = value
                known = sum(k * assignment[c] for c,k in coefficients.items() if c in assignment)
                pending = [k for c,k in coefficients.items() if c not in assignment]
                lower = known + sum(min(0,k) for k in pending)
                upper = known + sum(max(0,k) for k in pending)
                if op == 'GT':
                    return upper > target, lower > target
                if op == 'LT':
                    return lower < target, upper < target
                return lower <= target <= upper, lower == upper == target
            if kind == 'CONTIGUOUS':
                compatible = sum(all(c not in assignment or assignment[c] == bit
                                     for c,bit in zip(cells, pattern)) for pattern in value)
                free = sum(c not in assignment for c in cells)
                return compatible > 0, compatible == 1 << free
            if kind == 'FACT':
                if cells[0] not in assignment:
                    return True, False
                valid = assignment[cells[0]] == value
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
            if kind == 'PARITY':
                if lower != upper:
                    return True, False
                valid = lower % 2 == value
                return valid, valid
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
