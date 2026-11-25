"""python main.py              -> web UI using the SAT agent
python main.py --solve ID     -> solve one puzzle in the terminal and print the trace
python main.py --check        -> uniqueness check of every puzzle
python main.py --cnf-stats    -> opening and complete clue-set CNF sizes"""
import argparse

from app import create_app
from game.agent import SatAgent
from game.encoder import build_kb
from game.engine import GameEngine
from game.logic import CRIMINAL, INNOCENT
from game.puzzles import PUZZLES
from game.stub_sat import solve  # swap for the team's instrumented DPLL when ready


def make_agent():
    return SatAgent(build_kb, solve)


def initial_facts(puzzle):
    """Opening cards are public facts, but the puzzle stores them outside `clues`."""
    return [dict(id=f'init-{cell}', type='FACT', cells=[cell],
                 status=CRIMINAL if puzzle['solution'][cell] else INNOCENT)
            for cell in puzzle['initial']]


def print_cnf_stats():
    print('puzzle             state     primary  auxiliary  clauses')
    for pid, puzzle in PUZZLES.items():
        state = GameEngine(pid).knowledge()
        for label, clues in [('opening', state['clues']), ('full', list(puzzle['clues'].values()))]:
            kb = build_kb(state | {'clues': clues})
            print(f'{pid:<18} {label:<9} {kb.n_primary:>7} {kb.n_aux:>10} {kb.n_clauses:>8}')


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_mutually_exclusive_group()
    commands.add_argument('--solve', choices=PUZZLES)
    commands.add_argument('--check', action='store_true')
    commands.add_argument('--cnf-stats', action='store_true')
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
    elif args.cnf_stats:
        print_cnf_stats()
    else:
        create_app(agent_factory=make_agent).run(host='127.0.0.1', port=5000, debug=False)


if __name__ == '__main__':
    main()
