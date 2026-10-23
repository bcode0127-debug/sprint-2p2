"""No-LLM baseline rules, computed from information available before J's choice."""

from sprint2p2.data import break_flag, norm
from sprint2p2.views import _trial, crowded


def pressure(log: dict, trial: int, round_r: int, agent: str) -> int:
    """Count other round-r announcements on the same side as the agent's own."""
    agents = _trial(log, round_r, trial)["agents"]
    mine = norm(agents[agent]["stage2"]["stated_action"])
    return sum(
        norm(rec["stage2"]["stated_action"]) == mine
        for name, rec in agents.items()
        if name != agent
    )


def broke_last_round(log: dict, trial: int, round_r: int, agent: str) -> int:
    """Return 1 if the agent's choice differed from its announcement last round."""
    flag = break_flag(_trial(log, round_r - 1, trial)["agents"][agent])
    return int(bool(flag))


def last_round_crowded(log: dict, trial: int, round_r: int) -> int:
    """Return 1 if last round's public result was crowded."""
    choices = _trial(log, round_r - 1, trial)["outcomes"]["choices"]
    return int(crowded(sum(1 for c in choices.values() if c == "GO")))
