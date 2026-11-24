import pytest

from game.engine import GameEngine
from game.puzzles import PUZZLES
from main import initial_facts, make_agent


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