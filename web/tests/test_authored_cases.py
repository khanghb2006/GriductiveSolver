"""4.1 data validation using the already integrated agent, not a new solver."""
import pytest
from game.engine import GameEngine
from game.logic import UNKNOWN,CRIMINAL,INNOCENT,Inference
from game.puzzles import PUZZLES,DEMO_PROOFS
from app import create_app


@pytest.mark.parametrize('pid',PUZZLES)
def test_planned_combination_has_no_single_clue_shortcut(pid):
    g=GameEngine(pid)
    proof=DEMO_PROOFS[pid]
    for cell,status in proof['prefix']:
        assert g.verdict(cell,status)['code']=='ACCEPTED'
    state=g.knowledge()
    assert g.agent.classify(state).statuses[proof['target']]==proof['status']
    for clue in state['clues']:
        result=g.agent.classify(state|{'clues':[clue]})
        assert result.statuses[proof['target']]==UNKNOWN
    for cid in proof['clue_ids']:
        result=g.agent.classify(state|{'clues':[c for c in state['clues'] if c['id']!=cid]})
        assert result.statuses[proof['target']]==UNKNOWN
    g.hint()
    assert set(g.hint()['clue_ids'])==set(proof['clue_ids'])


@pytest.mark.parametrize('pid',['village-4','village-5','village-5-mist'])
def test_larger_cases_really_use_public_regional_counts(pid):
    clues=list(PUZZLES[pid]['clues'].values())
    assert sum(c['type']=='FACT' for c in clues)<=1
    regions={c['region']['kind'] for c in clues if 'region' in c}
    assert {'ROW','COLUMN','NEIGHBORS','LIST'}<=regions


def test_team_agent_factory_receives_only_public_input_for_all_hooks():
    seen=[]
    class TeamAdapter:
        def classify(self,public_state):
            assert set(public_state)=={'layout','known','clues'}
            assert all(c['owner'] in public_state['known'] for c in public_state['clues'])
            assert all('status' not in p and 'clue' not in p for p in public_state['layout'])
            seen.append(public_state)
            # A no-deduction stub is used only in this integration test.
            return Inference({p['id']:UNKNOWN for p in public_state['layout'] if p['id'] not in public_state['known']},1)
    app=create_app(agent_factory=TeamAdapter)
    client=app.test_client()
    initial=client.get('/api/state').get_json()
    assert client.post('/api/verdict',json={'cell':'C1','status':INNOCENT}).get_json()['code']=='NOT_PROVABLE'
    assert client.post('/api/hint',json={}).get_json()['code']=='NO_HINT'
    assert client.post('/api/auto-step',json={}).get_json()['code']=='STUCK'
    assert client.get('/api/state').get_json()==initial
    assert len(seen)==3
