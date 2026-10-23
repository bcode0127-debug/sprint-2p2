"""Score-scale spike: run the monitor at SCALE 100 and 1000 on 60 pilot cases.

Run from the project root with: PYTHONPATH=src .venv/bin/python -m scripts.spike_scale
"""

import json
import random
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from scripts.pilot_summary import PILOTS, break_flag
from sprint2p2 import monitor, views

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
SEED = 7
PER_LABEL = 30
SCALES = (100, 1000)
PRICE_PROMPT = 1e-7
PRICE_COMPLETION = 5e-7


def read_key() -> str:
    """Return OPENROUTER_API_KEY from .env without echoing it."""
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip()
    msg = "OPENROUTER_API_KEY missing"
    raise SystemExit(msg)


def sample_cases(log: dict) -> list[dict]:
    """Sample 30 break and 30 non-break agent-rounds from rounds 1 to 9."""
    pools: dict[bool, list[tuple[int, int, str]]] = {True: [], False: []}
    for rnd in log["rounds"]:
        if rnd["round_id"] < 1:
            continue
        for trial in rnd["trials"]:
            for name, rec in trial["agents"].items():
                flag = break_flag("elfarol", rec)
                if flag is not None:
                    pools[flag].append((trial["trial_id"], rnd["round_id"], name))
    rng = random.Random(SEED)  # noqa: S311
    picked = []
    for label in (True, False):
        pool = sorted(pools[label])
        picked += [(*ids, label) for ids in rng.sample(pool, PER_LABEL)]
    rng.shuffle(picked)
    return [{"trial": t, "round": r, "agent": a, "label": lab} for t, r, a, lab in picked]


def auroc(scores: list[int], labels: list[bool]) -> float | None:
    """Rank-based AUROC with average ranks for ties; None if one class is empty."""
    pos = [s for s, lab in zip(scores, labels, strict=True) if lab]
    neg = [s for s, lab in zip(scores, labels, strict=True) if not lab]
    if not pos or not neg:
        return None
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def run_case(case: dict, log: dict, post: monitor.Post) -> dict:
    """Run both scales on one case."""
    record = views.build_both_view(log, case["trial"], case["round"], case["agent"])
    out = {**case, "id": [case["trial"], case["round"], case["agent"]]}
    for scale in SCALES:
        prompt = monitor.render_prompt(case["agent"], case["round"], record, scale)
        res = monitor.monitor_call(prompt, scale, post)
        out[f"score_{scale}"] = res.score
        out[f"parse_ok_{scale}"] = res.parse_ok
        out[f"retried_{scale}"] = res.retried
        out[f"models_{scale}"] = res.models
        out[f"tokens_{scale}"] = {"prompt": res.prompt_tokens, "completion": res.completion_tokens}
        out[f"reasoning_tokens_{scale}"] = res.reasoning_tokens
    return out


def scale_stats(rows: list[dict], scale: int) -> dict:
    """Distinct values, largest tie group, parse failures and AUROC for one scale."""
    ok = [r for r in rows if r[f"parse_ok_{scale}"]]
    counts = Counter(r[f"score_{scale}"] for r in ok)
    value, size = counts.most_common(1)[0] if counts else (None, 0)
    return {
        "distinct_values": len(counts),
        "largest_tie_group": {"value": value, "count": size, "share": size / len(rows)},
        "parse_failures": len(rows) - len(ok),
        "auroc": auroc([r[f"score_{scale}"] for r in ok], [r["label"] for r in ok]),
    }


def main() -> None:
    """Sample, run 120 calls, and write results/spike_scale.json."""
    log = json.loads(PILOTS["elfarol"].read_text())
    cases = sample_cases(log)
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "spike_sample_ids.json").write_text(
        json.dumps([[c["trial"], c["round"], c["agent"], c["label"]] for c in cases]) + "\n",
    )
    post = monitor.make_post(read_key())
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(lambda c: run_case(c, log, post), cases))
    tokens = {"prompt": 0, "completion": 0}
    models = set()
    for row in rows:
        for scale in SCALES:
            tokens["prompt"] += row[f"tokens_{scale}"]["prompt"]
            tokens["completion"] += row[f"tokens_{scale}"]["completion"]
            models.update(row[f"models_{scale}"])
    reasoning = sum(row[f"reasoning_tokens_{s}"] for row in rows for s in SCALES)
    cost = tokens["prompt"] * PRICE_PROMPT + tokens["completion"] * PRICE_COMPLETION
    summary = {
        "source": "pilot file, rounds 1 to 9",
        "seed": SEED,
        "n_cases": len(rows),
        "per_scale": {str(s): scale_stats(rows, s) for s in SCALES},
        "total_tokens": tokens,
        "reasoning_param": monitor.VARIANTS["v0"].reasoning,
        "total_reasoning_tokens": reasoning,
        "returned_models": sorted(models),
        "estimated_cost_usd": cost,
        "pricing_per_token": {"prompt": PRICE_PROMPT, "completion": PRICE_COMPLETION},
        "cases": rows,
    }
    (RESULTS / "spike_scale.json").write_text(json.dumps(summary, indent=2) + "\n")
    if reasoning:
        msg = f"reasoning_tokens must be 0, got {reasoning}"
        raise SystemExit(msg)


if __name__ == "__main__":
    main()
