# Result tables (pre-registration v2)

## Primary: paired AUROC difference, Both minus Actions-only

AUROC 0.655 vs 0.508; difference 0.147; one-sided 95% lower bound 0.088; success = True; two-sided 95% interval (descriptive) 0.075 to 0.216

## S1 to S3 (AUROC, one-sided, Holm at 0.05)

| id | A minus B | diff | lower 95% | p | p Holm | reject | two-sided 95% (descriptive) |
|---|---|---|---|---|---|---|---|
| S1 | both - own_only | 0.106 | 0.075 | 0.000 | 0.000 | True | 0.070 to 0.148 |
| S2 | both - freshness | 0.122 | 0.080 | 0.000 | 0.000 | True | 0.072 to 0.181 |
| S3 | both - counting | -0.015 | -0.067 | 0.699 | 0.699 | False | -0.078 to 0.044 |

## Deployment reading: recall at the frozen 10% FPR

| scorer | AUROC | recall | recall lower 95% | FPR achieved | parse failures |
|---|---|---|---|---|---|
| actions_only | 0.508 | 0.134 | 0.106 | 0.127 | 0 |
| messages_only | 0.633 | 0.282 | 0.192 | 0.114 | 0 |
| both | 0.655 | 0.285 | 0.212 | 0.146 | 0 |
| structured | 0.650 | 0.221 | 0.166 | 0.125 | 0 |
| own_only | 0.549 | 0.115 | 0.072 | 0.076 | 0 |
| freshness | 0.532 | 0.067 | 0.029 | 0.072 | 0 |
| oracle | 1.000 | 1.000 | 1.000 | 0.109 | 0 |
| empty | 0.481 | 0.095 | 0.084 | 0.133 | 0 |
| round_only | 0.492 | 0.109 | 0.082 | 0.098 | 0 |
| random | 0.465 | 0.098 | 0.070 | 0.129 | 0 |
| last_crowded | 0.488 | 0.117 | 0.079 | 0.096 | 0 |
| broke_last | 0.503 | 0.092 | 0.064 | 0.090 | 0 |
| round_rate | 0.510 | 0.134 | 0.105 | 0.114 | 0 |
| counting | 0.670 | 0.187 | 0.139 | 0.107 | 0 |
| plan | 0.573 | 0.277 | 0.217 | 0.133 | 0 |

## Controls

- oracle: recall 1.000, AUROC 1.000, pass = True
- empty: AUROC 0.481, pass = True
- round_only vs round_rate: AUROC difference -0.018
- plan rule: recall 0.277, FPR 0.133 (expected near 0.32 and 0.11)

## Power (minimum detectable difference, 20 games)

| contrast | metric | between-game SD | min detectable |
|---|---|---|---|
| primary | auroc | 0.160 | 0.093 |
| primary | recall | 0.287 | 0.166 |
| S1 | auroc | 0.110 | 0.064 |
| S1 | recall | 0.245 | 0.142 |
| S2 | auroc | 0.156 | 0.091 |
| S2 | recall | 0.262 | 0.152 |
| S3 | auroc | 0.143 | 0.083 |
| S3 | recall | 0.335 | 0.194 |
