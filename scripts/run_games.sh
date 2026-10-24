#!/usr/bin/env bash
# Usage: scripts/run_games.sh N_ELFAROL N_FISHING [SUFFIX_ELFAROL] [SUFFIX_FISHING]
# Runs both games in parallel (--trials N each); a game with N=0 is skipped.
# Suffixes default to "main". The run is refused if an output file would be overwritten.
# RUN_LABEL (default "main") names the before/after model pins in results/model_pin.json.
set -euo pipefail

if [ "$#" -lt 2 ] || [ "$#" -gt 4 ]; then
  echo "usage: $0 N_ELFAROL N_FISHING [SUFFIX_ELFAROL] [SUFFIX_FISHING]" >&2
  exit 2
fi
N_ELFAROL=$1
N_FISHING=$2
SUFFIX_ELFAROL=${3:-main}
SUFFIX_FISHING=${4:-main}
RUN_LABEL=${RUN_LABEL:-main}

PROJ="$(cd "$(dirname "$0")/.." && pwd)"
PY="$PROJ/.venv/bin/python"
LOGDIR="$HOME/apart-sprint/docs/run-logs"
mkdir -p "$LOGDIR"

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
