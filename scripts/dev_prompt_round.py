"""Prompt-fix round on the development set only (pilot rounds 1-9, main trials 0-9).

Run from the project root with: PYTHONPATH=src .venv/bin/python -m scripts.dev_prompt_round
"""

import json
import random
import statistics
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from scripts.pilot_summary import PILOTS
from scripts.spike_scale import auroc, read_key
from sprint2p2 import data, monitor, rules, views

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
CACHE = Path.home() / "apart-sprint" / "docs" / "run-logs"
MAIN = ROOT / "harness/outputs/experiments/elfarol/5agents/gpt-5.2_endogenous_main.json"
SCALE = 100
N_BOOT = 2000
SEED = 7
PRICE_PROMPT = 1e-7
PRICE_COMPLETION = 5e-7
EXPECTED = {"pilot": 135, "main": 450}
RULES = ("rule_pressure", "rule_broke_last", "rule_last_crowded")
QUANTILES = (0, 0.25, 0.5, 0.75, 1)


def guard(case: dict) -> None:
    """Refuse to let a held-out main-run trial reach the monitor."""
    if case["source"] == "main" and case["trial"] > data.DEV_MAX_MAIN_TRIAL:
        msg = "held-out trial"
        raise ValueError(msg)


def build_cases() -> tuple[list[dict], dict[str, dict]]:
    """Return the 585 dev cases (with rule values) and the logs by source."""
    logs = {"pilot": data.dev_log(PILOTS["elfarol"], "pilot"), "main": data.dev_log(MAIN, "main")}
    cases = []
    for source, log in logs.items():
        found = data.dev_cases(log, source)
        if len(found) != EXPECTED[source]:
            msg = f"{source}: expected {EXPECTED[source]} cases, got {len(found)}"
            raise SystemExit(msg)
        for case in found:
            t, r, a = case["trial"], case["round"], case["agent"]
            case["rule_pressure"] = rules.pressure(log, t, r, a)
            case["rule_broke_last"] = rules.broke_last_round(log, t, r, a)
            case["rule_last_crowded"] = rules.last_round_crowded(log, t, r)
        cases += found
    return cases, logs


def run_variant(name: str, cases: list[dict], logs: dict, post: monitor.Post) -> list[dict]:
    """Run one variant over all cases, caching raw results on disk."""
    path = CACHE / f"dev_calls_{name}.json"
    if path.exists():
        return json.loads(path.read_text())
    cfg = monitor.VARIANTS[name]

    def one(case: dict) -> dict:
        guard(case)
        log = logs[case["source"]]
        record = views.build_both_view(log, case["trial"], case["round"], case["agent"])
        prompt = monitor.render_prompt(case["agent"], case["round"], record, SCALE, cfg.template)
        res = monitor.monitor_call(prompt, SCALE, post, cfg)
        return {
            "score": res.score,
            "parse_ok": res.parse_ok,
            "retried": res.retried,
            "models": res.models,
            "prompt_tokens": res.prompt_tokens,
            "completion_tokens": res.completion_tokens,
            "reasoning_tokens": res.reasoning_tokens,
        }

    with ThreadPoolExecutor(max_workers=8) as pool:
        out = list(pool.map(one, cases))
    CACHE.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out))
    return out


def bootstrap_ci(cases: list[dict], scores: list[float | None]) -> list[float | None]:
    """95% interval for AUROC, resampling whole games."""
    by_game: dict[str, list[tuple[float, bool]]] = {}
    for case, score in zip(cases, scores, strict=True):
        if score is not None:
            by_game.setdefault(case["game"], []).append((score, case["label"]))
    games = sorted(by_game)
    rng = random.Random(SEED)  # noqa: S311
    stats = []
    for _ in range(N_BOOT):
        pairs = [p for g in rng.choices(games, k=len(games)) for p in by_game[g]]
        value = auroc([s for s, _ in pairs], [lab for _, lab in pairs])
        if value is not None:
            stats.append(value)
    stats.sort()
    if not stats:
        return [None, None]
    return [stats[int(0.025 * len(stats))], stats[int(0.975 * len(stats)) - 1]]


def distribution(scores: list[int]) -> dict:
    """Summarise a score distribution and its largest tie group."""
    counts = Counter(scores)
    value, size = counts.most_common(1)[0] if counts else (None, 0)
    ordered = sorted(scores)
    quant = (
        {str(q): ordered[min(int(q * len(ordered)), len(ordered) - 1)] for q in QUANTILES}
        if ordered
        else {}
    )
    return {
        "n": len(scores),
        "distinct_values": len(counts),
        "largest_tie_group": {"value": value, "count": size, "share": size / max(len(scores), 1)},
        "mean": statistics.fmean(scores) if scores else None,
        "quantiles": quant,
        "top_values": counts.most_common(12),
    }


def score_block(cases: list[dict], scores: list[float | None]) -> dict:
    """AUROC with interval and distribution for one scorer."""
    valid = [(c, s) for c, s in zip(cases, scores, strict=True) if s is not None]
    point = auroc([s for _, s in valid], [c["label"] for c, _ in valid])
    return {
        "auroc": point,
        "auroc_ci95": bootstrap_ci(cases, scores),
        "distribution": distribution([s for _, s in valid]),
    }


def variant_block(cases: list[dict], calls: list[dict]) -> dict:
    """Score block plus parse, token and cost totals for one LLM variant."""
    scores = [c["score"] if c["parse_ok"] else None for c in calls]
    prompt = sum(c["prompt_tokens"] for c in calls)
    completion = sum(c["completion_tokens"] for c in calls)
    return {
        **score_block(cases, scores),
        "parse_failures": sum(not c["parse_ok"] for c in calls),
        "retries": sum(c["retried"] for c in calls),
        "reasoning_tokens": sum(c["reasoning_tokens"] for c in calls),
        "tokens": {"prompt": prompt, "completion": completion},
        "estimated_cost_usd": prompt * PRICE_PROMPT + completion * PRICE_COMPLETION,
        "returned_models": sorted({m for c in calls for m in c["models"]}),
    }


def main() -> None:
    """Run all variants and rules on the dev set and write results/dev_prompt_round.json."""
    cases, logs = build_cases()
    post = monitor.make_post(read_key())
    calls = {v: run_variant(v, cases, logs, post) for v in monitor.VARIANTS}
    result = {
        "dev_set": {
            "pilot_rounds_1_9": EXPECTED["pilot"],
            "main_trials_0_9_rounds_1_9": EXPECTED["main"],
        },
        "n_cases": len(cases),
        "n_games": len({c["game"] for c in cases}),
        "break_rate": sum(c["label"] for c in cases) / len(cases),
        "bootstrap": {"resample": "whole games", "n": N_BOOT, "seed": SEED},
        "variants": {v: variant_block(cases, calls[v]) for v in monitor.VARIANTS},
        "rules": {r: score_block(cases, [c[r] for c in cases]) for r in RULES},
        "cases": [
            {
                **{k: c[k] for k in ("source", "trial", "round", "agent", "label", *RULES)},
                **{f"score_{v}": calls[v][i]["score"] for v in calls},
            }
            for i, c in enumerate(cases)
        ],
    }
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "dev_prompt_round.json").write_text(json.dumps(result, indent=2) + "\n")
    bad = sum(calls[v][i]["reasoning_tokens"] for v in ("v0", "v1") for i in range(len(cases)))
    if bad:
        msg = f"reasoning tokens in non-reasoning variants: {bad}"
        raise SystemExit(msg)


if __name__ == "__main__":
    main()
