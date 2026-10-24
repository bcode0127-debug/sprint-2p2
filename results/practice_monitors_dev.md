**DEV-ONLY PRACTICE**: exploration for future work; not a registered result. 585 development cases, 13 games.

## AUROC (95% game-bootstrap interval)

| model | view | AUROC | 95% CI |
|---|---|---|---|
| haiku | both | 0.607 | 0.540 to 0.668 |
| haiku | actions_only | 0.507 | 0.450 to 0.548 |
| haiku | messages_only | 0.625 | 0.572 to 0.675 |
| haiku | both_run2 | 0.625 | 0.553 to 0.684 |
| gemini | both | 0.666 | 0.600 to 0.725 |
| gemini | actions_only | 0.517 | 0.466 to 0.560 |
| gemini | messages_only | 0.705 | 0.653 to 0.751 |
| sonnet | both | 0.629 | 0.558 to 0.691 |
| sonnet | actions_only | 0.537 | 0.479 to 0.593 |

## Announcement gain (Both minus Actions-only)

| model | pooled | per-game mean | one-sided 5th pct | two-sided 95% |
|---|---|---|---|---|
| haiku | 0.100 | 0.090 | 0.045 | 0.036 to 0.165 |
| gemini | 0.149 | 0.149 | 0.103 | 0.097 to 0.213 |
| sonnet | 0.092 | 0.090 | 0.049 | 0.041 to 0.156 |

## New model Both minus Haiku Both

| model | vs | pooled | per-game mean | two-sided 95% |
|---|---|---|---|---|
| gemini | haiku run1 | 0.059 | 0.054 | 0.028 to 0.089 |
| gemini | haiku run2 | 0.041 | 0.033 | -0.003 to 0.081 |
| sonnet | haiku run1 | 0.023 | 0.012 | -0.009 to 0.053 |
| sonnet | haiku run2 | 0.005 | -0.010 | -0.042 to 0.045 |

## Spearman on Both

- haiku_gemini: 0.603
- haiku_sonnet: 0.772
- gemini_sonnet: 0.754

## Rank averages on Both

| pair | AUROC | part a | part b | minus a | minus b |
|---|---|---|---|---|---|
| haiku+gemini | 0.652 | 0.607 | 0.666 | 0.045 | -0.014 |
| haiku+sonnet | 0.625 | 0.607 | 0.629 | 0.018 | -0.004 |
| gemini+sonnet | 0.656 | 0.666 | 0.629 | -0.010 | 0.027 |

## Both rank-averaged with the counting rule (counting alone 0.652)

| model | AUROC | Both alone | minus Both | minus counting |
|---|---|---|---|---|
| haiku | 0.667 | 0.607 | 0.060 | 0.015 |
| gemini | 0.693 | 0.666 | 0.027 | 0.041 |
| sonnet | 0.669 | 0.629 | 0.040 | 0.018 |

## Usage

| model | calls | parse failures | prompt | completion | reasoning | est. cost USD |
|---|---|---|---|---|---|---|
| haiku | 1755 | 0 | 2213020 | 523973 | 389199 | 0.483 |
| gemini | 1755 | 0 | 1533785 | 333676 | 245359 | 2.642 |
| sonnet | 1170 | 0 | 1282371 | 392675 | 101062 | 6.491 |
