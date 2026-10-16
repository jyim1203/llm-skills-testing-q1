#!/usr/bin/env bash
# Set up the Linux/WSL side of the experiment: a dedicated harness venv with the
# pinned SWE-bench harness, plus the environment hook that points the framework
# at it.
#
# Run from inside the WSL distro (as the default user):
#
#     wsl -d Ubuntu -- bash /mnt/c/.../scripts/wsl_setup_harness.sh
#
# Idempotent: safe to re-run. Requires `uv` (installs it if missing) so the
# interpreter is a real CPython 3.11 regardless of the distro's default Python.
set -euo pipefail

VENV="${SKILLS_HARNESS_VENV:-/root/skills-harness}"
PROFILE="${SKILLS_HARNESS_PROFILE:-/etc/profile.d/skills-harness.sh}"
PY_VERSION="${SKILLS_HARNESS_PY:-3.11}"
SWEBENCH_SPEC="${SKILLS_HARNESS_SPEC:-swebench==5.0.2}"

UV="$(command -v uv || true)"
if [ -z "$UV" ]; then
  UV="/root/.local/bin/uv"
fi
if [ ! -x "$UV" ]; then
  echo ">> installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  UV="/root/.local/bin/uv"
fi

echo ">> uv $("$UV" --version)"
echo ">> creating venv at $VENV (python $PY_VERSION)"
"$UV" venv --python "$PY_VERSION" "$VENV"
"$VENV/bin/python" --version

echo ">> installing $SWEBENCH_SPEC"
"$UV" pip install --python "$VENV/bin/python" "$SWEBENCH_SPEC"

echo ">> installed harness version:"
"$VENV/bin/python" -c 'import importlib.metadata as m; print("swebench", m.version("swebench"))'

echo ">> writing environment hook: $PROFILE"
if [ -w "$(dirname "$PROFILE")" ]; then
  cat > "$PROFILE" <<EOF
# Managed by scripts/wsl_setup_harness.sh -- points the framework at the
# harness venv (see evaluation/harness.py:resolve_harness_python).
export SWEBENCH_PYTHON="$VENV/bin/python"
EOF
  echo "   done"
else
  echo "   !! cannot write $PROFILE; set SWEBENCH_PYTHON=$VENV/bin/python yourself"
fi

echo ">> setup complete"
