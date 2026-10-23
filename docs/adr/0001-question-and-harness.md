# ADR 0001: Question and harness

Date: 2026-10-23. Status: accepted.

## Context

We want to know whether a separate monitor can predict, from the public record alone, that a GPT-5.2 agent will break its own announcement in a repeated El Farol game. An existing harness (Jerick-1380/LLM-Trust-Breaking, commit fd11aca351e52c65c929e1a7d46d9f087f237adf) already runs announce-then-choose rounds and logs every stage. The harness repository has no LICENSE file.

## Decision

Use the harness unmodified, cloned into `harness/` (git-ignored) at the pinned commit, and never redistribute it. Everything we write lives outside it. Agents run through the harness's queued OpenAI client with `--model gpt-5.2` (bare name), because that client matches model names exactly and does not recognise the dated id or an `openai/` prefix. The model that answered is recorded in `results/model_pin.json` before and after each run (it returned `gpt-5.2-2025-12-11`). Provenance is stated in `PROVENANCE.md`.

## Alternatives considered

Patch the harness to accept the dated model id (rejected: breaks the unmodified claim). Write our own game runner (rejected: loses the existing, reviewed stage structure). Vendor the harness into this repo (rejected: no licence to redistribute).

## Consequences

Results depend on a third-party commit we cannot change. The harness does not log token usage, so agent cost is unrecorded. The judge call hard-codes `openai/gpt-5-mini` and fails by design here; we do not use the judge label and compute our own break flag from raw fields.
