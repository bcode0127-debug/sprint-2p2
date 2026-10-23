"""Dev, threshold and test splits, round 0 as a separate set, and the scoring gate."""

import json
from pathlib import Path

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
FROZEN_FIELDS = ("prereg_commit", "osf_url")


class GateError(RuntimeError):
    """Raised when a monitor call is attempted on held-out data before the freeze."""


def load_logs() -> dict[str, dict]:
    """Load the committed raw logs by source."""
    return {
        "main": json.loads(MAIN_RAW.read_text()),
        "pilot": json.loads(PILOT_RAW.read_text()),
    }


def frozen_ok(path: Path = FROZEN) -> bool:
    """Return True when the freeze file exists with non-empty prereg_commit and osf_url."""
    if not path.exists():
        return False
    try:
        frozen = json.loads(path.read_text())
    except json.JSONDecodeError:
        return False
    return isinstance(frozen, dict) and all(
        isinstance(frozen.get(k), str) and frozen[k].strip() for k in FROZEN_FIELDS
    )


def check_gate(split: str, path: Path = FROZEN) -> None:
    """Raise unless the split may be scored by the monitor."""
    if split in GATED and not frozen_ok(path):
        msg = f"monitor calls on the {split} split need {path.name} with prereg_commit and osf_url"
        raise GateError(msg)


def guard_case(case: dict, path: Path = FROZEN) -> None:
    """Gate one case by its raw identity, so a wrong split label cannot bypass it."""
    held_out = case["source"] == "main" and case["trial"] >= FIRST_HELD_OUT_TRIAL
    if held_out or case.get("split") in GATED:
        check_gate("test" if held_out else case["split"], path)


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
