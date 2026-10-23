**DEV-ONLY**

# Result tables (pre-registration v2)

## Primary: paired AUROC difference, Both minus Actions-only

AUROC 0.607 vs 0.507; difference 0.100; one-sided 95% lower bound 0.045; success = True

## S1 to S3 (AUROC, one-sided, Holm at 0.05)

| id | A minus B | diff | lower 95% | p | p Holm | reject |
|---|---|---|---|---|---|---|
| S1 | both - own_only | 0.089 | 0.070 | 0.000 | 0.000 | True |
| S2 | both - freshness | 0.111 | 0.066 | 0.000 | 0.000 | True |
| S3 | both - counting | -0.045 | -0.113 | 0.879 | 0.879 | False |

## Deployment reading: recall at the frozen 10% FPR

| scorer | AUROC | recall | recall lower 95% | FPR achieved | parse failures |
|---|---|---|---|---|---|
| actions_only | 0.507 | 0.074 | 0.044 | 0.103 | 0 |
| messages_only | 0.625 | 0.135 | 0.077 | 0.100 | 0 |
| both | 0.607 | 0.160 | 0.090 | 0.100 | 0 |
| structured | 0.601 | 0.135 | 0.081 | 0.097 | 0 |
| own_only | 0.518 | 0.139 | 0.068 | 0.106 | 0 |
| freshness | 0.495 | 0.119 | 0.034 | 0.100 | 0 |
| oracle | 1.000 | 1.000 | 1.000 | 0.094 | 0 |
| empty | 0.508 | 0.094 | 0.076 | 0.103 | 0 |
| round_only | 0.489 | 0.049 | 0.030 | 0.100 | 0 |
| random | 0.518 | 0.123 | 0.075 | 0.100 | 0 |
| last_crowded | 0.435 | 0.037 | 0.016 | 0.103 | 0 |
| broke_last | 0.490 | 0.078 | 0.059 | 0.082 | 0 |
| round_rate | 0.635 | 0.234 | 0.194 | 0.097 | 0 |
| counting | 0.652 | 0.148 | 0.121 | 0.097 | 0 |
| plan | 0.655 | 0.361 | 0.279 | 0.100 | 0 |

## Controls

- oracle: recall 1.000, AUROC 1.000, pass = True
- empty: AUROC 0.508, pass = True
- round_only vs round_rate: AUROC difference -0.147
- plan rule: recall 0.361, FPR 0.100 (expected near 0.32 and 0.11)

## Power (minimum detectable difference, 20 games)

| contrast | metric | between-game SD | min detectable |
|---|---|---|---|
| primary | auroc | 0.121 | 0.070 |
| primary | recall | 0.186 | 0.108 |
| S1 | auroc | 0.051 | 0.029 |
| S1 | recall | 0.144 | 0.084 |
| S2 | auroc | 0.107 | 0.062 |
| S2 | recall | 0.194 | 0.112 |
| S3 | auroc | 0.136 | 0.079 |
| S3 | recall | 0.180 | 0.105 |
