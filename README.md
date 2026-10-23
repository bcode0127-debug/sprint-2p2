# sprint-2p2

## Question

When GPT-5.2 agents play a repeated El Farol game and announce what they will do before choosing,
can a separate monitor model, shown only the public record up to the moment before an agent acts,
predict that the agent will break its announcement?
We score this as a ranking problem (AUROC) and as recall at a fixed 10% false-positive rate,
against simple no-LLM rules and against ablated views of the record.

## New versus pre-existing

- Pre-existing: the game harness (https://github.com/Jerick-1380/LLM-Trust-Breaking at a pinned
  commit), cloned into `harness/` and used unmodified. See [PROVENANCE.md](PROVENANCE.md).
- New in this repo: everything in `src/sprint2p2/`, `scripts/`, `tests/`, `prompts/`, `configs/`,
  `docs/`, and the committed data and scores under `data/`, `scores/` and `results/`.

## Keys

Put two keys in `.env` at the project root (git-ignored, never commit it):

```
OPENAI_API_KEY=      # runs the GPT-5.2 agents through the harness
OPENROUTER_API_KEY=  # runs the Haiku 5.5 monitor
```

## Reproduce

```bash
make reproduce
```

This recomputes the primary row from the committed score files with no API calls and prints the row
and its SHA-256. While only development scores exist it uses `scores/dev/` and labels the output
DEV-ONLY. Install dependencies from `requirements.lock` (Python 3.12).

Other targets: `make test`, `make lint`. The pipeline is `scripts/score_views.py` (scores a split),
`scripts/analyze.py` (tables) and `scripts/reproduce_row.py`.

## Data and gate

Raw logs are in `data/raw/` with `SHA256SUMS`. Splits are dev (pilot plus main trials 0 to 9),
threshold (trials 10 to 19) and test (trials 20 to 39), rounds 1 to 9; round 0 is a separate set.
The monitor refuses to score threshold or test cases until `configs/frozen.json` exists with a
non-empty `prereg_commit` and `osf_url` (see `docs/adr/0006-decision-8-and-the-gate.md`).

## Costs

Measured so far, at OpenRouter list prices for Haiku 5.5 ($0.10 per million prompt tokens,
$0.50 per million completion tokens):

- Monitor, v2 setting (reasoning on): about $0.37 per 100 cases per view (585 dev cases cost
  $0.216).
- All spikes and prompt rounds so far: under $1 in total.
- Projection for scoring threshold plus test (1,350 cases) on all nine views: roughly $4.50.
  The OpenRouter key has a $10 spend cap and expires 2026-10-30.
- Agents (OpenAI GPT-5.2): the harness does not log token usage, so agent cost is not recorded.
