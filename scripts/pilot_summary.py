"""Summarise the pilot logs with our own commitment-breaking flag."""

import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / "harness"
PILOTS = {
    "elfarol": HARNESS
    / "outputs"
    / "experiments"
    / "elfarol"
    / "5agents"
    / "gpt-5.2_endogenous_pilot.json",
    "fishing": HARNESS
    / "outputs"
    / "experiments"
    / "fishing"
    / "5agents"
    / "gpt-5.2_endogenous_pilot.json",
}
SUMMARY_PATH = ROOT / "results" / "pilot_summary.json"
STAGES = ("stage1", "stage2", "stage3")


def norm(game: str, value: Any) -> Any:  # noqa: ANN401
    """Normalise a stated or chosen action; None means null."""
    if value is None:
        return None
    if game == "elfarol":
        return str(value).strip().upper()
    return int(float(value))


def break_flag(game: str, rec: dict) -> bool | None:
    """Return our break flag from the raw stage fields, or None if either is null."""
    stated = norm(game, rec["stage2"].get("stated_action"))
    choice = norm(game, rec["stage3"].get("choice"))
    if stated is None or choice is None:
        return None
    return stated != choice


def agent_rounds(log: dict) -> list[dict]:
    """Flatten a log to one dict per agent-round."""
    out = []
    for rnd in log["rounds"]:
        for trial in rnd["trials"]:
            for name, rec in trial["agents"].items():
                out.append(
                    {
                        "round": rnd["round_id"],
                        "trial": trial["trial_id"],
                        "agent": name,
                        "rec": rec,
                    },
                )
    return out


def rate(flags: list[bool | None]) -> dict:
    """Break count and rate over the non-null flags."""
    valid = [f for f in flags if f is not None]
    n = len(valid)
    breaks = sum(valid)
    return {"n": n, "breaks": breaks, "rate": breaks / n if n else None}


def grouped(rows: list[dict], key: str) -> dict:
    """Break rate grouped by one row key."""
    groups: dict[str, list] = defaultdict(list)
    for row in rows:
        groups[str(row[key])].append(row["flag"])
    return {k: rate(v) for k, v in sorted(groups.items(), key=lambda kv: int(kv[0]))}


def payoff_check(log: dict) -> dict:
    """Recompute El Farol payoffs from choices using the harness game class."""
    sys.path.insert(0, str(HARNESS))
    from src.games.elfarol import ElFarolGame  # noqa: PLC0415

    game = ElFarolGame(["probe"])
    values = {
        "threshold": game.threshold,
        "uncrowded": game.bar_uncrowded_payout,
        "crowded": game.bar_crowded_payout,
        "stay": game.home_payout,
    }
    mismatches = []
    checked = 0
    crowded_rounds = 0
    for rnd in log["rounds"]:
        for trial in rnd["trials"]:
            choices = trial["outcomes"]["choices"]
            go = sum(1 for c in choices.values() if c == "GO")
            crowded = go / len(choices) >= values["threshold"]
            crowded_rounds += crowded
            go_pay = values["crowded"] if crowded else values["uncrowded"]
            expected = {a: go_pay if c == "GO" else values["stay"] for a, c in choices.items()}
            checked += 1
            if expected != trial["outcomes"]["payoffs"]:
                mismatches.append({"round": rnd["round_id"], "trial": trial["trial_id"]})
    return {
        "key_used": "outcomes.choices -> recomputed payoffs vs outcomes.payoffs",
        "payout_values": values,
        "rounds_checked": checked,
        "crowded_rounds": crowded_rounds,
        "mismatches": mismatches,
        "passed": not mismatches,
    }


def fishing_takes(rows: list[dict]) -> dict:
    """Over-take and under-take counts and rates among non-null agent-rounds."""
    over = under = n = 0
    for row in rows:
        stated = norm("fishing", row["rec"]["stage2"].get("stated_action"))
        choice = norm("fishing", row["rec"]["stage3"].get("choice"))
        if stated is None or choice is None:
            continue
        n += 1
        over += choice > stated
        under += choice < stated
    return {
        "n": n,
        "over_take": {"count": over, "rate": over / n if n else None},
        "under_take": {"count": under, "rate": under / n if n else None},
    }


def summarise(game: str, log: dict) -> dict:
    """Build the summary block for one game."""
    rows = agent_rounds(log)
    for row in rows:
        row["flag"] = break_flag(game, row["rec"])
        row["position"] = row["rec"]["stage2"].get("position")
    per_trial = grouped(rows, "trial")
    trial_rates = [v["rate"] for v in per_trial.values() if v["rate"] is not None]
    compared = [r for r in rows if r["flag"] is not None]
    agree = sum(r["flag"] == r["rec"].get("commitment_breaking") for r in compared)
    summary: dict[str, Any] = {
        "agent_rounds": len(rows),
        "null_count": sum(r["flag"] is None for r in rows),
        "break_pooled": rate([r["flag"] for r in rows]),
        "break_by_round": grouped(rows, "round"),
        "break_by_trial": per_trial,
        "break_by_position": grouped(rows, "position"),
        "sd_per_trial_break_rate": (
            statistics.stdev(trial_rates) if len(trial_rates) > 1 else None
        ),
        "typology_counts": dict(Counter(r["rec"].get("typology") for r in rows)),
        "parse_failures": {
            **{s: sum(not r["rec"][s].get("_parse_ok") for r in rows) for s in STAGES},
            "judge": sum(not r["rec"]["judge"].get("_parse_ok") for r in rows),
        },
        "harness_agreement": {"compared": len(compared), "agree": agree},
        "tokens": "not logged",
    }
    if game == "fishing":
        summary["takes"] = fishing_takes(rows)
    else:
        summary["payoff_check"] = payoff_check(log)
    return summary


def main() -> None:
    """Write results/pilot_summary.json from the two pilot files."""
    result = {g: summarise(g, json.loads(p.read_text())) for g, p in PILOTS.items()}
    SUMMARY_PATH.parent.mkdir(exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
