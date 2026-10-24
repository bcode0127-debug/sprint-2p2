#!/usr/bin/env bash
# Usage:
#   scripts/run_games.sh N_ELFAROL N_FISHING [SUFFIX_ELFAROL] [SUFFIX_FISHING]
#   scripts/run_games.sh fishing-test A|B [--dry-run]
# The first form runs both games in parallel (--trials N each); a game with N=0 is skipped.
# Suffixes default to "main". RUN_LABEL (default "main") names the before/after model pins.
# The second form generates one batch of 20 Fishing test games (suffix fishtestA or fishtestB),
# with a model pin before and after the batch. Run batch A, check credit, then run batch B.
# Do not score or look at any batch-A label before batch B has been generated.
# Every form is refused if an output file would be overwritten.
set -euo pipefail

PROJ="$(cd "$(dirname "$0")/.." && pwd)"
PY="$PROJ/.venv/bin/python"
LOGDIR="$HOME/apart-sprint/docs/run-logs"

usage() {
  echo "usage: $0 N_ELFAROL N_FISHING [SUFFIX_ELFAROL] [SUFFIX_FISHING]" >&2
  echo "       $0 fishing-test A|B [--dry-run]" >&2
  exit 2
}

out_path() {
  echo "$PROJ/harness/outputs/experiments/$1/5agents/gpt-5.2_endogenous_$2.json"
}

refuse_overwrite() {
  local game=$1 n=$2 suffix=$3
  if [ "$n" -ne 0 ] && [ -e "$(out_path "$game" "$suffix")" ]; then
    echo "refusing: $(out_path "$game" "$suffix") already exists" >&2
    exit 3
  fi
}

harness_cmd() {
  local game=$1 n=$2 suffix=$3
  echo "cd $PROJ/harness && $PY experiments/run_endogenous.py --game $game --agents 5 --trials $n" \
    "--rounds 10 --model gpt-5.2 --round-robin --use-queue --run-suffix $suffix"
}

if [ "${1:-}" = "fishing-test" ]; then
  BATCH=${2:-}
  DRY=${3:-}
  case "$BATCH" in A | B) ;; *) usage ;; esac
  if [ -n "$DRY" ] && [ "$DRY" != "--dry-run" ]; then usage; fi
  SUFFIX="fishtest${BATCH}"
  refuse_overwrite fishing 20 "$SUFFIX"
  if [ "$DRY" = "--dry-run" ]; then
    echo "DRY RUN: nothing is executed, no file is written"
    echo "+ $PY $PROJ/scripts/model_pin.py before_${SUFFIX}"
    echo "+ ($(harness_cmd fishing 20 "$SUFFIX")) > $LOGDIR/${SUFFIX}_fishing.log 2>&1"
    echo "+ $PY $PROJ/scripts/model_pin.py after_${SUFFIX}"
    exit 0
  fi
  mkdir -p "$LOGDIR"
  "$PY" "$PROJ/scripts/model_pin.py" "before_${SUFFIX}"
  status=0
  (cd "$PROJ/harness" && "$PY" experiments/run_endogenous.py --game fishing \
    --agents 5 --trials 20 --rounds 10 --model gpt-5.2 --round-robin \
    --use-queue --run-suffix "$SUFFIX") > "$LOGDIR/${SUFFIX}_fishing.log" 2>&1 || status=1
  "$PY" "$PROJ/scripts/model_pin.py" "after_${SUFFIX}"
  echo "batch ${BATCH} finished (status ${status}). Check credit before the next batch."
  exit "$status"
fi

if [ "$#" -lt 2 ] || [ "$#" -gt 4 ]; then
  usage
fi
N_ELFAROL=$1
N_FISHING=$2
SUFFIX_ELFAROL=${3:-main}
SUFFIX_FISHING=${4:-main}
RUN_LABEL=${RUN_LABEL:-main}
mkdir -p "$LOGDIR"

refuse_overwrite elfarol "$N_ELFAROL" "$SUFFIX_ELFAROL"
refuse_overwrite fishing "$N_FISHING" "$SUFFIX_FISHING"

"$PY" "$PROJ/scripts/model_pin.py" "before_${RUN_LABEL}"

pids=()
launch() {
  local game=$1 n=$2 suffix=$3
  if [ "$n" -eq 0 ]; then
    echo "skipping $game (N=0)"
    return
  fi
  (cd "$PROJ/harness" && "$PY" experiments/run_endogenous.py --game "$game" \
    --agents 5 --trials "$n" --rounds 10 --model gpt-5.2 --round-robin \
    --use-queue --run-suffix "$suffix") > "$LOGDIR/${suffix}_${game}.log" 2>&1 &
  pids+=("$!")
  echo "started $game trials=$n suffix=$suffix pid=$!"
}

launch elfarol "$N_ELFAROL" "$SUFFIX_ELFAROL"
launch fishing "$N_FISHING" "$SUFFIX_FISHING"

status=0
for pid in ${pids[@]+"${pids[@]}"}; do
  wait "$pid" || status=1
done

"$PY" "$PROJ/scripts/model_pin.py" "after_${RUN_LABEL}"
exit "$status"
