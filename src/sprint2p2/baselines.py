"""No-LLM baseline scorers. Higher score means more likely to break."""

import random
from collections import defaultdict

from sprint2p2 import rules
from sprint2p2.data import norm
from sprint2p2.views import _trial

SEED = 2026
BASELINES = ("random", "last_crowded", "broke_last", "round_rate", "counting", "plan")


def random_score(case: dict) -> float:
    """Return a reproducible uniform score keyed on the case identity and seed 2026."""
    key = f"{SEED}|{case['source']}|{case['trial']}|{case['round']}|{case['agent']}"
    return random.Random(key).random()  # noqa: S311


def last_crowded(log: dict, case: dict) -> int:
    """Return 1 if last round was crowded (0 in round 0)."""
    if case["round"] == 0:
        return 0
    return rules.last_round_crowded(log, case["trial"], case["round"])


def broke_last(log: dict, case: dict) -> int:
    """Return 1 if the agent broke last round (0 in round 0)."""
    if case["round"] == 0:
        return 0
    return rules.broke_last_round(log, case["trial"], case["round"], case["agent"])


def fit_round_rate(cases: list[dict]) -> dict[int, float]:
    """Fit per-round break rates on the given cases (the threshold split)."""
    counts: dict[int, list[int]] = defaultdict(lambda: [0, 0])
    for case in cases:
        counts[case["round"]][0] += int(case["label"])
        counts[case["round"]][1] += 1
    return {r: b / n for r, (b, n) in counts.items()}


def round_rate(table: dict[int, float], case: dict) -> float:
    """Return the fitted break rate for the case's round (overall mean if unseen)."""
    if case["round"] in table:
        return table[case["round"]]
    return sum(table.values()) / len(table) if table else 0.0


def counting(log: dict, case: dict) -> int:
    """Count other round-r announcements matching J's announced action."""
    return rules.pressure(log, case["trial"], case["round"], case["agent"])


def plan(log: dict, case: dict) -> int:
    """Return 1 if the Stage 1 plan differs from the announcement."""
    rec = _trial(log, case["round"], case["trial"])["agents"][case["agent"]]
    planned = norm(rec["stage1"].get("intended_action"))
    said = norm(rec["stage2"].get("stated_action"))
    if planned is None or said is None:
        return 0
    return int(planned != said)


def score_all(logs: dict[str, dict], cases: list[dict], table: dict[int, float]) -> dict[str, list]:
    """Score every case with every baseline."""
    out: dict[str, list] = {name: [] for name in BASELINES}
    for case in cases:
        log = logs[case["source"]]
        out["random"].append(random_score(case))
        out["last_crowded"].append(last_crowded(log, case))
        out["broke_last"].append(broke_last(log, case))
        out["round_rate"].append(round_rate(table, case))
        out["counting"].append(counting(log, case))
        out["plan"].append(plan(log, case))
    return out
