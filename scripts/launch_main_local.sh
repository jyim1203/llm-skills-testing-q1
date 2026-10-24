#!/usr/bin/env bash
# Start the main local run detached from the terminal/OpenCode session.
#
# Usage (from the repo root, inside WSL):
#   bash scripts/launch_main_local.sh
#
# The launcher starts run_main_local.sh under nohup setsid and returns
# immediately. Closing the terminal or OpenCode does not stop the run. The run
# logs to runs/main-local-01/run.log; restart the same launcher after a crash and
# --resume will skip attempts already present in runs.jsonl.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

nohup setsid bash scripts/run_main_local.sh >/dev/null 2>&1 < /dev/null &
pid=$!

echo "started main-local run: pid $pid"
echo "log: $(pwd)/runs/main-local-01/run.log"
