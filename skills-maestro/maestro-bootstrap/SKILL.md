---
name: maestro-bootstrap
description: >
  Takes a machine from nothing to a running Rasa Maestro agent: install Rasa Pro,
  scaffold a project, write a first skill, validate, train, and talk to it. Use when
  the user wants a Maestro agent and no Rasa project (or no Rasa installation) exists
  yet. This runbook is self-contained — it can be fetched from its public URL and
  followed without installing anything first.
license: Apache-2.0
engine: maestro
rasa_version: ">=3.18"
metadata:
  author: rasa
  version: "0.1.0"
  docs-url: https://github.com/RasaHQ/maestro-docs
---

# Bootstrap a Maestro agent from zero

Maestro is Rasa's skills-based engine (Rasa Pro >= 3.18, beta). Agents are built from
**skills**: folders containing a `skill.md` (prose instructions + YAML frontmatter)
and auto-discovered Python tools. Full docs: the `docs-url` above — fetch its
`llms.txt` for an index, `llms-full.txt` for everything.

## Step 0 — collect what only the user can provide

Ask for these **before doing anything else** so the run doesn't stall halfway:

1. **Rasa Pro license** — the `RASA_PRO_LICENSE` env var. Free developer licenses:
   https://rasa.com/rasa-pro-developer-edition-license-key-request/
2. **An LLM provider API key** — e.g. `OPENAI_API_KEY`. Maestro drives one LLM loop;
   it needs a capable model (GPT-4-class or Claude).
3. **What the agent should do** — one sentence per skill. If the user has no
   preference, build the `check_balance` example from the quickstart.

Also verify: Python 3.11 or 3.12 available. Prefer `uv` for installation; fall back
to `python -m venv` + `pip`.

## Step 1 — install Rasa Pro

```bash
uv venv .venv && source .venv/bin/activate
uv pip install --prerelease=allow rasa-pro
# fallback: pip install --pre rasa-pro
rasa --version   # must report >= 3.18
```

If `rasa --version` reports < 3.18, Maestro is not in this build — stop and tell the
user which version they got and that Maestro requires the 3.18 beta line.

Export the secrets from Step 0 (`RASA_PRO_LICENSE`, provider key) in this shell.

## Step 2 — scaffold the project

Try the official template first:

```bash
rasa init --template maestro --no-prompt   # available in later betas
```

If that template is not available in the installed version, scaffold by hand — this
minimal layout is a complete, runnable agent:

```
my-agent/
├── agent.yml
├── integrations.yml
└── skills/
    └── check_balance/
        ├── skill.md
        └── tools/
            └── check_balance.py
```

```yaml agent.yml
agent:
  id: my-agent
  language: en
  persona: |
    You are a friendly, concise customer service assistant.
```

```yaml integrations.yml
model_groups:
  - id: primary_llm
    models:
      - provider: openai
        model: gpt-4o-2024-11-20
        api_key: ${OPENAI_API_KEY}
```

```markdown skills/check_balance/skill.md
---
name: check_balance
description: Look up a customer's account balance
---

Help the customer check their account balance.
Ask for their account number, then call @tool.check_balance to look it up.
Report the balance clearly.
```

```python skills/check_balance/tools/check_balance.py
from rasa_sdk import tool, ToolContext, ToolResult

@tool(description="Look up account balance by account number")
async def check_balance(
    account_number: str,
    context: ToolContext
) -> ToolResult:
    balance = 1234.56  # replace with a real API call
    return ToolResult(
        llm_response={"balance": balance, "currency": "USD"}
    )
```

## Step 3 — install the full Maestro skill set

So this harness has the complete guidance for the build phase:

```bash
rasa tools skills install maestro --ides <claude|cursor|vscode|codex> --yes
```

If that command is unavailable (older beta), fetch the skills directly from
`https://raw.githubusercontent.com/RasaHQ/rasa-agent-skills/main/skills-maestro/<name>/SKILL.md`
for each name listed in
`https://raw.githubusercontent.com/RasaHQ/rasa-agent-skills/main/manifest.json`,
and read them as needed instead of installing.

## Step 4 — build what the user asked for

Follow `maestro-building-skills` to write the user's skills. Rules of thumb until
you've read it: one skill per user goal, prose-first, add control levers
(`tool_constraints`, `if:` markers, ordered blocks) only for behavior that must be
guaranteed, not merely preferred.

## Step 5 — validate and train

```bash
rasa validate && rasa train
```

Fix validation errors before training; `maestro-testing-debugging` maps common
errors and misbehaviors to fixes.

## Step 6 — let the user talk to it

```bash
rasa inspect
```

Prefer `rasa inspect` (browser UI showing conversation + memory state) over
`rasa shell` — the shell currently shows the welcome message only after the first
user input in the beta. Hand the user the inspector URL and one example opening
message per skill.

## Done means

- `rasa validate` and `rasa train` exit 0.
- The user has exchanged at least one real turn with the agent.
- Total human interventions: the Step 0 answers, nothing else.
