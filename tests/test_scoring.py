"""Tests for sprint2p2.scoring, including the gate on the scoring path."""

from pathlib import Path

import pytest

from sprint2p2 import monitor, scoring, splits
from tests.test_data import make_log

CFG = monitor.load_config()


def case(source: str, trial: int, split: str) -> dict:
    """Build a case on the fake log."""
    return {
        "split": split,
        "source": source,
        "game": f"{source}:{trial}",
        "trial": trial,
        "round": 1,
        "agent": "J",
        "label": False,
    }


def fake_post(_payload: dict) -> dict:
    """Return a fixed valid monitor reply."""
    return {
        "model": "fake/model",
        "choices": [{"message": {"content": '{"probability": 42, "reason": "r"}'}}],
        "usage": {
            "prompt_tokens": 7,
            "completion_tokens": 3,
            "completion_tokens_details": {"reasoning_tokens": 1},
        },
    }


def test_dev_case_scores_and_logs_fields(tmp_path: Path) -> None:
    """A dev case is scored and the row logs model, tokens and reasoning tokens."""
    logs = {"pilot": make_log(3)}
    row = scoring.score_case(
        case("pilot", 2, "dev"),
        "both",
        scoring.Runner(logs, CFG, fake_post),
        tmp_path / "f",
    )
    assert row["score"] == 42  # noqa: PLR2004
    assert row["models"] == ["fake/model"]
    assert (row["prompt_tokens"], row["completion_tokens"], row["reasoning_tokens"]) == (7, 3, 1)
    assert row["tag"] == "DEV-ONLY"


def test_held_out_case_is_refused_before_any_call(tmp_path: Path) -> None:
    """Threshold and test cases raise and never reach the monitor without a freeze."""
    calls: list[dict] = []

    def spy(payload: dict) -> dict:
        calls.append(payload)
        return fake_post(payload)

    logs = {"main": make_log(25)}
    for trial, split in ((12, "threshold"), (22, "test"), (22, "dev")):
        with pytest.raises(splits.GateError):
            scoring.score_case(
                case("main", trial, split),
                "both",
                scoring.Runner(logs, CFG, spy),
                tmp_path / "f",
            )
    assert calls == []


def test_sample_balanced_is_reproducible() -> None:
    """A balanced sample has equal classes and is stable across calls."""
    cases = [{**case("pilot", i, "dev"), "label": i % 2 == 0, "agent": "J"} for i in range(40)]
    a = scoring.sample_balanced(cases, 10)
    assert a == scoring.sample_balanced(cases, 10)
    assert sum(c["label"] for c in a) == 5  # noqa: PLR2004
    assert len(a) == 10  # noqa: PLR2004
