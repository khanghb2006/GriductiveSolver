from copy import deepcopy
from itertools import product
import pytest
from app import create_app
from game.engine import GameEngine
from game.logic import (CRIMINAL, INNOCENT, UNKNOWN, ExhaustiveAgent, evaluate,
                        region_cells, proof_support, referenced_cells)
from game.puzzles import PUZZLES, compare, contiguous


def test_three_verdict_results_and_two_clue_necessity():
    g = GameEngine()
    before = g.view()
    # B1 is criminal in the secret answer, but remains ambiguous at this turn.
    assert g.verdict('B1',CRIMINAL)['code'] == 'NOT_PROVABLE'
    assert g.view() == before
    assert g.verdict('C1',CRIMINAL)['code'] == 'CONTRADICTED'
    assert g.view() == before
    assert g.verdict('C1',INNOCENT)['code']=='ACCEPTED'
    assert g.verdict('C2',INNOCENT)['code']=='ACCEPTED'
    state = g.knowledge()
    assert g.agent.classify(state).statuses['C3'] == INNOCENT
    for removed in [c for c in state['clues'] if c['id'] in ('clue-A2','clue-C2')]:
        trial = state | {'clues':[c for c in state['clues'] if c != removed]}
        assert g.agent.classify(trial).statuses['C3'] == UNKNOWN
    assert g.verdict('C3',INNOCENT)['code'] == 'ACCEPTED'
    assert len(g.view()['clues']) == 5


@pytest.mark.parametrize('puzzle_id',PUZZLES)
def test_manual_auto_and_uniqueness(puzzle_id):
    g = GameEngine(puzzle_id)
    initial = g.view()
    trace = []
    while not g.view()['completed']:
        state = g.knowledge()
        result = g.agent.classify(state)
        cell, status = next((c,s) for c,s in result.statuses.items() if s != UNKNOWN)
        assert g.verdict(cell,status)['code'] == 'ACCEPTED'
        trace.append(cell)
    assert len(trace) == g.view()['total']-2
    all_clues = g.knowledge()
    # Initial revealed statuses are part of the complete puzzle constraints.
    assert g.agent.classify(all_clues | {'known':initial['known']}).model_count == 1
    g.load(puzzle_id)
    assert g.view() == initial
    for cell in trace:
        assert g.auto_step()['code'] == 'ACCEPTED'
        assert g.history[-1]['cell'] == cell
    assert g.auto_step()['code'] == 'COMPLETE'


def test_hints_are_verified_and_reset():
    g = GameEngine()
    before = g.view()
    assert g.hint()['clue_ids'] == []
    hint = g.hint()
    assert set(hint['clue_ids']) == {'clue-A1'}
    assert 'C1' not in hint['message'] and CRIMINAL not in hint['message']
    assert g.view() == before
    g.verdict('C1',INNOCENT)
    assert g.hint()['level'] == 1
    while not g.view()['completed']:
        state = g.knowledge()
        result = g.agent.classify(state)
        cell,status = next((c,s) for c,s in result.statuses.items() if s != UNKNOWN)
        support = proof_support(g.agent,state,cell,status)
        assert g.agent.classify(state | {'clues':support}).statuses[cell] == status
        g.verdict(cell,status)


def test_inconsistent_and_mismatched_data_do_not_mutate():
    g = GameEngine()
    g.puzzle['clues']['A1'] = deepcopy(g.puzzle['clues']['A2'])
    g.puzzle['clues']['A1'].update(id='clue-A1',owner='A1',k=0)
    g.puzzle['clues']['A2']['k'] = 2
    before = g.view()
    assert g.verdict('B2',INNOCENT)['code'] == 'DATA_ERROR'
    assert g.auto_step()['code'] == 'DATA_ERROR'
    assert g.view() == before
    g = GameEngine()
    g.puzzle['solution']['B2'] = True
    before = g.view()
    assert g.verdict('B2',INNOCENT)['code'] == 'DATA_ERROR'
    assert g.view() == before


def test_unknown_auto_stops():
    g = GameEngine()
    g.puzzle['clues']['A1'] = deepcopy(g.puzzle['clues']['A2'])
    assert g.auto_step()['code'] == 'STUCK'


@pytest.mark.parametrize('kind',['FACT','SAME','DIFFERENT','EXACTLY','AT_LEAST','AT_MOST'])
def test_semantics_exhaustive(kind):
    layout = PUZZLES['village-3']['layout']
    cells = ['A1','B1']
    clue = dict(type=kind,cells=cells,status=CRIMINAL,k=1)
    for a,b in product((False,True),repeat=2):
        expected = {'FACT':a,'SAME':a==b,'DIFFERENT':a!=b,
                    'EXACTLY':a+b==1,'AT_LEAST':a+b>=1,'AT_MOST':a+b<=1}[kind]
        assert evaluate(clue,dict(zip(cells,[a,b])),layout) == expected


def test_regions():
    layout = PUZZLES['village-3']['layout']
    assert region_cells({'kind':'ROW','row':2},layout) == ['A2','B2','C2']
    assert region_cells({'kind':'COLUMN','column':2},layout) == ['B1','B2','B3']
    assert len(region_cells({'kind':'NEIGHBORS','cell':'B2'},layout)) == 8
    assert region_cells({'kind':'NEIGHBORS','cell':'A1'},layout) == ['B1','A2','B2']
    for kind,region in [('EXACTLY',{'kind':'ROW','row':1}),('AT_LEAST',{'kind':'COLUMN','column':2}),
                        ('AT_MOST',{'kind':'NEIGHBORS','cell':'A1'})]:
        assignment = {c['id']:False for c in layout}
        assert evaluate(dict(type=kind,region=region,k=0),assignment,layout)


def test_api_privacy_sessions_and_controls():
    app = create_app()
    a,b = app.test_client(),app.test_client()
    initial = a.get('/api/state').get_json()
    def privacy(view):
        assert 'solution' not in view and 'initial' not in view
        assert len(view['clues']) == len(view['known'])
        assert all(c['owner'] in view['known'] for c in view['clues'])
        for person in view['layout']:
            assert set(person) == {'id','row','column','name','profession'}
    privacy(initial)
    for status,code in [(CRIMINAL,'NOT_PROVABLE')]:
        response = a.post('/api/verdict',json=dict(cell='B1',status=status)).get_json()
        assert response['code'] == code and response['state'] == initial
    response = a.post('/api/verdict',json=dict(cell='C1',status=INNOCENT)).get_json()
    assert response['code']=='ACCEPTED'
    privacy(response['state'])
    assert b.get('/api/state').get_json() == initial
    assert a.post('/api/restart',json={}).get_json()['state'] == initial
    response = a.post('/api/load',json={'puzzle_id':'village-4'}).get_json()
    assert response['state']['total'] == 16 and response['state']['progress'] == 2
    privacy(response['state'])
    assert a.get('/game/puzzles.py').status_code == 404
    assert a.get('/static/../game/puzzles.py').status_code == 404
    assert a.post('/api/verdict',json={'cell':[],'status':{}}).status_code == 400
    assert a.post('/api/load',json={'puzzle_id':[]}).status_code == 400
    assert a.get('/').status_code == 200


@pytest.mark.parametrize('left_role,right_role', list(product((CRIMINAL, INNOCENT), repeat=2)))
def test_compare_truth_table_with_overlap_and_excluded_centers(left_role, right_role):
    layout = PUZZLES['village-3']['layout']
    ids = [p['id'] for p in layout]
    clue = compare('A1', left_role, 'B2', right_role)
    left_neighbors = ['B1', 'A2', 'B2']
    right_neighbors = [c for c in ids if c != 'B2']
    assert set(referenced_cells(clue, layout)) == set(left_neighbors + right_neighbors)
    for bits in product((False, True), repeat=9):
        assignment = dict(zip(ids, bits))
        left = sum(assignment[c] == (left_role == CRIMINAL) for c in left_neighbors)
        right = sum(assignment[c] == (right_role == CRIMINAL) for c in right_neighbors)
        assert evaluate(clue, assignment, layout) == (left == right)


@pytest.mark.parametrize('role', [CRIMINAL, INNOCENT])
def test_contiguous_all_row_patterns_including_empty_singleton_and_gap(role):
    layout = PUZZLES['village-4']['layout']
    clue = contiguous(2, role)
    cells = ['A2', 'B2', 'C2', 'D2']
    assert referenced_cells(clue, list(reversed(layout))) == cells
    for bits in product((False, True), repeat=4):
        assignment = {p['id']:False for p in layout} | dict(zip(cells, bits))
        target = [bit == (role == CRIMINAL) for bit in bits]
        # A separated target/opposite/target triple violates a single block.
        gap = any(target[i] and not target[j] and target[k]
                  for i in range(4) for j in range(i+1,4) for k in range(j+1,4))
        assert evaluate(clue, assignment, layout) == (not gap)


@pytest.mark.parametrize('clue', [compare('Z9',CRIMINAL,'A1',INNOCENT),
                                 compare('A1','WOLF','B1',INNOCENT),
                                 contiguous(99,CRIMINAL), contiguous(True,CRIMINAL),
                                 contiguous(1,'VILLAGER')])
def test_invalid_extension_parameters_are_rejected(clue):
    layout = PUZZLES['village-3']['layout']
    assignment = {p['id']:False for p in layout}
    with pytest.raises(ValueError):
        evaluate(clue, assignment, layout)
    with pytest.raises(ValueError):
        ExhaustiveAgent().classify(dict(layout=layout, known={}, clues=[clue]))


@pytest.mark.parametrize('pid', ['village-3-links', 'village-4-links'])
def test_extensions_api_text_highlight_hints_verdicts_and_auto_solve(pid):
    client = create_app().test_client()
    response = client.post('/api/load',json={'puzzle_id':pid}).get_json()
    state = response['state']
    assert len(state['clues']) == 2
    assert 'solution' not in state
    assert 'xung quanh' in state['clues'][0]['text']
    assert 'nằm liền nhau' in state['clues'][1]['text']
    for clue in state['clues']:
        assert set(clue['cells']) == set(referenced_cells(clue, state['layout']))
    assert client.post('/api/hint',json={}).get_json()['state'] == state
    assert client.post('/api/hint',json={}).get_json()['clue_ids']
    steps = 0
    while not state['completed']:
        result = client.post('/api/auto-step',json={}).get_json()
        assert result['code'] == 'ACCEPTED'
        state = result['state']
        assert len(state['clues']) == len(state['known'])
        assert all(c['owner'] in state['known'] for c in state['clues'])
        assert 'solution' not in state
        steps += 1
        assert steps <= state['total'] - 2
    assert steps == state['total'] - 2
