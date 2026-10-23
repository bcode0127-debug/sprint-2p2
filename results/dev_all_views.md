**DEV-ONLY**: thresholds fit in-sample on the development data. Not a test result.

## Scorers

| scorer | AUROC | 95% CI (13 games) | recall @10% FPR | FPR achieved | distinct |
|---|---|---|---|---|---|
| both | 0.607 | 0.540 to 0.668 | 0.160 | 0.100 | 44 |
| actions_only | 0.507 | 0.450 to 0.548 | 0.074 | 0.103 | 12 |
| messages_only | 0.625 | 0.572 to 0.675 | 0.135 | 0.100 | 39 |
| structured | 0.601 | 0.542 to 0.654 | 0.135 | 0.097 | 38 |
| own_only | 0.518 | 0.445 to 0.584 | 0.139 | 0.106 | 39 |
| freshness | 0.495 | 0.429 to 0.548 | 0.119 | 0.100 | 37 |
| oracle | 1.000 | 1.000 to 1.000 | 1.000 | 0.094 | 18 |
| empty | 0.508 | 0.476 to 0.543 | 0.094 | 0.103 | 3 |
| round_only | 0.489 | 0.448 to 0.528 | 0.049 | 0.100 | 5 |
| random | 0.518 | 0.478 to 0.561 | 0.123 | 0.100 | 585 |
| last_crowded | 0.435 | 0.368 to 0.495 | 0.037 | 0.103 | 2 |
| broke_last | 0.490 | 0.440 to 0.533 | 0.078 | 0.082 | 2 |
| round_rate | 0.635 | 0.573 to 0.706 | 0.234 | 0.097 | 8 |
| counting | 0.652 | 0.594 to 0.708 | 0.148 | 0.097 | 5 |
| plan | 0.655 | 0.590 to 0.720 | 0.361 | 0.100 | 2 |

## Contrasts (A minus B)

| contrast | metric | mean paired diff | between-game SD | min detectable (20 games) |
|---|---|---|---|---|
| primary: both - actions_only | auroc | 0.100 | 0.121 | 0.070 |
| primary: both - actions_only | recall | 0.086 | 0.186 | 0.108 |
| S1: both - own_only | auroc | 0.089 | 0.051 | 0.029 |
| S1: both - own_only | recall | 0.020 | 0.144 | 0.084 |
| S2: both - freshness | auroc | 0.111 | 0.107 | 0.062 |
| S2: both - freshness | recall | 0.041 | 0.194 | 0.112 |
| S3: both - counting | auroc | -0.045 | 0.136 | 0.079 |
| S3: both - counting | recall | 0.012 | 0.180 | 0.105 |

## Controls (DEV preview)

- oracle: recall 1.000, AUROC 1.000, pass = True (needs recall >= 0.95, AUROC >= 0.99)
- empty: AUROC 0.508, pass = True (band 0.40 to 0.60)
- round_only vs round_rate: AUROC 0.489 vs 0.635; recall 0.049 vs 0.234
