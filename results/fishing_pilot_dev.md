**DEV-ONLY**: Fishing development pilot, rounds 1 to 9, 3 games. Not a test result.

| scorer | AUROC (a) | 95% CI (3 games) | AUROC (b) |
|---|---|---|---|
| both | 0.579 | 0.377 to 0.741 | 0.255 |
| actions_only | 0.531 | 0.496 to 0.602 | 0.312 |
| R1 | 0.473 | 0.396 to 0.564 | 0.802 |
| R2 | 0.467 | 0.333 to 0.572 | 0.820 |
| R12 | 0.466 | 0.333 to 0.565 | 0.826 |
| R3 | 0.416 | 0.392 to 0.485 | 0.227 |

both - actions_only (label a): diff 0.049, one-sided 5th percentile -0.048, between-game SD 0.136

Break rate (a) 0.607, (b) 0.119; over-take 16, under-take 66, unchanged 53
