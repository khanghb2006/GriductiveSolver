from itertools import product

import pytest

from game.encoder import build_kb, encode_clue, variable_map
from game.engine import GameEngine
from game.logic import CRIMINAL, INNOCENT, evaluate
from game.stub_sat import solve
from main import make_agent


LAYOUT = GameEngine().knowledge()['layout']
CELLS = dict(kind='CELLS', cells=['A1', 'B1', 'B2'])
ROW = dict(kind='ROW', row=1)
COL = dict(kind='COL', col='B')
EMPTY = dict(kind='LIST', cells=[])


@pytest.mark.parametrize('clue', [
    dict(type='FACT', cell='B2', status=CRIMINAL),
    dict(type='FACT', cells=['A1'], status=INNOCENT),
    dict(type='SAME', cells=['A1', 'B2']),
    dict(type='DIFFERENT', cells=['A1', 'B2']),
    dict(type='DIFFERENT', cells=['A1', 'A1']),
    dict(type='PARITY', region=EMPTY, parity='EVEN'),
    dict(type='PARITY', region=EMPTY, parity='ODD'),
    dict(type='PARITY', region=dict(kind='NEIGHBORS', cell='A1'), parity='EVEN'),
    dict(type='PARITY', region=dict(kind='COLUMN', column=3), parity='ODD'),
    dict(type='CONTIGUOUS', region=ROW, status=CRIMINAL),
    dict(type='CONTIGUOUS', region=ROW, status=INNOCENT),
    dict(type='COMPARE', left=dict(cell='A1', status=CRIMINAL),
         right=dict(cell='C1', status=INNOCENT)),
] + [
    dict(type=kind, k=k, region=CELLS)
    for kind in ('EXACTLY', 'AT_LEAST', 'AT_MOST') for k in range(4)
] + [
    dict(type=kind, k=0, region=EMPTY)
    for kind in ('EXACTLY', 'AT_LEAST', 'AT_MOST')
] + [
    dict(type='COMPARE', left=left, op=op, right=right)
    for left, right in ((ROW, COL), (COL, EMPTY), (EMPTY, ROW), (ROW, ROW))
    for op in ('GT', 'EQ', 'LT')
])
def test_cnf_projection_matches_semantic_evaluator(clue):
    kb = encode_clue(clue, 3)
    variables = variable_map(3)
    for bits in product((False, True), repeat=len(variables)):
        assignment = dict(zip(variables, bits))
        assumptions = [var if assignment[cell] else -var for cell, var in variables.items()]
        assert solve(kb.clauses, kb.n_primary + kb.n_aux, assumptions).sat == evaluate(
            clue, assignment, LAYOUT
        )


@pytest.mark.parametrize('clue', [
    dict(type='FACT', cell='D1', status=CRIMINAL),
    dict(type='FACT', cells=['A1', 'A2'], status=CRIMINAL),
    dict(type='FACT', cell='A1', status='UNKNOWN'),
    dict(type='SAME', cells=['A1']),
    dict(type='DIFFERENT', cells=['A1', 'A2', 'A3']),
    dict(type='EXACTLY', k=True, region=ROW),
    dict(type='EXACTLY', k=-1, region=ROW),
    dict(type='AT_LEAST', k=4, region=ROW),
    dict(type='AT_MOST', k=0, region=dict(kind='ROW', row=4)),
    dict(type='AT_MOST', k=0, region=dict(kind='COLUMN', column='D')),
    dict(type='AT_MOST', k=0, region=dict(kind='NEIGHBORS', cell='D1')),
    dict(type='AT_MOST', k=1, region=dict(kind='LIST', cells=['A1', 'A1'])),
    dict(type='AT_MOST', k=1, region=dict(kind='LIST', cells=[['A1']])),
    dict(type='AT_MOST', k=0, region=dict(kind='BORDER')),
    dict(type='PARITY', region=ROW, parity='NEITHER'),
    dict(type='COMPARE', left=ROW, right=COL),
    dict(type='COMPARE', left=ROW, op='NE', right=COL),
    dict(type='COMPARE', left=ROW, op='EQ', right=None),
    dict(type='CONTIGUOUS', region=COL, status=CRIMINAL),
    dict(type='UNSUPPORTED'),
])
def test_rejects_malformed_clue(clue):
    with pytest.raises(ValueError):
        encode_clue(clue, 3)


def test_row_major_variables_unit_verdicts_and_public_only():
    assert list(variable_map(3).items()) == list(zip(
        ['A1', 'B1', 'C1', 'A2', 'B2', 'C2', 'A3', 'B3', 'C3'], range(1, 10)
    ))
    clues = [dict(type='DIFFERENT', cells=['A1', 'B2'])]
    state = dict(layout=LAYOUT, known={'A1': INNOCENT}, clues=clues)
    kb = build_kb(state | {'solution': {'A1': True}, 'unrevealed_clues': [None]})
    assert kb == build_kb(dict(N=3, proved=state['known'], revealed_clues=clues))
    assert kb == ([[-1], [-1, -5], [1, 5]], 9, 0)
    assert kb.n_clauses == 3
    assert make_agent().classify(state).statuses['B2'] == CRIMINAL


def test_auxiliary_variables_are_disjoint_across_clues():
    even = dict(type='PARITY', region=ROW, parity='EVEN')
    odd = dict(type='PARITY', region=COL, parity='ODD')
    each = [encode_clue(clue, 3) for clue in (even, odd)]
    kb = build_kb(dict(N=3, proved={}, revealed_clues=[even, odd]))
    first_size = each[0].n_clauses
    first_vars = {abs(lit) for clause in kb.clauses[:first_size] for lit in clause if abs(lit) > 9}
    last_vars = {abs(lit) for clause in kb.clauses[first_size:] for lit in clause if abs(lit) > 9}
    assert first_vars == {10, 11}
    assert last_vars == {12, 13}
    assert kb.n_aux == sum(item.n_aux for item in each)
    assumptions = [1, -2, 3, -5, 8]
    assert solve(kb.clauses, kb.n_primary + kb.n_aux, assumptions).sat


def test_compare_handles_full_board_without_enumerating_assignments():
    board = dict(kind='CELLS', cells=list(variable_map(5)))
    kb = encode_clue(dict(type='COMPARE', left=board, op='GT', right=EMPTY), 5)
    assert kb.n_primary == 25
    assert kb.n_aux == sum(range(2, 26))
    assert kb.n_clauses < 1300
    all_innocent = [-var for var in range(1, 26)]
    assert not solve(kb.clauses, kb.n_primary + kb.n_aux, all_innocent).sat
    assert solve(kb.clauses, kb.n_primary + kb.n_aux, [1, *all_innocent[1:]]).sat
