---
name: maestro-migrating-from-calm
description: >
  Migrates a CALM (flows-based) Rasa assistant to the Maestro engine: maps flows to
  skills, slots to memory, custom actions to tools, and identifies what has no
  migration path (custom components, command generators, NLU pipeline, rephraser
  customizations). Use when a project contains domain.yml/config.yml/flows and the
  goal is a Maestro agent.
license: Apache-2.0
engine: maestro
rasa_version: ">=3.18"
metadata:
  author: rasa
  version: "0.1.0"
  docs-url: https://github.com/RasaHQ/maestro-docs
---

# Migrating a CALM assistant to Maestro

Maestro is not a config translation — it's a different control model. CALM encodes
behavior as explicit flow steps; Maestro encodes it as prose instructions plus
targeted control levers. A mechanical 1:1 port of every flow step into an ordered
block produces the worst of both worlds. Migrate *intent*, not *structure*.

## Migration workflow

1. **Inventory** the source project: flows (`data/`), slots + responses
   (`domain.yml`), custom actions (`actions.py` / action server), pipeline
   customizations (`config.yml`), endpoints/credentials.
2. **Group flows into skills.** One skill per user goal. A CALM parent flow with
   its `call`ed child flows usually collapses into ONE skill — child flows become
   prose sections, `@block`s, or sub-skills only if independently reusable.
3. **Port tools first** (from custom actions) — they're the most mechanical part
   and everything else references them.
4. **Rewrite each flow as prose** in `skill.md`: describe the goal and what to
   gather, not step numbering. Let the LLM own sequencing initially.
5. **Re-add guarantees the old flow actually enforced** using the control ladder
   (see `maestro-building-skills`): slot preconditions → `requires:`, branching →
   `if:` markers, confirmations → `ask_confirmation:`, mandated wording → verbatim
   responses, genuinely order-critical sections → one ordered block.
6. **Port config** to `agent.yml` + `integrations.yml` (see
   `maestro-configuring-agent`).
7. **Test side by side**: run the same conversations against the old bot and the
   new agent (`rasa inspect`); compare outcomes per the checklist in
   `maestro-testing-debugging`.

## Mapping table

| CALM artifact | Maestro target | Effort |
|---|---|---|
| Flow (YAML steps) | Skill prose body; ordered block only for order-critical sections | Rewrite, not transform |
| `call` step → child flow | Same-skill prose section or `@block.<id>`; `@skill.<name>` if reused across skills | Judgment call |
| `link` step | `@skill.<name>` reference, or plain orchestrator routing | Small |
| `collect` step | Prose ("ask for X"); `collect:` step inside an ordered block if strict | Small |
| Slot | Memory entry (`memory.yml`) — `public` if other flows read it, else `private`; categorical slots keep their enum | Small |
| Slot validation action | `set_<memory_entry>` tool (raise `InvalidMemoryValue` to reject) | Small |
| Dynamic question generation | `ask_<memory_entry>` tool | Small |
| `utter_` response (must stay exact) | `responses.yml` + `utter:`/`on_success:`/`on_failure:` triggers | Small |
| `utter_` response (tone only) | Delete — prose instructions + persona cover it | Free |
| Custom action | `@tool` function: `tracker.get_slot` → `context.memory.get`, `SlotSet(...)` → `context.memory.set(...)`, `dispatcher.utter_message` → `context.send` or `llm_response` | Medium — code updates + verification |
| `pattern_session_start` | `agent.yml` `startup:` | Small |
| Rephraser prompt | `agent.yml` `persona:` | Small |
| `endpoints.yml` + `credentials.yml` | `integrations.yml` (one file) | Small |
| `domain.yml` | Dissolves — slots→memory, responses→responses.yml/prose, actions→tools | Structural |

## No migration path — flag these to the user, do not silently drop

| CALM artifact | Why it breaks | What to do |
|---|---|---|
| Custom graph components (`config.yml` pipeline) | The pipeline doesn't exist; one LLM loop replaced it | Identify the component's *intent*; check if a control lever or tool covers it; otherwise raise to the user |
| Custom command generators | The command-generation stage is gone | Usually subsumed by the orchestrator; verify the behaviors it enforced, re-add as levers |
| NLU pipeline tuning (intents, entities, regexes) | No NLU stage | Intent triggers → skill `description` phrasing; entity extraction → tool arguments typed by the LLM |
| Standalone rephraser customizations | Stage removed; phrasing is inline | Global tone → `persona`; per-response mandates → verbatim responses |
| ReAct-style sub-agents | Subsumed by the single orchestrator | Re-express as skills; external A2A agents keep working via tools/MCP |

## Anti-patterns

- **The 40-step ordered block.** If the migrated skill is one giant block mirroring
  the old flow graph, you've rebuilt the state machine. Ask which steps had a
  *regulatory or correctness* ordering requirement — typically 2-5 — and let prose
  handle the rest.
- **A slot-for-slot memory schema.** CALM projects accumulate bookkeeping slots
  (flow guards, internal flags). Most become unnecessary — the framework tracks
  block step state and skill routing itself. Port only memory that carries business
  meaning.
- **Porting `utter_` responses wholesale into responses.yml.** Verbatim responses
  are for wording that MUST be exact. Porting all 200 utterances makes the agent
  sound like the old bot and defeats the engine. Default to deletion; keep the
  legal/compliance set.
- **Migrating all flows at once.** Port one high-traffic skill end to end, validate
  behavior parity, then batch the rest with the patterns you established.

## Verification of parity

For each migrated skill, run the old bot's e2e test conversations manually against
the new agent and confirm: same data collected, same gates enforced (confirmations,
auth), same side effects (tool calls that hit real APIs), compliance wording
byte-identical where required. Log every intentional behavior difference in the
migration notes for the user — "more natural" is a change too.
