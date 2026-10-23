"""Tests for sprint2p2.data and sprint2p2.rules."""

import json
from pathlib import Path

import pytest

from sprint2p2 import data, rules

NAMES = ["J", "M", "Q", "T", "Z"]
MAX_TRIAL = 10


def agent(stated: str | None, choice: str | None) -> dict:
    """Build a minimal agent record."""
    return {
        "stage2": {"stated_action": stated, "message": "m"},
        "stage3": {"choice": choice},
    }


def make_log(n_trials: int = MAX_TRIAL + 2) -> dict:
    """Build a log with trials 0..n_trials-1 and 3 rounds."""
    rounds = []
    for rid in range(3):
        trials = []
        for tid in range(n_trials):
            agents = {n: agent("GO", "GO" if rid == 0 else "STAY") for n in NAMES}
            agents["M"] = agent("STAY", "GO")
            choices = {n: a["stage3"]["choice"] for n, a in agents.items()}
            trials.append(
                {
                    "trial_id": tid,
                    "agents": agents,
                    "announcement_order": NAMES,
                    "outcomes": {"choices": choices},
                },
            )
        rounds.append({"round_id": rid, "trials": trials})
    return {"rounds": rounds}


def test_loader_rejects_held_out_trial() -> None:
    """Requesting main-run trial 10 or above raises."""
    log = make_log()
    with pytest.raises(ValueError, match="held out"):
        data.dev_cases(log, "main", trials=[9, 10])
    with pytest.raises(ValueError, match="held out"):
        data.dev_cases(log, "main", trials=[25])


def test_dev_log_drops_held_out_trials(tmp_path: Path) -> None:
    """The main-run loader never returns trial 10 or above."""
    path = tmp_path / "main.json"
    path.write_text(json.dumps(make_log()))
    log = data.dev_log(path, "main")
    ids = {t["trial_id"] for rnd in log["rounds"] for t in rnd["trials"]}
    assert max(ids) == data.DEV_MAX_MAIN_TRIAL
    cases = data.dev_cases(log, "main")
    assert max(c["trial"] for c in cases) == data.DEV_MAX_MAIN_TRIAL
    assert {c["round"] for c in cases} == {1, 2}


def test_pilot_source_is_not_trial_limited() -> None:
    """The limit applies to the main run only."""
    assert data.dev_cases(make_log(), "pilot", trials=[11])


def test_rules() -> None:
    """Pressure, broke-last-round and last-round-crowded on a known log."""
    log = make_log(1)
    assert rules.pressure(log, 0, 1, "J") == len(NAMES) - 2
    assert rules.pressure(log, 0, 1, "M") == 0
    assert rules.broke_last_round(log, 0, 1, "M") == 1
    assert rules.broke_last_round(log, 0, 1, "J") == 0
    assert rules.last_round_crowded(log, 0, 1) == 1
    assert rules.last_round_crowded(log, 0, 2) == 0
