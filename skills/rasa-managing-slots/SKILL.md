---
name: rasa-managing-slots
description: >
  Defines and manages slots in Rasa CALM assistant domain files. Use when creating or
  editing slot definitions, choosing slot types and mappings, configuring validation, or
  controlling how slots get filled and persist across flows.
license: Apache-2.0
metadata:
  author: rasa
  version: "3.x"
  docs-url: https://rasa.com/docs/reference/primitives/slots/
---

# Managing Slots in Rasa

## Workflow

1. Identify what information the assistant needs to remember.
2. Review existing slots in the domain — reuse before creating new ones.
3. Choose the most restrictive slot type that fits the data (see "Choosing a slot type").
4. Define the slot in the domain file with type and mapping (see "Slot mappings").
5. Set an `initial_value` if the slot needs a default.
6. Add validation if the slot requires format or range checks
   (see "Validation strategies").
7. Use the slot in flows via `collect` or `set_slots` steps.

## File organization

Slots are defined in domain YAML files, typically under `domain/` or in a single
`domain.yml`. Before creating new slots, check the existing domain layout — the user's
existing convention always takes precedence.

Domain files are commonly split by business process, so each flow's slots, responses,
and actions live together (e.g. `domain/transfer_money.yml`).

```
domain/
├── transfer_money.yml  # slots + responses + actions for one flow
├── book_appointment.yml
└── shared.yml          # slots reused across multiple flows
```

## Choosing a slot type

Pick the most restrictive type that fits the data. This prevents invalid values and
helps the LLM within the Command Generator extract correctly.

| Type          | Use when | Example |
|---------------|----------|---------|
| `text`        | Any string value | names, emails, free-text input |
| `bool`        | Binary yes/no | `is_authenticated`, `terms_accepted` |
| `categorical` | Value must come from a fixed set (auto-coerces casing) | account types, priority levels |
| `float`       | Numeric value with decimals | temperature, amounts, scores |
| `any`         | Structured data (dicts, mixed types) | API responses, shopping carts |
| `list`        | List of values (custom actions only) | item lists — cannot be filled via `collect` or `set_slots` |

```yaml
slots:
  patient_name:
    type: text

  terms_accepted:
    type: bool

  priority:
    type: categorical
    values:
      - low
      - medium
      - high

  temperature:
    type: float

  search_results:
    type: any
```

## Slot mappings

Mappings define **how** a slot gets filled. Choose based on what controls the slot
value.

A slot can combine `from_llm` with NLU-based mappings — NLU takes priority when both
extract a value. Use `allow_nlu_correction: true` on `from_llm` if the LLM within the
Command Generator should be able to correct NLU-filled values.

| Mapping       | When to use |
|---------------|-------------|
| `from_llm`    | Default for CALM (assumed if no mapping defined). The LLM within the Command Generator extracts value from user messages at any point in the conversation, not just at the `collect` step. |
| `controlled`  | Slot should only be filled by custom actions, button payloads, or `set_slots`. NLU and the LLM within the Command Generator cannot fill it. Use `run_action_every_turn` to keep the slot up to date on every turn. |
| `from_entity` | NLU pipeline extracts a specific entity. Requires `NLUCommandAdapter` in config. Use `conditions` with `active_flow` to disambiguate when multiple slots map to the same entity. |
| `from_intent` | NLU pipeline maps a predicted intent to a value. Requires `NLUCommandAdapter` in config. |

```yaml
slots:
  destination_city:               # from_llm — LLM extracts from user messages
    type: text
    mappings:
      - type: from_llm

  is_authenticated:               # controlled — only set by custom actions or set_slots
    type: bool
    mappings:
      - type: controlled

  session_token:                  # controlled with run_action_every_turn
    type: text
    mappings:
      - type: controlled
        run_action_every_turn: action_refresh_session

  sender_name:                    # from_entity — NLU extracts, scoped to a flow
    type: text
    mappings:
      - type: from_entity
        entity: person
        conditions:
          - active_flow: transfer_money

  username:                       # combined — from_llm + from_entity, LLM can correct NLU
    type: text
    mappings:
      - type: from_llm
        allow_nlu_correction: true
      - type: from_entity
        entity: username
```

## Initial values

Set a default value for slots that should not start empty. The slot resets to this value
(not `null`) when a flow ends. Also useful for optional `collect` steps with
`ask_before_filling: false` — the flow skips the question if the slot already has a
value.

```yaml
slots:
  language:
    type: categorical
    values:
      - en
      - de
      - fr
    initial_value: en

  num_retries:
    type: float
    initial_value: 0
```

## Validation strategies

Three levels of validation, from simplest to most complex:

| Validation need                       | Where to define | How |
|---------------------------------------|-----------------|-----|
| Format/range checks (regex, length)   | Domain — `validation.rejections` on the slot | Runs globally whenever the slot is set. `refill_utter` is optional (defaults to `utter_ask_{slot_name}`). |
| Business rule tied to a specific flow | Flow — `rejections` on the `collect` step | Only runs at that collect step. |
| External API or database check        | Custom action named `validate_{slot_name}` | Rasa runs it automatically when the slot is collected. |

```yaml
# Domain-level — global format check
slots:
  phone_number:
    type: text
    mappings:
      - type: from_llm
    validation:
      rejections:
        - if: not (slots.phone_number matches "^\d{10}$")
          utter: utter_invalid_phone
      refill_utter: utter_ask_phone_again
```

## Naming conventions

This section proposes default conventions. If the user's project already follows
different conventions, match those instead.

- Use `snake_case`: `patient_name`, `order_id`, `is_authenticated`
- Use descriptive nouns: name after the data, not the flow — `email` not `collect_email`
- Prefix booleans with `is_` or `has_`: `is_verified`, `has_insurance`
- Avoid special characters `(`, `)`, `=`, `,` in slot names — they break response button
  payloads
