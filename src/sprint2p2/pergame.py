"""Descriptive per-game AUROC differences, reported next to every pooled difference."""

import numpy as np

from sprint2p2 import metrics


def per_game_auroc_difference(
    a: np.ndarray,
    b: np.ndarray,
    labels: np.ndarray,
    games: list[str],
) -> dict:
    """Return the AUROC(A) - AUROC(B) inside each game, and their mean.

    Games with only one class are skipped. This is descriptive and feeds no test.
    """
    a, b, lab = np.asarray(a, float), np.asarray(b, float), np.asarray(labels, bool)
    arr = np.asarray(games)
    diffs = {}
    for g in sorted(set(games)):
        idx = arr == g
        da, db = metrics.auroc(a[idx], lab[idx]), metrics.auroc(b[idx], lab[idx])
        if da is not None and db is not None:
            diffs[g] = da - db
    values = list(diffs.values())
    return {
        "mean_of_per_game_differences": float(np.mean(values)) if values else None,
        "per_game": diffs,
        "n_games_used": len(values),
    }
