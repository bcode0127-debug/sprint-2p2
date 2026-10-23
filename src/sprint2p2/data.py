"""Development-set loading. Main-run trials from 10 upward are held out and never loaded."""

import copy
import json
from pathlib import Path

DEV_MAX_MAIN_TRIAL = 9
FIRST_SCORED_ROUND = 1


def norm(value: object) -> str | None:
    """Normalise an El Farol action; None means null."""
    return None if value is None else str(value).strip().upper()


def break_flag(rec: dict) -> bool | None:
    """Return our break flag for one agent record, or None if either field is null."""
    stated = norm(rec["stage2"].get("stated_action"))
    choice = norm(rec["stage3"].get("choice"))
    if stated is None or choice is None:
        return None
    return stated != choice


def dev_log(path: Path, source: str) -> dict:
    """Load a log, dropping every held-out main-run trial before anything can use it."""
    log = json.loads(path.read_text())
    if source != "main":
        return log
    kept = copy.copy(log)
    kept["rounds"] = [
        {**rnd, "trials": [t for t in rnd["trials"] if t["trial_id"] <= DEV_MAX_MAIN_TRIAL]}
        for rnd in log["rounds"]
    ]
    return kept


def dev_cases(log: dict, source: str, trials: list[int] | None = None) -> list[dict]:
    """List dev cases (rounds 1 to 9). Rejects main-run trial ids above the dev limit."""
    available = sorted({t["trial_id"] for rnd in log["rounds"] for t in rnd["trials"]})
    wanted = available if trials is None else trials
    if source == "main" and any(t > DEV_MAX_MAIN_TRIAL for t in wanted):
        msg = f"main-run trial >= {DEV_MAX_MAIN_TRIAL + 1} is held out"
        raise ValueError(msg)
    cases = []
    for rnd in log["rounds"]:
        if rnd["round_id"] < FIRST_SCORED_ROUND:
            continue
        for trial in rnd["trials"]:
            if trial["trial_id"] not in wanted:
                continue
            for agent, rec in trial["agents"].items():
                flag = break_flag(rec)
                if flag is None:
                    continue
                cases.append(
                    {
                        "source": source,
                        "game": f"{source}:{trial['trial_id']}",
                        "trial": trial["trial_id"],
                        "round": rnd["round_id"],
                        "agent": agent,
                        "label": flag,
                    },
                )
    return cases
