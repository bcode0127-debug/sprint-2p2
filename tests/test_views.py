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


NON_ORACLE = [v for v in views.VIEWS if v != "oracle"]


@pytest.mark.parametrize("view", NON_ORACLE)
def test_no_leak(view: str) -> None:
    """No forbidden field reaches any view, for every round and agent."""
    log = make_log()
    for r in range(len(GO_PATTERN)):
        for name in NAMES:
            assert SENTINEL not in views.build_view(log, 0, r, name, view)


def test_oracle_adds_only_the_round_action() -> None:
    """The oracle shows J's round-r action and still leaks nothing else."""
    log = make_log()
    for rec in log["rounds"][LAST_ROUND]["trials"][0]["agents"].values():
        rec["stage3"]["choice"] = "GO"
    text = views.build_view(log, 0, LAST_ROUND, "J", "oracle")
    assert SENTINEL not in text
    assert "J's actual action in round 3: GO" in text
    assert text.startswith(views.build_view(log, 0, LAST_ROUND, "J", "both"))


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


def lines(view: str, r: int = 2, name: str = "J") -> set[str]:
    """Return the set of non-empty lines of a view."""
    return {ln for ln in views.build_view(make_log(), 0, r, name, view).split("\n") if ln}


@pytest.mark.parametrize("view", ["own_only", "freshness"])
def test_subsets_of_both(view: str) -> None:
    """own_only and freshness only remove lines from both."""
    assert lines(view) <= lines("both")
    assert lines(view) < lines("both")


def test_own_only_and_freshness_contents() -> None:
    """own_only keeps J's line only; freshness has no round-r announcements."""
    own = views.build_view(make_log(), 0, 2, "J", "own_only")
    assert "J announced" in own
    assert "2. J announced" in own
    for other in ("M", "Q", "T", "Z"):
        assert f". {other} announced" not in own
    fresh = views.build_view(make_log(), 0, 2, "J", "freshness")
    assert "Round 2 announcements" not in fresh
    assert "msg J r2" not in fresh


def test_actions_only_has_no_announcement_text() -> None:
    """actions_only carries no message and no announcement wording."""
    text = views.build_view(make_log(), 0, 2, "J", "actions_only")
    assert "msg" not in text
    assert "announce" not in text
    assert "went to the bar" in text


def test_messages_only_has_no_actions_or_crowd() -> None:
    """messages_only carries no crowd result and no past action."""
    text = views.build_view(make_log(), 0, 2, "J", "messages_only")
    assert "went to the bar" not in text
    assert "crowded" not in text
    assert " did " not in text
    assert "msg J r0" in text
    assert "5. Z announced" in text


def test_structured_has_no_message_text() -> None:
    """Structured has a table and stated actions but no message text."""
    text = views.build_view(make_log(), 0, LAST_ROUND, "J", "structured")
    assert "msg" not in text
    assert "| 0 | GO | GO | kept |" in text
    assert "| 2 | GO | STAY | broke | 0 of 5 went, not crowded |" in text
    assert "1. M: GO" in text


def test_controls_and_position() -> None:
    """Empty and round_only are bare; every other view states the position."""
    log = make_log()
    assert views.build_view(log, 0, 2, "J", "round_only") == "This is round 2 of 10."
    assert views.build_view(log, 0, 2, "J", "empty") == "(no record)"
    for view in views.VIEWS:
        text = views.build_view(log, 0, 1, "J", view)
        if view in views.NO_POSITION:
            assert "speaks" not in text
        else:
            assert "J speaks 2nd of 5 in round 1." in text
