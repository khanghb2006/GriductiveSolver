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