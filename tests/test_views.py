"""Tests for sprint2p2.views."""

import re

import pytest

from sprint2p2 import views

SENTINEL = "LEAK_SENTINEL"
NAMES = ["J", "M", "Q", "T", "Z"]
LEAK_FIELDS = {
    "stage1": {"intended_action": SENTINEL, "reasoning": SENTINEL, "_parse_ok": True},
    "reflection": {"text": SENTINEL},
    "commitment_breaking": SENTINEL,
    "typology": SENTINEL,
    "judge": {"primary_label": SENTINEL},
}
LAST_ROUND = 3
GO_PATTERN = [
    ["GO", "GO", "STAY", "STAY", "STAY"],
    ["GO", "GO", "GO", "STAY", "STAY"],
    ["STAY", "STAY", "STAY", "STAY", "STAY"],
    ["GO", "STAY", "STAY", "STAY", "STAY"],
]


def make_log() -> dict:
    """Build a 4-round log; forbidden fields in every round, round-r choices too."""
    rounds = []
    for rid, acts in enumerate(GO_PATTERN):
        last = rid == LAST_ROUND
        agents = {}
        for name, act in zip(NAMES, acts, strict=True):
            agents[name] = {
                "stage2": {"stated_action": "GO", "message": f"msg {name} r{rid}"},
                "stage3": {"choice": SENTINEL if last else act},
                **LEAK_FIELDS,
            }
        choices = {n: (SENTINEL if last else a) for n, a in zip(NAMES, acts, strict=True)}
        trial = {
            "trial_id": 0,
            "agents": agents,
            "announcement_order": ["M", "J", "Q", "T", "Z"],
            "outcomes": {
                "choices": choices,
                "payoffs": dict.fromkeys(NAMES, SENTINEL),
                "description": SENTINEL,
            },
        }
        rounds.append({"round_id": rid, "trials": [trial]})
    return {"rounds": rounds}


def test_no_leak() -> None:
    """No forbidden field reaches the view, for every round and agent."""
    log = make_log()
    for r in range(len(GO_PATTERN)):
        for name in NAMES:
            assert SENTINEL not in views.build_both_view(log, 0, r, name)


def test_round_one_has_one_past_round() -> None:
    """Round 1 lists exactly round 0 as history."""
    text = views.build_both_view(make_log(), 0, 1, "J")
    assert len(re.findall(r"^Round \d+: ", text, flags=re.MULTILINE)) == 1
    assert "Round 0: J announced" in text


def test_position_and_order() -> None:
    """J speaks 2nd, and announcements follow speaking order."""
    text = views.build_both_view(make_log(), 0, 1, "J")
    assert "J speaks 2nd of 5 in round 1." in text
    assert text.index("1. M announced") < text.index("2. J announced")


@pytest.mark.parametrize(("go", "expected"), [(0, False), (2, False), (3, True), (5, True)])
def test_crowded_flag(go: int, expected: bool) -> None:  # noqa: FBT001
    """Crowded means GO/5 >= 0.5 (so 3 of 5; 2 of 5 is 0.4)."""
    assert views.crowded(go) is expected


def test_public_result_text() -> None:
    """Past-round lines carry the GO count and crowded state."""
    text = views.build_both_view(make_log(), 0, 2, "J")
    assert "Round 0: J announced GO" in text
    assert "2 of 5 went to the bar (not crowded)" in text
    assert "3 of 5 went to the bar (crowded)" in text
