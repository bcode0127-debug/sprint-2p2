"""Tests for sprint2p2.splits and the scoring gate."""

import json
from pathlib import Path

import pytest

from sprint2p2 import splits

DEV_N = 585
THRESHOLD_N = 450
TEST_N = 900
ROUND0_DEV_N = 65


@pytest.fixture(scope="module")
def logs() -> dict:
    """Load the committed raw logs."""
    return splits.load_logs()


def test_split_sizes(logs: dict) -> None:
    """Rounds 1 to 9: dev 585, threshold 450, test 900 (nulls excluded)."""
    assert len(splits.split_cases(logs, "dev")) == DEV_N
    assert len(splits.split_cases(logs, "threshold")) == THRESHOLD_N
    assert len(splits.split_cases(logs, "test")) == TEST_N


def test_split_trials_are_disjoint(logs: dict) -> None:
    """Threshold is main trials 10 to 19 and test is 20 to 39."""
    thr = {c["trial"] for c in splits.split_cases(logs, "threshold")}
    tst = {c["trial"] for c in splits.split_cases(logs, "test")}
    dev_main = {c["trial"] for c in splits.split_cases(logs, "dev") if c["source"] == "main"}
    assert thr == set(range(10, 20))
    assert tst == set(range(20, 40))
    assert dev_main == set(range(10))


def test_round_zero_is_separate(logs: dict) -> None:
    """Round 0 appears only in the separate set."""
    assert {c["round"] for c in splits.split_cases(logs, "dev")} == set(range(1, 10))
    zero = splits.split_cases(logs, "dev", round_zero=True)
    assert {c["round"] for c in zero} == {0}
    assert len(zero) == ROUND0_DEV_N


def write_frozen(path: Path, body: object) -> Path:
    """Write a freeze file."""
    path.write_text(json.dumps(body))
    return path


def test_gate_blocks_without_freeze(tmp_path: Path) -> None:
    """Threshold and test are blocked when the freeze file is missing or incomplete."""
    missing = tmp_path / "frozen.json"
    for split in ("threshold", "test"):
        with pytest.raises(splits.GateError):
            splits.check_gate(split, missing)
    for body in (
        {"prereg_commit": "abc"},
        {"prereg_commit": "", "osf_url": "https://osf.io/x"},
        {"prereg_commit": "abc", "osf_url": "  "},
        [],
    ):
        path = write_frozen(tmp_path / "f.json", body)
        with pytest.raises(splits.GateError):
            splits.check_gate("test", path)
    (tmp_path / "bad.json").write_text("{not json")
    with pytest.raises(splits.GateError):
        splits.check_gate("threshold", tmp_path / "bad.json")


def test_gate_opens_with_freeze_and_never_blocks_dev(tmp_path: Path) -> None:
    """A complete freeze file opens the gate; dev is never gated."""
    path = write_frozen(
        tmp_path / "f.json", {"prereg_commit": "abc", "osf_url": "https://osf.io/x"}
    )
    splits.check_gate("test", path)
    splits.check_gate("dev", tmp_path / "absent.json")


def test_guard_case_uses_raw_identity(tmp_path: Path) -> None:
    """A held-out main trial is gated even if labelled dev."""
    absent = tmp_path / "absent.json"
    splits.guard_case({"source": "pilot", "trial": 2, "split": "dev"}, absent)
    splits.guard_case({"source": "main", "trial": 9, "split": "dev"}, absent)
    with pytest.raises(splits.GateError):
        splits.guard_case({"source": "main", "trial": 10, "split": "dev"}, absent)
    with pytest.raises(splits.GateError):
        splits.guard_case({"source": "main", "trial": 25, "split": "test"}, absent)
