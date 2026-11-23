"""5x5 proof, performance and equivalence against the direct semantic oracle."""
import json
from itertools import product
from pathlib import Path
from random import Random
from time import perf_counter
from app import create_app
from game.engine import GameEngine
from game.logic import ExhaustiveAgent, CRIMINAL, INNOCENT, UNKNOWN, evaluate
from game.puzzles import PUZZLES


def brute_force(state):
    unresolved = [c['id'] for c in state['layout'] if c['id'] not in state['known']]
    base = {c:s == CRIMINAL for c,s in state['known'].items()}
    models = []
    for bits in product((False,True),repeat=len(unresolved)):
        model = base | dict(zip(unresolved,bits))
        if all(evaluate(c,model,state['layout']) for c in state['clues']):
            models.append(model)
    statuses = {c:CRIMINAL if all(m[c] for m in models) else
                INNOCENT if all(not m[c] for m in models) else UNKNOWN for c in unresolved} if models else {}
    return len(models), statuses


def test_pruned_solver_matches_exhaustive_semantics():
    rng = Random(504)
    layout = PUZZLES['village-3']['layout'][:6]
    ids = [c['id'] for c in layout]
    agent = ExhaustiveAgent()
    for _ in range(120):
        clues = []
        for _ in range(rng.randrange(8)):
            kind = rng.choice(['FACT','SAME','DIFFERENT','EXACTLY','AT_LEAST','AT_MOST'])
            cells = rng.sample(ids, 1 if kind == 'FACT' else 2 if kind in ('SAME','DIFFERENT') else rng.randrange(7))
            clues.append(dict(type=kind,cells=cells,k=rng.randrange(len(cells)+1),status=rng.choice([CRIMINAL,INNOCENT])))
        known = {c:rng.choice([CRIMINAL,INNOCENT]) for c in rng.sample(ids,rng.randrange(4))}
        state = dict(layout=layout,known=known,clues=clues)
        count,statuses = brute_force(state)
        result = agent.classify(state)
        assert (result.model_count,result.statuses) == (count,statuses)


def test_free_25_variables_are_counted_without_enumeration():
    state = dict(layout=PUZZLES['village-5']['layout'],known={},clues=[])
    start = perf_counter()
    result = ExhaustiveAgent().classify(state)
    assert result.model_count == 2**25
    assert set(result.statuses.values()) == {UNKNOWN}
    assert perf_counter()-start < 1


def test_red_moon_two_clue_proof_at_actual_turn():
    g = GameEngine('village-5')
    before = g.view()
    assert g.verdict('C1',CRIMINAL)['code'] == 'NOT_PROVABLE'
    assert g.verdict('B1',CRIMINAL)['code'] == 'CONTRADICTED'
    assert g.view() == before
    assert g.verdict('B1',INNOCENT)['code'] == 'ACCEPTED'
    assert g.verdict('B2',INNOCENT)['code'] == 'ACCEPTED'
    state = g.knowledge()
    assert g.agent.classify(state).statuses['C3'] == INNOCENT
    for removed in ('clue-A2','clue-B1'):
        trial = state | {'clues':[c for c in state['clues'] if c['id'] != removed]}
        assert g.agent.classify(trial).statuses['C3'] == UNKNOWN
    assert g.hint()['clue_ids'] == []
    assert set(g.hint()['clue_ids']) == {'clue-A2','clue-B1'}


def test_mist_wharf_has_its_own_two_clue_proof():
    g = GameEngine('village-5-mist')
    initial = g.view()
    assert initial['title'] == 'Bến sương mù'
    assert set(initial['known']) == {'A1','E1'}
    assert g.puzzle['solution'] != PUZZLES['village-5']['solution']
    assert g.verdict('B1',CRIMINAL)['code'] == 'NOT_PROVABLE'
    assert g.verdict('A2',CRIMINAL)['code'] == 'CONTRADICTED'
    assert g.view() == initial
    assert g.verdict('A2',INNOCENT)['code'] == 'ACCEPTED'
    state = g.knowledge()
    assert g.agent.classify(state).statuses['C3'] == INNOCENT
    for removed in ('clue-E1','clue-A2'):
        trial = state | {'clues':[c for c in state['clues'] if c['id'] != removed]}
        assert g.agent.classify(trial).statuses['C3'] == UNKNOWN
    g.hint()
    assert set(g.hint()['clue_ids']) == {'clue-E1','clue-A2'}


def test_red_moon_api_playthrough_privacy_and_timings():
    client = create_app().test_client()
    metrics = {}
    def call(action,body):
        start = perf_counter()
        result = client.post('/api/'+action,json=body).get_json()
        elapsed = (perf_counter()-start)*1000
        metrics.setdefault(action,[]).append(elapsed)
        view = result['state']
        assert 'solution' not in view
        assert len(view['clues']) == len(view['known'])
        assert all(c['owner'] in view['known'] for c in view['clues'])
        assert all(set(p) == {'id','row','column','name','profession'} for p in view['layout'])
        return result
    result = call('load',{'puzzle_id':'village-5'})
    initial = result['state']
    assert initial['total'] == 25 and initial['progress'] == 2
    assert len({p['name'] for p in initial['layout']}) == 25
    for cell,status,code in [('C1',CRIMINAL,'NOT_PROVABLE'),('B1',CRIMINAL,'CONTRADICTED'),('B1',INNOCENT,'ACCEPTED')]:
        assert call('verdict',dict(cell=cell,status=status))['code'] == code
    call('hint',{})
    assert call('verdict',dict(cell='B2',status=INNOCENT))['code'] == 'ACCEPTED'
    call('hint',{}); call('hint',{})
    while not result['state']['completed']:
        result = call('auto-step',{})
        assert result['code'] == 'ACCEPTED'
    assert len(result['state']['history']) == 23
    puzzle = PUZZLES['village-5']
    full = dict(layout=puzzle['layout'],known=initial['known'],clues=list(puzzle['clues'].values()))
    assert ExhaustiveAgent().classify(full).model_count == 1
    assert call('restart',{})['state'] == initial
    summary = {k:dict(calls=len(v),max_ms=round(max(v),3),mean_ms=round(sum(v)/len(v),3)) for k,v in metrics.items()}
    Path('tmp/qa').mkdir(parents=True,exist_ok=True)
    Path('tmp/qa/gridwolf-5x5-timings.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    assert all(max(v) < 2000 for v in metrics.values()), summary
