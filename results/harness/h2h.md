# Head-to-head: Claude Code --bare, tasks 13-18, 3 reps

## Ornith-1.5 bartowski Q4_K_L
| Harness | Pass | Median time | Median requests | Median gen tokens | Total time | Timeouts | Edited tests |
|---|---|---|---|---|---|---|---|
| ccb | 16/18 (88%) | 218 s | 20 | 12522 | 73 min | 0 | 0 |

| Task | ccb pass | ccb median s |
|---|---|---|
| 13-import-csv | 3/3 | 304 |
| 14-tags | 3/3 | 136 |
| 15-undo | 3/3 | 217 |
| 16-date-range | 3/3 | 445 |
| 17-split | 1/3 | 256 |
| 18-store-interface | 3/3 | 109 |

## Qwen3.6 Unsloth UD-Q4_K_M (preserve_thinking)
| Harness | Pass | Median time | Median requests | Median gen tokens | Total time | Timeouts | Edited tests |
|---|---|---|---|---|---|---|---|
| ccb | 15/18 (83%) | 73 s | 14 | 3998 | 30 min | 0 | 0 |

| Task | ccb pass | ccb median s |
|---|---|---|
| 13-import-csv | 3/3 | 73 |
| 14-tags | 1/3 | 71 |
| 15-undo | 3/3 | 70 |
| 16-date-range | 2/3 | 92 |
| 17-split | 3/3 | 122 |
| 18-store-interface | 3/3 | 65 |
