#!/usr/bin/env bash
# Run the mechanism plan through the pinned runner image.
#
#   PRO_DIR=~/src/SWE-bench_Pro-os \
#     scripts/run_mechanism_docker.sh \
#     --plan data/mechanism-pilot-01/plan.json --pro-dir ~/src/SWE-bench_Pro-os --workers 2
#
# Every argument is forwarded to scripts/run_mechanism_wsl.py. Run it from WSL
# or Linux, where /var/run/docker.sock is your Docker Desktop / Engine socket.
#
# Environment:
#   PRO_DIR           SWE-bench_Pro-os checkout (required)
#   REPLICATION_IMAGE Image to run (default: the published GHCR tag)
#   DOCKER_SOCK       Docker socket path (default: /var/run/docker.sock)
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
raw_pro="${PRO_DIR:?set PRO_DIR to your SWE-bench_Pro-os checkout}"
image="${REPLICATION_IMAGE:-ghcr.io/jyim1203/llm-skills-testing-q1/replication:0.25.0}"
sock="${DOCKER_SOCK:-/var/run/docker.sock}"

if [[ ! -d "$raw_pro" ]]; then
  echo "run_mechanism_docker: PRO_DIR=$raw_pro is not a directory" >&2
  exit 2
fi
pro="$(cd "$raw_pro" && pwd)"

if [[ ! -S "$sock" ]]; then
  echo "run_mechanism_docker: $sock is not a socket; start Docker or set DOCKER_SOCK" >&2
  exit 2
fi

args=(
  run --rm -i
  --user root
  -v "${sock}:/var/run/docker.sock"
  -v "${repo}:${repo}"
  -v "${pro}:${pro}"
  -w "${repo}"
  -e "REPLICATION_REPO=${repo}"
)
if [[ -f "${repo}/.env" ]]; then
  args+=(--env-file "${repo}/.env")
fi

exec docker "${args[@]}" "$image" "$@"
