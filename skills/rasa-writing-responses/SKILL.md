---
name: rasa-writing-responses
description: >
  Writes response templates for Rasa CALM assistants in domain YAML files. Use when
  creating or editing responses, adding variations, buttons, images, conditional or
  channel-specific content, or overriding default pattern responses.
license: Apache-2.0
metadata:
  author: rasa
  version: "3.x"
  docs-url: https://rasa.com/docs/reference/primitives/responses/
---

# Writing Responses in Rasa

## Workflow

1. Identify what the assistant needs to say and in which flow step.
2. Review existing responses in the domain — reuse before creating new ones.
3. Name the response with the `utter_` or `utter_ask_` prefix (see "Naming conventions").
4. Write the response text with slot variables where needed (see "Slot variables").
5. Add variations if the response should not sound identical every time
   (see "Response variations").
6. Add buttons, images, or custom payloads for rich content if needed.
   (see "Rich responses").
7. Add conditions if the response should change based on slot values or channel
   (see "Conditional and channel-specific variations").
8. Enable rephrasing if needed (see "Rephrasing" and the
   `rasa-rephrasing-responses` skill).
9. Reference the response in a flow as an `action: utter_*` step.

## File organization

Responses are defined under the `responses` key in domain YAML files. Before creating
new responses, check the existing domain layout — the user's existing convention always
takes precedence.

Domain files are commonly split by business process, so each flow's slots, responses,
and actions live together (e.g. `domain/transfer_money.yml`).

```
domain/
├── transfer_money.yml  # slots + responses + actions for one flow
├── book_appointment.yml
└── shared.yml          # responses reused across multiple flows
```

## Naming conventions

This section proposes default conventions. If the user's project already
follows different conventions, match those instead.

- Every response name **must** start with `utter_`:
  `utter_greet`, `utter_ask_amount`, `utter_transfer_complete`
- Use `snake_case` after the prefix
- Name after the **intent or purpose**: `utter_ask_email`, `utter_confirm_booking`
- For collect steps, name responses `utter_ask_{slot_name}` — Rasa resolves this
  automatically (e.g. `collect: account_type` → `utter_ask_account_type`). See the
  `rasa-building-flows` skill for override and custom action details.
- Always include a default variation without conditions as a fallback

## Response basics

A response is a named template under the `responses` key. Each name maps to a list of
one or more variations. Responses starting with `utter_` can be used directly as flow
actions without listing them in the `actions` section.

```yaml
responses:
  utter_greet:
    - text: "Hey! How can I help you?"
  utter_bye:
    - text: "See you later!"
```

## Slot variables

Insert slot values into responses using curly brackets. If the slot is empty or does not
exist, the variable is replaced with `None`.

Values can also be passed from a custom action via
`dispatcher.utter_message(response="utter_greet_user", user_name="Sara")`.

```yaml
responses:
  utter_greet_user:
    - text: "Hello, {user_name}! How can I assist you today?"

  utter_order_status:
    - text: "Your order {order_id} is currently {delivery_status}."
```

## Response variations

Multiple variations under the same response name make the assistant sound
less repetitive — Rasa picks one randomly at runtime. Optionally assign an `id` to each
variation so an external NLG server can identify which was selected.

```yaml
responses:
  utter_greet:
    - id: "greet_1"                              # optional, for NLG server
      text: "Hello! How can I help you?"
    - id: "greet_2"
      text: "Hi there! What can I do for you?"
    - text: "Hey! How may I assist you today?"   # id is optional
```

## Rich responses

### Buttons

Buttons give users structured choices. Each button has a `title` (displayed text) and a
`payload` (message sent when clicked). Buttons skip the pipeline and directly annotate
the user message.

In CALM, use `/SetSlots(slot_name=value)` payloads to set slots directly. Multiple slots
can be set in one payload. Slot names must not contain `(`, `)`, `=`, `,` and slot
values must not contain `,`, `(`, `)`.

```yaml
responses:
  utter_ask_card_type:
    - text: "Which card would you like to use?"
      buttons:
        - title: "Credit"
          payload: "/SetSlots(card_type=credit)"
        - title: "Debit"
          payload: "/SetSlots(card_type=debit)"
        - title: "Premium Credit"
          payload: "/SetSlots(card_type=credit, tier=premium)"  # multiple slots
```

### Images

```yaml
responses:
  utter_cheer_up:
    - text: "Here is something to cheer you up:"
      image: "https://i.imgur.com/nGF1K8f.jpg"
```

### Custom payloads

Send arbitrary JSON to the output channel via the `custom` key. Styling and rendering
are handled by the frontend or messaging channel.

```yaml
responses:
  utter_date_picker:
    - custom:
        blocks:
          - type: section
            text:
              text: "Pick a date:"
              type: mrkdwn
            accessory:
              type: datepicker
              initial_date: "2026-01-01"
```

## Conditional and channel-specific variations

Variations can be filtered by slot conditions, channel, or both. When
combined, Rasa selects in this priority order:
1. Conditional match + matching channel
2. Default (no condition) + matching channel
3. Conditional match + no channel
4. Default + no channel

### Conditional variations

Select a variation based on slot values using the `condition` key with predicate
expressions (same syntax as flow conditions). Always include a default variation without
a condition.

```yaml
responses:
  utter_greet:
    - condition: slots.prior_visits > 1            # returning user
      text: "Welcome back, {name}! How are you?"
    - condition: not slots.prior_visits             # first visit
      text: "Welcome! How can I help you today?"
    - text: "Hello! How can I assist you?"          # default fallback
```

### Channel-specific variations

Use the `channel` key to tailor responses per output channel. Rasa prefers
channel-specific variations for the active channel and falls back to variations without
a `channel` key.

```yaml
responses:
  utter_ask_game:
    - text: "Which game would you like to play on Slack?"
      channel: "slack"
    - text: "Which game would you like to play?"    # all other channels
```

## Overriding default pattern responses

Rasa has built-in default responses for patterns (e.g.
`utter_can_do_something_else`). Override them by defining a response with the
same name in your domain:

```yaml
responses:
  utter_can_do_something_else:
    - text: "Is there anything else I can assist you with?"
```

## Rephrasing

Responses can be dynamically rephrased by the Contextual Response Rephraser.
Enable it per response with `metadata: rephrase: True`, or disable with
`rephrase: False`. See the `rasa-rephrasing-responses` skill for full details.

```yaml
responses:
  utter_greet:
    - text: "Hey! How can I help you?"
      metadata:
        rephrase: True
```

## Voice-specific properties

For voice assistants, control whether users can interrupt the assistant while a response
is being spoken using `allow_interruptions`. Use `allow_interruptions: false` for
critical information (balances, disclaimers, compliance content, emergency
instructions).

```yaml
responses:
  utter_terms_and_conditions:
    - text: "Please note the following terms and conditions..."
      allow_interruptions: false     # user must hear the full message

  utter_ask_preference:
    - text: "What would you like to do today?"
      allow_interruptions: true      # default
```

## Full reference

<!-- TODO: Add references/responses-reference.md with complete syntax documentation -->