"""Tests for the DEV-ONLY PRACTICE scorer and analysis (rank averages)."""

import numpy as np
import pytest
from scripts import analyze_practice, score_practice

from sprint2p2 import combine, monitor, scoring
from tests.test_data import make_log


@pytest.mark.parametrize(
    "split", ["test", "threshold", "replication", "fishing_test", "fishing_dev", "main"]
)
def test_every_split_but_dev_is_refused(split: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """The scorer refuses non-dev splits before reading any key or calling any API."""

    def boom() -> str:
        msg = "read_key must not be reached"
        raise AssertionError(msg)

    monkeypatch.setattr(score_practice, "read_key", boom)
    with pytest.raises(score_practice.PracticeError):
        score_practice.require_dev(split)
    with pytest.raises(score_practice.PracticeError):
        score_practice.main(["--model", "gemini", "--split", split, "--views", "both"])
    score_practice.require_dev("dev")


def fake_post(_payload: dict) -> dict:
    """Return a valid monitor reply."""
    return {
        "model": "fake/model",
        "choices": [{"message": {"content": '{"probability": 40, "reason": "r"}'}}],
        "usage": {
            "prompt_tokens": 5,
            "completion_tokens": 3,
            "completion_tokens_details": {"reasoning_tokens": 1},
        },
    }


def test_rows_are_tagged_practice() -> None:
    """Rows carry the practice tag; the practice configs match the main one except the model."""
    case = {
        "split": "dev",
        "source": "pilot",
        "game": "pilot:0",
        "trial": 0,
        "round": 1,
        "agent": "J",
        "label": False,
    }
    cfg = monitor.load_config(score_practice.ROOT / "configs" / "monitor_practice_gemini.json")
    runner = scoring.Runner({"pilot": make_log(1)}, cfg, fake_post)
    row = score_practice.score_one(case, "both", runner)
    assert row["tag"] == "DEV-ONLY PRACTICE"
    base = monitor.load_config(score_practice.ROOT / "configs" / "monitor.json")
    assert cfg.model == "google/gemini-3.8-flash"
    assert (cfg.template, cfg.reasoning, cfg.max_tokens, cfg.temperature, cfg.scale) == (
        base.template,
        base.reasoning,
        base.max_tokens,
        base.temperature,
        base.scale,
    )
    sonnet = monitor.load_config(score_practice.ROOT / "configs" / "monitor_practice_sonnet.json")
    assert sonnet.model == "anthropic/claude-sonnet-5.5"


def test_rank_average_hand_computed() -> None:
    """Opposite orderings average to a flat 2,2,2; ties use average ranks; the AUROC is 0.5."""
    a, b = np.array([1.0, 2.0, 3.0]), np.array([3.0, 2.0, 1.0])
    assert combine.combo_scores(a, b).tolist() == pytest.approx([2.0, 2.0, 2.0])
    labels = np.array([True, False, True])
    assert combine.combo_auroc(a, b, labels) == pytest.approx(0.5)
    tied = combine.combo_scores(np.array([1.0, 1.0, 2.0]), np.array([3.0, 1.0, 1.0]))
    assert tied.tolist() == pytest.approx([2.25, 1.5, 2.25])


def test_rank_average_block_reports_parts() -> None:
    """The block gives the average's AUROC, each part's, and differences with per-game means."""
    labels = np.array([True, False, True, False])
    games = ["g1", "g1", "g2", "g2"]
    perfect, constant = labels.astype(float), np.zeros(4)
    out = analyze_practice.rank_average_block(perfect, constant, labels, games, n_boot=100)
    assert out["average_auroc"] == pytest.approx(1.0)
    assert out["part_a_auroc"] == pytest.approx(1.0)
    assert out["part_b_auroc"] == pytest.approx(0.5)
    assert out["minus_a"]["diff"] == pytest.approx(0.0)
    assert out["minus_b"]["diff"] == pytest.approx(0.5)
    assert out["minus_b"]["mean_of_per_game_differences"] == pytest.approx(0.5)
