"""Tests for scripts/pilot_summary.py."""

import json
from pathlib import Path

import pytest
from scripts import pilot_summary as ps

NON_NULL_FISHING = 5
ELFAROL_TOTAL = 150
FISHING_TOTAL = 50
FIXTURE = Path(__file__).parent / "fixtures" / "fake_log.json"


def fake(game: str) -> dict:
    """Load one game's fake log."""
    return json.loads(FIXTURE.read_text())[game]


def flags(game: str) -> list[bool | None]:
    """Our flags for the fake log in agent-round order."""
    return [ps.break_flag(game, r["rec"]) for r in ps.agent_rounds(fake(game))]


def test_elfarol_flags() -> None:
    """Flip counts, case and spaces do not, null is None."""
    assert flags("elfarol") == [True, False, False, None, False, False]


def test_fishing_flags() -> None:
    """Over-take, under-take break; '3' versus 3.0 does not; null is None."""
    assert flags("fishing") == [True, True, False, False, None, False]


def test_fishing_takes() -> None:
    """Over and under counts exclude nulls."""
    takes = ps.fishing_takes(ps.agent_rounds(fake("fishing")))
    assert takes["n"] == NON_NULL_FISHING
    assert takes["over_take"]["count"] == 1
    assert takes["under_take"]["count"] == 1


def test_summary_fake() -> None:
    """Pooled rate, null count and harness agreement on the fixture."""
    s = ps.summarise("fishing", fake("fishing"))
    assert s["null_count"] == 1
    assert s["break_pooled"] == {"n": 5, "breaks": 2, "rate": 0.4}
    assert s["harness_agreement"] == {"compared": 5, "agree": 5}
    assert s["tokens"] == "not logged"


def test_payoff_check_fake() -> None:
    """Fixture payoffs match recomputed payoffs."""
    assert ps.payoff_check(fake("elfarol"))["passed"]


def real(game: str) -> dict:
    """Load a real pilot log or skip."""
    path = ps.PILOTS[game]
    if not path.exists():
        pytest.skip("pilot file missing")
    return json.loads(path.read_text())


def test_real_matches_harness() -> None:
    """Our flag equals harness commitment_breaking on all non-null agent-rounds."""
    for game in ps.PILOTS:
        rows = ps.agent_rounds(real(game))
        compared = [(ps.break_flag(game, r["rec"]), r["rec"]["commitment_breaking"]) for r in rows]
        compared = [c for c in compared if c[0] is not None]
        assert compared
        assert all(ours == theirs for ours, theirs in compared)


def test_real_totals() -> None:
    """El Farol has 150 agent-rounds and Fishing has 50."""
    assert len(ps.agent_rounds(real("elfarol"))) == ELFAROL_TOTAL
    assert len(ps.agent_rounds(real("fishing"))) == FISHING_TOTAL


def test_real_payoff_check() -> None:
    """Recomputed El Farol payoffs equal stored payoffs in every round."""
    assert ps.payoff_check(real("elfarol"))["passed"]
