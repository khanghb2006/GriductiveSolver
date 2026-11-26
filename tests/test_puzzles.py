import pytest

from app import create_app
from game.engine import GameEngine
from game.logic import CRIMINAL, INNOCENT, UNKNOWN, ExhaustiveAgent
from game.puzzles import PUZZLES, NAMES, JOBS, case, same, fact, count, row
from main import initial_facts, make_agent
from test_gridwolf import brute_force


def ambiguous_puzzle():
    """Exactly two models, even with all clues: C4/D4 may both be either role."""
    ids=[f'{chr(65+col)}{r}' for r in range(1,5) for col in range(4)]
    labels=[False,True,False,True,True,False,True,False,
            False,True,False,True,True,False,False,False]
    initial=['A1','A2']
    route=['A1']+[c for c in ids if c not in initial+['C4','D4']]
    authored={c:same('C4','D4') for c in ids}
    # Reveal twelve forced cells; no exposed or hidden clue fixes the final pair.
    for owner,target in zip(route,route[1:]):
        authored[owner]=fact(target,CRIMINAL if labels[ids.index(target)] else INNOCENT)
    return case('test-4-ambiguous','Kiểm thử: Mơ hồ',4,NAMES,JOBS,
                labels,authored,initial)


def inconsistent_puzzle():
    """Deliberately invalid fixture: the opening claims both 2 and 1 wolves."""
    ids=[f'{chr(65+col)}{r}' for r in range(1,5) for col in range(4)]
    labels=[False,True,False,True,True,False,True,False,
            False,True,False,True,True,False,False,False]
    authored={c:count('EXACTLY',2,row(2)) for c in ids}
    puzzle=case('test-4-inconsistent','Kiểm thử: Mâu thuẫn',4,NAMES,JOBS,
                labels,authored,['A1','A2'])
    # Only this negative fixture breaks the normal truth invariant, on purpose.
    # Keep case() validation intact for all regular puzzles.
    puzzle['clues']['A2']['k']=1
    return puzzle


TEST_PUZZLES={p['id']:p for p in (ambiguous_puzzle(),inconsistent_puzzle())}


@pytest.fixture
def diagnostic_catalog(monkeypatch):
    """Register negative cases only within tests; restore the catalog afterwards."""
    for pid,puzzle in TEST_PUZZLES.items():
        monkeypatch.setitem(PUZZLES,pid,puzzle)
    return TEST_PUZZLES


@pytest.mark.parametrize('pid', PUZZLES)
def test_agent_solves_every_puzzle(pid):
    agent = make_agent()
    outcome, trace = agent.auto_solve(GameEngine(pid, agent=agent))
    assert outcome == 'COMPLETE'
    assert len(trace) == len(PUZZLES[pid]['layout']) - len(PUZZLES[pid]['initial'])


@pytest.mark.parametrize('pid', PUZZLES)
def test_every_puzzle_has_one_solution(pid):
    puzzle = PUZZLES[pid]
    clues = list(puzzle['clues'].values()) + initial_facts(puzzle)
    assert make_agent().unique_check(clues, puzzle['size']) == 'UNIQUE'


def test_forest_echo_extensions_are_needed_and_revealed_only_after_proof():
    game=GameEngine('village-5-links')
    initial=game.knowledge()
    assert game.puzzle['size'] == 5
    assert sum(c['type']=='COMPARE' for c in game.puzzle['clues'].values()) == 2
    assert sum(c['type']=='CONTIGUOUS' for c in game.puzzle['clues'].values()) == 2
    result=ExhaustiveAgent().classify(initial)
    assert result.statuses['C3'] == INNOCENT
    for clue in initial['clues']:
        assert ExhaustiveAgent().classify(initial|{'clues':[clue]}).statuses['C3'] == UNKNOWN
    complete=initial|{'clues':list(game.puzzle['clues'].values())}
    assert ExhaustiveAgent().classify(complete).model_count == 1
    client=create_app(agent_factory=make_agent).test_client()
    state=client.post('/api/load',json={'puzzle_id':'village-5-links'}).get_json()['state']
    assert len(state['layout']) == 25 and len(state['clues']) == 2
    assert {c['type'] for c in state['clues']} == {'COMPARE','CONTIGUOUS'}
    rejected=client.post('/api/verdict',json={'cell':'C3','status':CRIMINAL}).get_json()
    assert rejected['code'] == 'CONTRADICTED' and rejected['state'] == state
    result=client.post('/api/verdict',json={'cell':'C3','status':INNOCENT}).get_json()
    assert result['code'] == 'ACCEPTED'
    assert len(result['state']['clues']) == 3
    assert 'clue-C3' in {c['id'] for c in result['state']['clues']}
    assert 'solution' not in result['state']


@pytest.mark.parametrize('pid,count,verdict', [
    ('test-4-ambiguous',2,'MULTIPLE'), ('test-4-inconsistent',0,'NO_SOLUTION')])
def test_diagnostic_model_counts_include_opening_statuses(pid,count,verdict,diagnostic_catalog):
    puzzle=diagnostic_catalog[pid]
    state=GameEngine(pid).knowledge() | {'clues':list(puzzle['clues'].values())}
    # Exhaust all 16,384 assignments to the fourteen hidden cells independently.
    actual,_=brute_force(state)
    assert actual == count
    assert ExhaustiveAgent().classify(state).model_count == count
    assert make_agent().unique_check(state['clues']+initial_facts(puzzle),4) == verdict


@pytest.mark.parametrize('factory',[None,make_agent],ids=['semantic','sat'])
def test_diagnostic_api_stops_without_guessing_or_leaking(factory,diagnostic_catalog):
    client=create_app(agent_factory=factory).test_client()
    catalog=client.get('/api/puzzles').get_json()
    assert set(TEST_PUZZLES) <= {p['id'] for p in catalog}
    initial=client.post('/api/load',json={'puzzle_id':'test-4-ambiguous'}).get_json()['state']
    state=initial
    for _ in range(12):
        result=client.post('/api/auto-step',json={}).get_json()
        assert result['code'] == 'ACCEPTED'
        state=result['state']
        assert 'solution' not in state
        assert len(state['clues']) == len(state['known'])
        assert all(c['owner'] in state['known'] for c in state['clues'])
    assert len(state['known']) == 14
    assert not state['completed']
    stopped=client.post('/api/auto-step',json={}).get_json()
    assert stopped['code'] == 'STUCK' and stopped['state'] == state
    for cell in ('C4','D4'):
        for status in (CRIMINAL,INNOCENT):
            rejected=client.post('/api/verdict',json={'cell':cell,'status':status}).get_json()
            assert rejected['code'] == 'NOT_PROVABLE' and rejected['state'] == state
    assert client.post('/api/hint',json={}).get_json()['code'] == 'NO_HINT'
    assert client.post('/api/restart',json={}).get_json()['state'] == initial

    initial=client.post('/api/load',json={'puzzle_id':'test-4-inconsistent'}).get_json()['state']
    assert len(initial['known']) == len(initial['clues']) == 2
    for action,body in [('auto-step',{}),('hint',{}),
                        ('verdict',{'cell':'B1','status':CRIMINAL})]:
        rejected=client.post('/api/'+action,json=body).get_json()
        assert rejected['code'] == 'DATA_ERROR'
        assert 'mâu thuẫn' in rejected['message']
        assert rejected['state'] == initial
        assert 'solution' not in rejected['state']


def test_sat_agent_stuck_and_inconsistent_traces_for_diagnostic_cases(diagnostic_catalog):
    agent=make_agent()
    game=GameEngine('test-4-ambiguous',agent=agent)
    outcome,trace=agent.auto_solve(game)
    assert outcome == 'STUCK' and len(trace) == 12
    assert agent.classify(game.knowledge()).statuses == {'C4':UNKNOWN,'D4':UNKNOWN}
    agent=make_agent()
    game=GameEngine('test-4-inconsistent',agent=agent)
    before=game.view()
    outcome,trace=agent.auto_solve(game)
    assert outcome == 'INCONSISTENT' and trace == []
    assert game.view() == before


def test_diagnostic_cases_are_not_available_in_the_real_game():
    client=create_app().test_client()
    state=client.get('/api/state').get_json()
    catalog=client.get('/api/puzzles').get_json()
    assert {p['id'] for p in catalog} == set(PUZZLES)
    assert set(TEST_PUZZLES).isdisjoint(PUZZLES)
    for pid in TEST_PUZZLES:
        response=client.post('/api/load',json={'puzzle_id':pid})
        assert response.status_code == 400
        assert client.get('/api/state').get_json() == state
