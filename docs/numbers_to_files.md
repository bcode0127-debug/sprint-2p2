# Numbers to files

Every number quoted in a write-up maps to one file here. Rows tagged DEV-ONLY or DEV-ONLY PRACTICE
are development or exploration and are never registered results. See [HANDOFF.md](HANDOFF.md) for
the current state and [../CLAUDE.md](../CLAUDE.md) for the standing rules.

Commands use `PY = PYTHONPATH=src .venv/bin/python`, run from the repo root. "No API" means the
command reads committed files only (a few also read caches in `~/apart-sprint/docs/run-logs/`).
"API" means it calls a model unless its cache is present; do not run those without instruction.

## Registered results

| Result | File | Reproduce | API |
|---|---|---|---|
| Test split: primary row (paired AUROC difference, Both minus Actions-only) | results/tables/final/tables.json (primary) | `make reproduce` (prints the row and its SHA-256) | no |
| Test split: S1 to S3 with Holm, deployment reading, controls, round 0, by agent, by break type, power | results/tables/final/tables.json and tables.md | `$PY -m scripts.analyze` | no |
| Replication (20 El Farol games): same tables | results/tables/replication/tables.json and tables.md | `$PY -m scripts.analyze_replication` | no |
| Replication: per-game means and C1, C2 (combination with the counting rule) | results/tables/replication/extras.json | `$PY -m scripts.analyze_replication` | no |
| Replication: recalibration on trials 10 to 19 (frozen vs refit thresholds) | results/tables/replication/recalibration.json | `$PY -m scripts.recalibrate_replication` | no |
| Fishing transfer (40 games): single test and descriptive tables | results/tables/fishing_test/tables.json and tables.md | `$PY -m scripts.analyze_fishing` | no |
| AUROC of Both by harness break type (premeditated deception, impulsive deviation) against all keeps, test and replication; descriptive | results/tables/break_type_auroc.json | `$PY -m scripts.break_type_auroc` | no |
| Report figures 1 to 3 (PNG and PDF) and the values plotted | results/figures/ (figure_data.json holds every plotted value) | `$PY -m scripts.make_figures` | no |
| Report Tables 1 and 2 | results/report_tables.md | `$PY -m scripts.make_figures` | no |
| Monitor scores behind the tables above | scores/threshold, scores/test, scores/replication, scores/fishing_test (one jsonl per view or rule) | `$PY -m scripts.score_views --split <split> --baselines` and `$PY -m scripts.score_fishing --split fishing_test` (already run once; do not rerun) | yes |
| Thresholds and freeze record | configs/frozen.json | `$PY -m scripts.freeze` then `$PY -m scripts.fit_thresholds` (already run once) | no |
| Raw agent logs and checksums | data/raw/ and data/raw/SHA256SUMS | `scripts/run_games.sh` (already run once; the guard refuses reruns) | yes |
| Model pins before and after each generation | results/model_pin.json | written by `scripts/model_pin.py` | yes |

## Development results (DEV-ONLY)

| Result | File | Reproduce | API |
|---|---|---|---|
| Prompt rounds v0, v1, v2 and no-LLM rules (585 cases) | results/dev_prompt_round.json | `$PY -m scripts.dev_prompt_round` (cached calls in run-logs) | yes |
| All views on the development set, contrasts, controls | results/dev_all_views.json and .md | `$PY -m scripts.dev_all_views` (cached in run-logs) | yes |
| Dev-only analysis tables on dev scores | results/tables/DEV-ONLY/ | `$PY -m scripts.analyze --dev-only` | no |
| Test-retest of the locked monitor | results/test_retest_dev.json | `$PY -m scripts.test_retest_dev` (run 2 cached in run-logs) | yes |
| Averaging two runs of Both | results/dev_run_averaging.json | `$PY -m scripts.average_runs_dev` | no |
| Score-scale spike (100 vs 1000) | results/spike_scale.json, spike_sample_ids.json, spike_example_prompt.txt | `$PY -m scripts.spike_scale` | yes |
| Fishing development pilot (3 games) | results/fishing_pilot_dev.json and .md | `$PY -m scripts.fishing_pilot_dev` | yes |
| Fishing development pilot, analysis tables | results/tables/DEV-ONLY-fishing/ | `$PY -m scripts.analyze_fishing --dev-only` | no |
| Pilot summary (El Farol and Fishing pilot games) | results/pilot_summary.json | `$PY -m scripts.pilot_summary` (reads the harness pilot outputs) | no |
| Development score files | scores/dev, scores/fishing_dev | `$PY -m scripts.build_dev_scores` (assembles from run-logs caches) | no |

## Practice (DEV-ONLY PRACTICE, exploration for future work)

| Result | File | Reproduce | API |
|---|---|---|---|
| Gemini 3.8 Flash and Sonnet 5.5 against Haiku on the development set | results/practice_monitors_dev.json and .md | `$PY -m scripts.analyze_practice` (needs run-logs/retest_run2.jsonl) | no |
| Practice monitor scores | scores/practice_gemini_dev, scores/practice_sonnet_dev | `$PY -m scripts.score_practice --model <gemini or sonnet> --views <list>` (dev split only) | yes |

## Planning documents

| Document | File |
|---|---|
| Pre-registration (frozen 2026-10-23T18:26:29-04:00, commit 3699338) | docs/preregistration.md |
| Amendment 1 (OSF update, recorded in commit 5c12546) | docs/amendment1.md |
| Design and decision records | docs/design.md, docs/adr/ |
