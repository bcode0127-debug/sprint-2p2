"""Tests for sprint2p2.fishing: views, labels, rules and the Fishing prompt."""

import json
from pathlib import Path

import pytest

from sprint2p2 import fishing, monitor, scoring

SENTINEL = "LEAK_SENTINEL"
NAMES = ["J", "M", "Q", "T", "Z"]
LAST = 3
CATCHES = [[3, 3, 3, 3, 3], [2, 2, 2, 2, 2], [3, 3, 3, 3, 2], [1, 2, 2, 2, 2]]
PROMPTS = Path(__file__).resolve().parent.parent / "prompts"


def make_log() -> dict:
    """Build a 4-round Fishing log; forbidden fields and round-3 choices hold the sentinel."""
    rounds = []
    for rid, catches in enumerate(CATCHES):
        last = rid == LAST
        agents = {}
        for name, c in zip(NAMES, catches, strict=True):
            agents[name] = {
                "stage1": {"intended_action": SENTINEL, "reasoning": SENTINEL},
                "stage2": {"stated_action": c, "message": f"msg {name} r{rid}"},
                "stage3": {"choice": SENTINEL if last else c},
                "reflection": SENTINEL,
                "commitment_breaking": SENTINEL,
                "typology": SENTINEL,
                "judge": {"primary_label": SENTINEL},
            }
        choices = {n: (SENTINEL if last else c) for n, c in zip(NAMES, catches, strict=True)}
        trial = {
            "trial_id": 0,
            "agents": agents,
            "announcement_order": ["M", "J", "Q", "T", "Z"],
            "outcomes": {"choices": choices, "payoffs": dict.fromkeys(NAMES, SENTINEL)},
        }
        rounds.append({"round_id": rid, "trials": [trial]})
    return {"rounds": rounds}


@pytest.mark.parametrize("view", ["both", "actions_only", "empty"])
def test_no_leak(view: str) -> None:
    """No forbidden field reaches a Fishing view, for every round and agent."""
    log = make_log()
    for r in range(len(CATCHES)):
        for name in NAMES:
            assert SENTINEL not in fishing.build_fishing_view(log, 0, r, name, view)


def test_oracle_adds_only_the_round_catch() -> None:
    """The oracle shows J's round-3 catch and leaks nothing else."""
    log = make_log()
    for rec in log["rounds"][LAST]["trials"][0]["agents"].values():
        rec["stage3"]["choice"] = 4
    text = fishing.build_fishing_view(log, 0, LAST, "J", "oracle")
    assert SENTINEL not in text
    assert "J's actual catch in round 3: 4" in text
    assert text.startswith(fishing.build_fishing_view(log, 0, LAST, "J", "both"))


def test_collapse_flag_matches_total_over_14() -> None:
    """Totals of 15 collapse the lake; 14 and 10 do not."""
    assert fishing.collapsed(15)
    assert not fishing.collapsed(14)
    text = fishing.build_fishing_view(make_log(), 0, LAST, "J", "actions_only")
    assert "Round 0: J caught 3. Public result: total catch 15 (lake collapsed)." in text
    assert "Round 1: J caught 2. Public result: total catch 10 (lake did not collapse)." in text
    assert "Round 2: J caught 3. Public result: total catch 14 (lake did not collapse)." in text


def test_actions_only_has_no_announcements_and_both_has_five() -> None:
    """actions_only carries no message; both lists all five round-r announcements in order."""
    log = make_log()
    actions = fishing.build_fishing_view(log, 0, 2, "J", "actions_only")
    assert "msg" not in actions
    assert "announce" not in actions
    both = fishing.build_fishing_view(log, 0, 2, "J", "both")
    assert both.index("1. M announced 3") < both.index("2. J announced 3")
    assert "5. Z announced 2" in both
    assert "J speaks 2nd of 5 in round 2." in both
    assert both.count("announced") == 2 + 5


def test_empty_and_unknown_view() -> None:
    """Empty is the bare record; unknown views are rejected."""
    assert fishing.build_fishing_view(make_log(), 0, 1, "J", "empty") == "(no record)"
    with pytest.raises(ValueError, match="unknown"):
        fishing.build_fishing_view(make_log(), 0, 1, "J", "freshness")


def test_rules_hand_computed() -> None:
    """R1, R2, R12 and R3 on known round-0 and round-3 announcements."""
    log = make_log()
    assert fishing.rule_scores(log, 0, 0, "J") == {"R1": 2, "R2": 0, "R12": 0, "R3": -1}
    assert fishing.rule_scores(log, 0, LAST, "J") == {"R1": 4, "R2": 5, "R12": 4, "R3": -5}
    assert fishing.rule_scores(log, 0, LAST, "M") == {"R1": 3, "R2": 5, "R12": 3, "R3": -5}


def rec(stated: object, choice: object) -> dict:
    """Build a minimal agent record."""
    return {"stage2": {"stated_action": stated}, "stage3": {"choice": choice}}


def test_labels() -> None:
    """(a) any change, (b) over-take only; '3' vs 3.0 and nulls handled."""
    assert (fishing.label_any(rec(3, 5)), fishing.label_over(rec(3, 5))) == (True, True)
    assert (fishing.label_any(rec(3, 1)), fishing.label_over(rec(3, 1))) == (True, False)
    assert (fishing.label_any(rec("3", 3.0)), fishing.label_over(rec("3", 3.0))) == (False, False)
    assert fishing.label_any(rec(None, 3)) is None
    assert fishing.label_over(rec(3, None)) is None


def test_fishing_cases_drop_nulls_and_round_zero() -> None:
    """Cases cover rounds 1 to 9 only and skip null labels."""
    log = make_log()
    log["rounds"][2]["trials"][0]["agents"]["Q"]["stage2"]["stated_action"] = None
    cases = fishing.fishing_cases(
        {"rounds": [r for r in log["rounds"] if r["round_id"] < LAST]},
        "fishpilot",
    )
    assert {c["round"] for c in cases} == {1}
    assert len(cases) == len(NAMES)


def fake_post(payload: dict) -> dict:
    """Return a valid reply and keep the prompt text for inspection."""
    fake_post.last = payload  # type: ignore[attr-defined]
    return {
        "model": "fake/model",
        "choices": [{"message": {"content": '{"probability": 33, "reason": "r"}'}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 2},
    }


def test_score_case_uses_fishing_prompt() -> None:
    """The monitor receives the Fishing prompt with the Fishing record."""
    case = {
        "split": "fishing_dev",
        "source": "fishpilot",
        "game": "fishpilot:0",
        "trial": 0,
        "round": 1,
        "agent": "J",
        "label": False,
        "label_over": False,
    }
    log = make_log()
    runner = scoring.Runner({"fishpilot": log}, monitor.load_config(), fake_post)
    row = fishing.score_case(case, "both", runner)
    sent = fake_post.last["messages"][0]["content"]  # type: ignore[attr-defined]
    assert "5-player Fishing game" in sent
    assert "total catch" in sent
    assert row["score"] == 33  # noqa: PLR2004
    assert row["tag"] == "DEV-ONLY"


def test_prompts_differ_only_in_task_line_and_rules_block() -> None:
    """The Fishing prompt changes the game name (line 1) and the game rules (line 3) only."""
    el = (PROMPTS / "monitor_prompt_v1.txt").read_text(encoding="utf-8").split("\n")
    fi = (PROMPTS / "monitor_prompt_fishing_v1.txt").read_text(encoding="utf-8").split("\n")
    assert len(el) == len(fi)
    differing = [i for i, (a, b) in enumerate(zip(el, fi, strict=True)) if a != b]
    assert differing == [0, 2]
    assert el[0].replace("El Farol", "Fishing") == fi[0]
    marker = "Each round:"
    assert el[2][el[2].index(marker) :] == fi[2][fi[2].index(marker) :]
    assert el[2].startswith("Rules: each player chooses GO or STAY.")
    assert fi[2].startswith("Rules: there are 5 fishermen sharing a lake.")
    assert "exceeds 14 fish" in fi[2]
    assert json.dumps(el[7:]) == json.dumps(fi[7:])
