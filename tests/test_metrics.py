"""Tests for sprint2p2.metrics with tiny hand-computed examples."""

import numpy as np
import pytest

from sprint2p2 import metrics

TIED_SCORES = np.array([1, 2, 2, 3])
TIED_LABELS = np.array([False, True, False, True])


def test_auroc_perfect_and_ties() -> None:
    """Perfect ranking is 1.0; the tied example is 3.5/4."""
    assert metrics.auroc(np.array([1, 2, 3, 4]), np.array([False, False, True, True])) == 1.0
    assert metrics.auroc(TIED_SCORES, TIED_LABELS) == pytest.approx(0.875)
    assert metrics.auroc(np.array([1, 1]), np.array([True, False])) == 0.5  # noqa: PLR2004
    assert metrics.auroc(np.array([1, 2]), np.array([True, True])) is None


def test_placement_values() -> None:
    """Per-case placements average to the AUROC within each class."""
    v = metrics.placement_values(TIED_SCORES, TIED_LABELS)
    assert v.tolist() == pytest.approx([1.0, 0.75, 0.75, 1.0])
    assert v[TIED_LABELS].mean() == pytest.approx(0.875)
    assert v[~TIED_LABELS].mean() == pytest.approx(0.875)


KEEPS = np.arange(10, dtype=float)


def test_randomized_threshold() -> None:
    """With keeps 0..9: FPR 0.2 gives t=7, q=0; FPR 0.25 gives t=7, q=0.5."""
    labels = np.zeros(10, dtype=bool)
    exact = metrics.randomized_threshold(KEEPS, labels, 0.2)
    assert (exact["t"], exact["q"]) == (7.0, pytest.approx(0.0))
    half = metrics.randomized_threshold(KEEPS, labels, 0.25)
    assert (half["t"], half["q"]) == (7.0, pytest.approx(0.5))


def test_apply_threshold_expected_and_extremes() -> None:
    """Expected recall is 1/3 + 0.5/3 = 0.5; q=1 flags every tie, q=0 none."""
    scores = np.array([9, 7, 3, 7, 7, 1], dtype=float)
    labels = np.array([True, True, True, False, False, False])
    keys = [str(i) for i in range(6)]
    res = metrics.apply_threshold(scores, labels, keys, {"t": 7.0, "q": 0.5})
    assert res["recall_expected"] == pytest.approx(0.5)
    assert res["fpr_expected"] == pytest.approx(1 / 3)
    all_ties = metrics.apply_threshold(scores, labels, keys, {"t": 7.0, "q": 1.0})
    assert (all_ties["recall"], all_ties["fpr"]) == (pytest.approx(2 / 3), pytest.approx(2 / 3))
    no_ties = metrics.apply_threshold(scores, labels, keys, {"t": 7.0, "q": 0.0})
    assert (no_ties["recall"], no_ties["fpr"]) == (pytest.approx(1 / 3), 0.0)


def test_holm() -> None:
    """Holm on .01, .04, .03 gives .03, .06, .06."""
    adj = metrics.holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert adj == {"a": pytest.approx(0.03), "c": pytest.approx(0.06), "b": pytest.approx(0.06)}
    assert metrics.holm({"a": 0.6, "b": 0.9})["b"] == pytest.approx(1.0)


def test_variance_decomposition() -> None:
    """All variance between games, then all within."""
    between = metrics.variance_decomposition(np.array([1, 1, 0, 0]), ["g1", "g1", "g2", "g2"])
    assert between["total"] == pytest.approx(0.25)
    assert between["between_game"] == pytest.approx(0.25)
    assert between["within_game"] == pytest.approx(0.0)
    within = metrics.variance_decomposition(np.array([1, 0, 1, 0]), ["g1", "g1", "g2", "g2"])
    assert within["between_game"] == pytest.approx(0.0)
    assert within["within_game"] == pytest.approx(0.25)


def test_paired_decomposition_mean_is_auroc_difference() -> None:
    """The mean per-case difference equals AUROC(A) - AUROC(B)."""
    a = np.array([1, 2, 3, 4], dtype=float)
    b = TIED_SCORES.astype(float)
    labels = np.array([False, False, True, True])
    out = metrics.paired_decomposition(a, b, labels, ["g1", "g2", "g1", "g2"])
    expected = metrics.auroc(a, labels) - metrics.auroc(b, labels)
    assert out["mean_difference"] == pytest.approx(expected)


def test_paired_bootstrap_deterministic_case() -> None:
    """A perfect and B constant in two games with both classes: diff .5 in every resample."""
    labels = np.array([True, False, True, False])
    games = ["g1", "g1", "g2", "g2"]
    perfect = labels.astype(float)
    constant = np.zeros(4)
    res = metrics.paired_bootstrap(perfect, constant, labels, games, n_boot=200)
    assert res["diff"] == pytest.approx(0.5)
    assert res["lower_95_one_sided"] == pytest.approx(0.5)
    assert res["p_one_sided"] == pytest.approx(1 / 201)
    assert res["n_resamples"] == 200  # noqa: PLR2004


def test_spearman() -> None:
    """Monotone is 1, reversed is -1, and ties use average ranks (hand value 4.5/sqrt(22.5))."""
    x = np.array([1, 2, 3, 4])
    assert metrics.spearman(x, x * 10) == pytest.approx(1.0)
    assert metrics.spearman(x, -x) == pytest.approx(-1.0)
    assert metrics.spearman(np.array([1, 2, 3, 4]), np.array([1, 2, 2, 4])) == pytest.approx(
        0.9486832980505138,
    )
    assert metrics.spearman(x, np.ones(4)) is None


def test_auroc_ci_constant_case() -> None:
    """When every game is perfectly ranked, the interval is exactly [1, 1]."""
    labels = np.array([True, False, True, False])
    games = ["g1", "g1", "g2", "g2"]
    assert metrics.auroc_ci(labels.astype(float), labels, games, n_boot=200) == [1.0, 1.0]
