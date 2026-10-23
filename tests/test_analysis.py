"""Tests for sprint2p2.analysis on synthetic score files."""

import random

import numpy as np

from sprint2p2 import analysis, baselines, views

N_GAMES = 6
PER_GAME = 12


def make_rows(signal: float, seed: int, *, fail_every: int = 0) -> dict:
    """Make score rows whose scores track the label with the given strength."""
    rng = random.Random(seed)  # noqa: S311
    rows = {}
    for g in range(N_GAMES):
        for i in range(PER_GAME):
            label = i % 2 == 0
            rid = f"main|{g}|1|A{i}"
            ok = not (fail_every and i % fail_every == 1 and g == 0)
            rows[rid] = {
                "id": rid,
                "game": f"main:{g}",
                "label": label,
                "score": round(signal * label * 50 + rng.random() * 50),
                "parse_ok": ok,
            }
    return rows


def all_scorers() -> dict:
    """Build a full set of scorer names."""
    names = [*views.VIEWS, *baselines.BASELINES]
    return {n: make_rows(0.5 if n in ("both", "oracle") else 0.1, i) for i, n in enumerate(names)}


def test_analyze_structure_and_holm() -> None:
    """All tables are present and Holm-adjusted p is at least the raw p."""
    rows = all_scorers()
    tables = analysis.analyze(rows, rows, "DEV-ONLY")
    assert tables["tag"] == "DEV-ONLY"
    assert set(tables["secondary"]) == {"S1", "S2", "S3"}
    for entry in tables["secondary"].values():
        assert entry["p_holm"] >= entry["p_one_sided"]
    assert set(tables["controls"]) == {"oracle", "empty", "round_only"}
    assert set(tables["baselines"]) == set(baselines.BASELINES)
    assert tables["primary"]["auroc_test"] > tables["primary"]["vs_comparator"]["diff"]
    assert 0 <= tables["primary"]["fpr_achieved"] <= 1


def test_parse_failures_are_counted_and_lowest() -> None:
    """A parse failure is scored below every real score and counted."""
    rows = make_rows(0.5, 1, fail_every=2)
    ids = sorted(rows)
    scores, failures = analysis.arrays(rows, ids)
    assert failures == sum(not r["parse_ok"] for r in rows.values())
    assert failures > 0
    assert np.min(scores) == analysis.MISSING


def test_canonical_and_hash_are_stable() -> None:
    """Rounding makes the hash insensitive to float noise past 6 places."""
    a = analysis.canonical({"x": 0.12345671, "y": [1.0]})
    b = analysis.canonical({"y": [1.0], "x": 0.12345672})
    assert a == b
    assert analysis.sha256(a) == analysis.sha256(b)
    assert len(analysis.sha256(a)) == 64  # noqa: PLR2004


def test_primary_only_matches_full_analysis() -> None:
    """The reproduce path gives the same primary row as the full analysis."""
    rows = all_scorers()
    full = analysis.analyze(rows, rows, "DEV-ONLY")["primary"]
    only = analysis.primary_only(rows, rows, "DEV-ONLY")
    assert analysis.canonical({k: v for k, v in only.items() if k != "tag"}) == analysis.canonical(
        full
    )
