**DEV-ONLY**

# Result tables

## Primary

| scorer | AUROC | recall | FPR achieved | parse failures |
|---|---|---|---|---|
| both | 0.730 | 0.200 | 0.100 | 0 |


vs counting: diff -0.025, one-sided 95% lower bound -0.279

## S1 to S3 (Holm-adjusted)

| id | view | diff | lower 95% | p | p Holm |
|---|---|---|---|---|---|
| S1 | actions_only | 0.040 | -0.206 | 0.441 | 0.514 |
| S2 | messages_only | 0.300 | 0.143 | 0.008 | 0.025 |
| S3 | structured | 0.075 | -0.150 | 0.257 | 0.514 |


## Ablations

| scorer | AUROC | recall | FPR achieved | parse failures |
|---|---|---|---|---|
| own_only | 0.625 | 0.000 | 0.100 | 0 |
| freshness | 0.565 | 0.100 | 0.100 | 0 |


## Controls

| scorer | AUROC | recall | FPR achieved | parse failures |
|---|---|---|---|---|
| oracle | 1.000 | 1.000 | 0.100 | 0 |
| empty | 0.535 | 0.200 | 0.100 | 0 |
| round_only | 0.675 | 0.100 | 0.100 | 0 |


## Baselines

| scorer | AUROC | recall | FPR achieved | parse failures |
|---|---|---|---|---|
| random | 0.680 | 0.300 | 0.100 | 0 |
| last_crowded | 0.450 | 0.100 | 0.100 | 0 |
| broke_last | 0.600 | 0.200 | 0.200 | 0 |
| round_rate | 0.830 | 0.600 | 0.100 | 0 |
| counting | 0.755 | 0.200 | 0.200 | 0 |
| plan | 0.600 | 0.300 | 0.100 | 0 |
