"""Run the same Griductive corpus with reproducible DPLL variants."""
import argparse
import csv
from html import escape
from collections import Counter
from pathlib import Path
from time import perf_counter

from experiments.cases import BENCHMARK_PUZZLES
from game.agent import SatAgent
from game.dpll import solve
from game.encoder import build_kb
from game.logic import CRIMINAL, INNOCENT, UNKNOWN


COLUMNS = (
    'puzzle_id', 'title', 'size', 'variant', 'status', 'n_primary',
    'n_aux', 'clauses', 'sat_calls', 'decisions', 'propagations',
    'backtracks', 'steps', 'runtime_ms', 'solver_runtime_ms', 'error',
)


class CountingSolver:
    def __init__(self, use_pure_literals):
        self.use_pure_literals = use_pure_literals
        self.calls = self.decisions = self.propagations = self.backtracks = 0
        self.runtime_ms = 0.0

    def __call__(self, clauses, n_vars, assumptions=()):
        answer = solve(clauses, n_vars, assumptions,
                       use_pure_literals=self.use_pure_literals)
        self.calls += 1
        self.decisions += answer.stats.decisions
        self.propagations += answer.stats.propagations
        self.backtracks += answer.stats.backtracks
        self.runtime_ms += answer.stats.runtime_ms
        return answer


def _full_kb(puzzle):
    known = {
        cell: CRIMINAL if puzzle['solution'][cell] else INNOCENT
        for cell in puzzle['initial']
    }
    return build_kb(dict(
        layout=puzzle['layout'], known=known,
        clues=list(puzzle['clues'].values()),
    ))


def run_case(puzzle, variant='dpll', timeout_seconds=30.0):
    use_pure_literals = variant == 'dpll+pure'
    counter = CountingSolver(use_pure_literals)
    agent = SatAgent(build_kb, counter)
    known = {
        cell: CRIMINAL if puzzle['solution'][cell] else INNOCENT
        for cell in puzzle['initial']
    }
    started = perf_counter()
    steps = 0
    status = 'RUNNING'
    error = ''

    try:
        while len(known) < len(puzzle['layout']):
            if perf_counter() - started > timeout_seconds:
                status = 'TIMEOUT'
                break
            state = dict(
                layout=puzzle['layout'], known=dict(known),
                clues=[puzzle['clues'][cell] for cell in known],
            )
            inference = agent.classify(state)
            if not inference.model_count:
                status = 'INCONSISTENT'
                break
            forced = next(
                ((cell['id'], inference.statuses.get(cell['id'], UNKNOWN))
                 for cell in puzzle['layout']
                 if cell['id'] not in known
                 and inference.statuses.get(cell['id'], UNKNOWN) != UNKNOWN),
                None,
            )
            if forced is None:
                status = 'STUCK'
                break
            cell, verdict = forced
            expected = CRIMINAL if puzzle['solution'][cell] else INNOCENT
            if verdict != expected:
                status = 'WRONG_VERDICT'
                error = f'{cell}: expected {expected}, got {verdict}'
                break
            known[cell] = verdict
            steps += 1
        else:
            status = 'COMPLETE'
    except Exception as exc:  # experiment rows must retain failures
        status = 'ERROR'
        error = f'{type(exc).__name__}: {exc}'

    kb = _full_kb(puzzle)
    return {
        'puzzle_id': puzzle['id'],
        'title': puzzle['title'],
        'size': puzzle['size'],
        'variant': variant,
        'status': status,
        'n_primary': kb.n_primary,
        'n_aux': kb.n_aux,
        'clauses': len(kb.clauses),
        'sat_calls': counter.calls,
        'decisions': counter.decisions,
        'propagations': counter.propagations,
        'backtracks': counter.backtracks,
        'steps': steps,
        'runtime_ms': round((perf_counter() - started) * 1000, 3),
        'solver_runtime_ms': round(counter.runtime_ms, 3),
        'error': error,
    }


def run_suite(variants=('dpll', 'dpll+pure'), timeout_seconds=30.0,
              puzzles=BENCHMARK_PUZZLES):
    return [
        run_case(puzzle, variant, timeout_seconds)
        for variant in variants
        for puzzle in puzzles.values()
    ]


def write_csv(rows, destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('w', newline='', encoding='utf-8') as output:
        writer = csv.DictWriter(output, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(rows, destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    sizes = Counter(puzzle['size'] for puzzle in BENCHMARK_PUZZLES.values())
    variants = list(dict.fromkeys(row['variant'] for row in rows))
    lines = [
        '# Griductive DPLL experiment summary',
        '',
        'Corpus: ' + ', '.join(
            f'{count} puzzle {size}×{size}' for size, count in sorted(sizes.items())),
        '',
        '| Variant | Complete | Total runtime (ms) | SAT calls | Decisions | Propagations | Backtracks |',
        '|---|---:|---:|---:|---:|---:|---:|',
    ]
    for variant in variants:
        selected = [row for row in rows if row['variant'] == variant]
        lines.append(
            f"| {variant} | {sum(row['status'] == 'COMPLETE' for row in selected)}/{len(selected)} "
            f"| {sum(row['runtime_ms'] for row in selected):.3f} "
            f"| {sum(row['sat_calls'] for row in selected)} "
            f"| {sum(row['decisions'] for row in selected)} "
            f"| {sum(row['propagations'] for row in selected)} "
            f"| {sum(row['backtracks'] for row in selected)} |"
        )
    lines += [
        '',
        '## Per-puzzle results',
        '',
        '| Puzzle | Size | Variant | Status | Clauses | SAT calls | Decisions | Propagations | Backtracks | Steps | Runtime (ms) |',
        '|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for row in rows:
        lines.append(
            f"| {row['puzzle_id']} | {row['size']}×{row['size']} | {row['variant']} "
            f"| {row['status']} | {row['clauses']} | {row['sat_calls']} "
            f"| {row['decisions']} | {row['propagations']} | {row['backtracks']} "
            f"| {row['steps']} | {row['runtime_ms']:.3f} |"
        )
    lines += ['', 'See `runtime.svg` for the runtime comparison chart.', '']
    destination.write_text('\n'.join(lines), encoding='utf-8')


def write_runtime_svg(rows, destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    width, label_width, row_height = 1000, 270, 25
    chart_width = width - label_width - 90
    height = 70 + row_height * len(rows)
    maximum = max((row['runtime_ms'] for row in rows), default=1) or 1
    colors = {'dpll': '#2563eb', 'dpll+pure': '#ea580c'}
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#172033}.title{font-size:20px;font-weight:700}.label{font-size:12px}.value{font-size:11px}</style>',
        '<text class="title" x="20" y="30">Griductive DPLL runtime by puzzle</text>',
    ]
    for index, row in enumerate(rows):
        y = 50 + index * row_height
        bar_width = max(1, round(row['runtime_ms'] / maximum * chart_width))
        label = escape(f"{row['puzzle_id']} · {row['variant']}")
        color = colors.get(row['variant'], '#64748b')
        svg.append(f'<text class="label" x="20" y="{y + 13}">{label}</text>')
        svg.append(f'<rect x="{label_width}" y="{y}" width="{bar_width}" height="16" rx="3" fill="{color}"/>')
        svg.append(f'<text class="value" x="{label_width + bar_width + 6}" y="{y + 12}">{row["runtime_ms"]:.3f} ms</text>')
    svg.append('</svg>')
    destination.write_text('\n'.join(svg), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='experiments/results.csv')
    parser.add_argument('--timeout', type=float, default=30.0)
    parser.add_argument('--variant', action='append',
                        choices=('dpll', 'dpll+pure'))
    parser.add_argument('--summary', default='experiments/summary.md')
    parser.add_argument('--chart', default='experiments/runtime.svg')
    args = parser.parse_args()
    variants = tuple(args.variant or ('dpll', 'dpll+pure'))
    rows = run_suite(variants, args.timeout)
    write_csv(rows, args.output)
    write_summary(rows, args.summary)
    write_runtime_svg(rows, args.chart)

    sizes = Counter(puzzle['size'] for puzzle in BENCHMARK_PUZZLES.values())
    print('Corpus:', ', '.join(f'{count} puzzle {size}x{size}'
                                for size, count in sorted(sizes.items())))
    print(f'Wrote {len(rows)} rows to {args.output}')
    print(f'Wrote summary to {args.summary} and chart to {args.chart}')
    for row in rows:
        print(f"{row['variant']:<10} {row['puzzle_id']:<24} "
              f"{row['status']:<12} calls={row['sat_calls']:<4} "
              f"decisions={row['decisions']:<5} runtime={row['runtime_ms']} ms")


if __name__ == '__main__':
    main()
