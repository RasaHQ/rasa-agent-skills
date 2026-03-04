---
name: rasa-calling-mcp-tools-from-flows
description: >
  Calls MCP tools directly from Rasa flow steps. Use when invoking an MCP tool via a
  call step, mapping slot values to tool parameters, or extracting tool results into
  slots. This replaces custom action code for simple API integrations.
license: Apache-2.0
metadata:
  author: rasa
  version: "3.14.x"
  docs-url: https://rasa.com/docs/pro/build/mcp-integration
---

# Calling MCP Tools from Flows

MCP tools can be invoked directly from flow steps using a `call` step with explicit
input/output mappings. This replaces the need for custom action code when you only need
to call an external API.

MCP servers must be defined in `endpoints.yml` before calling their tools. See the
`rasa-configuring-mcp-server` skill for server setup and authentication.

This feature is in **beta** and available starting from **Rasa 3.14.0**.

## Workflow

1. Ensure the MCP server is defined in `endpoints.yml`
   (see `rasa-configuring-mcp-server` skill).
2. Call the MCP tool from a flow using a `call` step with `mcp_server` and `mapping`
   (see "Calling an MCP tool from a flow").
3. Map tool results to slots, handling both structured and unstructured output
   (see "Tool result formats").
4. Validate the project.

## Calling an MCP tool from a flow

Use a `call` step with `mcp_server` and `mapping` to invoke a tool directly.

| Key              | Required | Description |
|------------------|----------|-------------|
| `call`           | yes | Tool name as exposed by the MCP server |
| `mcp_server`     | yes | Must exactly match a `name` in `endpoints.yml`. Fails at runtime if mismatched |
| `mapping.input`  | yes | Maps slot values to tool parameters. Each entry: `param` (tool parameter name) + `slot` (Rasa slot name) |
| `mapping.output` | yes | Maps tool results back to slots. Each entry: `slot` (target slot) + `value` (Jinja2 expression to extract the result) |

```yaml
flows:
  buy_order:
    description: helps users place a buy order for a particular stock
    steps:
      - collect: stock_name
      - collect: order_quantity
      - action: check_feasibility
        next:
          - if: slots.order_feasible is True
            then:
              - call: place_buy_order
                mcp_server: trade_server
                mapping:
                  input:
                    - param: ticker_symbol
                      slot: stock_name
                    - param: quantity
                      slot: order_quantity
                  output:
                    - slot: order_status
                      value: result.structuredContent.order_status.success
          - else:
              - action: utter_invalid_order
                next: END
```

## Tool result formats

MCP tools return results in one of two formats. Handle both in your output mapping.

### Structured content

When the tool defines an output schema, Rasa returns structured data. Access specific
values using dot notation in the `value` field:

```yaml
# Tool returns: {"result": {"structuredContent": {"order_status": {"success": true, "order_id": "abc123"}}}}
output:
  - slot: order_status
    value: result.structuredContent.order_status.success
  - slot: order_id
    value: result.structuredContent.order_status.order_id
```

### Unstructured content

When the tool has no output schema, the entire result is a serialized string. Capture
it in a single slot for downstream processing:

```yaml
# Tool returns: {"result": {"content": [{"type": "text", "text": "{\"order_status\": ...}"}]}}
output:
  - slot: order_data
    value: result.content
```

## Common pitfalls

- **MCP server name mismatch** — the `mcp_server` value in a flow `call` step must
  exactly match a `name` in `endpoints.yml`. A typo means the call fails at runtime
  with no compile-time warning.
- **Missing tool on server** — if the tool name in `call` doesn't exist on the
  referenced MCP server, the call fails at runtime.
- **Ignoring unstructured content** — when a tool has no output schema, results come
  back as a serialized string under `result.content`, not as `result.structuredContent`.
  Always account for both formats.
