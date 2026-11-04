# Reproducing Mechanism Pilot 01

This is the end-to-end runbook for the 60-attempt A/B/C mechanism study on
SWE-bench Pro V2. It reproduces the **protocol and artifacts**, not necessarily
the exact trajectories: DeepSeek exposes no sampling seed, so a new run is a new
stochastic draw from the same setup.

For the frozen design see `PROTOCOL.md`; for the task list see `TASKS.md`; for
the completed reference run see `../../results/mechanism-pilot-01/RESULTS.md`.

## 1. What was run

| Item | Value |
|---|---|
| Design | 10 tasks × 3 conditions (A/B/C) × 2 repeats = 60 attempts |
| Execution | 2 Harbor workers, randomized plan order |
| Workflow | canonical v2 |
| Model profile | `deepseek-flash-1017` |
| Provider model | `deepseek-flash` via `https://api.deepseek.com` |
| Agent | `skills_experiment.harbor_agent:HarborSkillsAgent` |
| Benchmark | SWE-bench Pro V2, the 10 tasks in `TASKS.md` |
| Harbor | 0.25.0, local Docker (not Modal) |
| Verifier | task verifier, `shared` mode |
| Budgets | 80 steps; 1,000,000 cumulative tokens; 16,384 per response; 3,000 s |
| Run code | harness commit `a13fe23` |
| Reference results | harness commit `493fdd6` |
| Analysis code | current `mechanism-study` (adds `--pattern` and summary tooling) |

The reference run took about 3 hours 2 minutes and produced 60/60 `rc=0`
statuses, 0 Harbor exceptions, and 27 budget-exhausted attempts.

## 2. Prerequisites

- Git.
- Python 3.11+ for the harness, extraction, and analysis (the exact run used
  Python 3.12.15 inside Harbor's tool environment).
- Docker Desktop on Windows with WSL 2 integration, or Docker Engine on Linux.
- WSL 2 Ubuntu if you are on Windows. The exact run used WSL 3.0.3.0 and Docker
  Engine 29.8.2.
- `uv` and Harbor 0.25.0.
- A DeepSeek API key with access to `deepseek-flash`.
- Roughly 40 GB free for the 10 task images, job artifacts, and Docker layers.
  The exact run's Docker store was larger because it also held other images.
- A long-lived terminal (or `tmux`/`screen`) for the run. Do not run the full
  three-hour command as a foreground OpenCode tool call.

You do **not** need the `swebench==5.0.2` harness venv or
`scripts/wsl_setup_harness.sh` for this study. SWE-bench Pro V2 task verifiers
run inside Harbor's task containers.

## 3. Clone the harness and benchmark

Use paths without spaces if possible; the examples below quote them.

```bash
git clone https://github.com/jyim1203/llm-skills-testing-q1.git
cd llm-skills-testing-q1
git switch mechanism-study
git checkout a13fe23          # exact run code; plan + launcher
```

The run code is `a13fe23`. Later commits add only the recorded results,
provenance, and analysis tooling. Before extraction, switch to the current
`mechanism-study` branch (it contains the `--pattern` extraction filter added
after the reference results commit):

```bash
git switch mechanism-study
```

Clone SWE-bench Pro separately and pin the benchmark commit:

```bash
git clone https://github.com/scaleapi/SWE-bench_Pro-os.git
cd SWE-bench_Pro-os
git checkout 66f92766bba642462d4bbe5479e83f91f9211862
```

This checkout contains `v2/tasks/` and the 10 task definitions. Harbor writes
jobs to `SWE-bench_Pro-os/jobs/` by default; that directory is untracked in the
Pro repository.

In WSL, set the equivalent paths once and use them below:

```bash
export HARNESS_WSL="/mnt/c/Users/<you>/.../Skills Test Q1"
export PRO_WSL="/mnt/c/Users/<you>/.../SWE-bench_Pro-os"
```

If you run Git inside WSL as root against a `/mnt/c` clone, Git may reject the
repositories as “dubious ownership.” Either use Windows Git or run:

```bash
git config --global --add safe.directory "$HARNESS_WSL"
git config --global --add safe.directory "$PRO_WSL"
```

## 4. Install Harbor in WSL/Linux

Run these commands inside WSL as root, because the launcher expects
`/root/.local/bin/harbor`:

```bash
wsl -d Ubuntu -u root -- bash
```

Inside WSL:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
/root/.local/bin/uv tool install 'harbor[modal]==0.25.0'
/root/.local/bin/harbor --version
```

The exact run used Harbor 0.25.0. The Pro V2 upstream instruction installs
`harbor[modal]>=0.22`; pinning `==0.25.0` is the reproducible choice. `modal`
is included by the upstream install command but is not used here: the launcher
omits `-e modal`, so Harbor uses local Docker.

Verify the Harbor environment can import the OpenAI SDK used by the harness:

```bash
/root/.local/share/uv/tools/harbor/bin/python \
  -c 'import openai; print(openai.__version__)'
```

The reference environment had `openai 2.54.0`. If it is missing:

```bash
/root/.local/bin/uv pip install \
  --python /root/.local/share/uv/tools/harbor/bin/python 'openai>=1.40'
```

If you install Harbor as a non-root user, edit the `HARBOR` constant near the
top of `scripts/run_mechanism_wsl.py` or invoke Harbor through the matching
path.

## 5. Docker and task images

Start Docker Desktop (Windows) or Docker Engine (Linux), then confirm that WSL
can see the engine:

```bash
docker version
docker ps
```

On Windows, enable Docker Desktop → Settings → Resources → WSL Integration for
Ubuntu. A `docker: permission denied` error means you are not in the Docker
group; running as root avoids it for this exact workflow.

Harbor pulls each task image on demand. To pre-pull the 10 images:

```bash
cd "$PRO_WSL"
PLAN="$HARNESS_WSL/data/mechanism-pilot-01/plan.json"
python3 - "$PLAN" <<'PY' | bash
import json
import sys
from pathlib import Path

plan = json.loads(Path(sys.argv[1]).read_text())
for task_id in sorted({row["task_id"] for row in plan["order"]}):
    print(f"docker pull ghcr.io/scaleapi/swe-bench_pro-v2:{task_id}")
PY
```

The images are public on GHCR and need no login. Compare the resulting local
image digests with the 10 digests recorded in `TASKS.md`; the per-attempt
manifest also records them. CPU, memory, storage, and network modes are defined
per task in each `v2/tasks/<instance_id>/task.toml`; for example, `e9e600`
requests 1 CPU, 4,096 MB memory, and 10,240 MB storage. Harbor honors those task
settings.

## 6. Credentials

From the harness repository:

```bash
cd "$HARNESS_WSL"
cp .env.example .env
```

Set only the key you use:

```dotenv
DEEPSEEK_API_KEY=...
```

The model profile reads `DEEPSEEK_API_KEY`; `.env` is ignored by Git and is
never written into run logs. The harness calls the provider from the host-side
agent process, not from the task container, so no Harbor
`--allow-agent-host` override is needed for this setup.

Check the profile resolves without making a scored call:

```bash
cd "$HARNESS_WSL"
PYTHONPATH=src /root/.local/share/uv/tools/harbor/bin/python - <<'PY'
from skills_experiment.models.registry import get_registry
client = get_registry().create("deepseek-flash-1017")
print(client.model_id)
PY
```

## 7. Verify the plan

The 60-attempt plan is committed and shuffled with seed `20261103`:

```bash
cd "$HARNESS_WSL"
python3 - <<'PY'
import json
from pathlib import Path
plan = json.loads(Path("data/mechanism-pilot-01/plan.json").read_text())
assert plan["attempts"] == 60
assert len(plan["order"]) == 60
assert len({row["order"] for row in plan["order"]}) == 60
assert len({(row["task_id"], row["condition"], row["repeat"]) for row in plan["order"]}) == 60
print("60 unique attempts; seed", plan["seed"])
PY
```

Inspect the exact Harbor commands without running them:

```bash
cd "$HARNESS_WSL"
python3 scripts/run_mechanism_wsl.py \
  --plan data/mechanism-pilot-01/plan.json \
  --pro-dir "$PRO_WSL" \
  --dry-run
```

The dry run prints 60 `harbor run` commands, one trial each.

## 8. Run the 60 attempts

Use a persistent WSL terminal, or launch a detached WSL process from Windows.
The following is the exact command shape used by the launcher:

```bash
cd "$HARNESS_WSL"
python3 scripts/run_mechanism_wsl.py \
  --plan data/mechanism-pilot-01/plan.json \
  --pro-dir "$PRO_WSL" \
  --workers 2
```

The launcher:

- uses plan order, so conditions are interleaved;
- runs one Harbor trial per job;
- uses `PYTHONPATH=src` so Harbor can import the custom agent;
- writes one log per job under `data/mechanism-pilot-01/logs/`;
- appends status rows to `data/mechanism-pilot-01/run_status.jsonl`;
- runs at most two jobs concurrently.

`run_status.jsonl` and `logs/` are gitignored runtime artifacts. From a clean
clone, start at order 1. If you resume a partial run, inspect the status file
first and use `--start <next-order>`; do not rerun completed orders, because
job names are deterministic and would collide.

If you want a detached Windows launch, use a dedicated `wsl.exe` process
rather than a one-shot background shell:

```powershell
$harness = "/mnt/c/Users/<you>/.../Skills Test Q1"
$pro = "/mnt/c/Users/<you>/.../SWE-bench_Pro-os"
$log = "C:\Users\<you>\...\Skills Test Q1\data\mechanism-pilot-01\run.out"
$err = "C:\Users\<you>\...\Skills Test Q1\data\mechanism-pilot-01\run.err"
Start-Process -FilePath "wsl.exe" -ArgumentList @(
  "-d", "Ubuntu", "-u", "root", "--", "bash", "-lc",
  "cd `"$harness`" && python3 scripts/run_mechanism_wsl.py --plan data/mechanism-pilot-01/plan.json --pro-dir `"$pro`" --workers 2"
) -RedirectStandardOutput $log -RedirectStandardError $err -WindowStyle Hidden
```

Keep the machine awake and Docker running. The exact run used about 3 hours.

## 9. Monitor

From any terminal:

```bash
cd "$HARNESS_WSL"
wc -l data/mechanism-pilot-01/run_status.jsonl
tail -n 5 data/mechanism-pilot-01/run_status.jsonl
docker ps
```

A completed run has 60 status rows. Each row has `order`, `job`, `returncode`,
`seconds`, and `log`; the reference run had `returncode=0` for every row and
no Harbor exceptions. Docker Desktop can be empty between attempts while a new
image/container is being prepared; that is not itself a failure.

## 10. Build the F2P/P2P dataset index

The run does not need this file. Extraction uses it to compute fail-to-pass and
pass-to-pass fractions, so build it before extraction.

The source is the HuggingFace default config of `ScaleAI/SWE-bench_Pro` (V2,
642 tasks). Use any Python 3.11+ environment with `datasets`:

```bash
cd "$HARNESS_WSL"
python3 -m venv .venv-data
. .venv-data/bin/activate
pip install "datasets>=2"
mkdir -p data/raw
python - <<'PY'
import json
from datasets import load_dataset

rows = load_dataset("ScaleAI/SWE-bench_Pro", split="test")
with open("data/raw/swebench_pro_default.json", "w", encoding="utf-8") as fh:
    json.dump(rows.to_list(), fh)
PY
sha256sum data/raw/swebench_pro_default.json
```

The reference file was 21,608,582 bytes with SHA-256:

```text
a2287582a2b273fd6acec18b56de91b7dcc7669c60943cb76f9924fd4f4471b4
```

If the HF dataset has changed, the hash will differ. The task tree is still
pinned by the Pro commit; the dataset index only supplies test membership.

## 11. Extract behavior and efficiency features

Switch to the current `mechanism-study` branch so `extract_behavior.py` has
the `--pattern` filter:

```bash
cd "$HARNESS_WSL"
git switch mechanism-study
python3 scripts/extract_behavior.py \
  --jobs "$PRO_WSL/jobs" \
  --pattern "mechanism-v2-[0-9][0-9]-*" \
  --dataset data/raw/swebench_pro_default.json \
  --out data/derived/mechanism-pilot-01
```

Expected output is `attempts=60` and an event table with the tool calls. The
reference extraction produced 60 attempts and 1,794 event rows; the exact event
count depends on the agent's tool behavior. The glob deliberately excludes any
non-numbered smoke jobs.

If `--dataset` is omitted, outcome still works but F2P/P2P fields are null.

## 12. Recompute the manifest and task-level analysis

```bash
cd "$HARNESS_WSL"
python3 scripts/summarize_mechanism_run.py \
  --plan data/mechanism-pilot-01/plan.json \
  --attempts data/derived/mechanism-pilot-01/attempts.json \
  --status data/mechanism-pilot-01/run_status.jsonl \
  --out results/mechanism-pilot-01
```

This writes `run_manifest.json` and `analysis.json`. If you ran from a different
harness commit, pass `--harness-commit-at-run <commit>`; the default is the
reference commit `a13fe23`.

Quick checks:

```bash
python3 - <<'PY'
import json
from pathlib import Path
summary = json.loads(Path("results/mechanism-pilot-01/analysis.json").read_text())
quality = summary["quality"]
assert quality["n_attempts"] == 60
assert quality["n_tasks"] == 10
print("attempts", quality["n_attempts"], "exceptions", quality["exceptions"])
print("by condition", quality["by_condition"])
PY
```

## 13. Verify against the reference run

Reference values from `results/mechanism-pilot-01/`:

| Check | Reference |
|---|---:|
| Attempts | 60 |
| Tasks | 10 |
| Harbor exceptions | 0 |
| Budget exhausted | 27 |
| Resolved | 44 / 60 |
| A resolved | 14 / 20 |
| B resolved | 17 / 20 |
| C resolved | 13 / 20 |
| C skill loaded | 20 / 20 |
| A/B skill loaded | 0 / 20 each |

Do **not** require a new run to match the outcome counts. The provider has no
sampling seed, and the model service build may change. A replication is valid
if the task set, conditions, budgets, workflow hash, image digests, and
manipulation checks match; outcome variation is expected.

Useful exactness checks:

- `run_manifest.json`: 60 rows, all `rc=0`, task checksums and image digests
  matching `TASKS.md`.
- Event logs: `model_id` is `deepseek-flash`, `workflow_sha256` is
  `586b13769c48f7fea32d0723a4948f58f016c14094063e3bf4606376f5dc78ab`.
- C attempts: `skill_loaded=true`; A/B attempts: no `load_skill` calls.
- Task IDs and strata: exactly the 10 in `TASKS.md`.

## 14. Common problems

| Symptom | Fix |
|---|---|
| `harbor: command not found` | Use `/root/.local/bin/harbor`; install it in WSL root. |
| `ModuleNotFoundError: openai` | Install `openai` into Harbor's tool venv with `uv pip install --python ...`. |
| `DEEPSEEK_API_KEY` missing | Put it in the harness repo `.env`; do not export it into logs. |
| Docker cannot be reached from WSL | Start Docker Desktop and enable WSL integration for Ubuntu. |
| Image pull looks stalled, no containers | Pull/setup can take minutes; check Harbor log, then `docker ps`. |
| `git` says dubious ownership in WSL | Use Windows Git, or add the repo to `safe.directory`. |
| Extraction includes smoke/old jobs | Use `--pattern "mechanism-v2-[0-9][0-9]-*"`. |
| F2P/P2P totals are zero | Build and pass `data/raw/swebench_pro_default.json`. |
| Analysis cannot find trial results | Run extraction and analysis in the same path context, or regenerate `attempts.json` after moving jobs. |
| A resumed run duplicates orders | Read `run_status.jsonl`; resume with `--start <next-order>` or use a fresh jobs directory. |

## 15. Artifacts

Committed reference artifacts:

```text
results/mechanism-pilot-01/RESULTS.md
results/mechanism-pilot-01/run_manifest.json
results/mechanism-pilot-01/analysis.json
docs/mechanism-study/TASKS.md          checksums + image digests
data/mechanism-pilot-01/plan.json      60-attempt order, seed 20261103
```

Local/generated artifacts (gitignored):

```text
data/mechanism-pilot-01/logs/
data/mechanism-pilot-01/run_status.jsonl
data/derived/mechanism-pilot-01/attempts.csv
data/derived/mechanism-pilot-01/events.csv
data/derived/mechanism-pilot-01/attempts.json
SWE-bench_Pro-os/jobs/mechanism-v2-*/
```

Raw transcripts contain reasoning text and should be reviewed before sharing.
The public result artifacts do not include raw reasoning.
