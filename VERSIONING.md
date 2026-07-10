# Versioning

Skill releases are keyed to the **Rasa Pro minor version** so agents always read
guidance matching the installed engine.

## Scheme

- Each engine in `manifest.json` has a `releases` list: `{ "tag": ..., "rasa_version": <PEP 440 specifier>, "latest": ... }`.
- A release `tag` is a git tag in this repo, named `<engine>/<rasa-minor>.<patch>` — e.g. `maestro/3.18.0`. The tag freezes the skill content that matches that engine release.
- The installer (`rasa tools skills install`) resolves the release whose `rasa_version` specifier matches the running Rasa version (major.minor comparison) and fetches skill files at that tag — never from `main` once tags exist.
- Individual skills additionally carry `rasa_version` frontmatter as a second gate, and `metadata.version` for content revisions within a release line.

## During beta (before the first tag)

`main` is "next" and tracks the current Maestro beta. Both engines resolve to `tag: main` in the manifest. The first tag (`maestro/3.18.0`) is cut when the first feature-flagged beta release of Rasa Pro ships; the manifest gains the tagged release entry and `main` stops being a valid install target for Maestro.

## Rules

1. Cut a skills tag for every Rasa Pro release that changes Maestro's authoring surface. Same day, not later — retrofitting version history is impossible.
2. When a docs version exists for the release (see maestro-docs VERSIONING), the skills tag and docs tag must reference each other's version.
3. Never edit content at an existing tag; publish a new patch tag (`maestro/3.18.1`).
4. `skills/` (CALM, legacy path) stays layout-frozen: released 3.9–3.17 clients fetch `skills/<name>/SKILL.md` from `main` directly.
5. CI (`scripts/validate.py`) must pass before any tag is cut.
