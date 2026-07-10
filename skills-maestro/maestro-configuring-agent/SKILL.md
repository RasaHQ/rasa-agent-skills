---
name: maestro-configuring-agent
description: >
  Configures the four Maestro project files outside skills/: agent.yml (identity,
  persona, voice, startup), integrations.yml (LLM model groups, MCP servers, voice
  providers, channels, storage, knowledge sources), memory.yml (schema, visibility,
  access control), and responses.yml (verbatim templates). Use when setting up or
  changing any of these files.
license: Apache-2.0
engine: maestro
rasa_version: ">=3.18"
metadata:
  author: rasa
  version: "0.1.0"
  docs-url: https://github.com/RasaHQ/maestro-docs
---

# Configuring a Maestro agent

Project layout:

```
my-agent/
├── agent.yml             # identity, persona, model config
├── integrations.yml      # providers, MCP servers, channels, storage
├── tools/                # shared tools (skills use via import_tools)
└── skills/
    └── <skill>/
        ├── skill.md
        ├── tools/        # skill-local, auto-discovered
        ├── memory.yml    # optional
        └── responses.yml # optional
```

Start minimal: `agent.yml` with `id`, `language`, `persona` plus `integrations.yml`
with one model group is a complete config. Add sections only when a feature needs
them.

## agent.yml — identity and persona

```yaml agent.yml
agent:
  id: telco-support
  language: en

  persona: |
    You are Telco support — a friendly, concise customer service assistant.

  startup:
    welcome_message: Hi, how can I help?

  voice:
    enabled: true
    sample_rate: 16000
    input_mime_type: audio/webm
    output_encoding: mp3
    asr: deepgram_asr        # ids from integrations.yml voice_providers
    tts: deepgram_tts
```

- `persona` replaces what the CALM rephraser prompt did: global tone and identity.
  Keep skill-specific behavior out of it — that belongs in the skill's body.
- `startup` replaces `pattern_session_start` (welcome message + start-of-session
  hooks).
- `voice` is only needed for voice agents; the `asr`/`tts` values reference provider
  ids declared in `integrations.yml`.

## integrations.yml — providers and infrastructure

Replaces both `endpoints.yml` and `credentials.yml`. Always use `${ENV_VAR}`
interpolation for secrets — never literal keys in the file.

```yaml integrations.yml
model_groups:
  - id: primary_llm
    models:
      - provider: openai
        model: gpt-4o-2024-11-20
        api_key: ${OPENAI_API_KEY}

  - id: primary_embeddings
    models:
      - provider: openai
        model: text-embedding-3-large
        api_key: ${OPENAI_API_KEY}

mcp_servers:
  - id: crm
    url: ${CRM_MCP_URL}

voice_providers:
  asr:
    - id: deepgram_asr
      provider: deepgram
      model: nova-2
      api_key: ${DEEPGRAM_API_KEY}
  tts:
    - id: deepgram_tts
      provider: deepgram
      model: aura-2-thalia-en
      api_key: ${DEEPGRAM_API_KEY}

tracker_store:
  type: postgres
  url: ${TRACKER_URL}

event_broker:
  type: kafka
  url: ${KAFKA_URL}

channels:
  slack:
    slack_channel: ${SLACK_CHANNEL}
    slack_token: ${SLACK_TOKEN}
    slack_signing_secret: ${SLACK_SIGNING_SECRET}
```

| Section | When you need it |
|---|---|
| `model_groups` | Always — at least one LLM. Embeddings only for knowledge search. |
| `mcp_servers` | A skill imports `mcp/<server-id>:<tool-name>` |
| `voice_providers` | `agent.yml` has `voice.enabled: true` |
| `tracker_store` / `event_broker` | Production persistence/streaming; omit locally |
| `channels` | Deploying beyond the local inspector/shell |
| `knowledge_sources` | RAG / enterprise search |

Knowledge sources are vector stores accessed from tools via
`context.knowledge["<id>"].search(query)`:

```yaml
knowledge_sources:
  - id: billing_docs
    type: vector_store
    provider: pinecone
    index: billing-help-en
    embeddings: primary_embeddings
    api_key: ${PINECONE_API_KEY}
    top_k: 4
```

## memory.yml — per-skill state schema

Lives inside a skill folder. Declare entries when you need types/enums (for `if:`
markers), cross-skill visibility, or access control. Undeclared keys written by
tools via `context.memory.set()` still work for `requires:` gating.

```yaml skills/card_replace/memory.yml
memory:
  public:                      # readable by other skills; exported on completion
    replacement_reason:
      type: categorical        # categorical + enum enables if:/else: markers
      enum: [lost, stolen, damaged, not_received]
    selected_card_id:
      type: string
  private:                     # internal to this skill
    eligibility_checked:
      type: boolean
```

Types: `string`, `boolean`, `integer`, `categorical`. Skills can also declare
`deny_read` / `deny_write` lists — the runtime rejects out-of-contract memory access
from tools at call time.

Design rule: `public` is the skill's API. Another skill gating on
`authenticated: { equals: true }` depends only on that key, not on the auth skill
itself — keep public entries few and stable.

## responses.yml — verbatim text

Lives inside a skill folder. Referenced from `skill.md` frontmatter (`utter:`
triggers, `on_success:`/`on_failure:`); the framework delivers the text directly,
the LLM never rewrites it. `{memory_key}` interpolates at delivery time.

```yaml skills/card_replace/responses.yml
responses:
  utter_recording_notice:
    - text: >-
        This interaction may be recorded for quality assurance
        and training purposes.
  utter_replacement_failed:
    - text: >-
        We were unable to process your replacement. A support ticket has
        been created. Reference: {ticket_id}.
```

Use verbatim responses for wording that must be exact (legal, compliance,
brand-mandated). Everything else stays prose so the agent sounds natural.

## Don't

- Don't put secrets literally in any of these files — `${ENV_VAR}` only.
- Don't put skill behavior in `persona` or global config; behavior belongs in the
  owning skill's `skill.md`.
- Don't create `domain.yml`, `config.yml`, `endpoints.yml`, or `credentials.yml` —
  those are CALM files; Maestro replaced them with the four above.
- Don't declare every memory key — only typed/visible/controlled ones need
  `memory.yml`.
- The engine is in beta: if a section is rejected by `rasa validate`, check the
  current reference at `docs-url` (llms.txt) before assuming a bug.
