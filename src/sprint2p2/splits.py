"""Dev, threshold and test splits, round 0 as a separate set, and the scoring gate."""

import json
from pathlib import Path

from sprint2p2 import views
from sprint2p2.data import break_flag

ROOT = Path(__file__).resolve().parent.parent.parent
RAW = ROOT / "data" / "raw"
MAIN_RAW = RAW / "elfarol_main_gpt-5.2.json"
PILOT_RAW = RAW / "elfarol_pilot_gpt-5.2.json"
FROZEN = ROOT / "configs" / "frozen.json"
MAIN_TRIALS = {"dev": range(10), "threshold": range(10, 20), "test": range(20, 40)}
SCORED_ROUNDS = range(1, 10)
ROUND_ZERO = range(1)
GATED = ("threshold", "test")
FIRST_HELD_OUT_TRIAL = 10
FIRST_TEST_TRIAL = 20
FROZEN_FIELDS = ("prereg_commit", "osf_url")


class GateError(RuntimeError):
    """Raised when a monitor call is attempted on held-out data before the freeze."""


def load_logs() -> dict[str, dict]:
    """Load the committed raw logs by source."""
    return {
        "main": json.loads(MAIN_RAW.read_text()),
        "pilot": json.loads(PILOT_RAW.read_text()),
    }


def _nonempty(frozen: dict, key: str) -> bool:
    """Return True when frozen[key] is a non-blank string."""
    return isinstance(frozen.get(key), str) and bool(frozen[key].strip())


def _has_thresholds(frozen: dict) -> bool:
    """Return True when every monitor view has a numeric t and q."""
    fits = frozen.get("thresholds")
    return isinstance(fits, dict) and all(
        isinstance(fits.get(v), dict)
        and all(isinstance(fits[v].get(k), (int, float)) for k in ("t", "q"))
        for v in views.VIEWS
    )


def gate_ok(split: str, path: Path = FROZEN) -> bool:
    """Return True when the freeze file allows monitor calls on the split.

    Threshold calls need prereg_commit and a non-empty osf_url. Test calls also need
    per-view t and q, written by scripts/fit_thresholds.py from threshold-split scores.
    """
    if split not in GATED:
        return True
    if not path.exists():
        return False
    try:
        frozen = json.loads(path.read_text())
    except json.JSONDecodeError:
        return False
    if not isinstance(frozen, dict):
        return False
    if not all(_nonempty(frozen, k) for k in FROZEN_FIELDS):
        return False
    return split != "test" or _has_thresholds(frozen)


def check_gate(split: str, path: Path = FROZEN) -> None:
    """Raise unless the split may be scored by the monitor."""
    if not gate_ok(split, path):
        need = "prereg_commit and a non-empty osf_url"
        if split == "test":
            need += ", plus per-view t and q from scripts/fit_thresholds.py"
        msg = f"monitor calls on the {split} split need {path.name} with {need}"
        raise GateError(msg)


def held_out_split(case: dict) -> str | None:
    """Return the split a case belongs to by its raw identity (main trial number)."""
    if case["source"] != "main" or case["trial"] < FIRST_HELD_OUT_TRIAL:
        return None
    return "threshold" if case["trial"] < FIRST_TEST_TRIAL else "test"


def guard_case(case: dict, path: Path = FROZEN) -> None:
    """Gate one case by its raw identity, so a wrong split label cannot bypass it."""
    by_trial = held_out_split(case)
    declared = case.get("split")
    for split in ("test", "threshold"):
        if split in (by_trial, declared):
            check_gate(split, path)
            break


def split_cases(logs: dict[str, dict], split: str, *, round_zero: bool = False) -> list[dict]:
    """List the cases of one split: rounds 1 to 9, or round 0 on its own."""
    rounds = ROUND_ZERO if round_zero else SCORED_ROUNDS
    sources = ["pilot", "main"] if split == "dev" else ["main"]
    cases = []
    for source in sources:
        trials = None if source == "pilot" else set(MAIN_TRIALS[split])
        for rnd in logs[source]["rounds"]:
            if rnd["round_id"] not in rounds:
                continue
            for trial in rnd["trials"]:
                if trials is not None and trial["trial_id"] not in trials:
                    continue
                for agent, rec in trial["agents"].items():
                    flag = break_flag(rec)
                    if flag is not None:
                        cases.append(
                            {
                                "split": split,
                                "source": source,
                                "game": f"{source}:{trial['trial_id']}",
                                "trial": trial["trial_id"],
                                "round": rnd["round_id"],
                                "agent": agent,
                                "label": flag,
                            },
                        )
    return cases
