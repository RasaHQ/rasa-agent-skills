---
name: rasa-configuring-model-groups
description: >
  Configures model_groups in endpoints.yml for LLM and embedding providers. Covers
  single and multi-deployment setups, routing strategies, failover, self-hosted models,
  and caching. Use when adding or changing LLM providers or setting up multi-LLM routing.
license: Apache-2.0
metadata:
  author: rasa
  version: "0.1.0"
  rasa_version: ">=3.11.0"
  docs-url: https://rasa.com/docs/pro/deploy/llm-routing
---

# Configuring Model Groups

Model groups are defined in `endpoints.yml` under the `model_groups` key. Pipeline
components, the rephraser, and other features reference groups by their `id`. Each
group contains one or more model deployments and an optional `router` for
multi-deployment routing.

## Workflow

1. Open `endpoints.yml` (create if it doesn't exist).
2. Add a model group for the LLM used by the pipeline's command generator.
3. Add a model group for embeddings if flow retrieval is enabled.
4. If multiple deployments are needed, add them to the same group and configure a
   routing strategy (see "Multi-deployment routing").
5. Reference the group `id` from `config.yml` pipeline components
   (see `rasa-configuring-assistant` skill).

## Providers

Rasa provides dedicated client wrappers only for certain providers. The supported sets
differ for LLM and embeddings.

**LLM** (Rasa wrappers):
- `openai`,
- `azure`,
- `self-hosted`,
- `rasa`.

**Embeddings** (Rasa wrappers):
- `openai`,
- `azure`,
- `huggingface_local`.

For any other provider (e.g. Anthropic, Cohere, Google), use the provider keys and
options from [LiteLLM's provider list](https://docs.litellm.ai/docs/providers), since
Rasa's generic clients are built on LiteLLM.

## Configuring single provider

The simplest setup — one deployment per group:

```yaml
model_groups:
  - id: my_llm
    models:
      - provider: openai                  # or azure, self-hosted, etc.
        model: <your-llm-model>

  - id: my_embeddings
    models:
      - provider: openai                  # or azure, huggingface_local, etc.
        model: <your-embedding-model>
```

To switch providers, change `provider` and add any required provider-specific settings:

```yaml
model_groups:
  - id: my_llm
    models:
      - provider: azure
        deployment: <your-deployment-name>
        api_base: https://my-azure-instance/
        api_version: "2024-02-15-preview"
        api_key: ${AZURE_API_KEY}
```

## Configuring multi-deployment routing

Place multiple deployments in the same group for load balancing, failover, or latency
optimization. Add a `router` block to control distribution.

Keep deployments in a group on the same underlying model — mixing fundamentally
different models (e.g. a small model vs a large model) leads to unpredictable
behavior. Router settings are per-group and independent — each group can use a
different strategy.

```yaml
model_groups:
  - id: azure_llm
    models:
      - provider: azure
        deployment: my-deployment-france
        api_base: https://azure-france/
        api_version: "2024-02-15-preview"
        api_key: ${AZURE_KEY_FRANCE}
      - provider: azure
        deployment: my-deployment-canada
        api_base: https://azure-canada/
        api_version: "2024-02-15-preview"
        api_key: ${AZURE_KEY_CANADA}
    router:
      routing_strategy: least-busy
```

### Routing strategies

| Strategy                | Description |
|-------------------------|-------------|
| `simple-shuffle`        | Distributes based on RPM (requests per minute) or weight |
| `least-busy`            | Routes to deployment with fewest ongoing requests |
| `latency-based-routing` | Routes to lowest-latency deployment |
| `cost-based-routing`    | Routes to lowest-cost deployment (requires Redis) |
| `usage-based-routing`   | Routes to lowest-usage deployment (requires Redis) |

### Router customization

Fine-tune failover behavior with these optional parameters:

```yaml
router:
  routing_strategy: least-busy
  cooldown_time: 10        # seconds before retrying a failed deployment
  allowed_fails: 2         # failures before marking deployment unavailable
  num_retries: 3           # retries per failed request
```

 Refer to the [LiteLLM's routing configuration documentation](https://docs.litellm.ai/docs/routing#init-params-for-the-litellmrouter)
 for more information on the configuration parameters.

### Redis for cost/usage routing

Cost- and usage-based strategies track token usage over time and require a Redis
backend:

```yaml
router:
  routing_strategy: cost-based-routing
  redis_host: localhost
  redis_port: 6379
  redis_password: ${REDIS_PASSWORD}
```

Or via URL:

```yaml
router:
  routing_strategy: usage-based-routing
  redis_url: "redis://:${REDIS_PASSWORD}@host:6379"
```

### Caching

Enable response caching to reduce load and cost. For production, back it with Redis
(in-memory caching does not persist across restarts):

```yaml
router:
  routing_strategy: simple-shuffle
  cache_responses: true
```

## Embeddings routing

The same routing configuration (strategies, Redis, caching) works for embedding model
groups — just use an embeddings provider in the `models` list.

## Self-hosted models

Use `provider: self-hosted` for vLLM and Llama.cpp, or `provider: ollama` for Ollama.
Multiple instances can be routed just like cloud deployments.

When routing is enabled for self-hosted models, `use_chat_completions_endpoint` must be
set at the **router level**, not on individual models.

```yaml
# vLLM
model_groups:
  - id: vllm_llm
    models:
      - provider: self-hosted
        model: meta-llama/Meta-Llama-3-8B
        api_base: "http://localhost:8000/v1"
      - provider: self-hosted
        model: meta-llama/Meta-Llama-3-8B
        api_base: "http://localhost:8001/v1"
    router:
      routing_strategy: least-busy
      use_chat_completions_endpoint: false   # router level, not model level

# Ollama
model_groups:
  - id: ollama_llm
    models:
      - provider: ollama
        model: llama3.1
        api_base: "http://localhost:11434"
```

## LiteLLM proxy

Route through a LiteLLM proxy server using `provider: litellm_proxy`:

```yaml
model_groups:
  - id: litellm_proxy_llm
    models:
      - provider: litellm_proxy
        model: <your-model-instance-1>
        api_base: "http://localhost:4000"
      - provider: litellm_proxy
        model: <your-model-instance-2>
        api_base: "http://localhost:4000"
    router:
      routing_strategy: least-busy
```
