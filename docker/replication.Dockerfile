# syntax=docker/dockerfile:1
#
# Runner image for the mechanism study.
#
# The benchmark environments are already Docker images: every task pulls
# ghcr.io/scaleapi/swe-bench_pro-v2:<task_id> at a digest recorded in
# docs/mechanism-study/TASKS.md. What this image pins is the *host-side*
# toolchain that REPLICATION.md asks you to install by hand: CPython 3.12,
# Harbor 0.25.0, the `openai` client Harbor needs to import the custom agent,
# and a `datasets` environment for the F2P/P2P index.
#
# It deliberately does not contain the harness checkout or the SWE-bench Pro
# checkout. Both are mounted at run time, at the same absolute path inside and
# outside the container, so Harbor writes jobs and results to your real tree.
#
# Built and published by .github/workflows/replication-image.yml.

FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.source="https://github.com/jyim1203/llm-skills-testing-q1" \
      org.opencontainers.image.description="Pinned Harbor 0.25.0 runner for the skills-vs-prompt mechanism study" \
      org.opencontainers.image.title="skills-mechanism-replication"

ARG HARBOR_VERSION=0.25.0
ARG OPENAI_VERSION=2.54.0
ARG DOCKER_CLI_VERSION=27.3.1

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH=/root/.local/bin:$PATH

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl git bash jq \
 && rm -rf /var/lib/apt/lists/*

# Docker CLI only. The daemon is the host's, reached through the mounted socket;
# Harbor uses it to launch the task containers as siblings of this container.
RUN curl -fsSL "https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_CLI_VERSION}.tgz" \
      | tar -xz --strip-components=1 -C /usr/local/bin docker/docker \
 && docker --version

# uv, then Harbor at the exact version the reference runs used (REPLICATION.md §4).
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
 && uv tool install "harbor[modal]==${HARBOR_VERSION}" \
 && harbor --version

# Harbor imports the custom agent in-process, so its tool venv must also have
# the provider SDK. The reference environment had openai 2.54.0.
RUN uv pip install --python /root/.local/share/uv/tools/harbor/bin/python "openai==${OPENAI_VERSION}" \
 && /root/.local/share/uv/tools/harbor/bin/python -c "import openai; print('openai', openai.__version__)"

# Isolated environment for building the HuggingFace dataset index
# (REPLICATION.md §10); the run itself does not need it.
RUN uv venv /opt/data-venv \
 && uv pip install --python /opt/data-venv/bin/python "datasets>=2" \
 && /opt/data-venv/bin/python -c "import datasets; print('datasets', datasets.__version__)"

COPY docker/entrypoint.sh /usr/local/bin/replication-entrypoint
RUN chmod +x /usr/local/bin/replication-entrypoint

WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/replication-entrypoint"]
