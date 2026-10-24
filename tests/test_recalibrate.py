"""Tests for scripts/recalibrate_replication.py on synthetic data."""

import json
from pathlib import Path

import numpy as np
import pytest
from scripts import recalibrate_replication as recal

from sprint2p2 import analysis, splits, views

BREAKS_PER_GAME = 4


def make_rows(shift: int) -> dict:
    """20 games x 10 cases; breaks score about 70, keeps about 30, plus a per-case wobble."""
    rng = np.random.default_rng(5)
    rows = {}
    for g in range(20):
        for k in range(10):
            label = k < BREAKS_PER_GAME
            rid = f"rep|{g}|1|A{k}"
            rows[rid] = {
                "id": rid,
                "trial": g,
                "game": f"rep:{g}",
                "label": label,
                "score": float(int(rng.integers(0, 20)) + (70 if label else 30) + shift),
                "parse_ok": True,
            }
    return rows


def test_refit_uses_trials_0_to_9_and_applies_to_10_to_19() -> None:
    """The refit threshold equals fit_all on trials 0-9 only; the applied set is trials 10-19."""
    rows = {v: make_rows(0) for v in views.VIEWS}
    frozen = {v: {"t": 1000.0, "q": 0.0} for v in views.VIEWS}
    res = recal.recalibrate(rows, frozen)
    expected = analysis.fit_all({"both": recal.subset(rows["both"], recal.FIT_TRIALS)})["both"]
    assert res["both"]["refit_on_trials_0_to_9"] == expected
    assert res["both"]["trials_10_to_19"]["n"] == 100  # noqa: PLR2004
    assert res["both"]["frozen_fit"] == frozen["both"]


def test_frozen_threshold_far_too_high_flags_nothing_and_refit_hits_target() -> None:
    """A frozen t above every score gives recall 0 and FPR 0; the refit lands near 10% FPR."""
    rows = {v: make_rows(0) for v in views.VIEWS}
    frozen = {v: {"t": 1000.0, "q": 0.0} for v in views.VIEWS}
    held = recal.recalibrate(rows, frozen)["both"]["trials_10_to_19"]
    assert (held["frozen"]["recall"], held["frozen"]["fpr"]) == (0.0, 0.0)
    assert held["refit"]["recall"] == pytest.approx(1.0)
    assert held["refit"]["fpr"] == pytest.approx(0.0, abs=0.15)
    assert 0.0 <= held["refit"]["fpr_expected"] <= 0.25  # noqa: PLR2004


def test_script_refused_without_amendment_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """main() raises the gate error while amendment1_url is missing."""
    frozen = tmp_path / "frozen.json"
    frozen.write_text(json.dumps({"prereg_commit": "a", "osf_url": "b"}))
    monkeypatch.setattr(splits, "FROZEN", frozen)
    with pytest.raises(splits.GateError):
        recal.main(["--out", str(tmp_path / "x.json")])
