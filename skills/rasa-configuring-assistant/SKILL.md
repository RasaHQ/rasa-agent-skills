---
name: rasa-configuring-assistant
description: >
  Configures config.yml and endpoints.yml for Rasa CALM assistants. Covers pipeline
  (command generators, flow retrieval), policies (FlowPolicy), action endpoint, and
  language settings. Use when setting up a new project or modifying pipeline components.
license: Apache-2.0
metadata:
  author: rasa
  version: "0.1.0"
  rasa_version: ">=3.13.0"
  docs-url: https://rasa.com/docs/pro/build/configuring-assistant
---

# Configuring a Rasa Assistant

## Workflow

1. Check if `config.yml` and `endpoints.yml` already exist.
2. Configure the pipeline in `config.yml` with at least one command generator
   (see "Pipeline").
3. Add `FlowPolicy` to policies (see "Policies").
4. Set the language and assistant ID (see "Language" and "Assistant ID").
5. Define model groups in `endpoints.yml`.
6. Configure the action endpoint if custom actions are used (see "Action endpoint").
7. Validate the project.

## config.yml

The `config.yml` file defines how the assistant processes user messages. It specifies
recipe, language, pipeline components, and policies.

### Minimal CALM configuration

A working CALM assistant requires at minimum:

```yaml
recipe: default.v1
language: en

pipeline:
  - name: CompactLLMCommandGenerator  # or SearchReadyLLMCommandGenerator

policies:
  - name: FlowPolicy
```

### Pipeline

The pipeline processes user messages and produces commands for the conversation. The
main component is the Command Generator (e.g. `CompactLLMCommandGenerator` or
`SearchReadyLLMCommandGenerator`), which uses an LLM to interpret user messages and
generate commands.

Configure the LLM model via `model_group` (defined in `endpoints.yml`), flow retrieval
embeddings, and input limits:

```yaml
pipeline:
  - name: CompactLLMCommandGenerator
    llm:
      model_group: my_llm                  # references model_groups in endpoints.yml
    flow_retrieval:
      embeddings:
        model_group: my_embeddings         # references model_groups in endpoints.yml
    user_input:
      max_characters: 420
```

### Policies

Policies determine how the assistant progresses conversations. For CALM, `FlowPolicy` is
required — it executes flow steps based on the commands produced by the pipeline. No
additional configuration is needed.

```yaml
policies:
  - name: FlowPolicy
```

### Language

Set the primary language with a two-letter ISO 639-1 code. Use `additional_languages`
for multilingual assistants.

```yaml
language: en
additional_languages:
  - de
  - fr
```

### Assistant ID

A unique identifier included in every event's metadata. Always set this explicitly — if
missing, a random ID is generated on every `rasa train`.

```yaml
assistant_id: my_assistant
```

## endpoints.yml

The `endpoints.yml` file defines how the assistant connects to external services — LLM
providers, action servers, model storage, and more.

Use `${VARIABLE_NAME}` to reference environment variables for API keys and other
sensitive values.

### Model groups

Define model groups in `endpoints.yml` for LLM and embedding providers. Pipeline
components reference groups by `id`.

See the `rasa-configuring-model-groups` skill for full details on providers,
multi-deployment routing, failover, and self-hosted models.

```yaml
model_groups:
  - id: my_llm
    models:
      - provider: <your-provider>       # e.g. openai, azure, self-hosted
        model: <your-llm-model>

  - id: my_embeddings
    models:
      - provider: <your-provider>
        model: <your-embedding-model>
```

### Action endpoint

Tells Rasa where the action server runs for executing custom actions. Supports HTTP,
HTTPS, gRPC, and secure gRPC protocols.

Use `enable_selective_domain: true` to only send the domain to actions that explicitly 
request it (reduces payload size).

```yaml
action_endpoint:
  url: "http://localhost:5055/webhook"   # or https://, grpc://
  # cafile: "/path/to/ssl_ca_certificate"  # for HTTPS or secure gRPC
  enable_selective_domain: true            # optional, reduces payload size
```

### NLG server

Configure an external NLG server to generate responses dynamically instead of using
static templates from the domain. The endpoint must serve a `/nlg` path.

```yaml
nlg:
  url: http://localhost:5055/nlg
  # token: "my_authentication_token"        # optional token auth
  # basic_auth:                             # or basic auth
  #   username: user
  #   password: pass
```

The rephraser (`nlg: type: rephrase`) is covered by the `rasa-rephrasing-responses`
skill.

### MCP servers

MCP server configuration (`mcp_servers` in `endpoints.yml`) is covered by the
`rasa-configuring-mcp-server` skill.

### Silence handling

Controls how long the assistant waits before assuming the user is silent. Only applies
to voice-stream channels (Twilio, Browser Audio, Genesys, Jambonz, Audiocodes).

```yaml
interaction_handling:
  global_silence_timeout: 7    # seconds, default: 7
```
