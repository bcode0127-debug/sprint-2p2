"""Tests for sprint2p2.combine."""

from pathlib import Path

import numpy as np
import pytest

from sprint2p2 import combine, scoring

SCORES = Path(__file__).resolve().parent.parent / "scores"


def test_tie_case_uses_average_ranks() -> None:
    """Both [1,1,2] ranks [1.5,1.5,3]; counting [3,1,1] ranks [3,1.5,1.5]; mean [2.25,1.5,2.25]."""
    out = combine.combo_scores(np.array([1, 1, 2]), np.array([3, 1, 1]))
    assert out.tolist() == pytest.approx([2.25, 1.5, 2.25])


def test_combo_is_rank_based_not_scale_based() -> None:
    """A positive rescaling or monotone map of one input leaves the combo unchanged."""
    both = np.array([10.0, 40.0, 25.0, 25.0])
    counting = np.array([0.0, 4.0, 2.0, 1.0])
    base = combine.combo_scores(both, counting)
    assert combine.combo_scores(both * 7 + 3, counting).tolist() == pytest.approx(base.tolist())
    assert combine.combo_scores(np.exp(both / 10), counting).tolist() == pytest.approx(
        base.tolist()
    )


def test_bootstrap_hand_computed_perfect_combo() -> None:
    """When counting is perfect and Both is constant, the combo equals the AUROC mean-rank pattern.

    Labels T,F,T,F in two games; counting = label, Both constant: combo ranks track counting, so
    combo AUROC is 1.0 in every resample, C1 = +0.5 always and C2 = 0 always.
    """
    labels = np.array([True, False, True, False])
    games = ["g1", "g1", "g2", "g2"]
    out = combine.combo_bootstrap(np.zeros(4), labels.astype(float), labels, games, n_boot=200)
    assert out["combo_auroc"] == pytest.approx(1.0)
    assert out["C1"]["diff"] == pytest.approx(0.5)
    assert out["C1"]["lower_95_one_sided"] == pytest.approx(0.5)
    assert out["C2"]["diff"] == pytest.approx(0.0)
    assert out["C2"]["p_one_sided"] == pytest.approx(1.0)
    assert out["C2"]["p_holm"] >= out["C2"]["p_one_sided"]
    assert out["C1"]["p_holm"] >= out["C1"]["p_one_sided"]


def load(split: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load Both, counting and labels for a committed split, aligned by case id."""
    both = scoring.read_rows(SCORES / split / "both.jsonl")
    counting = scoring.read_rows(SCORES / split / "counting.jsonl")
    ids = sorted(both)
    return (
        np.array([both[i]["score"] for i in ids], float),
        np.array([counting[i]["score"] for i in ids], float),
        np.array([both[i]["label"] for i in ids], bool),
    )


@pytest.mark.parametrize(("split", "expected"), [("dev", 0.667), ("test", 0.698)])
def test_code_check_against_the_amendment_draft_numbers(split: str, expected: float) -> None:
    """Code check only: the combination AUROC is 0.667 on dev and 0.698 on test (3 decimals)."""
    both, counting, labels = load(split)
    assert round(combine.combo_auroc(both, counting, labels), 3) == expected


def test_scores_files_are_not_written_by_the_code_check() -> None:
    """The code check reads committed scores only; there is no combo score file."""
    assert not (SCORES / "dev" / "combo.jsonl").exists()
    assert list(SCORES.glob("*/combo*")) == []


def test_per_game_means_next_to_pooled_differences() -> None:
    """Hand-computed: per-game differences are reported with their mean beside the pooled one.

    Game g1 (labels T,F): Both 1,0 (AUROC 1); counting 0,1 (AUROC 0). Game g2 (T,F): Both 0,1
    (AUROC 0); counting 1,0 (AUROC 1). The combo ranks over the whole set tie everything.
    """
    labels = np.array([True, False, True, False])
    games = ["g1", "g1", "g2", "g2"]
    both = np.array([1.0, 0.0, 0.0, 1.0])
    counting = np.array([0.0, 1.0, 1.0, 0.0])
    out = combine.combo_bootstrap(both, counting, labels, games, n_boot=50)
    assert out["combo_auroc"] == pytest.approx(0.5)
    assert out["C1"]["per_game_differences"] == {
        "g1": pytest.approx(-0.5),
        "g2": pytest.approx(0.5),
    }
    assert out["C1"]["mean_of_per_game_differences"] == pytest.approx(0.0)
    assert out["C2"]["per_game_differences"] == {
        "g1": pytest.approx(0.5),
        "g2": pytest.approx(-0.5),
    }
    assert out["C2"]["mean_of_per_game_differences"] == pytest.approx(0.0)
    assert out["C1"]["diff"] == pytest.approx(out["combo_auroc"] - out["both_auroc"])


def test_test_split_per_game_figures_match_the_amendment() -> None:
    """Code check: on the test split C2 averages -0.003 per game; the SDs are 0.068 and 0.098."""
    both, counting, labels = load("test")
    ids = sorted(scoring.read_rows(SCORES / "test" / "both.jsonl"))
    rows = scoring.read_rows(SCORES / "test" / "both.jsonl")
    games = [rows[i]["game"] for i in ids]
    desc = combine.per_game_combo_differences(both, counting, labels, games)
    assert round(desc["C2"]["mean_of_per_game_differences"], 3) == -0.003  # noqa: PLR2004
    assert round(desc["C1"]["between_game_sd"], 3) == 0.068  # noqa: PLR2004
    assert round(desc["C2"]["between_game_sd"], 3) == 0.098  # noqa: PLR2004
