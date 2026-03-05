---
name: rasa-setting-up-a2a-agents
description: >
  Connects external sub agents to a Rasa CALM assistant via the A2A (Agent-to-Agent)
  protocol. Use when adding an external agent, configuring an agent card, setting up
  A2A authentication, customizing input/output processing, or invoking an external
  sub agent from a flow.
license: Apache-2.0
metadata:
  author: rasa
  version: "3.14.x"
  docs-url: https://rasa.com/docs/reference/config/agents/external-sub-agents
---

# Connecting A2A External Sub Agents

External sub agents connected via the A2A protocol operate as autonomous entities that
handle complex, multi-turn conversations independently. When invoked through a `call`
step in a flow, the external agent takes control of the conversation until its task is
complete.

This feature is in **beta** and available starting from **Rasa 3.14.0**.

## Workflow

1. Ensure the external agent is running and exposes an A2A-compatible endpoint with an
   agent card.
2. Create the sub agent directory: `sub_agents/<agent_name>/` with a `config.yml`
   (see "Directory structure").
3. Set `agent.protocol: A2A` and point `configuration.agent_card` to the agent card
   file or URL (see "Configuration").
4. Add authentication if the external agent requires it (see "Authentication").
5. Invoke the sub agent from a flow using an autonomous `call` step
   (see "Invoking from a flow").
6. Optionally customize input/output processing with a Python module
   (see "Customization").
7. Validate the project.

## Directory structure

Each A2A sub agent lives in its own subdirectory under `sub_agents/`. Both `rasa train`
and `rasa run` scan this directory by default; pass `--sub-agents <path>` to either
command to use a different directory.

The agent name must be unique across all sub agents **and** all flow IDs.

```
your_project/
├── config.yml
├── domain/
├── data/flows/
└── sub_agents/
    └── car_shopping_agent/
        ├── config.yml              # required
        ├── agent_card.json         # local agent card (or use a URL instead)
        └── custom_agent.py         # optional customization module
```

## Configuration

The `config.yml` requires `agent.protocol: A2A` and a `configuration.agent_card`
pointing to either a local JSON file (relative to project root) or a remote URL.

```yaml
# sub_agents/car_shopping_agent/config.yml

agent:
  name: car_shopping_agent
  protocol: A2A
  description: "Helps users shop for cars by connecting them with dealers"

configuration:
  agent_card: ./sub_agents/car_shopping_agent/agent_card.json
```

| Key                        | Required | Description |
|----------------------------|----------|-------------|
| `agent.name`               | yes      | Unique name — must not clash with any flow ID |
| `agent.protocol`           | yes      | Must be `A2A` for external sub agents |
| `agent.description`        | yes      | Brief description of the agent's capabilities |
| `configuration.agent_card` | yes      | Path or URL to the A2A agent card |
| `configuration.module`     | no       | Python class path for customization |

### Agent card

Do **not** create the agent card yourself — it is supplied by the external agent's
provider. Your job is to obtain it (as a JSON file or URL) and reference it in
`configuration.agent_card`. Rasa reads the card at startup to resolve the agent's
endpoint, transport, and auth requirements, then health-checks the connection. If the
agent is unreachable, startup fails.

## Authentication

Add an `auth` section under `configuration` in the sub agent's `config.yml`
(`sub_agents/<agent_name>/config.yml`) when the external agent requires credentials.
Sensitive values (`api_key`, `token`, `client_secret`) **must** use `${ENV_VAR}`
syntax — plain text is rejected by validation.

### API key

Sent as `Authorization: Bearer <key>` by default. Add `header_name` and
`header_format` to override the header.

```yaml
configuration:
  agent_card: ./sub_agents/shopping_agent/agent_card.json
  auth:
    api_key: "${API_KEY}"
    header_name: "X-API-Key"       # optional, default: Authorization
    header_format: "{key}"          # optional, default: Bearer {key}
```

### OAuth 2.0 (client credentials)

```yaml
  auth:
    oauth:
      client_id: "${CLIENT_ID}"
      client_secret: "${CLIENT_SECRET}"
      token_url: "https://auth.company.com/oauth/token"
      scope: "read:users"
```

### Pre-issued token

```yaml
  auth:
    token: "${ACCESS_TOKEN}"
```

## Invoking from a flow

Use an autonomous `call` step to delegate part of a conversation to the external
agent. The agent name must match `agent.name` in the sub agent's `config.yml`.

```yaml
flows:
  shop_for_car:
    description: Helps users browse and purchase a car through an external agent.
    steps:
      - collect: user_budget
      - call: car_shopping_agent    # runs until the external agent signals completion
      - action: utter_purchase_summary
```

Do **not** use `exit_if` — it is only supported for ReAct sub agents. The external
agent controls its own completion via the A2A protocol.

## Task vs Message responses

When designing the external agent's response behavior:

- Use **Tasks** for the main workflow — they support status tracking and allow the
  agent to signal `COMPLETED`.
- Use **Messages** only for clarifications — Rasa maps every `Message` to
  `INPUT_REQUIRED`, so the conversation stays open and never completes.
- Never rely on Messages alone for the main operations — use a Task-only or hybrid
  approach.

## Customization

By default Rasa sends all conversation slots to the external agent and passes the
agent's response straight back. Customization is **optional** — only create a custom
class when you need to:

- **Filter input** — limit which slots reach the external agent (e.g. send only
  `user_budget` and `car_type`, not every slot in the conversation).
- **Map output to slots** — extract structured data from the agent's response and
  store it in Rasa slots so downstream flow steps can branch on it.

### Creating a custom A2A agent class

1. Create a Python file in the sub agent directory (e.g.
   `sub_agents/car_shopping_agent/custom_agent.py`).
2. Subclass `A2AAgent` and override `process_input` and/or `process_output`.
3. Point `configuration.module` to the class.

```python
from rasa.agents.protocol.a2a.a2a_agent import A2AAgent
from rasa.agents.schemas import AgentInput, AgentOutput
from rasa.sdk.events import SlotSet

class CarShoppingAgent(A2AAgent):
    async def process_input(self, input: AgentInput) -> AgentInput:
        input.slots = [s for s in input.slots if s.name in {"user_budget", "car_type"}]
        return input

    async def process_output(self, output: AgentOutput) -> AgentOutput:
        if output.structured_results:
            results = output.structured_results[-1]
            output.events = output.events or []
            output.events.append(SlotSet("selected_car", results))
        return output
```

```yaml
# sub_agents/car_shopping_agent/config.yml
agent:
  name: car_shopping_agent
  protocol: A2A
  description: "Helps users shop for cars"

configuration:
  agent_card: ./sub_agents/car_shopping_agent/agent_card.json
  module: "sub_agents.car_shopping_agent.custom_agent.CarShoppingAgent"
```

### What you can modify

**`process_input(input: AgentInput) -> AgentInput`** — modify what the external agent
receives. Key fields on `AgentInput`:

| Field                  | Type | What to do with it |
|------------------------|------|--------------------|
| `slots`                | `List[AgentInputSlot]` | Filter to only relevant slots |
| `user_message`         | `str` | Rewrite or augment the user message |
| `conversation_history` | `str` | Trim or redact sensitive history |
| `metadata`             | `Dict[str, Any]` | Inject custom metadata |

**`process_output(output: AgentOutput) -> AgentOutput`** — modify what comes back into
Rasa. Key fields on `AgentOutput`:

| Field | Type | What to do with it |
|-------|------|--------------------|
| `events` | `Optional[List[SlotSet]]` | Add `SlotSet` events to store data in Rasa slots |
| `structured_results` | `Optional[List]` | Read raw results from agent tool calls |
| `response_message` | `Optional[str]` | Rewrite the message sent to the user |

## Common pitfalls

- **Missing `protocol: A2A`** — without this, Rasa defaults to the RASA protocol and
  treats the agent as a ReAct sub agent, which will fail.
- **Agent name clashes with flow IDs** — the agent name must be unique across all
  flows and all other sub agents.
- **Agent unreachable at startup** — Rasa health-checks the agent card endpoint on
  boot. If the external agent is down, Rasa will not start.
- **Using `exit_if` with A2A agents** — `exit_if` is only supported for ReAct sub
  agents. A2A agents control their own completion via the A2A protocol.
- **Message-only response pattern** — responding only with `Message` objects keeps the
  conversation in `INPUT_REQUIRED` indefinitely. Use `Task` objects for the main
  workflow so the agent can signal `COMPLETED`.
- **User messages during processing** — messages sent while the sub agent is still
  processing are not handled. Users must wait for `INPUT_REQUIRED` or `COMPLETED`.
