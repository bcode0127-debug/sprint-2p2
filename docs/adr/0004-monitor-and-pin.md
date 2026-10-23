# ADR 0004: Monitor and pin

Date: 2026-10-23. Status: accepted.

## Context

The monitor is anthropic/claude-haiku-5.5 through OpenRouter. By default it spends its token budget on hidden reasoning, so a 150-token cap returned empty answers (most calls failed to parse). Dev-set rounds compared prompt v0 (AUROC 0.476), v1 (0.479, task text says 'this round' and adds the real protocol) and v2 (v1 with reasoning, AUROC 0.607).

## Decision

The candidate setting is v2: prompt `prompts/monitor_prompt_v1.txt`, scale 0 to 100, reasoning {max_tokens: 1024}, max_tokens 1500, temperature omitted. It is stored only in `configs/monitor.json` and is marked pending a lock. Calls use up to 8 concurrent workers (the key endpoint reports no request cap; the $10 spend cap is the binding limit) with exponential backoff on 429 and 5xx. Every call logs the returned model, prompt and completion tokens and reasoning tokens.

## Alternatives considered

Reasoning off with a small token cap (cleaner and cheaper, but near chance on dev). A larger max_tokens without a reasoning parameter (still reasons, costs more). Another monitor model (not tried in this sprint).

## Consequences

The monitor is not deterministic with reasoning on; a test-retest on the dev set measures how much (DEV-ONLY, results/test_retest_dev.json). Locking the setting needs an explicit decision, after which configs/frozen.json can be written.
