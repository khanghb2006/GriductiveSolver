# Griductive Solver

CSC14003 – Introduction to AI, Project 2 (HCMUS). A **no-guess** solver for the grid-deduction game Griductive, built on propositional logic, CNF encoding and a hand-written DPLL SAT solver.

Every person on the grid is secretly `CRIMINAL` or `INNOCENT`. A verdict is accepted only if it is **logically entailed** by the clues currently revealed; a correct verdict flips a card and reveals a new clue.

> **Status:** planning stage. Only the spec and task split exist so far; the code layout below is the agreed target, not what is on disk yet.

## Docs

- [statement.md](statement.md) – assignment text (the PDF `AI - Project 2.pdf` is authoritative)
- [assignment.md](assignment.md) – team split, module contracts, timeline (Vietnamese)

## How it works

1. **Encode** – each cell *i* is a variable `C_i` (true = criminal), numbered row-major (`A1, B1, C1, A2, …` → `1..N²`). Every revealed clue becomes CNF (auxiliary vars start at `N²+1`).
2. **Classify** – for each unsolved cell, with `KB` = revealed clues + known verdicts:
   - `KB ∧ ¬C_i` UNSAT → `CRIMINAL`
   - `KB ∧ C_i` UNSAT → `INNOCENT`
   - both SAT → `UNKNOWN`; `KB` UNSAT → `INCONSISTENT`
3. **Verdict check** – `ACCEPTED`, `NOT_PROVABLE` or `CONTRADICTED`. Never guesses.
4. **Loop** – take the first forced cell (row-major), reveal its card, update the KB, repeat until solved or stuck (ambiguous / inconsistent puzzles stop cleanly).

Clues: `FACT`, `SAME`, `DIFFERENT`, `EXACTLY`, `AT_LEAST`, `AT_MOST` over regions `ROW | COL | NEIGHBORS | CELLS`, plus extensions `PARITY` and `COMPARE`.

## Planned layout

```
main.py  README.md  requirements.txt
griductive/
  clues.py     clue schema, regions, semantic evaluator
  engine.py    GameEngine (hidden solution, reveal, public_state)
  encoder.py   clue -> CNF, build_kb
  dpll.py      SAT solver (+ decisions/propagations/backtracks/runtime stats)
  agent.py     LogicAgent (classify, hint, auto_solve, uniqueness_check)
  gui/         web or tkinter front end
puzzles/*.json        3x3, 4x4, 5x5, plus one ambiguous and one contradictory
experiments/run.py    runs all puzzles, writes CSV
tests/
```

Rule: the agent only sees `public_state` (`{N, revealed_clues, proved}`) and never imports the engine.

## Usage

Fill in once `main.py` exists:

```bash
pip install -r requirements.txt
python main.py                      # launch GUI
python -m pytest                    # tests
python experiments/run.py           # experiments -> CSV
```

## Team

See the table in [assignment.md](assignment.md) (members, student IDs, contribution %).
