# Harness comparison (lc = little-coder) (Ornith official Q4_K_M, tasks 13-18, 2 reps)

| Harness | Pass | Median time | Median requests | Median gen tokens | Total time | Timeouts | Edited tests |
|---|---|---|---|---|---|---|---|
| cc | 10/12 (83%) | 285 s | 20 | 17086 | 58 min | 0 | 1 |
| ccb | 11/12 (91%) | 211 s | 16 | 13548 | 50 min | 0 | 0 |
| lc | 11/12 (91%) | 529 s | 35 | 32402 | 109 min | 0 | 4 |
| pi | 6/12 (50%) | 78 s | 11 | 4582 | 16 min | 0 | 0 |

| Task | cc pass | cc median s | ccb pass | ccb median s | lc pass | lc median s | pi pass | pi median s |
|---|---|---|---|---|---|---|---|---|
| 13-import-csv | 2/2 | 393 | 2/2 | 457 | 2/2 | 852 | 2/2 | 91 |
| 14-tags | 2/2 | 154 | 2/2 | 142 | 2/2 | 462 | 1/2 | 78 |
| 15-undo | 2/2 | 268 | 2/2 | 197 | 2/2 | 687 | 0/2 | 52 |
| 16-date-range | 2/2 | 501 | 2/2 | 376 | 2/2 | 617 | 1/2 | 146 |
| 17-split | 0/2 | 314 | 1/2 | 238 | 1/2 | 529 | 0/2 | 76 |
| 18-store-interface | 2/2 | 96 | 2/2 | 87 | 2/2 | 119 | 2/2 | 39 |
