"""Tests for the by-break-type AUROC table."""

import json

import pytest
from scripts import break_type_auroc as bt

EXPECTED = {
    "test": {"premeditated_deception": (98, 0.547), "impulsive_deviation": (260, 0.696)},
    "replication": {"premeditated_deception": (139, 0.579), "impulsive_deviation": (237, 0.720)},
}


def row(score: float, *, label: bool) -> dict:
    """Build one score row."""
    return {"label": label, "game": "g", "score": score, "parse_ok": True}


def test_by_type_hand_computed_with_ties() -> None:
    """Impulsive 3 and 2 against keeps 2, 1, 3 give 4/6; premeditated 1 gives 0.5/3."""
    rows = {
        "i1": row(3, label=True),
        "i2": row(2, label=True),
        "p1": row(1, label=True),
        "o1": row(9, label=True),
        "k1": row(2, label=False),
        "k2": row(1, label=False),
        "k3": row(3, label=False),
    }
    typology = {
        "i1": "impulsive_deviation",
        "i2": "impulsive_deviation",
        "p1": "premeditated_deception",
        "o1": "other",
    }
    got = bt.by_type(rows, typology)
    assert got["impulsive_deviation"] == {"n": 2, "n_keep": 3, "auroc": pytest.approx(4 / 6)}
    assert got["premeditated_deception"] == {"n": 1, "n_keep": 3, "auroc": pytest.approx(0.5 / 3)}


def test_committed_json_matches_fresh_run() -> None:
    """The committed file equals a fresh recomputation and the expected anchors."""
    committed = json.loads(bt.DEFAULT_OUT.read_text(encoding="utf-8"))
    assert committed == json.loads(json.dumps(bt.build()))
    for split, kinds in EXPECTED.items():
        for kind, (n, auroc) in kinds.items():
            assert committed[split][kind]["n"] == n
            assert committed[split][kind]["auroc"] == pytest.approx(auroc, abs=5e-4)
