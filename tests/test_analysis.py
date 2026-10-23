"""Tests for sprint2p2.analysis and scripts.analyze on synthetic score files."""

import json
import random
from pathlib import Path

import numpy as np
import pytest
from scripts import analyze

from sprint2p2 import analysis, baselines, splits, views

N_GAMES = 6
PER_GAME = 12


def make_rows(signal: float, seed: int, *, fail_every: int = 0) -> dict:
    """Make score rows whose scores track the label with the given strength."""
    rng = random.Random(seed)  # noqa: S311
    rows = {}
    for g in range(N_GAMES):
        for i in range(PER_GAME):
            label = i % 2 == 0
            rid = f"main|{g}|1|A{i % 5}x{i}"
            ok = not (fail_every and i % fail_every == 1 and g == 0)
            rows[rid] = {
                "id": rid,
                "game": f"main:{g}",
                "agent": f"A{i % 5}",
                "label": label,
                "score": round(signal * label * 50 + rng.random() * 50),
                "parse_ok": ok,
            }
    return rows


STRONG = ("both", "oracle")


def all_scorers() -> dict:
    """Build a full set of scorer names; both and oracle are informative."""
    names = [*views.VIEWS, *baselines.BASELINES]
    return {n: make_rows(0.8 if n in STRONG else 0.05, i) for i, n in enumerate(names)}


def test_analyze_tables_follow_v2() -> None:
    """Primary is both vs actions_only; S1 to S3 follow v2 and carry Holm values."""
    rows = all_scorers()
    t = analysis.analyze(rows, rows, "DEV-ONLY")
    assert (t["primary"]["a"], t["primary"]["b"]) == ("both", "actions_only")
    assert t["primary"]["success"] is (t["primary"]["lower_95_one_sided"] > 0)
    assert t["primary"]["diff"] > 0
    assert {k: (v["a"], v["b"]) for k, v in t["secondary"].items()} == {
        "S1": ("both", "own_only"),
        "S2": ("both", "freshness"),
        "S3": ("both", "counting"),
    }
    for entry in t["secondary"].values():
        assert entry["p_holm"] >= entry["p_one_sided"]
    assert set(t["deployment_reading"]) == set(analysis.SCORERS)
    assert t["tag"] == "DEV-ONLY"


def test_controls_pass_fail_per_section_8() -> None:
    """Oracle and empty carry pass or fail from the stated bands."""
    rows = all_scorers()
    rows["oracle"] = {k: {**v, "score": 100 * v["label"]} for k, v in rows["oracle"].items()}
    rows["empty"] = make_rows(0.0, 99)
    c = analysis.analyze(rows, rows, "DEV-ONLY")["controls"]
    assert c["oracle"]["pass"] is True
    assert c["empty"]["pass"] is True
    rows["empty"] = make_rows(0.8, 98)
    assert analysis.analyze(rows, rows, "DEV-ONLY")["controls"]["empty"]["pass"] is False


def test_power_table_uses_058_factor() -> None:
    """Minimum detectable difference is 0.58 times the between-game SD."""
    rows = all_scorers()
    power = analysis.analyze(rows, rows, "DEV-ONLY")["power"]["primary"]["auroc"]
    assert power["min_detectable_difference_20_games"] == pytest.approx(
        0.58 * power["between_game_sd"],
    )
    assert power["n_games_used"] == N_GAMES


def test_parse_failures_are_counted_and_lowest() -> None:
    """A parse failure is scored below every real score and counted."""
    rows = make_rows(0.5, 1, fail_every=2)
    scores, failures = analysis.arrays(rows, sorted(rows))
    assert failures == sum(not r["parse_ok"] for r in rows.values())
    assert failures > 0
    assert np.min(scores) == analysis.MISSING


def test_canonical_and_hash_are_stable() -> None:
    """Rounding makes the hash insensitive to float noise past 6 places."""
    a = analysis.canonical({"x": 0.12345671, "y": [1.0]})
    b = analysis.canonical({"y": [1.0], "x": 0.12345672})
    assert a == b
    assert len(analysis.sha256(a)) == 64  # noqa: PLR2004


def test_primary_only_matches_full_analysis() -> None:
    """The reproduce path gives the same primary numbers as the full analysis."""
    rows = all_scorers()
    full = analysis.analyze(rows, rows, "DEV-ONLY")["primary"]
    only = analysis.primary_only(rows, "DEV-ONLY", analysis.fit_all(rows))
    for key in ("diff", "lower_95_one_sided", "p_one_sided", "success"):
        assert only[key] == full[key]


def test_analyze_refuses_without_freeze(tmp_path: Path) -> None:
    """The threshold and test splits are refused unless configs/frozen.json exists."""
    with pytest.raises(splits.GateError):
        analyze.require_frozen(tmp_path / "frozen.json")
    present = tmp_path / "frozen.json"
    present.write_text(json.dumps({"prereg_commit": "abc"}))
    assert analyze.require_frozen(present) == {"prereg_commit": "abc"}


def test_analyze_main_refuses_without_freeze(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() without --dev-only raises before reading any score file."""
    monkeypatch.setattr(splits, "FROZEN", Path("/nonexistent/frozen.json"))
    with pytest.raises(splits.GateError):
        analyze.main([])


def test_frozen_fits_requires_every_scorer() -> None:
    """Missing thresholds are an error, not a silent refit."""
    with pytest.raises(splits.GateError):
        analyze.frozen_fits({"thresholds": {"both": {"t": 1, "q": 0}}})
    full = {n: {"t": 1.0, "q": 0.0} for n in analysis.SCORERS}
    assert set(analyze.frozen_fits({"thresholds": full})) == set(analysis.SCORERS)
