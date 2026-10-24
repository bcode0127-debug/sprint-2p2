# Result tables (pre-registration v2)

## Primary: paired AUROC difference, Both minus Actions-only

AUROC 0.668 vs 0.501; difference 0.167; one-sided 95% lower bound 0.133; success = True; two-sided 95% interval (descriptive) 0.126 to 0.203

## S1 to S3 (AUROC, one-sided, Holm at 0.05)

| id | A minus B | diff | lower 95% | p | p Holm | reject | two-sided 95% (descriptive) |
|---|---|---|---|---|---|---|---|
| S1 | both - own_only | 0.111 | 0.080 | 0.000 | 0.000 | True | 0.075 to 0.153 |
| S2 | both - freshness | 0.153 | 0.111 | 0.000 | 0.000 | True | 0.103 to 0.206 |
| S3 | both - counting | 0.035 | -0.020 | 0.153 | 0.153 | False | -0.029 to 0.101 |

## Deployment reading: recall at the frozen 10% FPR

| scorer | AUROC | recall | recall lower 95% | FPR achieved | parse failures |
|---|---|---|---|---|---|
| actions_only | 0.501 | 0.120 | 0.082 | 0.139 | 0 |
| messages_only | 0.653 | 0.274 | 0.204 | 0.101 | 0 |
| both | 0.668 | 0.295 | 0.231 | 0.122 | 0 |
| structured | 0.645 | 0.191 | 0.146 | 0.076 | 0 |
| own_only | 0.557 | 0.104 | 0.072 | 0.067 | 0 |
| freshness | 0.515 | 0.069 | 0.034 | 0.067 | 0 |
| oracle | 1.000 | 1.000 | 1.000 | 0.122 | 0 |
| empty | 0.534 | 0.152 | 0.126 | 0.109 | 0 |
| round_only | 0.497 | 0.088 | 0.061 | 0.120 | 0 |
| random | 0.494 | 0.098 | 0.073 | 0.088 | 0 |
| last_crowded | 0.443 | 0.122 | 0.086 | 0.130 | 0 |
| broke_last | 0.515 | 0.096 | 0.073 | 0.082 | 0 |
| round_rate | 0.549 | 0.152 | 0.127 | 0.097 | 0 |
| counting | 0.632 | 0.202 | 0.161 | 0.137 | 0 |
| plan | 0.642 | 0.380 | 0.315 | 0.105 | 0 |

## Controls

- oracle: recall 1.000, AUROC 1.000, pass = True
- empty: AUROC 0.534, pass = True
- round_only vs round_rate: AUROC difference -0.053
- plan rule: recall 0.380, FPR 0.105 (expected near 0.32 and 0.11)

## Power (minimum detectable difference, 20 games)

| contrast | metric | between-game SD | min detectable |
|---|---|---|---|
| primary | auroc | 0.099 | 0.058 |
| primary | recall | 0.223 | 0.129 |
| S1 | auroc | 0.108 | 0.062 |
| S1 | recall | 0.153 | 0.089 |
| S2 | auroc | 0.117 | 0.068 |
| S2 | recall | 0.185 | 0.107 |
| S3 | auroc | 0.140 | 0.081 |
| S3 | recall | 0.247 | 0.143 |
