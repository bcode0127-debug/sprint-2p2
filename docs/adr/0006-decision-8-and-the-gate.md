# ADR 0006: Decision 8 and the gate

Date: 2026-10-23 (aligned with docs/preregistration.md the same day). Status: accepted.

## Context

Held-out data (main trials 10 to 39) can only give an honest answer if the analysis is fixed before the monitor sees it. Decision 8, as set out in docs/preregistration.md (DRAFT, NOT FROZEN), is the cross-agent and freshness views (own_only and freshness) plus the Fishing transfer. The Fishing transfer runs only if the primary comparison (Both vs Actions-only, one-sided) succeeds, and it is reported whichever way it lands. The pre-registration also makes S1 (Both vs Own-announcement-only), S2 (Both vs No-current-round) and S3 (the LLM on Both vs the counting rule) a Holm-corrected family. The Fishing label (any change, or over-take only) is still PENDING and must be fixed before any Fishing game runs.

## Decision

No monitor call may be made on a threshold or test case unless `configs/frozen.json` exists with non-empty `prereg_commit` and `osf_url` fields. The check runs when a split is selected and again for every case, using the case's raw identity (main trial 10 or above), so a wrong split label cannot bypass it. Development work loads main trials 0 to 9 only; the dev loader drops later trials before building cases. Tests cover a missing file, empty fields, malformed JSON, the open gate, and the per-case guard.

## Alternatives considered

A convention in the README only (rejected: not enforced). Encrypting the held-out logs (rejected: the raw data is committed and checksummed for reproducibility).

## Consequences

The Fishing transfer is blocked by the same freeze plus the primary result, so it cannot run on a hunch. Writing configs/frozen.json is a deliberate, reviewable act. Until then the pipeline can be exercised only on dev data, which is what the walking skeleton does.
