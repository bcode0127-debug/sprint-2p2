"""Tests for sprint2p2.baselines."""

from sprint2p2 import baselines
from tests.test_data import make_log


def case(rnd: int, agent: str = "J", label: bool = False) -> dict:  # noqa: FBT001, FBT002
    """Build a case dict for trial 0 of the fake log."""
    return {"source": "x", "trial": 0, "round": rnd, "agent": agent, "label": label}


def test_random_is_reproducible_and_in_range() -> None:
    """The same case always gets the same score in [0, 1)."""
    a = baselines.random_score(case(1))
    assert a == baselines.random_score(case(1))
    assert 0 <= a < 1
    assert a != baselines.random_score(case(2))


def test_history_rules() -> None:
    """Last-crowded and broke-last read only the previous round; round 0 is 0."""
    log = make_log(1)
    assert baselines.last_crowded(log, case(1)) == 1
    assert baselines.last_crowded(log, case(2)) == 0
    assert baselines.last_crowded(log, case(0)) == 0
    assert baselines.broke_last(log, case(1, "M")) == 1
    assert baselines.broke_last(log, case(1, "J")) == 0
    assert baselines.broke_last(log, case(0, "M")) == 0


def test_counting_and_plan() -> None:
    """Counting matches other announcements; plan compares stage1 to the announcement."""
    log = make_log(1)
    assert baselines.counting(log, case(1, "J")) == 3  # noqa: PLR2004
    assert baselines.counting(log, case(1, "M")) == 0
    rec = log["rounds"][1]["trials"][0]["agents"]
    rec["J"]["stage1"] = {"intended_action": "stay"}
    rec["Q"]["stage1"] = {"intended_action": "GO"}
    rec["M"]["stage1"] = {"intended_action": None}
    assert baselines.plan(log, case(1, "J")) == 1
    assert baselines.plan(log, case(1, "Q")) == 0
    assert baselines.plan(log, case(1, "M")) == 0


def test_round_rate_fit() -> None:
    """Rates are per-round break frequencies; unseen rounds get the mean."""
    cases = [case(1, label=True), case(1), case(2), case(2)]
    table = baselines.fit_round_rate(cases)
    assert table == {1: 0.5, 2: 0.0}
    assert baselines.round_rate(table, case(1)) == 0.5  # noqa: PLR2004
    assert baselines.round_rate(table, case(7)) == 0.25  # noqa: PLR2004
