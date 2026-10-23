"""Metrics: randomized threshold, AUROC, paired game-clustered bootstrap, Holm, variance split.

Positive class = break (label True). A higher score means more likely to break.
"""

import random

import numpy as np

SEED = 2026
FPR_TARGET = 0.10
N_BOOT = 10_000
ONE_SIDED_ALPHA = 0.05


def _avg_ranks(x: np.ndarray) -> np.ndarray:
    """Return 1-based average ranks, giving tied values the mean of their ranks."""
    order = np.argsort(x, kind="mergesort")
    xs = x[order]
    starts = np.flatnonzero(np.r_[True, xs[1:] != xs[:-1]])
    counts = np.diff(np.r_[starts, len(xs)])
    avg = starts + (counts + 1) / 2
    ranks = np.empty(len(x))
    ranks[order] = np.repeat(avg, counts)
    return ranks


def auroc(scores: np.ndarray, labels: np.ndarray) -> float | None:
    """Return AUROC with ties counted as 0.5, or None if one class is empty."""
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels, dtype=bool)
    n_pos = int(labels.sum())
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    ranks = _avg_ranks(scores)
    return float((ranks[labels].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def spearman(x: np.ndarray, y: np.ndarray) -> float | None:
    """Return the Spearman correlation (Pearson on average ranks), or None if constant."""
    rx, ry = _avg_ranks(np.asarray(x, float)), _avg_ranks(np.asarray(y, float))
    if rx.std() == 0 or ry.std() == 0:
        return None
    return float(np.corrcoef(rx, ry)[0, 1])


def placement_values(scores: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """Return each case's share of opposite-class cases it is ranked correctly against."""
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels, dtype=bool)
    pos, neg = scores[labels], scores[~labels]
    out = np.empty(len(scores))
    for i, (s, lab) in enumerate(zip(scores, labels, strict=True)):
        if lab:
            out[i] = (np.sum(neg < s) + 0.5 * np.sum(neg == s)) / len(neg)
        else:
            out[i] = (np.sum(pos > s) + 0.5 * np.sum(pos == s)) / len(pos)
    return out


def randomized_threshold(scores: np.ndarray, labels: np.ndarray, fpr: float = FPR_TARGET) -> dict:
    """Fit (t, q): flag score > t, and score == t with probability q, so expected FPR = fpr.

    t is the lowest keep-score whose strictly-greater share of keeps is at most fpr.
    """
    scores = np.asarray(scores, dtype=float)
    keeps = scores[~np.asarray(labels, dtype=bool)]
    if len(keeps) == 0:
        msg = "no keeps to fit a threshold"
        raise ValueError(msg)
    for value in np.unique(keeps):
        above = float(np.mean(keeps > value))
        if above <= fpr:
            equal = float(np.mean(keeps == value))
            return {"t": float(value), "q": (fpr - above) / equal, "fpr_target": fpr}
    msg = "unreachable"
    raise RuntimeError(msg)


def case_uniforms(keys: list[str], seed: int = SEED) -> np.ndarray:
    """Return a reproducible uniform draw per case key."""
    return np.array([random.Random(f"{seed}|{k}").random() for k in keys])  # noqa: S311


def apply_threshold(
    scores: np.ndarray,
    labels: np.ndarray,
    keys: list[str],
    fit: dict,
    *,
    seed: int = SEED,
) -> dict:
    """Apply a frozen fit {t, q} to a split; report recall and the FPR actually achieved."""
    t, q = fit["t"], fit["q"]
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels, dtype=bool)
    u = case_uniforms(keys, seed)
    flagged = (scores > t) | ((scores == t) & (u < q))
    expected = (scores > t) + q * (scores == t)
    return {
        "recall": float(flagged[labels].mean()),
        "fpr": float(flagged[~labels].mean()),
        "recall_expected": float(expected[labels].mean()),
        "fpr_expected": float(expected[~labels].mean()),
        "n_break": int(labels.sum()),
        "n_keep": int((~labels).sum()),
    }


def _groups(games: list[str]) -> list[np.ndarray]:
    """Return the case indices of each game."""
    arr = np.asarray(games)
    return [np.flatnonzero(arr == g) for g in sorted(set(games))]


def paired_bootstrap(
    scores_a: np.ndarray,
    scores_b: np.ndarray,
    labels: np.ndarray,
    games: list[str],
    n_boot: int = N_BOOT,
) -> dict:
    """Bootstrap AUROC(A) - AUROC(B), resampling whole games.

    Returns the point difference, a one-sided 95% lower bound (5th percentile) and the
    one-sided bootstrap p-value for 'difference <= 0'.
    """
    a, b = np.asarray(scores_a, float), np.asarray(scores_b, float)
    lab = np.asarray(labels, bool)
    groups = _groups(games)
    rng = np.random.default_rng(SEED)
    diffs = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(groups), len(groups))
        idx = np.concatenate([groups[i] for i in pick])
        da, db = auroc(a[idx], lab[idx]), auroc(b[idx], lab[idx])
        if da is not None and db is not None:
            diffs.append(da - db)
    arr = np.array(diffs)
    point = float(auroc(a, lab) - auroc(b, lab))
    return {
        "diff": point,
        "lower_95_one_sided": float(np.percentile(arr, 100 * ONE_SIDED_ALPHA)),
        "p_one_sided": float((1 + np.sum(arr <= 0)) / (1 + len(arr))),
        "n_resamples": len(arr),
        "n_games": len(groups),
    }


def holm(p_values: dict[str, float]) -> dict[str, float]:
    """Return Holm-adjusted p-values."""
    ordered = sorted(p_values.items(), key=lambda kv: kv[1])
    m = len(ordered)
    adjusted: dict[str, float] = {}
    running = 0.0
    for i, (name, p) in enumerate(ordered):
        running = max(running, min(1.0, (m - i) * p))
        adjusted[name] = running
    return adjusted


def variance_decomposition(delta: np.ndarray, games: list[str]) -> dict:
    """Split the variance of per-case differences into between-game and within-game parts."""
    d = np.asarray(delta, dtype=float)
    arr = np.asarray(games)
    mean = d.mean()
    between = within = 0.0
    for g in set(games):
        part = d[arr == g]
        between += len(part) * (part.mean() - mean) ** 2
        within += float(np.sum((part - part.mean()) ** 2))
    n = len(d)
    total = between / n + within / n
    return {
        "total": total,
        "between_game": between / n,
        "within_game": within / n,
        "between_share": (between / n) / total if total else None,
    }


def paired_decomposition(
    scores_a: np.ndarray,
    scores_b: np.ndarray,
    labels: np.ndarray,
    games: list[str],
) -> dict:
    """Decompose the paired AUROC difference using per-case placement-value differences.

    The mean of the per-case differences equals AUROC(A) - AUROC(B).
    """
    delta = placement_values(scores_a, labels) - placement_values(scores_b, labels)
    out = variance_decomposition(delta, games)
    out["mean_difference"] = float(delta.mean())
    return out
