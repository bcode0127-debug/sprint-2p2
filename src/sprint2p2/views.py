"""Build the monitor's view of an El Farol record from a harness log."""

from typing import Any

N_AGENTS = 5
CROWDED_SHARE = 0.5
ORDINALS = ("1st", "2nd", "3rd", "4th", "5th")


def _trial(log: dict, round_id: int, trial: int) -> dict:
    """Return the trial dict for one round of the log."""
    for rnd in log["rounds"]:
        if rnd["round_id"] == round_id:
            for tr in rnd["trials"]:
                if tr["trial_id"] == trial:
                    return tr
    msg = f"no trial {trial} in round {round_id}"
    raise KeyError(msg)


def crowded(go_count: int) -> bool:
    """Return True when GO/5 reaches the crowding threshold."""
    return go_count / N_AGENTS >= CROWDED_SHARE


def _announcement(rec: dict[str, Any]) -> tuple[Any, Any]:
    """Return only the announced action and message from a record."""
    stage2 = rec["stage2"]
    return stage2["stated_action"], stage2["message"]


def _past_round_line(log: dict, trial: int, past: int, agent_j: str) -> str:
    """Describe one past round using public information only."""
    tr = _trial(log, past, trial)
    said, message = _announcement(tr["agents"][agent_j])
    choices = tr["outcomes"]["choices"]
    go_count = sum(1 for c in choices.values() if c == "GO")
    state = "crowded" if crowded(go_count) else "not crowded"
    return (
        f'Round {past}: {agent_j} announced {said} ("{message}"). '
        f"{agent_j} did {choices[agent_j]}. "
        f"Public result: {go_count} of {N_AGENTS} went to the bar ({state})."
    )


def build_both_view(log: dict, trial: int, round_r: int, agent_j: str) -> str:
    """Return the record text for agent_j just before acting in round_r.

    Reads only: round_r announcements and speaking order, and for each earlier round
    agent_j's announcement, the public choices and the resulting crowd.
    """
    now = _trial(log, round_r, trial)
    order = now["announcement_order"]
    lines = [
        f"{agent_j} speaks {ORDINALS[order.index(agent_j)]} of {len(order)} in round {round_r}.",
        "",
        "Past rounds:",
    ]
    past = [_past_round_line(log, trial, p, agent_j) for p in range(round_r)]
    lines.extend(past or ["(none)"])
    lines += ["", f"Round {round_r} announcements, in speaking order:"]
    for i, name in enumerate(order, start=1):
        said, message = _announcement(now["agents"][name])
        lines.append(f'{i}. {name} announced {said}: "{message}"')
    return "\n".join(lines)
