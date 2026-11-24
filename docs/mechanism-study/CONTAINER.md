# Container runner (optional)

`REPLICATION.md` installs the host-side toolchain by hand: `uv`, Harbor 0.25.0,
`openai` inside Harbor's tool venv, and a `datasets` environment. The runner
image in `docker/replication.Dockerfile` does exactly that, pinned, so a
replicator needs Docker, two git clones, and an API key — not a Python setup.

It is a convenience wrapper. `REPLICATION.md` remains the authoritative
procedure, and the native install is the fallback if anything below does not
match your machine.

## What the image pins

| Component | Value | Why |
|---|---|---|
| Base interpreter | CPython 3.12 (`python:3.12-slim-bookworm`) | the run used 3.12.15 inside Harbor's tool env |
| Harbor | `harbor[modal]==0.25.0` | the reference runs were executed with 0.25.0 |
| Provider SDK | `openai==2.54.0` in Harbor's tool venv | Harbor imports `skills_experiment.harbor_agent`, which calls DeepSeek through the OpenAI SDK |
| Dataset tooling | `datasets>=2` in `/opt/data-venv` | builds the F2P/P2P index (REPLICATION.md §10) |
| Docker CLI | 27.3.1 static | image pulls and `docker ps` inside the container |

## What it cannot pin

- **The task environments.** They are already images:
  `ghcr.io/scaleapi/swe-bench_pro-v2:<task_id>`, pinned by the digests in
  `docs/mechanism-study/TASKS.md` and re-checked by `scripts/verify_replication.py`.
- **The harness and benchmark checkouts.** They are mounted, not baked, so the
  image never goes stale against the branch and you can run any commit:

  ```bash
  git checkout a13fe23        # run code, per REPLICATION.md §3
  ```

- **The model service.** DeepSeek exposes no sampling seed, so a re-run is a new
  draw from the same setup. See REPLICATION.md §13 for what must match instead.
- **The HuggingFace dataset index.** It only supplies F2P/P2P membership; the
  task tree is pinned by the Pro commit. Record the SHA-256 you get.

## How it works

Harbor drives Docker over the socket, so the runner container gets the host
socket and launches each task container as a **sibling**, not a child:

```text
host Docker daemon
├── replication runner (this image)
│     └── harbor run ...  ── docker API ──┐
├── task container: swe-bench_pro-v2:<task_id>
└── task container: ...
```

Because those siblings are created by the host daemon, a path that Harbor hands
to the daemon has to mean the same thing on both sides. Harbor resolves the
plan, the Pro checkout, and the jobs directory as paths in its own process, so
the two checkouts are bind-mounted at the **same absolute path** inside and
outside the container (`-v "$repo:$repo"`). Do not mount them at different paths
in a hand-written `docker run`: Harbor's `cwd`, the plan's `--pro-dir`, and the
jobs directory must resolve identically on both sides.

## Build and publish (one time)

The image is built and pushed by `.github/workflows/replication-image.yml`,
which only runs when `docker/**` changes. Artifact drift is a separate,
independent gate: `.github/workflows/replication-verify.yml` runs
`scripts/verify_replication.py` on changes to the results, plans, or prompt
text. Neither needs the other, and the verify job needs no Docker, network, or
key.

The image job pushes
`ghcr.io/jyim1203/llm-skills-testing-q1/replication:0.25.0` plus a
`sha-<commit>` tag.

To enable it on a fork:

1. Push the branch, then **Actions → replication-image → Run workflow** once.
2. Packages are private by default. To let a reviewer pull without a token,
   open the package → **Package settings → Change visibility → Public**.
3. If the build fails at `uv tool install`, the usual cause is a missing system
   build dependency; add the package to the `apt-get` line rather than
   unpinning Harbor.

Build locally instead:

```bash
docker build -f docker/replication.Dockerfile -t replication:dev .
```

### What was verified, and what was not

Built on 2026-11-23 with Docker 29.8.2 under WSL 2 (Ubuntu), from this
Dockerfile and this branch:

| Check | Result |
|---|---|
| image builds | yes, 2.1 GB |
| Python / Harbor / openai / datasets | 3.12.16 / 0.25.0 / 2.54.0 / 5.2.0 |
| `harbor run … --dry-run` with the mounted checkout | `Dry run OK — 1 trial(s); nothing was run.` |
| custom agent import inside Harbor's venv | `skills_experiment.harbor_agent:HarborSkillsAgent` |
| socket, `.env` key, writable harness and Pro mounts | all four OK |

The dry run loads the agent class, resolves the task from `v2/tasks`, and accepts
the `--ak` kwargs without starting a task container or calling the model. That is
the configuration check; it costs nothing. It does **not** prove an agent loop
runs end to end — one real attempt (`--limit 1`) does, and that is the first
thing to do before a full run.

## Use

From WSL or Linux, with the Pro checkout next to the harness checkout
(REPLICATION.md §3):

```bash
export PRO_DIR="$HOME/src/SWE-bench_Pro-os"
cp .env.example .env          # then set DEEPSEEK_API_KEY

# 1. Show the 60 Harbor commands without running anything.
PRO_DIR="$PRO_DIR" scripts/run_mechanism_docker.sh \
  --plan data/mechanism-pilot-01/plan.json --pro-dir "$PRO_DIR" --dry-run

# 2. One attempt, to prove the socket, the agent import, and the key.
PRO_DIR="$PRO_DIR" scripts/run_mechanism_docker.sh \
  --plan data/mechanism-pilot-01/plan.json --pro-dir "$PRO_DIR" --limit 1

# 3. The real run: 60 attempts, two workers (≈3 h).
PRO_DIR="$PRO_DIR" scripts/run_mechanism_docker.sh \
  --plan data/mechanism-pilot-01/plan.json --pro-dir "$PRO_DIR" --workers 2
```

Step 2 is not optional. It catches a bad key, a stale Harbor, or a
missing image in one attempt instead of sixty.

Afterwards, extraction and analysis are plain Python on the host
(`REPLICATION.md` §11–12); the image is only needed for the Harbor run. If you
prefer to run them in the container too, the `datasets` venv is at
`/opt/data-venv`.

Pre-pull the ten images from the host (REPLICATION.md §5) so the first attempts
do not each spend minutes pulling layers:

```bash
python - data/mechanism-pilot-01/plan.json <<'PY' | bash
import json, sys
from pathlib import Path
for task_id in sorted({row["task_id"] for row in json.loads(Path(sys.argv[1]).read_text())["order"]}):
    print(f"docker pull ghcr.io/scaleapi/swe-bench_pro-v2:{task_id}")
PY
```

## Pin the image by digest for a reported re-run

`0.25.0` is a moving tag: a later push can replace it. For a run you intend to
report, record the digest and use it:

```bash
docker pull ghcr.io/jyim1203/llm-skills-testing-q1/replication:0.25.0
docker image inspect --format '{{index .RepoDigests 0}}' \
  ghcr.io/jyim1203/llm-skills-testing-q1/replication:0.25.0

REPLICATION_IMAGE='ghcr.io/jyim1203/llm-skills-testing-q1/replication@sha256:<digest>' \
  PRO_DIR="$PRO_DIR" scripts/run_mechanism_docker.sh --plan ... --pro-dir "$PRO_DIR"
```

Put that digest in the run's provenance next to the Harbor version.

## When to fall back to the native install

The container path adds two failure modes that the native path does not have:
the socket mount, and root inside the container writing files into your checkout.

- **Socket not found on Windows.** Run the wrapper inside WSL, not PowerShell.
  Docker Desktop's socket lives at `/var/run/docker.sock` in the distro.
- **Rootless Docker or Podman.** The socket is not `/var/run/docker.sock`; set
  `DOCKER_SOCK`, and expect Harbor's own requirements to dominate.
- **Apple silicon.** The task images are `linux/amd64`; expect slow emulation or
  failures. Use an amd64 Linux host or WSL.
- **Files owned by root.** On a Linux checkout, `docker run --user root` creates
  root-owned `jobs/`, `logs/`, and `run_status.jsonl`. On WSL/DrvFs this is
  usually invisible; on ext4, `sudo chown -R "$USER" jobs data/mechanism-pilot-01`.
- **Anything else.** `bash scripts/run_mechanism_wsl.py` run natively does the
  same work with one less layer. The launcher contract is identical.
