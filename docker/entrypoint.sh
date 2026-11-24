#!/usr/bin/env bash
# Entrypoint for the mechanism-study runner image (docker/replication.Dockerfile).
#
# The image holds the pinned toolchain. The two things it cannot hold are
# mounted at run time:
#
#   * the harness checkout, at the same absolute path inside and outside the
#     container, so Harbor's cwd and relative paths line up;
#   * the host Docker socket, because Harbor launches the task containers as
#     siblings on your daemon.
#
# Everything after the image name is passed straight to
# scripts/run_mechanism_wsl.py, so the flags are the ones REPLICATION.md uses.
set -euo pipefail

repo="${REPLICATION_REPO:-}"
if [[ -z "$repo" ]]; then
  cat >&2 <<'EOF'
replication: set REPLICATION_REPO to the mounted harness checkout, for example:

  docker run --rm -i \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$PWD:$PWD" -v "$PRO_DIR:$PRO_DIR" -w "$PWD" \
    -e REPLICATION_REPO="$PWD" --env-file .env \
    ghcr.io/jyim1203/llm-skills-testing-q1/replication:0.25.0 \
    --plan data/mechanism-pilot-01/plan.json --pro-dir "$PRO_DIR" --dry-run

scripts/run_mechanism_docker.sh builds that command for you.
EOF
  exit 2
fi
if [[ ! -f "$repo/scripts/run_mechanism_wsl.py" ]]; then
  echo "replication: $repo does not look like the harness checkout" >&2
  exit 2
fi

if ! docker version --format '{{.Server.Version}}' >/dev/null 2>&1; then
  echo "replication: cannot reach the Docker daemon." >&2
  echo "  Mount the host socket: -v /var/run/docker.sock:/var/run/docker.sock" >&2
  exit 2
fi

if [[ -z "${DEEPSEEK_API_KEY:-}" ]]; then
  echo "replication: warning: DEEPSEEK_API_KEY is unset; Harbor runs will fail fast." >&2
fi

cd "$repo"
exec python3 scripts/run_mechanism_wsl.py "$@"
