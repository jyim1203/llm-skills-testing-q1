"""Skill document helpers.

A ``SKILL.md`` file has YAML-ish front matter (``name`` + ``description``)
followed by a Markdown body. To satisfy the study's fairness requirement
(handoff section 5), the skill **body is generated from the same workflow file**
that Condition B injects directly (default:
``assets/prompts/workflow_instructions.md``). ``scripts/build_skill.py`` and the
runner both regenerate it, so the two can never drift.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import paths

# Canonical skill metadata (the "metadata appropriate to its purpose" that the
# handoff explicitly permits the skill condition to carry).
DEFAULT_SKILL_NAME = "python-repo-maintenance"
DEFAULT_SKILL_DESCRIPTION = (
    "Use when resolving an issue in a Python repository: inspect the structure, "
    "trace the current behavior, make the smallest correct change, and verify it "
    "with tests."
)

_FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass
class SkillDoc:
    name: str
    description: str
    body: str
    path: Optional[Path] = None
    source: str = "assets/prompts/workflow_instructions.md"

    @property
    def body_hash(self) -> str:
        return sha256_text(self.body)

    def render(self) -> str:
        return render_skill_md(self.name, self.description, self.body)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Split ``---`` front matter from the body. Missing front matter is fine."""
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta, text[match.end() :]


def render_skill_md(
    name: str,
    description: str,
    body: str,
    *,
    meta_extra: Optional[dict[str, str]] = None,
) -> str:
    """Compose a SKILL.md document.

    Extra provenance lives in the front matter (metadata), so the *body* stays
    byte-identical to the Condition B instruction text.
    """
    lines = [f"name: {name}", f"description: {description}"]
    for key, value in (meta_extra or {}).items():
        lines.append(f"{key}: {value}")
    header = "---\n" + "\n".join(lines) + "\n---\n"
    return f"{header}\n{body.strip()}\n"


def build_skill_doc(
    workflow_instructions: str,
    *,
    name: str = DEFAULT_SKILL_NAME,
    description: str = DEFAULT_SKILL_DESCRIPTION,
    source: str = "assets/prompts/workflow_instructions.md",
) -> SkillDoc:
    return SkillDoc(
        name=name,
        description=description,
        body=workflow_instructions.strip(),
        source=source,
    )


def write_skill_md(skill: SkillDoc, skill_dir: Path) -> Path:
    skill_dir.mkdir(parents=True, exist_ok=True)
    target = skill_dir / "SKILL.md"
    target.write_text(
        render_skill_md(
            skill.name,
            skill.description,
            skill.body,
            meta_extra={
                "generated_from": skill.source,
                "body_sha256": skill.body_hash,
            },
        ),
        encoding="utf-8",
        newline="\n",
    )
    return target


def load_skill_doc(path: Path) -> SkillDoc:
    text = Path(path).read_text(encoding="utf-8")
    meta, body = parse_front_matter(text)
    return SkillDoc(
        name=meta.get("name", ""),
        description=meta.get("description", ""),
        body=body.strip(),
        path=Path(path),
    )


def ensure_skill_built(
    workflow_instructions: str,
    skill_dir: Optional[Path] = None,
    *,
    source: str = "assets/prompts/workflow_instructions.md",
    **kwargs,
) -> SkillDoc:
    """Regenerate the on-disk SKILL.md from the workflow text and return it."""
    skill = build_skill_doc(workflow_instructions, source=source, **kwargs)
    target_dir = skill_dir or (paths.SKILLS_DIR / "python_repo_maintenance")
    write_skill_md(skill, target_dir)
    skill.path = (target_dir / "SKILL.md")
    return skill


def read_text(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")
