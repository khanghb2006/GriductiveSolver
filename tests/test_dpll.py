from collections import Counter
from itertools import product
from random import Random

from experiments.cases import BENCHMARK_PUZZLES, EXTRA_PUZZLES
from experiments.run import run_case
from game.agent import SatAgent
from game.dpll import solve
from game.logic import CRIMINAL, INNOCENT
from game.encoder import build_kb


def _holds(clauses, model):
    return all(any(model[abs(literal)] == (literal > 0) for literal in clause)
               for clause in clauses)


def _brute_force(clauses, n_vars, assumptions=()):
    for values in product((False, True), repeat=n_vars):
        model = {index + 1: value for index, value in enumerate(values)}
        if all(model[abs(literal)] == (literal > 0) for literal in assumptions) \
                and _holds(clauses, model):
            return model
    return None


def test_sat_unsat_assumptions_and_metrics():
    clauses = [[1, 2], [-1, 2], [1, -2]]
    answer = solve(clauses, 2)
    assert answer.sat and _holds(clauses, answer.model)
    assert set(answer.model) == {1, 2}
    assert not solve(clauses, 2, assumptions=(-1,)).sat
    assert not solve([[1], [-1]], 1).sat
    assert answer.stats.runtime_ms >= 0


def test_random_small_cnfs_match_brute_force():
    random = Random(14003)
    for n_vars in range(1, 6):
        literals = [literal for variable in range(1, n_vars + 1)
                    for literal in (variable, -variable)]
        for _ in range(40):
            clauses = [random.sample(literals, random.randint(1, min(3, len(literals))))
                       for _ in range(random.randint(0, 10))]
            assumptions = tuple(random.sample(literals, random.randint(0, min(2, n_vars))))
            expected = _brute_force(clauses, n_vars, assumptions)
            for pure in (False, True):
                answer = solve(clauses, n_vars, assumptions,
                               use_pure_literals=pure)
                assert answer.sat == (expected is not None)
                if answer.sat:
                    assert _holds(clauses, answer.model)
                    assert all(answer.model[abs(literal)] == (literal > 0)
                               for literal in assumptions)


def test_benchmark_corpus_meets_required_size_counts():
    counts = Counter(puzzle['size'] for puzzle in BENCHMARK_PUZZLES.values())
    assert counts[3] >= 3
    assert counts[4] >= 3
    assert counts[5] >= 1


def test_extra_benchmark_puzzles_are_unique_and_complete():
    for puzzle in EXTRA_PUZZLES:
        initial_facts = [
            dict(id=f'init-{cell}', type='FACT', cells=[cell],
                 status=CRIMINAL if puzzle['solution'][cell] else INNOCENT)
            for cell in puzzle['initial']
        ]
        agent = SatAgent(build_kb, solve)
        assert agent.unique_check(
            list(puzzle['clues'].values()) + initial_facts,
            puzzle['size'],
        ) == 'UNIQUE'
        row = run_case(puzzle, timeout_seconds=5)
        assert row['status'] == 'COMPLETE'
        assert row['steps'] == puzzle['size'] ** 2 - len(puzzle['initial'])
        assert row['sat_calls'] > 0
        assert row['clauses'] > 0
