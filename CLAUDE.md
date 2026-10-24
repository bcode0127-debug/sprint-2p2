# CLAUDE.md

Standing rules for any agent working in this repository. Read this file and docs/HANDOFF.md first.

## What this repo is

A pre-registered study (OSF osf.io/buxrm, plus Amendment 1): do announcements help a text monitor
(Claude Haiku 5.5 through OpenRouter) predict that a GPT-5.2 agent will break its announced action
in a 5-agent El Farol game? The Fishing transfer repeats the test in a second game. Code is in
`src/sprint2p2/` and `scripts/`, data in `data/raw/`, scores in `scores/`, results in `results/`,
plan in `docs/preregistration.md` and `docs/amendment1.md`.

## Environment

- Python: `.venv/bin/python`. Run modules as `PYTHONPATH=src .venv/bin/python -m scripts.<name>`.
- Tests: `.venv/bin/pytest -q`. Lint: `.venv/bin/ruff check src tests scripts`. Hooks: pre-commit
  runs ruff check, ruff format, pytest and a key-pattern scan on every commit (about 45 seconds).
- A commit that fails a hook does not land and prints little. After every commit run
  `git rev-parse --short HEAD` and confirm the hash changed.
- Keys live in `.env` (OPENAI_API_KEY for the agents, OPENROUTER_API_KEY for the monitor).
- Out-of-repo files in `~/apart-sprint/docs/`: the frozen plan copies, drafts, and
  `run-logs/` (logs, timing files, and score caches such as `retest_run2.jsonl`, `devall_*.jsonl`,
  `dev_calls_v*.json`). Some no-API reproductions read those caches.

## Secrets and files that never go into git

1. Never read `.env`. To check a key, print only "set" or "missing". Never paste a key value into
   a command, a file, a commit, a log or a message. Scripts read the key themselves.
2. Never commit `harness/`, `outputs/`, `.env` or `.venv/`. They are in `.gitignore`.
3. The harness (github.com/Jerick-1380/LLM-Trust-Breaking, commit fd11aca) has no license. Use it
   unmodified and never redistribute it. PROVENANCE.md states this.
4. `data/raw/` is read-only. Its checksums are in `data/raw/SHA256SUMS`. Before committing any
   data, scan it for key patterns (`sk-[A-Za-z0-9_-]{20,}`).
5. No em dashes in any file.

## Git workflow

1. Never commit to main. One branch per task, one commit per step, merge with `git merge --no-ff`,
   then delete the branch locally and on origin (`git push origin --delete <branch>`).
2. Avoid git worktrees. If one is ever needed, any tool or test that runs git must clear
   `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE` and the related variables first
   (`scripts/freeze.py` has `clean_git_env()`). The Oct 24 incident: a commit hook in a linked
   worktree exported `GIT_DIR`, and the freeze tests then rewrote the shared repo config and the
   worktree's tracked files. See docs/HANDOFF.md.
3. `gh` runs with `GH_CONFIG_DIR=~/.gh-zay` (for example
   `GH_CONFIG_DIR=$HOME/.gh-zay /opt/homebrew/bin/gh ...`). The repo-local git config holds the
   identity (bcode0127-debug) and the credential helper. Never touch the global git config or
   `~/.config`.
4. Tests, ruff and the pre-commit hooks must pass before any merge.

## Locked files: never edit

`tests/test_locked_files.py` fails if any of these changes. SHA-256 values:

| File | SHA-256 |
|---|---|
| docs/amendment1.md | 72510f08c4653003ac00040059cfc3e93c826755ff94c644f033049785ce1256 |
| docs/preregistration.md | a07ea2f7a2be513a06b594f431ae504bb0851f88518e4a048afd73cffaac34e9 |
| configs/monitor.json | bc6da2d7c5df992bc7ce2423f7b248308e65d5735b96e806a2e6a25acfb5ecb1 |
| prompts/monitor_prompt_v1.txt | a526d0d078e2056c58f7d6a9a583e176b7dc8b03f30d4b4ac918d4ca54678844 |
| prompts/monitor_prompt_fishing_v1.txt | 56554ad64b0df8ee4712e7bebe86b671cb18b1b8f26511af60ec7018dcec8f75 |
| src/sprint2p2/views.py | 6607cd0f4bb4935325914b7b6e14b98462ca83cd0c3a26bb8b0c21c03934e3f5 |
| src/sprint2p2/metrics.py | c8b845c061b166ed64503f0042ed40a239ce550734feb910c8218503794acf08 |
| src/sprint2p2/analysis.py | ee517880765422d90e597555291674e5a1fa80584664e95cd7a4e8ba843a4475 |
| src/sprint2p2/baselines.py | c4ce6e615854a335d55c025a7cd847a166e6ad287c07e8ad84d6e5df8202ca7d |
| scripts/analyze.py | 9c4419cfd39122999a97d88dd436daa0000e39565a6b6176e8d20c02e36c3bdd |

The same test also pins three raw logs: `data/raw/elfarol_rep_gpt-5.2.json`
(7c2f040a...), `fishing_fishpilot_gpt-5.2.json` (98c42a74...), `fishing_pilot_gpt-5.2.json`
(24936ea4...). New work goes in new files; wrappers call locked code unchanged.

## Gates: never bypass

`configs/frozen.json` and `src/sprint2p2/splits.py` gate every monitor call on held-out data:

- threshold: needs `prereg_commit` and `osf_url`.
- test: also needs per-view `t` and `q` (written by `scripts/fit_thresholds.py`).
- replication: test requirements plus `amendment1_url`.
- fishing_test: test requirements plus `amendment1_url`, and both batch logs must exist.

All four are open today, and every one of those splits has been scored once. Score a gated split
again only on an explicit instruction. Never edit the gate, the freeze file or the thresholds to
get a run through. Development data (pilot plus main trials 0 to 9, rounds 1 to 9) is the only
split that may be used freely.

## Tags and what counts as a result

- Anything tagged DEV-ONLY or DEV-ONLY PRACTICE is exploration. Never report it as a registered
  result, never mix it into a registered table.
- Registered results: `results/tables/final/` (test), `results/tables/replication/` (Amendment 1
  replication) and `results/tables/fishing_test/` (Amendment 1 Fishing transfer). Everything else
  is development or practice.

## Generation and scoring discipline

1. Run `scripts/model_pin.py` before and after any generation (`scripts/run_games.sh` does this).
   It appends to `results/model_pin.json`.
2. The overwrite guard in `scripts/run_games.sh` refuses when an output file exists. Never remove
   it and never delete an output to get around it.
3. Never rerun failed games without asking. If generation stops on a credit error, commit what
   completed and report the shortfall.
4. Print OpenRouter usage (`GET /api/v1/key`, usage and limit) before and after any scoring.
   Every task packet states a floor for remaining credit. If remaining credit is below the floor,
   HOLD and report. If a packet states none, ask. Scoring scripts also run a spend guard.
5. Run long jobs in the background (`nohup`, with a log and a `.done` marker) and wait for them.
   Never edit a shell script while it runs.
6. Do not look at labels or break rates of data that a plan says must not be inspected yet.

## Reporting

1. Never write report prose. Make tables and figures only when asked.
2. Every report back gives numbers together with their source files, says what was not done,
   and then HOLDs. Do not start the next task unasked.
3. Say plainly when a step failed or a commit did not land.
