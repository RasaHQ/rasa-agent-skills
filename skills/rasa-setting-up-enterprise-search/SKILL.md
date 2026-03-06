---
name: rasa-setting-up-enterprise-search
description: >
  Adds knowledge base search to a Rasa CALM assistant using EnterpriseSearchPolicy,
  connects vector stores (Faiss, Milvus, Qdrant), and configures generative or
  extractive search modes. Use when setting up RAG, connecting a vector store,
  overriding pattern_search, or implementing a custom information retriever.
license: Apache-2.0
metadata:
  author: rasa
  version: "0.1.0"
  rasa_version: ">=3.13.0"
  docs-url: https://rasa.com/docs/pro/build/configuring-enterprise-search
---

# Setting Up Enterprise Search

Enterprise Search lets a Rasa assistant answer informational questions by
retrieving relevant documents from a knowledge base and generating (or
extracting) answers. It is powered by the `EnterpriseSearchPolicy` and
triggered via the built-in `pattern_search` pattern.

## Workflow

1. Check the existing project — does it already have `EnterpriseSearchPolicy`
   configured? If not, add `EnterpriseSearchPolicy` to `policies` in `config.yml` with
   the desired vector store type and options (see "Enterprise Search Policy").
2. Switch the command generator in `config.yml` to
   `SearchReadyLLMCommandGenerator` (see "Command generator").
3. Add vector store connection details to `endpoints.yml` if using Milvus or Qdrant
   (see "Connecting vector stores").
5. Add model groups for the LLM and embeddings used by the policy
   (see `rasa-configuring-model-groups` skill).
6. Override `pattern_search` in a flows file to trigger `action_trigger_search`
   (see "Triggering Enterprise Search").
7. Place documents in the knowledge base — `./docs` for Faiss, or ingest into your
   vector database for Milvus/Qdrant.
8. Validate and train.

## Command generator

Enterprise Search requires `SearchReadyLLMCommandGenerator` in the pipeline. This is the
search-aware variant of `CompactLLMCommandGenerator` — it produces `SearchAndReply`
commands when the LLM within the Command Generator detects an informational question.

If the project currently uses `CompactLLMCommandGenerator`, replace it.

```yaml
# config.yml
pipeline:
  - name: SearchReadyLLMCommandGenerator
    llm:
      model_group: command_generator_llm    # defined in endpoints.yml
```

## Enterprise Search Policy

Add `EnterpriseSearchPolicy` to `policies` in `config.yml`. The policy
supports two modes:
- **Generative** (default) — uses an LLM to produce a context-aware answer from
  retrieved documents. When `check_relevancy` is enabled and the answer is not relevant,
  the policy triggers `pattern_cannot_handle`.
- **Extractive** — set `use_generative_llm: false` to return a pre-authored answer
  directly with no LLM generation. Documents must be ingested in Q&A format (see example
  below). Use `vector_store.threshold` so only high-confidence matches are returned.

The embedding model used for querying **must match** the model used to embed documents
during ingestion.

```yaml
# config.yml
policies:
  - name: FlowPolicy
  - name: EnterpriseSearchPolicy
    llm:
      model_group: enterprise_search_llm           # LLM for answer generation
    embeddings:
      model_group: enterprise_search_embeddings     # must match ingestion model
    vector_store:
      type: "faiss"                                 # faiss | milvus | qdrant | custom module path
      source: "./docs"                              # Faiss only: path to .txt files
    # threshold: 0.0                                # Milvus/Qdrant only: minimum similarity (0–1)
    # use_generative_llm: true                      # false for extractive search
    citation_enabled: true                           # append source references to the answer
    check_relevancy: true                            # trigger pattern_cannot_handle if irrelevant
    max_messages_in_query: 2                         # conversation turns in search query (default: 2)
    include_date_time: true                          # current date/time in prompt (default: true)
    timezone: "UTC"                                  # IANA timezone for date/time context
```

Corresponding model groups in `endpoints.yml`:

```yaml
# endpoints.yml
model_groups:
  - id: enterprise_search_llm
    models:
      - provider: openai
        model: gpt-4.1-mini-2025-04-14

  - id: enterprise_search_embeddings
    models:
      - provider: openai
        model: text-embedding-3-large               # default ingestion model
```

Extractive search Q&A ingestion format — `page_content` holds the question
(vectorized for similarity), `metadata.answer` holds the response text:

```json
[
  {
    "page_content": "What is the return policy?",
    "metadata": {
      "title": "return_policy",
      "type": "faq",
      "answer": "Items can be returned within 30 days of purchase."
    }
  }
]
```

## Triggering Enterprise Search

By default, `pattern_search` responds with `utter_no_knowledge_base` (denying the
request). Override it to trigger document search instead.

### Automatic triggering via `pattern_search`

When the command generator detects an informational question, it pushes `pattern_search`
onto the dialogue stack. Override this pattern to call `action_trigger_search`:

```yaml
# data/pattern_search.yml (or any flows file)
flows:
  pattern_search:
    description: handle a knowledge-based question or request
    name: pattern search
    steps:
      - action: action_trigger_search
```

### Triggering from within a flow

`action_trigger_search` is a default action that can also be used as a step in any flow.
This is useful when a specific point in a business process needs to pull knowledge base
content:

```yaml
flows:
  troubleshoot_device:
    description: Guides users through troubleshooting their device.
    steps:
      - collect: device_model
      - action: action_trigger_search    # search KB for device-specific help
      - action: utter_anything_else
```

## Connecting vector stores

Rasa supports three built-in vector stores. Choose based on your environment.

### Faiss (development only)

In-memory index built from `.txt` files during `rasa train`. Not meant for production.
Use Milvus or Qdrant for production workloads.

```yaml
# config.yml
- name: EnterpriseSearchPolicy
  vector_store:
    type: "faiss"
    source: "./docs"           # directory of .txt files, indexed at train time
```

No `endpoints.yml` configuration needed — the index is stored on disk.

### Milvus

Connect to a self-hosted Milvus instance. Documents must already be ingested with the
same embedding model.

```yaml
# config.yml
- name: EnterpriseSearchPolicy
  vector_store:
    type: "milvus"
    threshold: 0.7             # minimum similarity score (0–1)
```

```yaml
# endpoints.yml
vector_store:
  type: milvus
  host: localhost              # required
  port: 19530                  # required
  collection: rasa             # required
  # user: ""
  # password: ""
```

### Qdrant

Connect to a self-hosted or Qdrant Cloud instance.

Adjust `content_payload_key` and `metadata_payload_key` to match how documents were
ingested into Qdrant.


```yaml
# config.yml
- name: EnterpriseSearchPolicy
  vector_store:
    type: "qdrant"
    threshold: 0.5
```

```yaml
# endpoints.yml
vector_store:
  type: qdrant
  collection: rasa                       # required
  host: 0.0.0.0
  port: 6333
  content_payload_key: page_content      # key for document text during ingestion
  metadata_payload_key: metadata         # key for document metadata during ingestion
  # api_key: ${QDRANT_API_KEY}          # for Qdrant Cloud
  # prefer_grpc: false
  # grpc_port: 6334
```

## Prompt customization

Override the default prompt with a Jinja2 template file. Available variables:
- `docs`,
- `slots`,
- `current_conversation`,
- `current_datetime`.

```yaml
# config.yml
- name: EnterpriseSearchPolicy
  prompt_template: prompts/enterprise-search-template.jinja2
```

See the Rasa docs on
[Generative Search prompts](https://rasa.com/docs/reference/config/policies/generative-search#prompt)
for the default template and all available variables.

## Custom information retrievers

For proprietary search engines, slot-based filtering, re-ranking, or unsupported vector
stores, implement a custom retriever class.

Subclass `rasa.core.information_retrieval.InformationRetrieval` and implement `connect`
and `search`:

```python
from rasa.utils.endpoints import EndpointConfig
from rasa.core.information_retrieval import SearchResultList, InformationRetrieval

class MyRetriever(InformationRetrieval):
    def connect(self, config: EndpointConfig) -> None:
        # config.kwargs contains keys from endpoints.yml vector_store block
        pass

    async def search(
        self, query: str, tracker_state: dict, threshold: float = 0.0
    ) -> SearchResultList:
        # query: user message; tracker_state: full conversation state
        # self.embeddings: langchain Embeddings object from Rasa config
        pass
```

Reference the class in `config.yml`:

```yaml
- name: EnterpriseSearchPolicy
  vector_store:
    type: "addons.custom_retrieval.MyRetriever"
```

Connection parameters in `endpoints.yml` are passed to `connect` via `config.kwargs`:

```yaml
# endpoints.yml
vector_store:
  api_key: ${SEARCH_API_KEY}
  collection: my_collection
```
