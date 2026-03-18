---
name: rasa-writing-e2e-tests
description: >
  Writes end-to-end tests for Rasa CALM assistants in YAML. Use when creating or editing
  test cases, adding assertions, setting up fixtures, stubbing custom actions, or
  verifying flows, slots, and generative responses.
license: Apache-2.0
metadata:
  author: rasa
  version: "0.1.0"
  rasa_version: ">=3.12.0"
  docs-url: https://rasa.com/docs/pro/testing/evaluating-assistant
---

# Writing E2E Tests in Rasa

E2E tests validate the assistant as a whole system — from user message to bot response,
including flow execution, slot filling, custom actions, and generative responses. They
live as YAML files in the `tests/` directory and run via `rasa test e2e`.

## Workflow

1. Identify the conversation scenario to test (happy path, edge case, error path).
2. Review existing tests — extend before creating new ones.
3. Create or open a YAML file under `tests/` (see "File organization").
4. Write the test case with `user` steps and expected outcomes
   (see "Writing test cases").
5. Add assertions for detailed validation if needed (see "Assertions").
6. Set up fixtures if the test requires pre-filled slots (see "Fixtures").
7. Stub custom actions if needed to avoid external calls (see "Stubbing custom actions").
8. Run tests with `rasa test e2e` (see "Running tests").

## Key principles

- **One test case per scenario**: happy path, cancellation, validation failure, etc.
- **Start with a `user` step**: the test runner begins evaluation after
  `action_session_start`.
- **Alternate `user` and expected outcomes**: avoid consecutive `user` steps.
- **Use assertions for CALM-specific checks**: `flow_started`, `flow_completed`,
  `action_executed` give stronger guarantees than matching bot text.
- **Use `bot` or `utter` steps for simple cases**: when you only need to verify the
  response text or domain response name.
- **Use fixtures to avoid repetitive setup**: shared context like authentication goes
  in `conftest.yml`.

## File organization

Test files live under `tests/` and are automatically discovered by Rasa. Subdirectories
are supported — pass the path as a positional argument to `rasa test e2e`.

```
tests/
├── e2e_test_cases.yml           # default test file
├── conftest.yml                 # shared fixtures (visible to all tests)
├── booking/
│   ├── conftest.yml             # fixtures scoped to this directory
│   ├── test_book_trip.yml
│   └── test_cancel_booking.yml
└── payments/
    └── test_process_payment.yml
```

Each file must contain the `test_cases` key with a list of test cases. Each test case
needs a unique `test_case` name and a list of `steps`.

## Writing test cases

A test case simulates a conversation turn by turn. After each `user` step, the test
runner captures events from the tracker and compares them with expected steps. Avoid
multiple consecutive `user` steps without bot responses between them — the runner only
evaluates events from the most recent `user` step.

### Step types

| Step               | Purpose |
|--------------------|---------|
| `user`             | Simulates a user message |
| `bot`              | Checks exact text of bot response |
| `utter`            | Checks domain response name (e.g. `utter_ask_email`) |
| `slot_was_set`     | Confirms a slot was set, optionally with a value |
| `slot_was_not_set` | Confirms a slot was not set or has a different value |

The order of `bot`, `utter`, and `slot` steps after a `user` step does not matter —
they just need to occur after that user turn. Extra events beyond those specified are
ignored and do not cause failures.

```yaml
test_cases:
  - test_case: user schedules an appointment
    steps:
      - user: I need to see Dr. Smith next Tuesday
      - slot_was_set:
          - doctor_name: "Dr. Smith"
          - preferred_date                     # checks slot is set, any value
      - utter: utter_ask_appointment_time
      - user: "10am"
      - slot_was_set:
          - appointment_time: "10am"
      - utter: utter_confirm_appointment
      - user: "yes"
      - bot: "Your appointment with Dr. Smith has been confirmed."
```

## Assertions

For more detailed checks, attach `assertions` to a `user` step. When a step has
assertions, the basic step types (`bot`, `utter`, `slot_was_set`) are ignored for that
step — use the corresponding assertion types instead.

| Assertion                         | Purpose |
|-----------------------------------|---------|
| `flow_started`                    | Verify a flow began |
| `flow_completed`                  | Confirm a flow (and optionally a step) finished |
| `flow_cancelled`                  | Ensure a flow was cancelled |
| `pattern_clarification_contains`  | Check clarification suggestions returned |
| `slot_was_set`                    | Validate slot name and value |
| `slot_was_not_set`                | Confirm slot is not set or has a different value |
| `action_executed`                 | Assert an action was triggered |
| `bot_uttered`                     | Verify response text (regex), buttons, or utter name |
| `bot_did_not_utter`               | Ensure bot did not respond with specific content |
| `generative_response_is_relevant` | Check generative response relevance (threshold 0–1) |
| `generative_response_is_grounded` | Check factual accuracy against ground truth (threshold 0–1) |

```yaml
test_cases:
  - test_case: user tracks an order
    steps:
      - user: "Where is my order?"
        assertions:
          - flow_started:
              operator: "all"
              flow_ids:
                - "track_order"
          - bot_uttered:
              utter_name: utter_ask_order_id
      - user: "ORD-12345"
        assertions:
          - slot_was_set:
              - name: "order_id"
                value: "ORD-12345"
          - action_executed: "action_fetch_order_status"
          - bot_uttered:
              text_matches: "Your order .* is currently .*"  # regex
```

### Generative response assertions

Use `generative_response_is_relevant` and `generative_response_is_grounded` to test
outputs from the Contextual Response Rephraser, Enterprise Search, or custom actions.
Specify `utter_source` to target a specific component.

```yaml
- user: "What is your return policy?"
  assertions:
    - generative_response_is_relevant:
        threshold: 0.85
        utter_source: EnterpriseSearchPolicy
    - generative_response_is_grounded:
        threshold: 0.90
        utter_source: EnterpriseSearchPolicy
        ground_truth: "Items can be returned within 30 days of purchase."
```

The LLM Judge model is configured in `conftest.yml` at the project root (if not
specified, Rasa falls back to its default model):

```yaml
llm_judge:
  llm:
    provider: <your-provider>           # e.g. openai, azure, self-hosted
    model: <your-llm-model>
  embeddings:
    provider: <your-provider>
    model: <your-embedding-model>
```

## Fixtures

Fixtures pre-fill slots before a test case runs — useful for testing scenarios that
require context (e.g. logged-in user, specific membership tier). Define fixtures at the
top of a test file or in `conftest.yml` for shared access.

Fixture override order: root conftest < folder conftest < test file. Slots are set
after `action_session_start` and before the first step.

```yaml
fixtures:
  - verified_user:
      - is_authenticated: true
      - membership_tier: "premium"

test_cases:
  - test_case: premium user books a trip
    fixtures:
      - verified_user
    steps:
      - user: "I want to book a trip"
      - utter: utter_ask_destination
```

### Mocking datetime

For deterministic testing of time-dependent behavior, use the built-in
`mocked_datetime` slot in fixtures (ISO 8601 format):

```yaml
fixtures:
  - fixed_date:
      - mocked_datetime: "2025-06-15T10:00:00+00:00"

test_cases:
  - test_case: user asks about today
    fixtures:
      - fixed_date
    steps:
      - user: "What day is it?"
      - bot: "Today is Sunday, June 15, 2025."
```

## Stubbing custom actions

Stub custom actions to test without running the action server. Define
`stub_custom_actions` at the top level of the test file. When stubbing is used, all
custom actions called in the file must be stubbed.

Requires `RASA_PRO_BETA_STUB_CUSTOM_ACTION=true`.

```yaml
stub_custom_actions:
  action_fetch_order_status:                   # applies to all test cases in this file
    events:
      - event: slot
        name: order_status
        value: "shipped"
    responses:
      - text: "Your order has been shipped."

  test_express_delivery::action_fetch_order_status:   # scoped to one test case
    events:
      - event: slot
        name: order_status
        value: "out_for_delivery"
    responses:
      - text: "Your order is out for delivery."
```

## Running tests

```bash
rasa test e2e                                  # run all tests in tests/
rasa test e2e tests/booking/                   # run tests in a subdirectory
rasa test e2e --fail-fast                      # stop at first failure
rasa test e2e --coverage-report                # generate flow coverage report
```

If custom actions are not stubbed, start the action server first:

```bash
rasa run actions &
rasa test e2e
```
