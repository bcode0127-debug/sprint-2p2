"""Tests for sprint2p2.budget."""

import pytest

from sprint2p2 import budget


def test_within_budget_returns_estimate() -> None:
    """1,000 calls at $0.00045 cost $0.45."""
    assert budget.check_budget(1.0, 1000) == pytest.approx(0.45)


def test_over_budget_raises() -> None:
    """Usage 8.80 plus a 0.45 estimate exceeds the $9 cap."""
    with pytest.raises(budget.BudgetError):
        budget.check_budget(8.8, 1000)
    assert budget.check_budget(8.5, 1000) == pytest.approx(0.45)
