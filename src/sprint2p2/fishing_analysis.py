"""Fishing transfer analysis (Amendment 1, section 4).

The single test is the AUROC difference Both minus Actions-only under label (a). Everything else
is descriptive. Scores arrays are aligned with the case list; parse failures carry the lowest score.
"""

import numpy as np

from sprint2p2 import analysis, fishing, metrics, pergame, scoring

SCORED_VIEWS = ("both", "actions_only", "oracle", "empty")
LABELS = ("label_a_any_change", "label_b_over_take_only")


def class_counts(labels: np.ndarray) -> dict:
    """Return the positive and negative counts of a label."""
    return {"n_positive": int(labels.sum()), "n_negative": int((~labels).sum())}


def scorer_block(scores: np.ndarray, labels: np.ndarray, games: list[str]) -> dict:
    """AUROC with a two-sided game-clustered interval and the class counts."""
    return {
        "auroc": metrics.auroc(scores, labels),
        "auroc_ci95": metrics.auroc_ci(scores, labels, games),
        **class_counts(labels),
    }


def contrast(a: np.ndarray, b: np.ndarray, labels: np.ndarray, games: list[str]) -> dict:
    """Pooled paired AUROC difference with the mean of per-game differences beside it."""
    boot = metrics.paired_bootstrap(a, b, labels, games)
    per_game = pergame.per_game_auroc_difference(a, b, labels, games)
    return {
        **boot,
        "success": boot["lower_95_one_sided"] > 0,
        "mean_of_per_game_differences": per_game["mean_of_per_game_differences"],
        "per_game_differences": per_game["per_game"],
        "n_games_used": per_game["n_games_used"],
        **class_counts(labels),
    }


def deployment(
    scores: np.ndarray, labels: np.ndarray, games: list[str], ids: list[str], fit: dict
) -> dict:
    """Recall and achieved FPR at a frozen El Farol (t, q), with a one-sided recall interval."""
    flagged = metrics.flags(scores, ids, fit)
    applied = metrics.apply_threshold(scores, labels, ids, fit)
    boot = metrics.recall_bootstrap(flagged, labels, games)
    return {
        "frozen_fit": fit,
        "recall": applied["recall"],
        "recall_lower_95_one_sided": boot["lower_95_one_sided"],
        "fpr_achieved": applied["fpr"],
        **class_counts(labels),
    }


def label_block(
    labels: np.ndarray,
    scores: dict[str, np.ndarray],
    rules: dict[str, np.ndarray],
    ctx: dict,
) -> dict:
    """Everything the amendment asks for under one label."""
    games, ids, fits = ctx["games"], ctx["ids"], ctx["fits"]
    both, actions = scores["both"], scores["actions_only"]
    return {
        "counts": class_counts(labels),
        "both_minus_actions_only": contrast(both, actions, labels, games),
        "both_vs_0.5": contrast(both, np.zeros(len(both)), labels, games),
        "scorers": {n: scorer_block(s, labels, games) for n, s in scores.items()},
        "rules": {n: scorer_block(s, labels, games) for n, s in rules.items()},
        "deployment": {
            n: deployment(scores[n], labels, games, ids, fits[n])
            for n in ("both", "actions_only")
            if n in fits
        },
    }


def controls(scores: dict[str, np.ndarray], labels: np.ndarray, ctx: dict) -> dict:
    """Section 8 bands on the oracle and empty views, when they were scored."""
    out = {}
    if "oracle" in scores and "oracle" in ctx["fits"]:
        dep = deployment(scores["oracle"], labels, ctx["games"], ctx["ids"], ctx["fits"]["oracle"])
        auroc = metrics.auroc(scores["oracle"], labels)
        out["oracle"] = {
            "recall": dep["recall"],
            "auroc": auroc,
            "pass": dep["recall"] >= analysis.ORACLE_RECALL and auroc >= analysis.ORACLE_AUROC,
        }
    if "empty" in scores:
        auroc = metrics.auroc(scores["empty"], labels)
        low, high = analysis.EMPTY_BAND
        out["empty"] = {"auroc": auroc, "pass": low <= auroc <= high}
    return out


def round0_report(logs: dict[str, dict]) -> dict:
    """Round-0 break rates and rule AUROCs under both labels (no monitor scoring)."""
    cases = []
    for source, log in logs.items():
        cases += fishing.fishing_cases(log, source, rounds=range(1))
    la = np.array([c["label"] for c in cases], bool)
    lb = np.array([c["label_over"] for c in cases], bool)
    games = [c["game"] for c in cases]
    rules = rule_arrays(cases, logs)
    return {
        "n": len(cases),
        "break_rate_a": float(la.mean()),
        "break_rate_b": float(lb.mean()),
        "rules": {
            n: {
                "auroc_a": metrics.auroc(s, la),
                "auroc_b": metrics.auroc(s, lb),
                "n_positive_b": int(lb.sum()),
                "n_negative_b": int((~lb).sum()),
            }
            for n, s in rules.items()
        },
        "n_games": len(set(games)),
    }


def rule_arrays(cases: list[dict], logs: dict[str, dict]) -> dict[str, np.ndarray]:
    """Return R1, R2, R12 and R3 for every case."""
    vals = [
        fishing.rule_scores(logs[c["source"]], c["trial"], c["round"], c["agent"]) for c in cases
    ]
    return {n: np.array([v[n] for v in vals], float) for n in fishing.RULE_NAMES}


def analyze(
    cases: list[dict],
    rows_by_view: dict[str, dict[str, dict]],
    logs: dict[str, dict],
    fits: dict[str, dict],
) -> dict:
    """Build the Fishing tables from cases, score rows by view, the raw logs and frozen fits."""
    ids = [scoring.case_id(c) for c in cases]
    games = [c["game"] for c in cases]
    labels_a = np.array([c["label"] for c in cases], bool)
    labels_b = np.array([c["label_over"] for c in cases], bool)
    scores = {v: analysis.arrays(rows, ids)[0] for v, rows in rows_by_view.items()}
    failures = {v: analysis.arrays(rows, ids)[1] for v, rows in rows_by_view.items()}
    rules = rule_arrays(cases, logs)
    ctx = {"games": games, "ids": ids, "fits": fits}
    return {
        "n_cases": len(cases),
        "n_games": len(set(games)),
        "outcome_counts": {
            "over_take": int(labels_b.sum()),
            "under_take": int((labels_a & ~labels_b).sum()),
            "unchanged": int((~labels_a).sum()),
        },
        "parse_failures": failures,
        LABELS[0]: label_block(labels_a, scores, rules, ctx),
        LABELS[1]: label_block(labels_b, scores, rules, ctx),
        "controls": controls(scores, labels_a, ctx),
        "round0": round0_report(logs),
    }
