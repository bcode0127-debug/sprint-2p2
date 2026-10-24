"""Tests for the Fishing scoring gate and analysis (Amendment 1, section 4)."""

import json
from pathlib import Path

import numpy as np
import pytest
from scripts import analyze_fishing, score_fishing

from sprint2p2 import fishing, fishing_analysis, scoring, splits, views

ROOT = Path(__file__).resolve().parent.parent
NAMES = ["J", "M", "Q", "T", "Z"]
STATED = [3, 2, 3, 3, 3]
CHOICES = [[3, 2, 3, 3, 3], [5, 2, 3, 3, 3], [1, 2, 3, 3, 3]]


def clean_log(n_trials: int = 2) -> dict:
    """Build a 3-round Fishing log with plain integers: round 1 over-take, round 2 under-take."""
    rounds = []
    for rid, choice in enumerate(CHOICES):
        trials = []
        for tid in range(n_trials):
            agents = {
                n: {
                    "stage2": {"stated_action": s, "message": "m"},
                    "stage3": {"choice": c},
                }
                for n, s, c in zip(NAMES, STATED, choice, strict=True)
            }
            trials.append(
                {
                    "trial_id": tid,
                    "agents": agents,
                    "announcement_order": NAMES,
                    "outcomes": {"choices": dict(zip(NAMES, choice, strict=True))},
                },
            )
        rounds.append({"round_id": rid, "trials": trials})
    return {"rounds": rounds}


def write_frozen(path: Path, *, amendment: str = "") -> Path:
    """Write a freeze file that is complete except, optionally, for amendment1_url."""
    body = {
        "prereg_commit": "abc",
        "osf_url": "https://osf.io/x",
        "thresholds": {v: {"t": 1.0, "q": 0.5} for v in views.VIEWS},
    }
    if amendment:
        body["amendment1_url"] = amendment
    path.write_text(json.dumps(body))
    return path


def test_fishing_test_refused_without_amendment_url(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """score_fishing and analyze_fishing both refuse fishing_test while amendment1_url is empty."""
    monkeypatch.setattr(splits, "FROZEN", write_frozen(tmp_path / "f.json"))
    with pytest.raises(splits.GateError, match="amendment1_url"):
        score_fishing.load_inputs("fishing_test")
    with pytest.raises(splits.GateError, match="amendment1_url"):
        analyze_fishing.run_test(tmp_path / "out")


def test_fishing_test_refused_unless_both_batch_logs_exist(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """With the gate open, a missing batch log still blocks scoring; both present is accepted."""
    monkeypatch.setattr(splits, "FROZEN", write_frozen(tmp_path / "f.json", amendment="https://x"))
    paths = {"fishtestA": tmp_path / "a.json", "fishtestB": tmp_path / "b.json"}
    monkeypatch.setattr(splits, "FISHING_TEST_RAW", paths)
    with pytest.raises(splits.GateError, match="fishtestA, fishtestB"):
        score_fishing.load_inputs("fishing_test")
    paths["fishtestA"].write_text(json.dumps(clean_log()))
    with pytest.raises(splits.GateError, match="fishtestB"):
        score_fishing.load_inputs("fishing_test")
    paths["fishtestB"].write_text(json.dumps(clean_log()))
    logs, cases = score_fishing.load_inputs("fishing_test")
    assert set(logs) == {"fishtestA", "fishtestB"}
    assert {c["split"] for c in cases} == {"fishing_test"}
    assert {c["source"] for c in cases} == {"fishtestA", "fishtestB"}


def test_dev_split_needs_no_gate() -> None:
    """The development Fishing pilot loads without any freeze file entry."""
    logs, cases = score_fishing.load_inputs("fishing_dev")
    assert set(logs) == {"fishpilot"}
    assert len(cases) == 135  # noqa: PLR2004


def rows_for(cases: list[dict], scores: list[int]) -> dict:
    """Make score rows for the cases."""
    return {
        scoring.case_id(c): {"score": s, "parse_ok": True, "label": c["label"], "game": c["game"]}
        for c, s in zip(cases, scores, strict=True)
    }


def test_analysis_counts_labels_and_per_game_means() -> None:
    """Hand-computed: counts, class counts under label (b), and a per-game mean beside each diff."""
    log = clean_log(2)
    cases = fishing.fishing_cases(log, "fishpilot")
    assert len(cases) == 2 * 2 * 5
    labels_b = [c["label_over"] for c in cases]
    both = rows_for(cases, [90 if b else 10 for b in labels_b])
    actions = rows_for(cases, [50] * len(cases))
    out = fishing_analysis.analyze(
        cases,
        {"both": both, "actions_only": actions},
        {"fishpilot": log},
        {},
    )
    assert out["outcome_counts"] == {"over_take": 2, "under_take": 2, "unchanged": 16}
    b = out["label_b_over_take_only"]
    assert (b["counts"]["n_positive"], b["counts"]["n_negative"]) == (2, 18)
    for name, block in {**b["scorers"], **b["rules"]}.items():
        assert block["n_positive"] + block["n_negative"] == 20, name  # noqa: PLR2004
    contrast = b["both_minus_actions_only"]
    assert contrast["diff"] == pytest.approx(0.5)
    assert contrast["mean_of_per_game_differences"] == pytest.approx(0.5)
    assert contrast["per_game_differences"].keys() == {"fishpilot:0", "fishpilot:1"}
    a = out["label_a_any_change"]["both_minus_actions_only"]
    assert "mean_of_per_game_differences" in a
    assert a["n_positive"] == 4  # noqa: PLR2004


def test_rule_arrays_exclude_r4() -> None:
    """Only R1, R2, R12 and R3 exist; R4 was dropped by the final amendment text."""
    assert fishing.RULE_NAMES == ("R1", "R2", "R12", "R3")
    rules = fishing.rule_scores(clean_log(1), 0, 1, "J")
    assert set(rules) == {"R1", "R2", "R12", "R3"}


def test_dev_only_reproduces_the_pilot_and_writes_only_to_its_own_folder(tmp_path: Path) -> None:
    """Reproduces the pilot numbers and writes nothing outside its own folder."""
    tables_dir = ROOT / "results" / "tables"
    before = sorted(p.name for p in tables_dir.iterdir())
    analyze_fishing.run_dev(tmp_path)
    assert sorted(p.name for p in tables_dir.iterdir()) == before
    assert analyze_fishing.DEV_OUT.name == "DEV-ONLY-fishing"
    got = json.loads((tmp_path / "tables.json").read_text())
    pilot = json.loads((ROOT / "results" / "fishing_pilot_dev.json").read_text())
    a = got["label_a_any_change"]
    assert got["tag"] == "DEV-ONLY"
    assert round(a["scorers"]["both"]["auroc"], 3) == 0.579  # noqa: PLR2004
    assert round(a["scorers"]["actions_only"]["auroc"], 3) == 0.531  # noqa: PLR2004
    assert round(a["both_minus_actions_only"]["diff"], 3) == 0.049  # noqa: PLR2004
    assert round(a["both_minus_actions_only"]["mean_of_per_game_differences"], 3) == 0.014  # noqa: PLR2004
    for name in ("both", "actions_only", "R1", "R2", "R12", "R3"):
        group = "scorers" if name in ("both", "actions_only") else "rules"
        assert a[group][name]["auroc"] == pytest.approx(pilot["scorers"][name]["auroc_a"], abs=1e-6)
        b = got["label_b_over_take_only"][group][name]
        assert b["auroc"] == pytest.approx(pilot["scorers"][name]["auroc_b"], abs=1e-6)
        assert (b["n_positive"], b["n_negative"]) == (16, 119)
    assert a["both_minus_actions_only"]["diff"] == pytest.approx(
        pilot["contrast_both_minus_actions_only"]["diff"],
        abs=1e-6,
    )
    assert not np.isnan(a["deployment"]["both"]["recall"])
