# Reproducing the Qwen `main-local-01` experiment

This is the end-to-end reproduction guide for the reported Qwen 3.5 9B study
(`main-local-01`) on the `main` branch. The earlier DeepSeek `pilot-01` run is
setup validation only and is not pooled with this experiment.

The frozen design is in [`PROTOCOL-main-local.md`](PROTOCOL-main-local.md); the
reported outcome and caveats are in
[`results/main-local-01/RESULTS.md`](results/main-local-01/RESULTS.md). The
experiment configuration is
[`configs/experiments/main-local.toml`](configs/experiments/main-local.toml).

## What is being reproduced

| Item | Value |
|---|---|
| Model under test | Qwen 3.5 9B Q4_K_M, served as `qwen3.5-9b-agent-64k` |
| Model profile | `configs/models/local-qwen-sampling.toml` |
| Decoding | temperature 0.2, 16,384 tokens per response |
| Tasks | 6 frozen SWE-bench Lite instances (`data/task_selection_local.json`) |
| Conditions | A baseline, B prompt instructions, C skill file |
| Design | 6 tasks x 3 conditions x 5 repeats = **90 attempts** |
| Budgets | 80 steps, 2,500,000 cumulative tokens, 1,800 s, 120 s per tool call |
| Harness | official SWE-bench harness, `swebench==5.0.2` |
| Dataset revision | `b0dde1093fe417d83b7184254edf8199c1f0dff5` |
| Image lock | `data/image_locks/main-local-01.json` |

The reported run is the one in `results/main-local-01/RESULTS.md`: 46 resolved
and 44 unresolved attempts, with A 16/30, B 15/30, and C 15/30. Because the main
run samples at temperature 0.2, a rerun reproduces the **procedure and
configuration**, not necessarily the exact same patches or counts.

## Prerequisites

- Linux or WSL2 Ubuntu. The reported main run executed on the Linux/WSL side,
  not the Windows `local` sandbox.
- Python 3.11 for the SWE-bench harness.
- Docker with enough disk for the six SWE-bench task images.
- Ollama. The reported run used Ollama 0.40.10 on a 12 GB RTX 5070.
- An OpenAI-compatible endpoint for the model. The committed profile expects
  `http://localhost:11434/v1`.

## 1. Get the code

```bash
git clone https://github.com/jyim1203/llm-skills-testing-q1.git
cd llm-skills-testing-q1
git checkout main
```

## 2. Set up the official harness (WSL/Linux)

From Windows PowerShell, run the repository's harness setup script inside WSL:

```powershell
wsl -d Ubuntu -- bash /mnt/c/path/to/llm-skills-testing-q1/scripts/wsl_setup_harness.sh
```

That script creates `/root/skills-harness` with `swebench==5.0.2` and exports
`SWEBENCH_PYTHON` through `/etc/profile.d/skills-harness.sh`.

The launcher runs the experiment CLI with that harness interpreter, so install
the OpenAI SDK there too:

```bash
cd /mnt/c/path/to/llm-skills-testing-q1
/root/skills-harness/bin/python -m pip install "openai>=1.40"
```

Validate both sides of the setup before spending model time:

```bash
# The Docker sandbox must be able to start an image and read/write/patch files.
python scripts/validate_sandbox.py pylint-dev__astroid-1268

# The official harness must grade the gold patch as PASSED.
PYTHONPATH=src /root/skills-harness/bin/python scripts/validate_harness.py pylint-dev__astroid-1268
```

`validate_sandbox.py` requires Docker. `validate_harness.py` should print
`VALIDATION PASSED (gold patch)`.

## 3. Configure credentials

```bash
cp .env.example .env
```

Set the local endpoint key in `.env`:

```dotenv
LOCAL_LLM_API_KEY=not-needed
```

The framework loads `.env` without overwriting your shell. Local servers ignore
the key value, but the `openai` provider requires one.

## 4. Serve Qwen with the right context and tool calling

The reported model is a 64k-context Qwen 3.5 9B Q4_K_M profile. Create the named
Ollama model from a Modelfile like this:

```text
FROM qwen3.5:9b
PARAMETER num_ctx 65536
PARAMETER temperature 0
PARAMETER presence_penalty 0
```

```bash
ollama create qwen3.5-9b-agent-64k -f Modelfile
```

Serve it with the settings used for the 12 GB GPU:

```bash
export OLLAMA_FLASH_ATTENTION=1
export OLLAMA_KV_CACHE_TYPE=q8_0
export OLLAMA_NUM_PARALLEL=1
ollama serve
```

The `local-qwen-sampling` request overrides the model temperature to 0.2 and
uses a 16,384-token response cap. Tool calling must be enabled by the server;
the running Ollama version must support tool calls for this model.

Check that the endpoint is reachable from the harness environment:

```bash
curl -s http://localhost:11434/api/tags
```

If Ollama runs on Windows while the harness runs in WSL, `localhost` will not
reach it. Either run Ollama inside WSL or point `base_url` in
`configs/models/local-qwen-sampling.toml` at the Windows host IP. That is an
environment-only change; record it with the run.

The repository does not pin the Ollama model digest. Record `ollama show
qwen3.5-9b-agent-64k` with the run for provenance.

## 5. Check the frozen experiment before running

The six-task selection and image lock are committed. Do **not** regenerate them
for an exact replay.

```bash
# Fast plumbing check; uses the mock model and no Docker.
python scripts/smoke.py

# Should show 6 tasks, 3 conditions, 5 repeats, 90 planned runs, and the B/C
# fairness hashes.
PYTHONPATH=src /root/skills-harness/bin/python -m skills_experiment plan --experiment main-local

# Pull the six images and verify them against data/image_locks/main-local-01.json.
# Do not add --write-lock: that would replace the frozen lock.
PYTHONPATH=src /root/skills-harness/bin/python -m skills_experiment preflight --experiment main-local
```

`preflight` must end with `Lock OK (all images match the recorded digests)`.
If it reports a mismatch, do not run; the task environment has moved.

An optional 18-attempt calibration run is available, but it is validation only
and is not part of the reported sample:

```bash
PYTHONPATH=src /root/skills-harness/bin/python -m skills_experiment run \
  --experiment main-local-pilot --grade
```

## 6. Run the reported experiment

From Windows PowerShell, use the persistent WSL launcher:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/launch_main_local.ps1
```

Or, from a WSL terminal you keep open:

```bash
bash scripts/run_main_local.sh
```

Both paths run:

```bash
python -m skills_experiment run --experiment main-local --resume --grade
```

The launcher waits for Docker and Ollama, runs all 90 attempts, grades them with
the official harness, and appends to `runs/logs/main-local-01.log`. Expect
roughly 6-9 hours plus grading. Do not run this as a foreground OpenCode shell
call; it will hit the tool timeout. `--resume` skips attempts already recorded
in `runs.jsonl` after a crash.

## 7. Analyze and compare with the reported result

```bash
PYTHONPATH=src /root/skills-harness/bin/python -m skills_experiment analyze \
  --experiment main-local --json
```

This writes `runs/main-local-01/analysis.json` next to the run log. The main
artifacts are:

- `runs/main-local-01/runs.csv` and `runs.jsonl` — one row per attempt.
- `runs/main-local-01/analysis.json` — condition summaries and task-level effects.
- `runs/main-local-01/attempts/` — patches, transcripts, and stop reasons.
- `runs/main-local-01/harness/` — predictions and raw harness reports.

The committed reference result is
[`results/main-local-01/RESULTS.md`](results/main-local-01/RESULTS.md). The
reported 90-attempt run had 46 resolved / 44 unresolved attempts; A 16/30,
B 15/30, C 15/30; and C-B = 0.0 percentage points with zero discordant
attempts. Because the run is stochastic, a rerun can differ at the attempt
level even when the procedure matches.

## Exact-replay checklist

- Use the committed `data/task_selection_local.json`, not a regenerated
  selection.
- Use the committed `data/image_locks/main-local-01.json`; preflight must pass
  without `--write-lock`.
- Keep `configs/experiments/main-local.toml` at the committed settings.
- Do not pool `main-local-pilot-01` or the DeepSeek `pilot-01` into the result.
- Check the hashes in `PROTOCOL-main-local.md` if you change any frozen input.
- Use the same model tag and record its Ollama digest.
- The reported code state is recorded in `results/main-local-01/RESULTS.md`
  (`d3fbbd7`); current `main` contains later documentation, launcher, and
  other-experiment commits.

## Troubleshooting

- **Model not found:** `ollama create` must finish before running; the profile
  calls `qwen3.5-9b-agent-64k`, not the base tag.
- **Context errors:** the loop needs at least 64k context. Set `num_ctx 65536`
  and use the q8_0 KV cache settings above.
- **Agent cannot call tools:** enable tool calling in the server, or the model
  will only emit text.
- **`localhost` unreachable from WSL:** use the Windows host IP or run Ollama
  inside WSL.
- **Harness not found:** run `wsl_setup_harness.sh`, then confirm
  `SWEBENCH_PYTHON=/root/skills-harness/bin/python`.
- **Windows harness file issue:** reported runs use the Linux/WSL path. The
  Windows LF shim is a fallback, not the reported environment.
- **Resume after a crash:** rerun the same launcher; `--resume` skips completed
  rows. Use `rerun` only for infrastructure-error attempts.
