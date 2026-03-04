---
name: rasa-configuring-mcp-server
description: >
  Configures MCP (Model Context Protocol) servers in a Rasa CALM assistant. Use when
  defining MCP servers in endpoints.yml, setting up authentication (API key, OAuth 2.0,
  pre-issued token), or connecting to multiple external services.
license: Apache-2.0
metadata:
  author: rasa
  version: "3.14.x"
  docs-url: https://rasa.com/docs/reference/integrations/mcp-servers
---

# Configuring MCP Servers

MCP servers expose external tools — APIs, databases, services — to a Rasa assistant. All
MCP servers are defined in `endpoints.yml` and shared across direct flow tool calls and
ReAct sub agents.

This feature is in **beta** and available starting from **Rasa 3.14.0**.

## Workflow

1. Add each MCP server to `endpoints.yml` (see "Server definition").
2. Add authentication if the server requires it (see "Authentication").
3. Validate the project.

## Server definition

Register every MCP server in `endpoints.yml`.

| Key    | Required | Description |
|--------|----------|-------------|
| `name` | yes      | Unique identifier — referenced from flows and sub agent configs. Duplicates cause a validation error at startup |
| `url`  | yes      | URL where the MCP server is running |
| `type` | yes      | `http` or `https` |

```yaml
# endpoints.yml
mcp_servers:
  - name: trade_server
    url: http://localhost:8080
    type: http
  - name: payment_server
    url: https://api.payment-service.com
    type: https
```

## Authentication

Add auth fields directly to the server entry in `endpoints.yml` when the MCP server
requires credentials. Sensitive values (`api_key`, `token`, `client_secret`) **must**
use `${ENV_VAR}` syntax — plain text is rejected by validation.

### API key

Sent as `Authorization: Bearer <key>` by default. Add `header_name` and
`header_format` to override the header.

```yaml
mcp_servers:
  - name: secure_api_server
    url: https://api.example.com
    type: https
    api_key: "${API_KEY}"
    header_name: "X-API-Key"       # optional, default: Authorization
    header_format: "{key}"          # optional, default: Bearer {key}
```

### OAuth 2.0 (client credentials)

```yaml
mcp_servers:
  - name: oauth_server
    url: https://api.example.com
    type: https
    oauth:
      client_id: "${CLIENT_ID}"
      client_secret: "${CLIENT_SECRET}"
      token_url: "https://auth.example.com/oauth/token"
      scope: "read:data write:data"    # optional
      audience: "https://api.example.com"  # optional
      timeout: 10                      # optional
```

### Pre-issued token

```yaml
mcp_servers:
  - name: token_server
    url: https://api.example.com
    type: https
    token: "${ACCESS_TOKEN}"
```
