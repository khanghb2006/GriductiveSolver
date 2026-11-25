# Griductive DPLL experiment summary

Corpus: 4 puzzle 3×3, 4 puzzle 4×4, 2 puzzle 5×5

| Variant | Complete | Total runtime (ms) | SAT calls | Decisions | Propagations | Backtracks |
|---|---:|---:|---:|---:|---:|---:|
| dpll | 10/10 | 1026.322 | 2298 | 3623 | 37236 | 144 |
| dpll+pure | 10/10 | 1482.804 | 2298 | 3623 | 37252 | 144 |

## Per-puzzle results

| Puzzle | Size | Variant | Status | Clauses | SAT calls | Decisions | Propagations | Backtracks | Steps | Runtime (ms) |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| village-3 | 3×3 | dpll | COMPLETE | 27 | 63 | 30 | 363 | 0 | 7 | 3.798 |
| village-4 | 4×4 | dpll | COMPLETE | 185 | 224 | 43 | 2163 | 0 | 14 | 17.359 |
| village-5 | 5×5 | dpll | COMPLETE | 304 | 575 | 1472 | 7986 | 0 | 23 | 221.490 |
| village-5-mist | 5×5 | dpll | COMPLETE | 218 | 575 | 1409 | 8547 | 5 | 23 | 187.484 |
| village-3-links | 3×3 | dpll | COMPLETE | 121 | 63 | 81 | 1606 | 6 | 7 | 18.329 |
| village-4-links | 4×4 | dpll | COMPLETE | 519 | 224 | 588 | 12217 | 133 | 14 | 540.917 |
| benchmark-3-river | 3×3 | dpll | COMPLETE | 16 | 63 | 0 | 350 | 0 | 7 | 2.764 |
| benchmark-3-market | 3×3 | dpll | COMPLETE | 16 | 63 | 0 | 350 | 0 | 7 | 4.448 |
| benchmark-4-tower | 4×4 | dpll | COMPLETE | 29 | 224 | 0 | 1827 | 0 | 14 | 15.775 |
| benchmark-4-bridge | 4×4 | dpll | COMPLETE | 28 | 224 | 0 | 1827 | 0 | 14 | 13.958 |
| village-3 | 3×3 | dpll+pure | COMPLETE | 27 | 63 | 30 | 363 | 0 | 7 | 6.605 |
| village-4 | 4×4 | dpll+pure | COMPLETE | 185 | 224 | 43 | 2163 | 0 | 14 | 25.427 |
| village-5 | 5×5 | dpll+pure | COMPLETE | 304 | 575 | 1472 | 7986 | 0 | 23 | 331.894 |
| village-5-mist | 5×5 | dpll+pure | COMPLETE | 218 | 575 | 1409 | 8547 | 5 | 23 | 388.198 |
| village-3-links | 3×3 | dpll+pure | COMPLETE | 121 | 63 | 81 | 1606 | 6 | 7 | 31.691 |
| village-4-links | 4×4 | dpll+pure | COMPLETE | 519 | 224 | 588 | 12233 | 133 | 14 | 631.179 |
| benchmark-3-river | 3×3 | dpll+pure | COMPLETE | 16 | 63 | 0 | 350 | 0 | 7 | 4.650 |
| benchmark-3-market | 3×3 | dpll+pure | COMPLETE | 16 | 63 | 0 | 350 | 0 | 7 | 6.910 |
| benchmark-4-tower | 4×4 | dpll+pure | COMPLETE | 29 | 224 | 0 | 1827 | 0 | 14 | 20.954 |
| benchmark-4-bridge | 4×4 | dpll+pure | COMPLETE | 28 | 224 | 0 | 1827 | 0 | 14 | 35.296 |

See `runtime.svg` for the runtime comparison chart.
