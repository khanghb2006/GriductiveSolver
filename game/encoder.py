"""Encode structured public clues as CNF with signed DIMACS literals."""

from collections.abc import Mapping
from itertools import combinations
from math import isqrt
from typing import NamedTuple

from .logic import (
    checked_count,
    checked_parity,
    checked_role,
    comparison,
    referenced_cells,
)


class KB(NamedTuple):
    clauses: list[list[int]]
    n_primary: int
    n_aux: int

    @property
    def n_clauses(self):
        return len(self.clauses)


def _layout(n):
    if type(n) is not int or not 1 <= n <= 26:
        raise ValueError('N must be an integer from 1 to 26')
    return [dict(id=f'{chr(64 + col)}{row}', row=row, column=col)
            for row in range(1, n + 1) for col in range(1, n + 1)]


def variable_map(n):
    """Return the row-major map, starting with A1 = 1."""
    return {cell['id']: var for var, cell in enumerate(_layout(n), start=1)}


def _negate(literal):
    return not literal if type(literal) is bool else -literal


class _Encoder:
    def __init__(self, n):
        self.layout = _layout(n)
        self.variables = {cell['id']: var for var, cell in enumerate(self.layout, start=1)}
        self.last_var = len(self.variables)
        self.clauses = []

    def result(self):
        n_primary = len(self.variables)
        return KB(self.clauses, n_primary, self.last_var - n_primary)

    def variable(self, cell):
        if not isinstance(cell, str) or cell not in self.variables:
            raise ValueError(f'Invalid cell: {cell!r}')
        return self.variables[cell]

    def new_aux(self):
        self.last_var += 1
        return self.last_var

    def clause(self, *literals):
        """Fold constants from gate boundary conditions before writing DIMACS."""
        if not any(literal is True for literal in literals):
            self.clauses.append([literal for literal in literals if literal is not False])

    def parity(self, variables, odd):
        # Accumulate XOR using a fresh output for each pair.
        value = False
        for var in variables:
            if value is False:
                value = var
                continue
            output = self.new_aux()
            self.clauses.extend([
                [-value, -var, -output], [value, var, -output],
                [-value, var, output], [value, -var, output],
            ])
            value = output
        self.clause(value if odd else _negate(value))

    def thresholds(self, literals):
        """Return literals for count >= k, including the true threshold k=0."""
        previous = [True]
        for literal in literals:
            current = [True]
            for k in range(1, len(previous) + 1):
                already = previous[k] if k < len(previous) else False
                lower = previous[k - 1]
                if already is False and lower is True:
                    current.append(literal)
                    continue
                output = self.new_aux()
                # output <=> already OR (literal AND lower)
                self.clause(_negate(already), output)
                self.clause(-literal, _negate(lower), output)
                self.clause(-output, already, literal)
                self.clause(-output, already, lower)
                current.append(output)
            previous = current
        return previous

    def compare(self, clue):
        (left, left_role), (right, right_role), op = comparison(clue, self.layout)
        a = self.thresholds([self.variable(cell) * (1 if left_role else -1) for cell in left])
        b = self.thresholds([self.variable(cell) * (1 if right_role else -1) for cell in right])
        if op == 'EQ':
            size = max(len(a), len(b))
            a += [False] * (size - len(a))
            b += [False] * (size - len(b))
            for a_k, b_k in zip(a[1:], b[1:]):
                self.clause(_negate(a_k), b_k)
                self.clause(a_k, _negate(b_k))
        else:
            if op == 'LT':
                a, b = b, a
            for k, b_k in enumerate(b):
                a_next = a[k + 1] if k + 1 < len(a) else False
                self.clause(_negate(b_k), a_next)

    def encode(self, clue):
        if not isinstance(clue, Mapping):
            raise ValueError('A clue must be a mapping')
        kind = clue.get('type')
        if kind == 'COMPARE':
            self.compare(clue)
            return
        if kind not in ('FACT', 'SAME', 'DIFFERENT', 'EXACTLY', 'AT_LEAST', 'AT_MOST',
                        'PARITY', 'CONTIGUOUS'):
            raise ValueError(f'Unknown clue type: {kind!r}')

        variables = [self.variable(cell) for cell in referenced_cells(clue, self.layout)]
        if kind == 'FACT':
            var = variables[0]
            self.clause(var if checked_role(clue.get('status')) else -var)
        elif kind in ('SAME', 'DIFFERENT'):
            a, b = variables
            if kind == 'DIFFERENT':
                b = -b
            self.clauses.extend([[-a, b], [a, -b]])
        elif kind == 'PARITY':
            self.parity(variables, checked_parity(clue))
        elif kind == 'CONTIGUOUS':
            sign = 1 if checked_role(clue.get('status')) else -1
            self.clauses.extend([[-a, b, -c] for a, b, c in
                                 combinations([sign * var for var in variables], 3)])
        else:
            size = len(variables)
            k = checked_count(clue, size)
            if kind in ('EXACTLY', 'AT_MOST'):
                self.clauses.extend([-var for var in group] for group in combinations(variables, k + 1))
            if kind in ('EXACTLY', 'AT_LEAST'):
                self.clauses.extend(list(group) for group in combinations(variables, size - k + 1))


def encode_clue(clue, n):
    """Return a KB for one clue, with its auxiliary and clause counts."""
    encoder = _Encoder(n)
    encoder.encode(clue)
    return encoder.result()


def build_kb(public_state):
    """Build a KB from the assignment schema or GameEngine.knowledge().

    The engine supplies a row-major layout. Only the board coordinates, proved
    verdicts and revealed clues participate in encoding.
    """
    if 'N' in public_state:
        encoder = _Encoder(public_state['N'])
        known = public_state.get('proved')
        clues = public_state.get('revealed_clues')
    else:
        layout = public_state.get('layout')
        if not isinstance(layout, (list, tuple)):
            raise ValueError('A public state must include N or a square row-major layout')
        encoder = _Encoder(isqrt(len(layout)))
        if not all(isinstance(cell, Mapping) for cell in layout) or [
            cell.get('id') for cell in layout
        ] != list(encoder.variables):
            raise ValueError('Public layout must contain all cell IDs in row-major order')
        known = public_state.get('known')
        clues = public_state.get('clues')
    if not isinstance(known, Mapping) or not isinstance(clues, (list, tuple)):
        raise ValueError('A public state must include proved verdicts and revealed clues')
    for cell, status in known.items():
        var = encoder.variable(cell)
        encoder.clause(var if checked_role(status) else -var)
    for clue in clues:
        encoder.encode(clue)
    return encoder.result()
