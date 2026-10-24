# Handoff

Written 2026-10-24 for the next session. Read [../CLAUDE.md](../CLAUDE.md) for the standing rules
and [numbers_to_files.md](numbers_to_files.md) for where every number lives. Main was 708b5e0 when
this was written; this handoff is the merge commit after it.

## Current state

Everything planned is generated, scored and merged. All four held-out splits (threshold, test,
replication, fishing_test) have been scored once; the gates in `configs/frozen.json` are open.
160 tests pass, ruff is clean, and no locked file has changed.

| Milestone | Commit |
|---|---|
| Pre-registration frozen (marker replaced, committed) | 3699338 |
| Freeze record (`configs/frozen.json`) | dfdb9be |
| OSF link recorded (osf.io/buxrm) | 2c7cbfa |
| Threshold scores, then thresholds frozen before any test call | 36fd3a0, 40cb3a7 |
| Test-split scores | a61d1f8 |
| Test analysis merged (`--no-ff`) | 8bb2481 |
| S3 two-sided interval added before the freeze | 738e22e |
| Amendment 1 recorded (OSF update, buxrm) | 5c12546 |
| Replication scored and analyzed | e94ea97 |
| Amendment 1 part 1 merged | bc6f834 |
| Fishing batch A log | 52b898e |
| Fishing batch B log | 1665577 |
| Amendment 1 part 2 merged (Fishing test scored and analyzed) | 42178da |
| Practice run merged (DEV-ONLY PRACTICE) | 708b5e0 |
| GIT_DIR incident fix | 575d537 |
| This handoff | merge commit of branch docs/handoff |

Headline numbers (paired AUROC difference, Both minus Actions-only, one-sided 5th percentile):

| Split | Both vs Actions-only | Difference | 5th percentile | Source |
|---|---|---|---|---|
| Test (registered) | 0.655 vs 0.508 | +0.147 | +0.088 | results/tables/final/tables.json |
| Replication (Amendment 1) | 0.668 vs 0.501 | +0.167 | +0.133 | results/tables/replication/tables.json |
| Fishing transfer (Amendment 1) | 0.650 vs 0.536 | +0.114 | +0.072 | results/tables/fishing_test/tables.json |

S3 (Both vs the counting rule) was not rejected on test or replication. C1 and C2 are in
results/tables/replication/extras.json.

## The Oct 24 GIT_DIR incident

1. A commit hook run inside a linked worktree exported `GIT_DIR`, so the freeze tests ran `git init`
   and `git config` against the real repository: `core.bare` became true, the repo identity became
   `t`, and seven tracked files in the worktree were overwritten with test fixtures.
2. I restored the config and files, confirmed GitHub main was untouched (bc6f834) and every hash in
   `configs/frozen.json` matched, then verified refs and the remote URL.
3. Fix 575d537: `scripts/freeze.py` drops git's structural variables (`clean_git_env()`), the freeze
   tests use it, and a test sets those variables to a decoy path. Avoid worktrees anyway.

## Where results live

See [numbers_to_files.md](numbers_to_files.md), which covers the registered results, the
replication, Fishing, development and practice files, and the command that reproduces each.
Quick reproductions without any API call:

```bash
make reproduce                                    # primary row on the test split, with its SHA-256
PYTHONPATH=src .venv/bin/python -m scripts.analyze              # results/tables/final
PYTHONPATH=src .venv/bin/python -m scripts.analyze_replication  # results/tables/replication
PYTHONPATH=src .venv/bin/python -m scripts.recalibrate_replication
PYTHONPATH=src .venv/bin/python -m scripts.analyze_fishing      # results/tables/fishing_test
PYTHONPATH=src .venv/bin/python -m scripts.analyze_practice     # needs run-logs/retest_run2.jsonl
```

## Environment facts to know

- OpenRouter key: limit $50, expires 2026-10-30T15:02Z, usage about $17.14 on Oct 24. Zay topped up
  OpenAI by $20 for the Fishing batches.
- The harness checkout `harness/` (git-ignored, needed only for generation and the pilot summary)
  is at commit fd11aca. Agent model is `gpt-5.2`, which resolved to `gpt-5.2-2025-12-11` on every pin.
- Out-of-repo files are in `~/apart-sprint/docs/`: the frozen plan copy and hash that went to OSF,
  the drafts, and `run-logs/` with logs and score caches.

## Open items

1. Report: figures and tables (make them only when asked; no prose written by the agent).
2. README: add results, mark which code is pre-existing (the harness) and which is new, and add the
   harness attribution (repository URL and commit; the harness has no license, so it is not
   redistributed). PROVENANCE.md already says this and can be linked.
3. Public-repo checks before making the repo public: scan the whole git history for key patterns
   (`git log -p | grep -E "sk-[A-Za-z0-9_-]{20,}"` returned nothing at the last check), confirm
   `.env`, `harness/`, `outputs/` and `.venv/` are ignored and absent from history, and decide
   about transferring the repo to Zay's main account (pending his decision).
4. Post-sprint cleanup: `gh auth logout` for the `~/.gh-zay` config, delete `~/.gh-zay`, and delete
   the copy of the token. Rotate or delete the OpenRouter and OpenAI keys if they are not reused.
5. Optional, only if instructed: nothing further is registered. The "not added" ideas in
   Amendment 1 section 5 (stronger monitor, larger reasoning budget, averaging calls) stay future
   work; the practice results in results/practice_monitors_dev.md are exploration only.
