#!/usr/bin/env python3
"""Validate the skills repo: manifest consistency and SKILL.md frontmatter.

Checks:
  1. manifest.json parses, has manifest_version 1, and required engine fields.
  2. Every skill listed in the manifest exists on disk with a SKILL.md.
  3. Every skill directory on disk is listed in the manifest (no orphans).
  4. Each SKILL.md has frontmatter with `name` (matching its directory) and a
     non-empty `description`.
  5. Maestro skills declare `engine: maestro` and a `rasa_version` specifier.

Run from the repo root: python scripts/validate.py
Exits non-zero with a message per violation.
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
REQUIRED_ENGINE_FIELDS = (
    "display_name",
    "skills_path",
    "docs_url",
    "releases",
    "skills",
)

# Engines whose skills must carry engine/rasa_version frontmatter. Legacy CALM
# skills predate these fields and are exempt.
STRICT_FRONTMATTER_ENGINES = ("maestro",)


def parse_frontmatter(content: str) -> dict:
    """Extract simple top-level key: value pairs from YAML frontmatter.

    Handles the subset used in SKILL.md files (scalars and folded `>` blocks)
    without a YAML dependency.
    """
    match = FRONTMATTER_RE.match(content)
    if not match:
        return {}
    fields = {}
    lines = match.group(1).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        key_match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if key_match:
            key, value = key_match.group(1), key_match.group(2).strip()
            if value in (">", ">-", "|", "|-"):
                block = []
                i += 1
                while i < len(lines) and (
                    lines[i].startswith(" ") or not lines[i].strip()
                ):
                    block.append(lines[i].strip())
                    i += 1
                fields[key] = " ".join(part for part in block if part)
                continue
            fields[key] = value.strip("\"'")
        i += 1
    return fields


def main() -> int:
    errors = []

    manifest_path = REPO_ROOT / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read manifest.json: {exc}")
        return 1

    if manifest.get("manifest_version") != 1:
        errors.append("manifest.json: manifest_version must be 1")

    for engine, entry in manifest.get("engines", {}).items():
        for field in REQUIRED_ENGINE_FIELDS:
            if field not in entry:
                errors.append(f"manifest.json: engine '{engine}' missing '{field}'")
        if not any(release.get("latest") for release in entry.get("releases", [])):
            errors.append(
                f"manifest.json: engine '{engine}' has no release marked latest"
            )

        skills_dir = REPO_ROOT / entry.get("skills_path", "")
        listed = {skill["name"] for skill in entry.get("skills", [])}

        for name in sorted(listed):
            skill_md = skills_dir / name / "SKILL.md"
            if not skill_md.is_file():
                errors.append(
                    f"{engine}: '{name}' listed in manifest but {skill_md.relative_to(REPO_ROOT)} missing"
                )
                continue

            fields = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
            if not fields:
                errors.append(f"{name}: SKILL.md has no YAML frontmatter")
                continue
            if fields.get("name") != name:
                errors.append(
                    f"{name}: frontmatter name '{fields.get('name')}' != directory name"
                )
            if not fields.get("description"):
                errors.append(f"{name}: frontmatter missing non-empty 'description'")
            if engine in STRICT_FRONTMATTER_ENGINES:
                if fields.get("engine") != engine:
                    errors.append(
                        f"{name}: frontmatter must declare 'engine: {engine}'"
                    )
                if not fields.get("rasa_version"):
                    errors.append(f"{name}: frontmatter must declare 'rasa_version'")

        if skills_dir.is_dir():
            on_disk = {p.name for p in skills_dir.iterdir() if p.is_dir()}
            for orphan in sorted(on_disk - listed):
                errors.append(
                    f"{engine}: directory '{entry['skills_path']}/{orphan}' not listed in manifest.json"
                )

    if errors:
        print(f"FAILED: {len(errors)} problem(s)")
        for error in errors:
            print(f"  - {error}")
        return 1

    total = sum(
        len(entry.get("skills", [])) for entry in manifest.get("engines", {}).values()
    )
    print(f"OK: manifest and {total} skills validate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
