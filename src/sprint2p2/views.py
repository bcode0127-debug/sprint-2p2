"""Build the monitor's view of an El Farol record from a harness log.

Every view is built only from raw fields. No view reads stage1, reflection,
commitment_breaking, typology, judge or payoffs, and no view except the oracle
reads a round-r choice.
"""

from typing import Any

N_AGENTS = 5
N_ROUNDS = 10
CROWDED_SHARE = 0.5
ORDINALS = ("1st", "2nd", "3rd", "4th", "5th")
VIEWS = (
    "actions_only",
    "messages_only",
    "both",
    "structured",
    "own_only",
    "freshness",
    "oracle",
    "empty",
    "round_only",
)
NO_POSITION = ("empty", "round_only")


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


def _public(tr: dict) -> tuple[dict, int, str]:
    """Return a past round's public choices, GO count and crowd state."""
    choices = tr["outcomes"]["choices"]
    go_count = sum(1 for c in choices.values() if c == "GO")
    return choices, go_count, "crowded" if crowded(go_count) else "not crowded"


def _position(order: list[str], agent_j: str, round_r: int) -> str:
    """Return the speaking position line."""
    return f"{agent_j} speaks {ORDINALS[order.index(agent_j)]} of {len(order)} in round {round_r}."


def _past_both(log: dict, trial: int, past: int, agent_j: str) -> str:
    """Describe one past round: announcement, action and public result."""
    tr = _trial(log, past, trial)
    said, message = _announcement(tr["agents"][agent_j])
    choices, go_count, state = _public(tr)
    return (
        f'Round {past}: {agent_j} announced {said} ("{message}"). '
        f"{agent_j} did {choices[agent_j]}. "
        f"Public result: {go_count} of {N_AGENTS} went to the bar ({state})."
    )


def _past_actions(log: dict, trial: int, past: int, agent_j: str) -> str:
    """Describe one past round without any announcement."""
    choices, go_count, state = _public(_trial(log, past, trial))
    return (
        f"Round {past}: {agent_j} did {choices[agent_j]}. "
        f"Public result: {go_count} of {N_AGENTS} went to the bar ({state})."
    )


def _past_messages(log: dict, trial: int, past: int, agent_j: str) -> str:
    """Describe one past round with the announcement only."""
    said, message = _announcement(_trial(log, past, trial)["agents"][agent_j])
    return f'Round {past}: {agent_j} announced {said} ("{message}").'


def _structured_row(log: dict, trial: int, past: int, agent_j: str) -> str:
    """Describe one past round as a table row with no message text."""
    tr = _trial(log, past, trial)
    claim = tr["agents"][agent_j]["stage2"]["stated_action"]
    choices, go_count, state = _public(tr)
    action = choices[agent_j]
    if claim is None or action is None:
        kept = "unknown"
    else:
        kept = "kept" if str(claim).strip().upper() == str(action).strip().upper() else "broke"
    return f"| {past} | {claim} | {action} | {kept} | {go_count} of {N_AGENTS} went, {state} |"


def _past_block(log: dict, trial: int, round_r: int, agent_j: str, fn: Any) -> list[str]:  # noqa: ANN401
    """Join the per-round lines of J's past rounds."""
    return [fn(log, trial, p, agent_j) for p in range(round_r)] or ["(none)"]


def _announcements(now: dict, agent_j: str | None, *, with_text: bool) -> list[str]:
    """List round-r announcements in speaking order; agent_j limits to one speaker."""
    lines = []
    for i, name in enumerate(now["announcement_order"], start=1):
        if agent_j is not None and name != agent_j:
            continue
        said, message = _announcement(now["agents"][name])
        if with_text:
            lines.append(f'{i}. {name} announced {said}: "{message}"')
        else:
            lines.append(f"{i}. {name}: {said}")
    return lines


def build_view(log: dict, trial: int, round_r: int, agent_j: str, view: str) -> str:
    """Return the record text for agent_j just before acting in round_r."""
    if view == "empty":
        return "(no record)"
    if view == "round_only":
        return f"This is round {round_r} of {N_ROUNDS}."
    now = _trial(log, round_r, trial)
    head = [_position(now["announcement_order"], agent_j, round_r), ""]
    header = f"Round {round_r} announcements, in speaking order:"
    if view == "actions_only":
        body = ["Past rounds:", *_past_block(log, trial, round_r, agent_j, _past_actions)]
    elif view == "messages_only":
        body = ["Past rounds:", *_past_block(log, trial, round_r, agent_j, _past_messages)]
        body += ["", header, *_announcements(now, None, with_text=True)]
    elif view == "structured":
        body = [
            f"{agent_j}'s past rounds:",
            "| round | claim | action | kept or broke | crowd result |",
            *_past_block(log, trial, round_r, agent_j, _structured_row),
            "",
            f"Round {round_r} stated actions, in speaking order:",
            *_announcements(now, None, with_text=False),
        ]
    elif view in ("both", "oracle", "own_only", "freshness"):
        body = ["Past rounds:", *_past_block(log, trial, round_r, agent_j, _past_both)]
        if view in ("both", "oracle"):
            body += ["", header, *_announcements(now, None, with_text=True)]
        elif view == "own_only":
            body += ["", header, *_announcements(now, agent_j, with_text=True)]
        if view == "oracle":
            action = now["agents"][agent_j]["stage3"]["choice"]
            body += ["", f"{agent_j}'s actual action in round {round_r}: {action}"]
    else:
        msg = f"unknown view {view}"
        raise ValueError(msg)
    return "\n".join([*head, *body])


def build_both_view(log: dict, trial: int, round_r: int, agent_j: str) -> str:
    """Return the both view (kept for earlier scripts)."""
    return build_view(log, trial, round_r, agent_j, "both")
