#!/usr/bin/env bash
# Run the 90-attempt main local experiment with resume + grading.
#
# Usage (from the repo root, inside WSL):
#   bash scripts/run_main_local.sh
#
# The script waits for Docker and Ollama, then runs:
#   python -m skills_experiment run --experiment main-local --resume --grade
# and appends the output to runs/logs/main-local-01.log.
#
# The log lives outside runs/main-local-01 on purpose: the runner resets its own
# run directory at startup, so a log inside it can be deleted mid-run.
#
# --resume skips attempts already present in runs.jsonl, so restarting after a
# crash does not redo completed attempts. Keep the machine awake for the run.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

export PATH="/root/.local/bin:$PATH"
export SWEBENCH_PYTHON="${SWEBENCH_PYTHON:-/root/skills-harness/bin/python}"
export PYTHONPATH=src
export PYTHONUNBUFFERED=1

PY="$SWEBENCH_PYTHON"
LOG="runs/logs/main-local-01.log"
mkdir -p runs/logs

{
  echo "=== START $(date -u +%FT%TZ) ==="
  until docker info >/dev/null 2>&1; do sleep 2; done
  until curl -sf http://localhost:11434/api/tags >/dev/null; do sleep 2; done
  "$PY" -m skills_experiment run --experiment main-local --resume --grade
  echo "run_exit=$?"
  echo "=== END $(date -u +%FT%TZ) ==="
} 2>&1 | tee -a "$LOG"
