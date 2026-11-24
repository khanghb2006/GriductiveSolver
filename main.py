"""python main.py              -> web UI using the SAT agent
python main.py --solve ID     -> solve one puzzle in the terminal and print the trace
python main.py --check        -> uniqueness check of every puzzle"""
import argparse

from app import create_app
from game.agent import SatAgent
from game.engine import GameEngine
from game.logic import CRIMINAL, INNOCENT
from game.puzzles import PUZZLES
from game.stub_sat import build_kb, solve  # swap for the real encoder/dpll when ready


def make_agent():
    return SatAgent(build_kb, solve)


def initial_facts(puzzle):
    """Opening cards are public facts, but the puzzle stores them outside `clues`."""
    return [dict(id=f'init-{cell}', type='FACT', cells=[cell],
                 status=CRIMINAL if puzzle['solution'][cell] else INNOCENT)
            for cell in puzzle['initial']]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--solve', choices=PUZZLES)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()

    if args.solve:
        agent = make_agent()
        outcome, trace = agent.auto_solve(GameEngine(args.solve, agent=agent))
        for t in trace:
            print(f"{t['step']:>2}. {t['cell']} = {t['verdict']:<9} clues={t['clue_ids']} "
                  f"queries={t['sat_queries']} revealed={t['revealed']}")
        print(outcome)
    elif args.check:
        for pid, puzzle in PUZZLES.items():
            clues = list(puzzle['clues'].values()) + initial_facts(puzzle)
            print(pid, make_agent().unique_check(clues, puzzle['size']))
    else:
        create_app(agent_factory=make_agent).run(host='127.0.0.1', port=5000, debug=False)


if __name__ == '__main__':
    main()