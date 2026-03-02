---
name: rasa-rephrasing-responses
description: >
  Enables and configures LLM-powered Contextual Response Rephraser in Rasa CALM. Covers
  endpoints.yml setup, per-response metadata, and prompt customization. Use when setting
  up or tuning the Contextual Response Rephraser.
license: Apache-2.0
metadata:
  author: rasa
  version: "3.x"
  docs-url: https://rasa.com/docs/reference/primitives/contextual-response-rephraser/
---

# Rephrasing Responses in Rasa

The Contextual Response Rephraser uses an LLM to dynamically rewrite templated
responses, making them sound more natural and context-aware while preserving the
original meaning. It reads conversation history and user input to ensure rephrasings fit
the context.

## Workflow

1. Enable the rephraser in `endpoints.yml` (see "Endpoints configuration").
2. Decide the rephrasing scope — per-response or all responses
   (see "Rephrasing scope").
3. Add `metadata: rephrase: True/False` on individual responses as needed
   (see "Domain-side metadata").
4. Optionally customize the prompt globally or per response
   (see "Prompt customization").

## Endpoints configuration

Enable the rephraser by adding `nlg: type: rephrase` to `endpoints.yml`.

Configure the LLM model and temperature. Lower temperature (default 0.3) produces more
predictable rephrasings; higher temperature produces more variable output but risks
altering meaning.

```yaml
nlg:
  type: rephrase
  llm:
    model_group: gpt-4o-2024-11-20-openai-model  # optional, defaults to gpt-4o-2024-11-20

model_groups:
  - id: gpt-4o-2024-11-20-openai-model
    models:
      - provider: openai
        model: gpt-4o-2024-11-20
        temperature: 0.3              # 0.0–2.0, default 0.3
```

### Conversation history

Two modes for how conversation history is included in the rephrasing
prompt.

**Summary mode** (default) — summarizes history using an additional LLM call. No extra
config needed.

**Transcript mode** — keeps the last *n* turns as-is. Set `summarize_history: False` and
optionally adjust `max_historical_turns` (default 5).

```yaml
nlg:
  type: rephrase
  summarize_history: False
  max_historical_turns: 5
```

## Rephrasing scope

### Specific responses only (default)

No `endpoints.yml` change needed. Add `metadata: rephrase: True` on each response you
want rephrased.

```yaml
responses:
  utter_greet:
    - text: "Hey! How can I help you?"
      metadata:
        rephrase: True
```

### All responses

Set `rephrase_all: true` in `endpoints.yml`. Every response is rephrased without needing
per-response metadata.

```yaml
nlg:
  type: rephrase
  rephrase_all: true
```

### All except specific ones

Set `rephrase_all: true` in `endpoints.yml`, then opt out individual responses with
`metadata: rephrase: False`.

```yaml
responses:
  utter_legal_disclaimer:
    - text: "By proceeding you agree to our terms and conditions."
      metadata:
        rephrase: False
```

## Prompt customization

Reference a custom Jinja2 template globally in `endpoints.yml`, or override per response
via `rephrase_prompt` in metadata.

Available variables: `{{history}}`, `{{current_input}}`, `{{suggested_response}}`.

```yaml
# Global prompt — endpoints.yml
nlg:
  type: rephrase
  prompt: prompts/response-rephraser-template.jinja2
```

```yaml
# Per-response prompt — domain.yml
responses:
  utter_greet:
    - text: "Hey! How can I help you?"
      metadata:
        rephrase: True
        rephrase_prompt: |
          Rephrase the suggested response in a friendly, casual tone.
          Stay close to the original meaning.
          Context: {{history}}
          {{current_input}}
          Suggested: {{suggested_response}}
          Rephrased:
```

## Full reference

<!-- TODO: Add references/slots-reference.md with complete syntax documentation -->