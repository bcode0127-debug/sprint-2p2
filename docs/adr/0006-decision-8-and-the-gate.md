# ADR 0006: Decision 8 and the gate

Date: 2026-10-23. Status: accepted.

## Context

Held-out data (main trials 10 to 39) can only give an honest answer if the analysis is fixed before the monitor sees it. The sprint plan refers to this as decision 8; that plan is not stored in this repository, so this ADR records only the mechanism we built.

## Decision

No monitor call may be made on a threshold or test case unless `configs/frozen.json` exists with non-empty `prereg_commit` and `osf_url` fields. The check runs when a split is selected and again for every case, using the case's raw identity (main trial 10 or above), so a wrong split label cannot bypass it. Development work loads main trials 0 to 9 only; the dev loader drops later trials before building cases. Tests cover a missing file, empty fields, malformed JSON, the open gate, and the per-case guard.

## Alternatives considered

A convention in the README only (rejected: not enforced). Encrypting the held-out logs (rejected: the raw data is committed and checksummed for reproducibility).

## Consequences

Writing configs/frozen.json is a deliberate, reviewable act. Until then the pipeline can be exercised only on dev data, which is what the walking skeleton does.
