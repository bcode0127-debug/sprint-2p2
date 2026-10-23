"""Score cases with the monitor: gate, view, prompt, call, row."""

import json
import random
from dataclasses import dataclass
from pathlib import Path

from sprint2p2 import monitor, splits, views

SEED = 2026
DEV_TAG = "DEV-ONLY"


@dataclass(frozen=True)
class Runner:
    """Everything needed to score a case: logs, monitor settings and the post function."""

    logs: dict[str, dict]
    cfg: monitor.Config
    post: monitor.Post


def case_id(case: dict) -> str:
    """Return the stable id of a case."""
    return f"{case['source']}|{case['trial']}|{case['round']}|{case['agent']}"


def sample_balanced(cases: list[dict], n: int, seed: int = SEED) -> list[dict]:
    """Pick n cases, half break and half keep, reproducibly."""
    rng = random.Random(seed)  # noqa: S311
    out = []
    for label in (True, False):
        pool = sorted((c for c in cases if c["label"] is label), key=case_id)
        out += rng.sample(pool, n // 2)
    return sorted(out, key=case_id)


def score_case(case: dict, view: str, runner: Runner, frozen_path: Path = splits.FROZEN) -> dict:
    """Gate, build the view, call the monitor and return one score row."""
    splits.guard_case(case, frozen_path)
    cfg, logs = runner.cfg, runner.logs
    record = views.build_view(
        logs[case["source"]], case["trial"], case["round"], case["agent"], view
    )
    prompt = monitor.render_prompt(case["agent"], case["round"], record, cfg.scale, cfg.template)
    res = monitor.monitor_call(prompt, cfg.scale, runner.post, cfg)
    return {
        "tag": DEV_TAG if case["split"] == "dev" else "",
        "id": case_id(case),
        **{k: case[k] for k in ("split", "source", "game", "trial", "round", "agent", "label")},
        "view": view,
        "score": res.score,
        "parse_ok": res.parse_ok,
        "retried": res.retried,
        "models": res.models,
        "prompt_tokens": res.prompt_tokens,
        "completion_tokens": res.completion_tokens,
        "reasoning_tokens": res.reasoning_tokens,
    }


def write_rows(path: Path, rows: list[dict]) -> None:
    """Write rows as JSON lines."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def read_rows(path: Path) -> dict[str, dict]:
    """Read a score file into a dict keyed by case id."""
    rows = [json.loads(line) for line in path.read_text().splitlines() if line]
    return {r["id"]: r for r in rows}
