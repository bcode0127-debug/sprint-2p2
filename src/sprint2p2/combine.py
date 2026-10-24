"""Monitor combined with the counting rule (Amendment 1, section 3).

Score = mean of an agent-round's rank under Both and its rank under the counting rule. Ties get
average ranks and ranks are taken within the evaluated set. Weights are equal and nothing is fitted.
"""

import numpy as np

from sprint2p2 import metrics
from sprint2p2.metrics import _avg_ranks

SEED = metrics.SEED
N_BOOT = metrics.N_BOOT


def combo_scores(both: np.ndarray, counting: np.ndarray) -> np.ndarray:
    """Return the mean of the two average-rank vectors, ranked within the given set."""
    return (_avg_ranks(np.asarray(both, float)) + _avg_ranks(np.asarray(counting, float))) / 2


def combo_auroc(both: np.ndarray, counting: np.ndarray, labels: np.ndarray) -> float | None:
    """Return the AUROC of the combination on the given set."""
    return metrics.auroc(combo_scores(both, counting), labels)


def per_game_combo_differences(
    both: np.ndarray,
    counting: np.ndarray,
    labels: np.ndarray,
    games: list[str],
) -> dict:
    """Descriptive per-game AUROC differences for C1 and C2, ranking inside each game.

    Each game is its own evaluated set, so the combination is re-ranked within the game. These
    reproduce the amendment's per-game figures; the pooled C1 and C2 use ranks over the whole set.
    """
    b, c, lab = np.asarray(both, float), np.asarray(counting, float), np.asarray(labels, bool)
    arr = np.asarray(games)
    c1, c2 = {}, {}
    for g in sorted(set(games)):
        m = arr == g
        a_x, a_b, a_c = (
            combo_auroc(b[m], c[m], lab[m]),
            metrics.auroc(b[m], lab[m]),
            metrics.auroc(c[m], lab[m]),
        )
        if a_x is not None and a_b is not None and a_c is not None:
            c1[g], c2[g] = a_x - a_b, a_x - a_c
    return {name: _summary(d) for name, d in (("C1", c1), ("C2", c2))}


def _summary(per_game: dict[str, float]) -> dict:
    """Mean and between-game SD of per-game differences."""
    values = list(per_game.values())
    return {
        "mean_of_per_game_differences": float(np.mean(values)),
        "between_game_sd": float(np.std(values, ddof=1)) if len(values) > 1 else None,
        "per_game_differences": per_game,
        "n_games_used": len(values),
    }


def combo_bootstrap(
    both: np.ndarray,
    counting: np.ndarray,
    labels: np.ndarray,
    games: list[str],
    n_boot: int = N_BOOT,
) -> dict:
    """C1 (combo - Both) and C2 (combo - counting): one-sided game bootstrap, Holm across the two.

    Ranks are recomputed inside every resample. Seed 2026.
    """
    b, c, lab = np.asarray(both, float), np.asarray(counting, float), np.asarray(labels, bool)
    arr = np.asarray(games)
    groups = [np.flatnonzero(arr == g) for g in sorted(set(games))]
    rng = np.random.default_rng(SEED)
    d1, d2 = [], []
    for _ in range(n_boot):
        idx = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        a_b, a_c = metrics.auroc(b[idx], lab[idx]), metrics.auroc(c[idx], lab[idx])
        a_x = combo_auroc(b[idx], c[idx], lab[idx])
        if a_b is not None and a_c is not None and a_x is not None:
            d1.append(a_x - a_b)
            d2.append(a_x - a_c)
    point = combo_auroc(b, c, lab)
    descriptive = per_game_combo_differences(b, c, lab, games)
    out = {
        "combo_auroc": point,
        "both_auroc": metrics.auroc(b, lab),
        "counting_auroc": metrics.auroc(c, lab),
    }
    for name, diffs, base in (("C1", d1, out["both_auroc"]), ("C2", d2, out["counting_auroc"])):
        arr_d = np.array(diffs)
        out[name] = {
            "diff": point - base,
            "lower_95_one_sided": float(np.percentile(arr_d, 100 * metrics.ONE_SIDED_ALPHA)),
            "p_one_sided": float((1 + np.sum(arr_d <= 0)) / (1 + len(arr_d))),
            "n_resamples": len(arr_d),
            "mean_of_per_game_differences": descriptive[name]["mean_of_per_game_differences"],
            "between_game_sd": descriptive[name]["between_game_sd"],
            "per_game_differences": descriptive[name]["per_game_differences"],
        }
    holm = metrics.holm({"C1": out["C1"]["p_one_sided"], "C2": out["C2"]["p_one_sided"]})
    for name, adjusted in holm.items():
        out[name]["p_holm"] = adjusted
        out[name]["reject_at_0.05"] = adjusted <= metrics.ONE_SIDED_ALPHA
    return out
