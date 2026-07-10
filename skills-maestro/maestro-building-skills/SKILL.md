---
name: maestro-building-skills
description: >
  Authors Maestro skills: skill.md instructions, auto-discovered Python tools, and
  the progressive control ladder (tool constraints, scoped instructions, verbatim
  responses, ordered blocks, sub-skills). Use when creating or editing any file under
  skills/, deciding how much control a skill needs, or composing skills together.
license: Apache-2.0
engine: maestro
rasa_version: ">=3.18"
metadata:
  author: rasa
  version: "0.1.0"
  docs-url: https://github.com/RasaHQ/maestro-docs
---

# Building Maestro skills

A skill is a folder under `skills/` holding one user goal. The only required file is
`skill.md`: YAML frontmatter (metadata + control declarations) and a markdown body
(prose instructions the LLM follows). Tools are Python files in the skill's `tools/`
folder — auto-discovered, no registration.

**The core discipline is progressive control: write prose first, add control levers
only when observed behavior must become guaranteed behavior. Every lever is additive
— you never restructure what's already written.**

## Workflow

1. Scope the skill — one user goal per skill (see "Scoping").
2. Write `skill.md` with `name`, `description`, and a prose body. No control levers.
3. Write the tools it needs in `tools/` (see "Tools").
4. Validate, train, converse (`rasa validate && rasa train && rasa inspect`).
5. Observe drift, then add the *narrowest* lever that fixes it (see "The control
   ladder"). Re-test. Repeat.
6. Extract shared behavior into sub-skills only when a second skill needs it.

## Scoping

- **One user goal, clear start and end**: `replace_card`, `check_balance`,
  `book_appointment`. Verb-first `snake_case` names.
- The `description` in frontmatter is what the orchestrator uses to route — write it
  as a routing summary, including trigger phrasings ("lost, stolen, damaged, or not
  received"), not marketing copy.
- Too big: one skill mixing unrelated goals (returns + payments + tracking). Split.
- Too small: a skill that only wraps one utterance or one tool call with no
  conversation. Inline it into the skill that uses it.

## The minimal skill

```markdown skills/card_replace/skill.md
---
name: card_replace
description: Replace a credit card -- lost, stolen, damaged, or not received
---

Help the customer replace a credit card.

Check whether their account is eligible for replacement. If they have
multiple cards, ask which one. Ask why they need a replacement -- the valid
reasons are lost, stolen, damaged, or not received.

For stolen or not-received cards, offer to lock the card while a new one
ships. Once everything is gathered, ask their shipping preference,
confirm the order, and process the replacement.
```

Write the body like instructions to a competent human agent: what to gather, what
order matters (softly), what to offer when. Reference tools as `@tool.<name>`,
ordered blocks as `@block.<id>`, other skills as `@skill.<name>`.

## Tools

```python skills/card_replace/tools/lock_card.py
from rasa_sdk import tool, ToolContext, ToolResult

@tool(description="Lock a card to prevent further transactions")
async def lock_card(
    card_id: str,
    context: ToolContext
) -> ToolResult:
    """Lock a card to prevent further transactions.

    Args:
        card_id: Card identifier from get_customer_info.
    """
    result = await api.post(f"/cards/{card_id}/lock")
    return ToolResult(llm_response={"locked": True, "card_id": card_id})
```

- Function name = tool name; `@tool(description=...)` = what the LLM sees; type
  hints = input schema; Google-docstring `Args:` = per-argument descriptions.
- `context: ToolContext` is injected, invisible to the LLM. Use
  `context.memory.set(key, value)` to write memory (this is what `requires:`
  conditions gate on), `context.send(text)` for immediate deterministic messages.
- Return `ToolResult(llm_response=...)` — the LLM reads this as the tool's result.
  `ToolResult(next=[RunTool(...), ActivateSkill(...)])` overrides control flow
  (e.g. hand off after max auth failures).
- Tools outside the skill folder need frontmatter declaration:

```yaml
import_tools:
  - get_customer_info        # shared: from tools/ at agent root
  - mcp/crm:lookup_account   # MCP server "crm" from integrations.yml
```

- Resolution order: skill-local → shared → MCP. First match wins.
- Naming conventions the framework invokes automatically: `set_<memory_entry>`
  (validate/clean a value during collection), `ask_<memory_entry>` (generate the
  question for a collect step).

## The control ladder

Add levers in this order. Each row is a symptom you actually observed in testing —
don't add levers speculatively.

| Observed drift | Lever | Where |
|---|---|---|
| Calls a tool before its inputs exist | `tool_constraints` → `requires:` | frontmatter |
| Executes an irreversible action without asking | `ask_confirmation:` on the tool | frontmatter |
| Follows the wrong branch / mixes workflows | `if:` / `else:` markers | body |
| Paraphrases wording that must be exact (legal, compliance) | `utter:` triggers + `responses.yml` | frontmatter |
| Right words, wrong moment after a tool | `on_success:` / `on_failure:` on the tool | frontmatter |
| Skips or reorders steps where order IS the requirement | ordered block | body |
| Enters the skill when it shouldn't | skill-level `requires:` | frontmatter |

### Tool gating and confirmation

```yaml
tool_constraints:
  - lock_card:
      requires:
        selected_card_id: { exists: true }
  - process_card_replacement:
      requires:
        order_confirmed: { equals: true }
      ask_confirmation: "Replace {selected_card_label}, shipping {shipping_type}?"
      on_success: utter_replacement_disclaimer
      on_failure: utter_replacement_failed
```

`requires:` removes the tool from the LLM's schema until the memory condition holds
— it cannot call what it cannot see. Conditions check memory keys written by tools
(`context.memory.set`) — no declaration needed for that. `tool_constraints` are
enforced no matter who triggers the tool (LLM or ordered-block step).

### Scoped instructions (`if:`/`else:`)

Deterministic branching without restructuring. Requires a `categorical` entry in
`memory.yml`; the framework strips non-matching paragraphs from the prompt once the
entry is set:

```markdown
if: replacement_reason is stolen
Tell the customer the card will be locked for their protection.
Confirm, then call @tool.lock_card.

if: replacement_reason is lost or replacement_reason is not_received
Call @tool.check_transactions and review recent transactions with them.
```

```yaml memory.yml
memory:
  public:
    replacement_reason:
      type: categorical
      enum: [lost, stolen, damaged, not_received]
```

A marker scopes only the paragraph immediately after it (up to the blank line).
Unmarked paragraphs are always visible.

### Verbatim responses

Exact wording the LLM never touches, declared in frontmatter, text in
`responses.yml` (supports `{memory_key}` interpolation):

```yaml
utter:
  - utter_recording_notice:
      on: activate
  - utter_stolen_warning:
      when: { replacement_reason: { equals: "stolen" } }
```

### Ordered blocks — last resort, not first

Most skills never need one. Reach for a block only when the *sequence itself* is the
requirement (compliance, multi-step approval). Prefer the hybrid form — one block
inside prose, referenced with `@block.<id>`:

```markdown
Ask why they need a replacement. Once the reason is collected invoke @block.pick_card

:::ordered_block
	id: pick_card
	steps:
    - id: check_eligibility
      execute_tool: card_replace_eligibility
    - id: fetch_cards
      execute_tool: get_customer_info
    - id: select_card
      instructions: show user's cards and let them pick one
      complete_when: "selected_card_id" is not null
:::
```

Step types: `execute_tool:` (framework calls, no LLM), `instructions:` +
`complete_when:` (LLM converses inside the step), `noop: true` + `next:`
(deterministic routing), `collect:` + `utter:` (framework collects a value). A block
enforces local order only — users can still interrupt to another skill; the block
resumes at the same step.

## Composition

- `@skill.<name>` in the body runs another skill and *guarantees* the parent
  resumes with access to the sub-skill's public memory exports. A user-initiated
  topic change (interrupt) does not guarantee resumption.
- Default to small focused skills exporting results as `public` memory. Compose
  when a skill needs another's logic mid-conversation (disputes → transaction
  lookup).
- The parent must have business logic of its own — a skill that is nothing but
  `@skill.` references is the orchestrator's job, delete it.
- Cross-skill dependencies go through memory, not direct coupling: gate with
  `requires: { authenticated: { equals: true } }` rather than referencing the auth
  skill.

## Don't

- Don't add control levers the user's requirements don't demand — every lever costs
  conversational flexibility.
- Don't write a fully-controlled ordered block as the starting point; that recreates
  the rigid state machines Maestro exists to replace.
- Don't restate tool results in prose ("the tool returns JSON with...") — the LLM
  sees `llm_response` directly.
- Don't invent frontmatter fields. The set is: `name`, `description`, `requires`,
  `import_tools`, `tool_constraints`, `utter`, `disabled`.
- Don't trust this file over the docs if they disagree — the engine is in beta and
  the docs at `docs-url` are the source of truth. Check `llms.txt` there when
  something fails unexpectedly.
