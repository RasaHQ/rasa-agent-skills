# AGENTS.md — template for the Maestro project scaffold

> This file is a **template** maintained with the agent skills (see ENG-2901).
> `rasa init` copies it into new Maestro projects as `AGENTS.md` so any coding
> agent opening the project knows what it is and how to work on it.
> Everything below the marker is the template content.

---

# This is a Rasa Maestro agent project

Maestro is Rasa's skills-based conversational AI engine (Rasa Pro >= 3.18). The
agent is built from **skills** — folders under `skills/`, each with a `skill.md`
(YAML frontmatter + prose instructions) and auto-discovered Python tools in
`tools/`. Global config: `agent.yml` (identity/persona), `integrations.yml`
(LLM providers, MCP servers, channels).

## Agent skills — install these first

Rasa publishes skills that teach coding agents how to build Maestro agents
(authoring skills, configuring, testing/debugging, migrating from CALM):

```bash
rasa tools skills install maestro --yes
```

If they are already installed (check `.claude/skills/`, `.cursor/skills/`,
`.github/skills/`, or `.codex/skills/`), use them. If the command is unavailable,
the machine-readable index is
https://raw.githubusercontent.com/RasaHQ/rasa-agent-skills/main/manifest.json —
fetch and read any skill directly.

## Core commands

```bash
rasa validate   # static checks — run after every edit
rasa train      # compile the project into a model
rasa inspect    # browser UI to converse and watch memory/tool state
```

Retrain after any change to `skill.md`, `memory.yml`, `responses.yml`,
`agent.yml`, or `integrations.yml`.

## Documentation

Maestro docs index (agent-friendly): fetch `llms.txt` from the docs site for the
page list, `llms-full.txt` for the complete bundle.

## Ground rules

- Secrets only via `${ENV_VAR}` in `integrations.yml` — never literal keys.
- Prose-first: add control levers (`tool_constraints`, `if:` markers, ordered
  blocks) only for behavior that must be guaranteed.
- Don't create CALM files (`domain.yml`, `config.yml`, `endpoints.yml`) — this
  engine replaced them.
- Validate before claiming done; exchange at least one real conversation turn via
  `rasa inspect` when behavior changed.
