#!/usr/bin/env bash
# Usage: scripts/run_games.sh N_ELFAROL N_FISHING
# Runs both games in parallel (--trials N each); a game with N=0 is skipped.
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: $0 N_ELFAROL N_FISHING" >&2
  exit 2
fi
N_ELFAROL=$1
N_FISHING=$2

PROJ="$(cd "$(dirname "$0")/.." && pwd)"
PY="$PROJ/.venv/bin/python"
LOGDIR="$HOME/apart-sprint/docs/run-logs"
mkdir -p "$LOGDIR"

"$PY" "$PROJ/scripts/model_pin.py" before_main

pids=()
launch() {
  local game=$1 n=$2
  if [ "$n" -eq 0 ]; then
    echo "skipping $game (N=0)"
    return
  fi
  (cd "$PROJ/harness" && "$PY" experiments/run_endogenous.py --game "$game" \
    --agents 5 --trials "$n" --rounds 10 --model gpt-5.2 --round-robin \
    --use-queue --run-suffix main) > "$LOGDIR/main_${game}.log" 2>&1 &
  pids+=("$!")
  echo "started $game trials=$n pid=$!"
}

launch elfarol "$N_ELFAROL"
launch fishing "$N_FISHING"

status=0
for pid in "${pids[@]}"; do
  wait "$pid" || status=1
done

"$PY" "$PROJ/scripts/model_pin.py" after_main
exit "$status"
