---
name: rasa-building-skills
description: >
  Builds skills (capabilities) for a Rasa CALM assistant. Use when the user asks to
  create, add, or build a skill, capability, or feature for their Rasa assistant.
license: Apache-2.0
metadata:
  author: rasa
  version: "0.1.0"
  rasa_version: ">=3.14.0"
---

# Building Skills for a Rasa Assistant

## Terminology

In Rasa, a **skill** is a self-contained module inside a Rasa assistant that packages a
specific capability or domain (e.g. booking, payments, order tracking).

The term "skill" can also refer to a IDE agent skill (SKILL.md). Use conversation
context to determine which meaning the user intends. If ambiguous, **ask**.

A Rasa skill defines its interface (slots / memory) and logic (flows, prompts, actions,
or tools). It is implemented as either:

1. **Flow-based** — a bundle of flows and slots for guided, deterministic behavior.
2. **Sub-agent** — a sub-agent that plans and acts autonomously using tools.
3. **Hybrid** — an orchestrator flow that delegates some steps to a sub-agent.

## Workflow

1. Clarify what the user wants the Rasa assistant to do.
2. Choose the implementation approach (see "Choosing the approach").
3. Design the skill boundary — slots, flows, responses, actions, sub-agents
   (see "Designing the skill boundary").
4. Implement using the appropriate skill:
   - Flow-based → `rasa-building-flows`
   - ReAct sub-agent → `rasa-setting-up-react-agents`
   - A2A sub-agent → `rasa-setting-up-a2a-agents`
5. Ensure the new flows or sub-agents are reachable (via `call`/`link` steps or
   triggerable by their description).

## Choosing the approach

The first design choice is how autonomous the skill should be:

```
if high-risk domain (payments, auth, KYC, PII, compliance):
    use flow-based
elif business logic must be tightly controlled (strict validation, fixed steps):
    use flow-based
elif most steps are deterministic but some need autonomy:
    use hybrid (flow orchestrates, sub-agent handles open-ended steps)
else:
    use sub-agent (start autonomous, add flows later for guardrails as needed)
```

If the approach is not obvious from context, ask the user whether they want more control
over the conversation (flow-based) or a more autonomous experience (sub-agent). Frame it
in terms of the trade-off: flows give predictability and auditability, sub-agents give
flexibility and a more natural interaction. This is especially important when the user
asks for multiple skills at once — each skill may warrant a different approach, so
confirm the intent per skill before implementing.

## Designing the skill boundary

Before implementing, outline:

1. **Slots** — the skill's interface. See `rasa-managing-slots`.
2. **Flows** — one per user goal. See `rasa-building-flows`.
3. **Responses** — See `rasa-writing-responses`.
4. **Actions** — backend operations. See `rasa-writing-custom-actions`.
5. **Sub-agents** — MCP servers and tools. See `rasa-setting-up-react-agents` or
   `rasa-setting-up-a2a-agents`.

### File organization

A single-flow skill can live in one file (e.g. `data/track_order.yml`). When a skill
contains multiple flows, group them in a subdirectory named after the skill:

```
data/
├── track_order.yml              # single-flow skill
├── booking/                     # multi-flow skill
│   ├── book_flight.yml
│   ├── select_destination.yml
│   └── choose_seats.yml
├── payments/
│   ├── process_payment.yml
│   └── verify_payment.yml
domain/
├── booking.yml
├── payments.yml
sub_agents/
├── policy_search/
│   └── config.yml
```

## Related skills

| Skill | Use for |
|-------|---------|
| `rasa-building-flows` | Writing flows, branching logic, `call`/`link` steps |
| `rasa-managing-slots` | Defining slots, types, mappings, persistence |
| `rasa-writing-responses` | Bot responses and `utter_ask_*` templates |
| `rasa-writing-custom-actions` | Custom actions and validation actions |
| `rasa-setting-up-react-agents` | ReAct sub-agents with MCP tools |
| `rasa-setting-up-a2a-agents` | External sub-agents via A2A protocol |
| `rasa-calling-mcp-tools-from-flows` | Invoking MCP tools directly from flow steps |
| `rasa-configuring-mcp-server` | MCP server setup in `endpoints.yml` |
| `rasa-configuring-assistant` | Pipeline, policies, `config.yml` / `endpoints.yml` |
| `rasa-writing-e2e-tests` | End-to-end conversation tests |


## Examples

For worked examples (flight booking, stock research, payments, insurance claims, Jira),
see [references/examples.md](references/examples.md).