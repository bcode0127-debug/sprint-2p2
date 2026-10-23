"""Turn score files into the result tables."""

import hashlib
import json

import numpy as np

from sprint2p2 import baselines, metrics, views

MISSING = -1.0
PRIMARY_VIEW = "both"
PRIMARY_COMPARATOR = "counting"
SECONDARY = {"S1": "actions_only", "S2": "messages_only", "S3": "structured"}
CONTROLS = ("oracle", "empty", "round_only")
ABLATIONS = ("own_only", "freshness")
ROUND_DP = 6

Rows = dict[str, dict]


def arrays(rows: Rows, ids: list[str]) -> tuple[np.ndarray, int]:
    """Return scores for the ids (parse failures get the lowest score) and the failure count."""
    scores, failures = [], 0
    for i in ids:
        row = rows[i]
        if row.get("parse_ok") and row.get("score") is not None:
            scores.append(float(row["score"]))
        else:
            scores.append(MISSING)
            failures += 1
    return np.array(scores), failures


def _labels_games(rows: Rows, ids: list[str]) -> tuple[np.ndarray, list[str]]:
    """Return labels and game ids for the ids."""
    return np.array([rows[i]["label"] for i in ids], dtype=bool), [rows[i]["game"] for i in ids]


def evaluate(thr: Rows, tst: Rows) -> dict:
    """Fit the randomized threshold on thr, apply it to tst and report AUROC and recall."""
    thr_ids, tst_ids = sorted(thr), sorted(tst)
    s_thr, _ = arrays(thr, thr_ids)
    s_tst, failures = arrays(tst, tst_ids)
    y_thr, _ = _labels_games(thr, thr_ids)
    y_tst, _ = _labels_games(tst, tst_ids)
    fit = metrics.randomized_threshold(s_thr, y_thr)
    applied = metrics.apply_threshold(s_tst, y_tst, tst_ids, fit)
    return {
        "auroc_test": metrics.auroc(s_tst, y_tst),
        "auroc_threshold_split": metrics.auroc(s_thr, y_thr),
        "threshold": fit,
        "recall": applied["recall"],
        "fpr_achieved": applied["fpr"],
        "recall_expected": applied["recall_expected"],
        "fpr_expected": applied["fpr_expected"],
        "parse_failures": failures,
        "n_test": len(tst_ids),
        "n_break": applied["n_break"],
        "n_keep": applied["n_keep"],
    }


def compare(tst_a: Rows, tst_b: Rows) -> dict:
    """Paired, game-clustered comparison of A against B on the test split."""
    ids = sorted(tst_a)
    a, _ = arrays(tst_a, ids)
    b, _ = arrays(tst_b, ids)
    labels, games = _labels_games(tst_a, ids)
    boot = metrics.paired_bootstrap(a, b, labels, games)
    boot["variance"] = metrics.paired_decomposition(a, b, labels, games)
    return boot


def analyze(thr: dict[str, Rows], tst: dict[str, Rows], tag: str) -> dict:
    """Build every table from score rows keyed by scorer name."""
    named = lambda names: [n for n in names if n in tst]  # noqa: E731
    primary = {
        "view": PRIMARY_VIEW,
        **evaluate(thr[PRIMARY_VIEW], tst[PRIMARY_VIEW]),
        "comparator": PRIMARY_COMPARATOR,
        "vs_comparator": compare(tst[PRIMARY_VIEW], tst[PRIMARY_COMPARATOR]),
    }
    secondary = {
        key: {
            "view": view,
            "vs": PRIMARY_VIEW,
            **compare(tst[PRIMARY_VIEW], tst[view]),
            **evaluate(thr[view], tst[view]),
        }
        for key, view in SECONDARY.items()
        if view in tst
    }
    adjusted = metrics.holm({k: v["p_one_sided"] for k, v in secondary.items()})
    for key, value in adjusted.items():
        secondary[key]["p_holm"] = value
    table = lambda names: {n: evaluate(thr[n], tst[n]) for n in named(names)}  # noqa: E731
    return {
        "tag": tag,
        "primary": primary,
        "secondary": secondary,
        "ablations": table(ABLATIONS),
        "controls": table(CONTROLS),
        "baselines": table(baselines.BASELINES),
        "views": table(views.VIEWS),
    }


def canonical(obj: object) -> str:
    """Serialise with sorted keys and rounded floats so hashes are stable."""

    def rnd(x: object) -> object:
        if isinstance(x, float):
            return round(x, ROUND_DP)
        if isinstance(x, dict):
            return {k: rnd(v) for k, v in x.items()}
        if isinstance(x, list):
            return [rnd(v) for v in x]
        return x

    return json.dumps(rnd(obj), sort_keys=True, indent=2)


def sha256(text: str) -> str:
    """Return the SHA-256 hex digest of a string."""
    return hashlib.sha256(text.encode()).hexdigest()


def primary_only(thr: dict[str, Rows], tst: dict[str, Rows], tag: str) -> dict:
    """Recompute just the primary row."""
    return {
        "tag": tag,
        "view": PRIMARY_VIEW,
        **evaluate(thr[PRIMARY_VIEW], tst[PRIMARY_VIEW]),
        "comparator": PRIMARY_COMPARATOR,
        "vs_comparator": compare(tst[PRIMARY_VIEW], tst[PRIMARY_COMPARATOR]),
    }
