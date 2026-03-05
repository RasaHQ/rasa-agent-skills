---
name: rasa-building-flows
description: >
  Builds conversation flows for Rasa CALM assistants using YAML. Use when creating or
  editing flows, designing flow architecture, adding branching logic, writing flow and
  collect step descriptions, or connecting flows with call and link steps.
license: Apache-2.0
metadata:
  author: rasa
  version: "3.x"
  docs-url: https://rasa.com/docs/reference/primitives/flows/
---

# Building Flows in Rasa

## Workflow

1. Identify the business process the user wants to implement.
2. Review existing flows, slots, responses, and actions. Reuse before creating new ones.
3. Scope the work — one file per business process, one flow per user goal
   (see "Scoping a flow").
4. Create or open the YAML file under `data/`, named after the primary flow
   (see "File organization").
5. Define the flow with a `snake_case` ID (see "Naming conventions").
6. Write the flow `description` (see "Writing descriptions").
7. Add steps: `collect` for user input, `action` for responses or invoking custom
   actions.
8. Write descriptions for `collect` steps (see "Writing descriptions").
9. Add branching with `next`/`if`/`then`/`else` where the process has decision points
   (see "Branching and conditions").
10. Extract reusable sub-tasks into child flows via `call` (see "Connecting flows").
11. Connect follow-up flows via `link` if a separate process should start after.
12. Ensure all referenced slots, responses, and actions exist in the domain
    (see "Ensure domain completeness").
13. Validate the project (see "Fixing validation errors").

## Scoping a flow

A flow represents **one business process** from the user's perspective. Use these
questions to decide whether something warrants its own flow:
1. Does a user explicitly ask for this? → yes = flow
2. Can it run independently from start to finish? → yes = flow
3. Is it a sub-task reused by multiple flows? → yes = child flow with `if: False`
4. Is it just one action at the end of another flow? → no, keep it inline

**Right-sized** flow - a single user goal with a clear start and end:

```yaml
flows:
  track_order:
    description: Lets users check the delivery status of an existing order.
    steps:
      - collect: order_id
      - action: action_fetch_order_status
      - action: utter_order_status
      # ... can also include branching, call, link steps as needed
```

**Too big** - multiple unrelated goals in one flow. Split them:

```yaml
# BAD
flows:
  shopping:
    description: Handles all shopping operations.
    steps:
      - collect: operation_type
      # ... 20 or more steps mixing order tracking, returns, payments,
      # branching, sub-flow calls — too many unrelated concerns in one place
```

**Too small** - a single step that is not a business process. Inline it:

```yaml
# BAD
flows:
  say_goodbye:
    description: Says goodbye.
    steps:
      - action: utter_goodbye
```

## File organization

Before creating new files, check the existing project layout. If the project already
uses a different convention, follow that convention instead.

By default, all flow files live under `data/`. Subdirectories are supported — Rasa
recursively scans `data/` for YAML files. Each file groups a business process with its
sub-flows:

```
data/
├── book_appointment.yml        # flow + child flows in one file
├── track_order.yml
├── transfer_money.yml
└── onboarding/                 # subdirectory for a larger domain area
    ├── register_patient.yml
    └── verify_insurance.yml
```

Name the file after the **primary flow** it contains. If `book_trip` has child flows
like `select_destination` and `choose_flights`, all three go in `data/book_trip.yml`.

Use subdirectories to group related flows by domain area when the project grows large
(e.g. `data/payments/`, `data/scheduling/`). The directory structure has no functional
impact — it's purely organizational.

## Naming conventions

This section proposes default conventions. If the user's project already
follows different conventions, match those instead.

### Flow IDs

- Use `snake_case`: `transfer_money`, `book_appointment`, `track_order`
- Start with a verb: `check_balance`, `schedule_visit` — not `flow_1` or `appointment`
- Child flows can use a prefix of the parent for clarity:
  `book_appointment_collect_patient_info`

### Flow names

The optional `name` field is a human-readable label. It has no functional impact.

```yaml
flows:
  book_appointment:
    name: "Book Appointment"
    description: Helps patients schedule a visit with their doctor.
```

## Writing descriptions

### Flow descriptions

The `description` is the **primary signal** the LLM within the Command Generator uses to
decide when to start a flow. A bad description means the flow won't trigger — or
triggers for the wrong request.

- **Be information-dense**: precisely outline the flow's purpose and scope. Avoid filler
  words. Use imperative language.
- **Use clear, standard language**: avoid unusual phrasing. Stick to universally
  understood terms.
- **Explicitly define context**: the embedding model lacks situational awareness - it
  can't read between the lines. State the domain and intent directly.
- **Clarify specialized knowledge**: if the flow references brand names or product
  names, explain what they are. The embedding model won't know.
- **Keep descriptions distinct**: if two flows sound similar, add distinguishing details
  so the LLM within the Command Generator can disambiguate.

```yaml
# GOOD — information-dense, user perspective, explicit context
book_appointment:
  description: Helps patients schedule a visit with their doctor.

track_order:
  description: Lets users check the delivery status of an existing order.

# BAD — implementation detail, vague, no context
book_appointment:
  description: Runs action_book_slot and fills the date slot.

track_order:
  description: A flow for orders.
```

### Collect step descriptions

The `description` on a `collect` step tells the LLM within the Command Generator
**what value to extract** from the user's message. Without it, the LLM within
the Command Generator only has the slot name to guess.

- Describe the **expected value**, not the question being asked
- Include **format, constraints, or valid values** when applicable
- Provide **examples** for ambiguous or structured data

```yaml
# GOOD
- collect: insurance_id
  description: >
    Insurance member ID printed on the patient's card.
    Alphanumeric, 9-12 characters (e.g. XYZ-123456789).

- collect: return_reason
  description: "Reason for the return: damaged, wrong_item, changed_mind, or other."

# BAD — no useful information / describes the question, not the value
- collect: amount
  description: the amount
- collect: email
  description: Ask the user for their email address.
```

## Slots and collect steps

By default, slots filled in `collect` or `set_slots` steps reset when the flow ends (to
`null` or to the slot's `initial_value` from the domain). To retain a slot's value after
the flow completes, list it in `persisted_slots` at the flow level. Slots set in custom
actions are persistent by default and should not be listed in `persisted_slots`.

```yaml
flows:
  return_item:
    description: Helps users return a purchased item for a refund or exchange.
    persisted_slots:
      - order_id         # kept after flow ends
      - return_reason    # kept after flow ends
    steps:
      - collect: order_id
      - collect: return_reason
      - action: action_process_return
```

A `collect` step automatically uses a response named `utter_ask_{slot_name}` to prompt
the user. Override this with the `utter` property on the collect step, or use a custom
action named `action_ask_{slot_name}` instead — but not both.

```yaml
- collect: account_type
  utter: utter_ask_secondary_account_type   # overrides default utter_ask_account_type
```

Use `rejections` on a `collect` step to validate values inline. The assistant re-asks
automatically on rejection. For complex validation, create a custom action named
`validate_{slot_name}`.

```yaml
- collect: age
  rejections:
    - if: slots.age < 1
      utter: utter_invalid_age
    - if: slots.age < 18
      utter: utter_must_be_18
```

To reset a slot mid-flow, set it to `null` in a `set_slots` step. In a custom action,
return `None`. Empty slots are not eligible for user correction.

```yaml
- set_slots:
    - amount: null
```

See the full reference for all collect step properties (`ask_before_filling`,
`force_slot_filling`, `utter`, etc.).

## Branching and conditions

Any step can branch by adding a `next` property with `if`/`then`/`else` conditions.
Conditions support operators like `and`, `or`, `not`, `<`, `>`, `=`, `!=`, `is`,
`is not`, `contains`, and `matches` (see full reference for details).

Two namespaces are available in conditions:
- `slots.` — slot values: `slots.age < 18`, `slots.plan = "premium"`
- `context.` — dialogue frame properties: `context.previous_flow_name`,
  `context.collect`, `context.canceled_name`

When `context.collect` or `context.validate` reference a slot name, wrap them in Jinja
with the `slots.` prefix: `"slots.{{context.collect}} is not null"`

When a condition leads to `next: END`, the flow completes without running further steps.
Use a `noop` step when you need a branch point without performing any action.

```yaml
- collect: membership_tier
  next:
    - if: slots.membership_tier = "premium"
      then: premium_step
    - if: slots.membership_tier = "standard"
      then: standard_step
    - else:
        - action: utter_unknown_tier
          next: END
- id: premium_step
  action: utter_premium_benefits
- id: standard_step
  noop: true
  next:
    - if: not slots.verified_email
      then:
        - call: verify_email
          next: continue_step
    - else: continue_step
- id: continue_step
  action: utter_standard_benefits
```

## Connecting flows: `call` vs `link`

Two step types connect flows together. Choose based on whether the current flow should
continue or end:

|                  | `call` | `link` |
|------------------|--------|--------|
| **When**         | Sub-task needed, then parent continues | Current process is done, different one starts |
| **Control**      | Returns to parent after child completes | Current flow ends, target starts fresh |
| **Position**     | Anywhere in the flow | Must be the last step |
| **Slots**        | Child slots accessible in parent | No slot sharing — target flow is independent |
| **Cancellation** | Cancelling child cancels parent too | N/A — current flow already ended |

Example — an **orchestrator flow** that sequences `call` steps for sub-tasks and ends
with `link` to hand off to a separate process. Child flows should not overlap in the
slots they collect, so the LLM within the Command Generator can unambiguously
route user input.

```yaml
flows:
  book_trip:
    description: Guides the user through booking a complete trip with flight and hotel.
    steps:
      - call: book_flight                  # sub-task: returns here when done
      - call: book_hotel                   # sub-task: returns here when done
      - action: utter_trip_summary
      - link: process_payment              # done — hand off to a separate process

  book_flight:
    description: Helps the user search and select a flight.
    if: False
    steps:
      # ... collect destination, dates, search, select flight

  book_hotel:
    description: Helps the user search and select a hotel at the destination.
    if: False
    steps:
      # ... search hotels, select hotel

  process_payment:
    description: Handles payment for a completed booking using a saved or new card.
    steps:
      # ... independent business process, starts fresh after link
```

## Flow guards

Guards control whether a flow can be started by the LLM within the Command Generator:

```yaml
# Only start if patient is verified
view_medical_records:
  if: slots.authenticated AND slots.identity_verified

# Never start directly — only via call or link
collect_patient_info:
  if: False
```

## Ensure domain completeness

Every element a flow references must be defined in the domain (`domain.yml` or split
domain files). After writing or editing a flow, walk through each step and verify the
items below are present. Missing entries cause validation errors or silent runtime
failures.

- Every slot used in the flow → `slots:`
  (see `rasa-managing-slots`)
- Every `collect: slot_name` → `utter_ask_{slot_name}` in `responses:`
  (see `rasa-writing-responses`)
- Every `action: utter_*` step → matching entry in `responses:`
- Every custom action / validation action → `actions:`
  (see `rasa-writing-custom-actions`)
- Rejection responses → `responses:`

## Fixing validation errors

When validation fails, preserve the user's **intent** — what the flow is supposed to
accomplish. The flow steps themselves can change, but the intended behavior must not be
lost.

Never strip down a flow's intended behavior to make validation pass. If needed, fix the
domain: slots, responses, and actions to support what the user asked for.
