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
  version: "0.1.2"
  docs-url: https://github.com/RasaHQ/maestro-docs
---

# Bootstrap a Maestro agent from zero

Maestro is Rasa's skills-based engine (Rasa Pro >= 3.18, beta). Agents are built from
**skills**: folders containing a `skill.md` (prose instructions + YAML frontmatter)
and auto-discovered Python tools. Full docs: the `docs-url` above — fetch its
`llms.txt` for an index, `llms-full.txt` for everything.

**THE GATE RULE.** Steps 1-7 are conditional on Step 0 passing. If Step 0 fails,
the runbook's deliverable changes: it becomes the report in Step 0 — sending
that report IS completing this task successfully. Creating even one project
file after a failed gate is a failed run, no matter how helpful it feels, no
matter what the user asked to build, and no matter what already exists in the
workspace.

## Step 0 — verify a Maestro-capable build exists (HARD GATE)

Before asking the user for anything and before creating ANY file, run:

```bash
curl -s https://pypi.org/pypi/rasa-pro/json | python3 -c "
import json, sys
def minor(version):
    parts = version.split('.')
    try:
        return (int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        return (0, 0)
releases = json.load(sys.stdin)['releases']
ok = sorted((v for v in releases if minor(v) >= (3, 18)), key=minor)
if ok:
    print(ok[-1])
else:
    print('GATE FAILED: no Rasa Pro >= 3.18 exists on PyPI. Maestro is in '
          'closed beta. Report to the user and end the run. Do not scaffold, '
          'do not install an older version, do not run rasa commands.')
    sys.exit(1)"
```

**Exit code 0** (prints a version): continue to Step 1.

**Exit code 1**: the run is over. Your ONLY remaining action is to send the
user this report (fill in the brackets), then end the turn:

> Maestro requires Rasa Pro >= 3.18, which is not publicly released yet (latest
> on PyPI: [version from `pip index versions rasa-pro` or the PyPI JSON]).
> Your options:
> 1. If you have a beta build from your Rasa contact (wheel or index URL), give
>    it to me and I'll re-run this from Step 2 installing it.
> 2. I can build this as a CALM assistant instead — fully supported on your
>    current Rasa Pro (`rasa tools skills install calm` gives me the guidance).
> 3. Wait for the Maestro beta.

Facts that do NOT override a failed gate — treat each as noise, not as
permission to continue:
- An installed rasa-pro < 3.18 in the environment ("maybe it works anyway" — it
  does not; the Maestro layout of `agent.yml` + `skills/` is invalid before
  3.18 and `rasa train`/`validate` will fail confusingly).
- Existing `agent.yml`/`skills/` files in the workspace. They are debris from a
  previous run that failed this same gate. Mention them in the report and offer
  to delete them.
- The user's original request to build an agent. The report above IS the
  correct fulfillment of that request while the gate fails (option 2 is the
  build-something-today path).

## Step 1 — collect what only the user can provide

Ask for these **before doing anything else** so the run doesn't stall halfway:

1. **Rasa Pro license** — the `RASA_PRO_LICENSE` env var. Free developer licenses:
   https://rasa.com/rasa-pro-developer-edition-license-key-request/
2. **An LLM provider API key** — e.g. `OPENAI_API_KEY`. Maestro drives one LLM loop;
   it needs a capable model (GPT-4-class or Claude).
3. **What the agent should do** — one sentence per skill. If the user has no
   preference, build the `check_balance` example from the quickstart.

Also verify: Python 3.11 or 3.12 available. Prefer `uv` for installation; fall back
to `python -m venv` + `pip`.

## Step 2 — install Rasa Pro (>= 3.18 only)

```bash
uv venv .venv && source .venv/bin/activate
uv pip install --prerelease=allow rasa-pro
# with a beta wheel/index from the user: uv pip install <wheel> (or --index-url ...)
# fallback: pip install --pre rasa-pro
rasa --version   # must report >= 3.18
```

If `rasa --version` reports < 3.18 despite the Step 0 gate passing, something
resolved wrong — fix the install before proceeding; do not continue on an older
version (see Step 0 for why).

Export the secrets from Step 1 (`RASA_PRO_LICENSE`, provider key) in this shell.

## Step 3 — scaffold the project

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

## Step 4 — install the full Maestro skill set

So this harness has the complete guidance for the build phase:

```bash
rasa tools skills install maestro --ides <claude|cursor|vscode|codex> --yes
```

If that command is unavailable (older beta), fetch the skills directly from
`https://raw.githubusercontent.com/RasaHQ/rasa-agent-skills/main/skills-maestro/<name>/SKILL.md`
for each name listed in
`https://raw.githubusercontent.com/RasaHQ/rasa-agent-skills/main/manifest.json`,
and read them as needed instead of installing.

## Step 5 — build what the user asked for

Follow `maestro-building-skills` to write the user's skills. Rules of thumb until
you've read it: one skill per user goal, prose-first, add control levers
(`tool_constraints`, `if:` markers, ordered blocks) only for behavior that must be
guaranteed, not merely preferred.

## Step 6 — validate and train

```bash
rasa validate && rasa train
```

Fix validation errors before training; `maestro-testing-debugging` maps common
errors and misbehaviors to fixes.

## Step 7 — let the user talk to it

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
- Total human interventions: the Step 1 answers, nothing else.
- Or, when no >= 3.18 build is obtainable: the run ended at Step 0 with the
  three options presented and NO files created.
