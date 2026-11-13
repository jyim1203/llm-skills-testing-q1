# Skills vs. Prompt Instructions — SWE-bench Lite

This repository contains the code, frozen task data, and reproduction
instructions for a controlled experiment on whether delivering workflow
instructions as an agent *Skill* differs from pasting the same instructions into
the prompt.

The study compares three conditions on the same SWE-bench Lite tasks:

| Condition | What the agent gets |
|---|---|
| **A — baseline** | Task and repository context only |
| **B — direct prompt** | A plus the workflow instructions pasted into the system prompt |
| **C — skill** | A plus the *same* instructions packaged as `SKILL.md`, advertised by name/description, and loaded on demand |

The primary comparison is **C vs B**. Condition A anchors the comparison. B and C
use byte-identical instruction text; C must load the skill body before editing.
Each attempt gets a fresh workspace, a fresh conversation, and its own Docker
container. The official SWE-bench harness grades all patches.

The reported experiment is `main-local-01`: Qwen 3.5 9B Q4_K_M on six frozen
SWE-bench Lite tasks, with five repeats per condition (90 attempts). The
pre-registered design is in
[`PROTOCOL-main-local.md`](PROTOCOL-main-local.md), and the reported result is in
[`results/main-local-01/RESULTS.md`](results/main-local-01/RESULTS.md).

A longer runbook with troubleshooting and exact-replay checks is in
[`REPRODUCING_MAIN_LOCAL.md`](REPRODUCING_MAIN_LOCAL.md). Task-selection criteria
and the current six tasks are in [`TASK_SELECTION.md`](TASK_SELECTION.md).

---

## Reproducing the reported Qwen results

### Data access and storage

The experiment uses the `SWE-bench/SWE-bench_Lite` dataset, `test` split, at
revision `b0dde1093fe417d83b7184254edf8199c1f0dff5`.

- The exact six-task selection is committed at
  `data/task_selection_local.json`.
- The corresponding instance records are committed under `data/instances/`, so a
  fresh clone already contains the task bytes needed for the reported run. No
  dataset download is required for an exact replay.
- `data/image_locks/main-local-01.json` stores the Docker image digests.
  `preflight` pulls the six images and verifies them against this lock. Do not
  overwrite the lock for an exact replay.
- Run artifacts are written under `runs/main-local-01/` and are gitignored:
  `runs.csv`, `runs.jsonl`, per-attempt patches/transcripts, and harness reports.
  Keep this directory if you want to inspect the raw attempts. The committed
  summary is `results/main-local-01/RESULTS.md`.

If you intentionally want to rebuild the dataset cache rather than replay the
frozen selection, use:

```bash
PYTHONPATH=src /root/skills-harness/bin/python -m skills_experiment select-tasks --local --cache
```

That downloads and caches the six records, but it can change the selection file.
Do not use it for an exact replay of `main-local-01`.

### Software dependencies

- Linux/WSL2 Ubuntu. The reported main run executed on the Linux/WSL side, not
  in the Windows `local` sandbox.
- Python 3.11 for the official SWE-bench harness.
- `swebench==5.0.2` in a dedicated harness environment.
- `openai>=1.40` for the local OpenAI-compatible model endpoint.
- Docker, with enough disk for the six SWE-bench task images.
- Ollama 0.40.10 (or a tools-capable version) serving Qwen 3.5 9B with a 64k
  context. The reported run used a 12 GB RTX 5070.

The core framework has no third-party dependencies. The harness, model SDK,
Docker, and Ollama are the runtime dependencies.

### Commands to reproduce

Run these from the repository root. The reported environment is WSL/Linux.

```bash
# 1. Get the code.
git clone https://github.com/jyim1203/llm-skills-testing-q1.git
cd llm-skills-testing-q1
git checkout main

# 2. Create the official harness environment (from Windows PowerShell).
wsl -d Ubuntu -- bash /mnt/c/path/to/llm-skills-testing-q1/scripts/wsl_setup_harness.sh

# 3. Install the provider SDK in the same harness environment used by the launcher.
/root/skills-harness/bin/python -m pip install "openai>=1.40"

# 4. Configure the local endpoint key.
cp .env.example .env
# In .env: LOCAL_LLM_API_KEY=not-needed
```

Serve the reported model. The model name must match
`configs/models/local-qwen-sampling.toml`:

```text
# Modelfile
FROM qwen3.5:9b
PARAMETER num_ctx 65536
PARAMETER temperature 0
PARAMETER presence_penalty 0
```

```bash
ollama create qwen3.5-9b-agent-64k -f Modelfile
export OLLAMA_FLASH_ATTENTION=1
export OLLAMA_KV_CACHE_TYPE=q8_0
export OLLAMA_NUM_PARALLEL=1
ollama serve
```

The request profile overrides the model temperature to 0.2 and sets a
16,384-token response cap. If Ollama runs on Windows while the harness runs in
WSL, point `base_url` in `configs/models/local-qwen-sampling.toml` at the
Windows host IP, or run Ollama inside WSL. Record any environment-only change.

Validate the environment before the full run:

```bash
# Fast plumbing check; mock model, no Docker.
python scripts/smoke.py

# Docker sandbox validation.
python scripts/validate_sandbox.py pylint-dev__astroid-1268

# Official harness validation; must print "VALIDATION PASSED (gold patch)".
PYTHONPATH=src /root/skills-harness/bin/python scripts/validate_harness.py pylint-dev__astroid-1268

# Should show 6 tasks, 3 conditions, 5 repeats, 90 planned runs, and matching
# B/C fairness hashes.
PYTHONPATH=src /root/skills-harness/bin/python -m skills_experiment plan --experiment main-local

# Pull and verify the committed Docker image digests.
# Do not add --write-lock for an exact replay.
PYTHONPATH=src /root/skills-harness/bin/python -m skills_experiment preflight --experiment main-local
```

Run the experiment with the persistent launcher (recommended):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/launch_main_local.ps1
```

Or, from a WSL terminal you keep open:

```bash
bash scripts/run_main_local.sh
```

Both launch the equivalent of:

```bash
python -m skills_experiment run --experiment main-local --resume --grade
```

The run takes roughly 6-9 hours plus grading. `--resume` skips attempts already
recorded in `runs.jsonl` after a crash. Do not run the whole command as a
foreground OpenCode shell call; it will hit the tool timeout.

After the run, write the analysis summary:

```bash
PYTHONPATH=src /root/skills-harness/bin/python -m skills_experiment analyze \
  --experiment main-local --json
```

This writes `runs/main-local-01/analysis.json`. The reported run produced 46
resolved / 44 unresolved attempts, with A 16/30, B 15/30, and C 15/30. Because
the model samples at temperature 0.2, a rerun reproduces the procedure and
configuration, not necessarily the exact same patches or counts.

---

## Repository map

```text
configs/      experiment, model, and A/B/C condition definitions
data/         frozen task selection, cached instances, and image locks
src/          agent loop, conditions, sandbox, harness wrapper, runner, analysis
scripts/      setup, validation, planning, and main-run launchers
results/      committed result summaries
PROTOCOL-main-local.md   pre-registered protocol for the reported experiment
```

---

## Contributors and AI assistance

The human authors (Tony Bai and Jonathan Yim) designed the experiment,
implemented and reviewed the code, ran the experiments, analyzed the results,
and wrote the report. AI coding assistants, including ChatGPT and DeepSeek,
were used for implementation and debugging support, documentation, and editing.
All AI-generated code and suggestions were reviewed, tested, and adapted by the
human authors, who retain responsibility for the repository and its results.
DeepSeek was not an experimental condition.
