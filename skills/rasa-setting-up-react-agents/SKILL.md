---
name: rasa-setting-up-react-agents
description: >
  Configures ReAct sub agents in a Rasa CALM assistant. Use when creating a sub-agent
  that dynamically selects MCP tools, choosing between general-purpose and task-specific
  agent types, customizing prompts, filtering tools, adding custom Python tools, or
  overriding input/output processing.
license: Apache-2.0
metadata:
  author: rasa
  version: "0.1.0"
  rasa_version: ">=3.14.0"
  docs-url: https://rasa.com/docs/reference/config/agents/react-sub-agents
---

# Configuring ReAct Sub Agents

ReAct sub agents are built-in autonomous agents that dynamically choose which MCP
tools to invoke based on conversation context. They operate in a ReAct
(Reasoning + Acting) loop — the agent reasons about the user's request, picks a tool,
observes the result, and repeats until the task is done.

MCP servers must be defined in `endpoints.yml` before configuring a ReAct sub agent.
See the `rasa-configuring-mcp-server` skill for server setup and authentication.

This feature is in **beta** and available starting from **Rasa 3.14.0**.

## Workflow

1. Ensure the MCP server is defined in `endpoints.yml` (see `rasa-configuring-mcp-server`
   skill).
2. Create the sub agent directory with a `config.yml`
   (see "Directory structure" and "Configuration").
3. Choose between general-purpose or task-specific agent type
   (see "General-purpose vs task-specific").
4. Optionally filter which MCP tools the agent can access
   (see "Tool filtering").
5. Invoke the sub agent from a flow using a `call` step
   (see "Invoking from a flow").
6. Optionally customize the prompt, input/output processing, or add custom tools
   (see "Customization").
7. Validate the project.

## Directory structure

Each ReAct sub agent lives in its own subdirectory under `sub_agents/`. Both
`rasa train` and `rasa run` scan this directory by default; pass `--sub-agents <path>`
to either command to use a different directory.

The agent name must be unique across all sub agents **and** all flow IDs.

```
your_project/
├── config.yml
├── endpoints.yml
├── domain/
├── data/flows/
└── sub_agents/
    └── stock_explorer/
        ├── config.yml              # required
        ├── prompt_template.jinja2  # optional
        └── custom_agent.py         # optional
```

## Configuration

The sub agent's `config.yml` connects the agent to one or more MCP servers defined in
`endpoints.yml`. The protocol defaults to `RASA` — do **not** set it to `A2A`.

```yaml
# sub_agents/stock_explorer/config.yml
agent:
  name: stock_explorer
  description: "Agent that helps users research and analyze stock options"

configuration:
  llm:                                   # optional, defaults to GPT-4o
    model_group: openai-gpt-4o
  prompt_template: sub_agents/stock_explorer/prompt_template.jinja2  # optional
  timeout: 30                            # optional, seconds before timing out
  max_retries: 3                         # optional, MCP connection retries
  include_date_time: true                # optional, default: true
  timezone: "America/New_York"           # optional, default: "UTC"

connections:
  mcp_servers:
    - name: trade_server
      include_tools:
        - find_symbol
        - get_company_news
        - fetch_live_price
```

| Key | Required | Description |
|-----|----------|-------------|
| `agent.name` | yes | Unique name — must not clash with any flow ID or other sub agent |
| `agent.description` | yes | Brief description of the agent's capabilities |
| `configuration.llm` | no | LLM to power the agent's reasoning. Defaults to GPT-4o |
| `configuration.prompt_template` | no | Path to a Jinja2 prompt template |
| `configuration.timeout` | no | Seconds before timing out. No timeout by default |
| `configuration.max_retries` | no | MCP connection retry attempts. Default: 3 |
| `configuration.include_date_time` | no | Include current date/time in prompts. Default: true |
| `configuration.timezone` | no | IANA timezone (e.g. `"UTC"`, `"Europe/London"`). Default: `"UTC"` |
| `configuration.module` | no | Python class path for customization |
| `connections.mcp_servers` | yes | List of MCP servers this agent connects to. At least one required |

### Tool filtering

For each MCP server entry under `connections.mcp_servers`, use `include_tools` or
`exclude_tools` to control which tools the agent can access. These are **mutually
exclusive** — use one or the other per server, never both.

- `include_tools` — only these tools are available to the agent.
- `exclude_tools` — all tools except these are available.

```yaml
connections:
  mcp_servers:
    - name: trade_server
      include_tools:
        - find_symbol
        - get_company_news
    - name: analytics_server
      exclude_tools:
        - admin_analytics
```

## General-purpose vs task-specific

Rasa supports two types of ReAct sub agents. Choose based on how the agent signals
completion.

| | General-purpose | Task-specific |
|---|---|---|
| **When to use** | Open-ended tasks where the agent decides when it's done | Structured data collection (form filling, booking) |
| **Completion** | Agent calls a built-in `task_completed` tool | Automatic when `exit_if` slot conditions are met |
| **Built-in tools** | `task_completed` only | `set_slot_<slot_name>` for each slot in `exit_if` |
| **Final response** | Sends a summary message to the user | Completes silently — flow continues to next step |
| **Base class** | `MCPOpenAgent` | `MCPTaskAgent` |

## Invoking from a flow

### General-purpose (no exit conditions)

The agent runs autonomously until it calls `task_completed`:

```yaml
flows:
  stock_research:
    description: helps research and analyze stock investment options
    steps:
      - call: stock_explorer
```

### Task-specific (with exit conditions)

The agent runs until the specified slot conditions are met. Rasa automatically provides
`set_slot_<slot_name>` tools for each slot in `exit_if`:

```yaml
flows:
  appointment_booking:
    description: helps users book appointments
    steps:
      - call: booking_agent
        exit_if:
          - slots.appointment_time is not null
      - collect: final_confirmation
```

## Customization

Customization is **optional**. Only create a custom class when you need to:

- **Customize the prompt** — add specific instructions or pass slot values as context.
- **Filter input** — limit which slots reach the agent.
- **Map output to slots** — extract structured data from the agent's tool results.
- **Add custom Python tools** — tools that run alongside MCP tools.

### Custom prompt template

Create a Jinja2 file and reference it in `configuration.prompt_template`. Available
variables:

- `{{ description }}` — the agent's description from `config.yml`.
- `{{ slots.<slot_name> }}` — any slot value.
- `{{ conversation_history }}` — full dialogue transcript.
- `{{ current_datetime }}` — datetime object (when `include_date_time` is enabled).
  Use methods like `{{ current_datetime.strftime("%d %B, %Y") }}`.

### Creating a custom ReAct agent class

1. Create a Python file in the sub agent directory (e.g.
   `sub_agents/stock_explorer/custom_agent.py`).
2. Subclass `MCPOpenAgent` (general-purpose) or `MCPTaskAgent` (task-specific).
3. Override `process_input`, `process_output`, and/or `get_custom_tool_definitions`.
4. Point `configuration.module` to the class.

```python
from rasa.agents.protocol.mcp.mcp_open_agent import MCPOpenAgent
from rasa.agents.schemas import AgentInput, AgentOutput, AgentToolResult
from rasa.sdk.events import SlotSet

class StockAnalysisAgent(MCPOpenAgent):
    async def process_input(self, input: AgentInput) -> AgentInput:
        input.slots = [s for s in input.slots if s.name in {"portfolio_id", "risk_level"}]
        return input

    async def process_output(self, output: AgentOutput) -> AgentOutput:
        if output.structured_results:
            results = output.structured_results[-1]
            output.events = output.events or []
            output.events.append(SlotSet("analysis_result", results))
        return output
```

```yaml
# sub_agents/stock_explorer/config.yml
agent:
  name: stock_explorer
  description: "Agent that helps users research and analyze stock options"

configuration:
  module: "sub_agents.stock_explorer.custom_agent.StockAnalysisAgent"

connections:
  mcp_servers:
    - name: trade_server
```

### What you can modify

**`process_input(input: AgentInput) -> AgentInput`** — modify what the agent receives.
Key fields on `AgentInput`:

| Field | Type | What to do with it |
|-------|------|--------------------|
| `slots` | `List[AgentInputSlot]` | Filter to only relevant slots |
| `user_message` | `str` | Rewrite or augment the user message |
| `conversation_history` | `str` | Trim or redact sensitive history |
| `metadata` | `Dict[str, Any]` | Inject custom metadata |

**`process_output(output: AgentOutput) -> AgentOutput`** — modify what comes back
into Rasa. Key fields on `AgentOutput`:

| Field | Type | What to do with it |
|-------|------|--------------------|
| `events` | `Optional[List[SlotSet]]` | Add `SlotSet` events to store data in Rasa slots |
| `structured_results` | `Optional[List]` | Read raw results from agent tool calls |
| `response_message` | `Optional[str]` | Rewrite the message sent to the user |

### Adding custom tools

Implement `get_custom_tool_definitions` to add Python tools alongside MCP tools. Each
tool definition follows the OpenAI function calling spec and must include a
`tool_executor` key pointing to an async method.

The `tool_executor` method receives `arguments` as a dict and must return an
`AgentToolResult`:

| Field | Type | Description |
|-------|------|-------------|
| `tool_name` | `str` | Name of the tool |
| `result` | `Optional[str]` | The tool's output |
| `is_error` | `bool` | Whether the execution failed. Default: `False` |
| `error_message` | `Optional[str]` | Error details if execution failed |

Tool executors must be async. Do **not** use blocking calls (`time.sleep`,
synchronous `requests`). Use `httpx.AsyncClient`, `asyncio.to_thread`, etc.

```python
from typing import Any, Dict, List

class StockAnalysisAgent(MCPOpenAgent):
    def get_custom_tool_definitions(self) -> List[Dict[str, Any]]:
        return [{
            "type": "function",
            "function": {
                "name": "recommend_stocks",
                "description": "Analyze results and return stock recommendations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_results": {
                            "type": "string",
                            "description": "The search results to analyze",
                        },
                    },
                    "required": ["search_results"],
                    "additionalProperties": False,
                },
                "strict": True,
            },
            "tool_executor": self._recommend_stocks,
        }]

    async def _recommend_stocks(self, arguments: Dict[str, Any]) -> AgentToolResult:
        results = arguments["search_results"]
        return AgentToolResult(tool_name="recommend_stocks", result=results)
```

## Common pitfalls

- **Agent name clashes with flow IDs** — the sub agent name must be unique across all
  flows and all other sub agents.
- **Using `exit_if` with general-purpose agents** — `exit_if` is only for task-specific
  agents. General-purpose agents signal completion via `task_completed`.
- **`include_tools` and `exclude_tools` on the same server** — these are mutually
  exclusive per MCP server entry. Using both causes a validation error.
- **MCP server name mismatch** — the `name` under `connections.mcp_servers` must
  exactly match a `name` in `endpoints.yml`.
- **Blocking calls in custom tool executors** — tool executors are async. Using
  `time.sleep` or synchronous HTTP clients blocks the event loop.
- **Invalid timezone** — `configuration.timezone` must be a valid IANA timezone name.
  Invalid values raise a `ValidationError` during agent initialization.
- **User messages during processing** — messages sent while the sub agent is still
  processing are not handled. Users must wait for the agent to complete or reach
  `INPUT_REQUIRED`.
