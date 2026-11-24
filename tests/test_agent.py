from collections import namedtuple
from itertools import product

from game.agent import SatAgent

KB = namedtuple('KB', 'clauses n_primary n_aux')
Result = namedtuple('Result' , 'sat')

def build_kb(state):
     return KB([[1, 2], [-1, 2]], 2, 0)
 
def solve(clauses , n_vars , assumptions):
    for bits in product([False , True] , repeat = n_vars):
        holds = lambda l: bits[abs(l) - 1] == (l > 0)
        if all(holds(a) for a in assumptions) and all(any(holds(l) for l in c) for c in clauses):
            return Result(True)
    return Result(False)
    
def test_classify_example():
    state = dict(layout = [dict(id = 'A'), dict(id = 'B')], known = {}, clues = [])
    assert SatAgent(build_kb , solve).classify(state).statuses == {'A' : 'UNKNOWN' , 'B' : 'CRIMINAL'}
    
def test_check_verdict():
    state = dict(layout = [dict(id = 'A') , dict(id = 'B')] , known = {}, clues = [])
    agent = SatAgent(build_kb , solve)
    assert agent.check_verdict(state , 'B' , 'CRIMINAL') == 'ACCEPTED'
    assert agent.check_verdict(state , 'B' , 'INNOCENT') == 'CONTRADICTED'
    assert agent.check_verdict(state , 'A' , 'CRIMINAL') == 'NOT_PROVABLE'
    assert agent.check_verdict(state , 'A' , 'INNOCENT') == 'NOT_PROVABLE'

def kb_of(clauses, n=2):
    return lambda state: KB(clauses, n, 0)

AMBIGUOUS = kb_of([[1, 2], [-1, 2]])   # B forced CRIMINAL, A unknown
ALL_FORCED = kb_of([[1], [2]])         # A and B both forced CRIMINAL
CONTRADICTION = kb_of([[1], [-1]])


class FakeEngine:
    """Minimal engine: reveals clue 'clue-<cell>' when a cell is accepted."""
    def __init__(self):
        self.layout = [dict(id='A'), dict(id='B')]
        self.known, self.clues = {}, []

    def knowledge(self):
        return dict(layout=self.layout, known=dict(self.known), clues=list(self.clues))

    def verdict(self, cell, status):
        self.known[cell] = status
        self.clues.append(dict(id=f'clue-{cell}'))
        return dict(code='ACCEPTED')


def test_step_picks_first_forced_cell():
    found = SatAgent(ALL_FORCED, solve).step(FakeEngine().knowledge())
    assert (found['outcome'], found['cell'], found['verdict']) == ('FORCED', 'A', 'CRIMINAL')


def test_step_stuck_and_inconsistent():
    state = FakeEngine().knowledge()
    assert SatAgent(kb_of([[1, 2]]), solve).step(state)['outcome'] == 'STUCK'
    assert SatAgent(CONTRADICTION, solve).step(state)['outcome'] == 'INCONSISTENT'


def test_auto_solve_stops_when_ambiguous():
    outcome, trace = SatAgent(AMBIGUOUS, solve).auto_solve(FakeEngine())
    assert outcome == 'STUCK'
    assert [(t['cell'], t['verdict']) for t in trace] == [('B', 'CRIMINAL')]


def test_auto_solve_complete_with_trace():
    outcome, trace = SatAgent(ALL_FORCED, solve).auto_solve(FakeEngine())
    assert outcome == 'COMPLETE'
    assert [t['step'] for t in trace] == [1, 2]
    assert [t['cell'] for t in trace] == ['A', 'B']          # row-major order
    assert [t['revealed'] for t in trace] == [['clue-A'], ['clue-B']]
    assert all(t['sat_queries'] > 0 for t in trace)


def test_auto_solve_inconsistent():
    assert SatAgent(CONTRADICTION, solve).auto_solve(FakeEngine()) == ('INCONSISTENT', [])


def test_check_verdict_inconsistent():
    state = FakeEngine().knowledge()
    assert SatAgent(CONTRADICTION, solve).check_verdict(state, 'A', 'CRIMINAL') == 'INCONSISTENT'
