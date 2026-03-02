---
name: rasa-writing-custom-actions
description: >
  Writes custom actions in Python for Rasa CALM assistants using the Rasa SDK. Use when
  creating or editing custom action files, calling external APIs from flows, implementing
  slot validation actions, or building dynamic ask actions.
license: Apache-2.0
metadata:
  author: rasa
  version: "3.x"
  docs-url: https://rasa.com/docs/reference/integrations/action-server/actions
---

# Writing Custom Actions in Rasa

Custom actions run Python code when a flow reaches an `action` step — for example,
calling an external API, querying a database, or computing a value. They execute on an
action server that communicates with the Rasa server via HTTP or gRPC.

**Key principle**: keep business logic in flows, not in actions. Flows define *how* the
conversation proceeds (branching, conditions, collect steps). Actions do the *raw work*
(fetch data, call APIs, query databases) and return results via `SlotSet` events for
flows to use. Keep each action focused on one responsibility — `action_search_products`
searches, `action_place_order` places an order.

## Workflow

1. Identify what raw work the flow needs — API call, database query, computation.
   If the task can be handled with `set_slots` or flow logic alone, don't create an
   action.
2. Review existing actions, slots, and responses — reuse before creating new ones.
3. Create or open the Python file under `actions/` (see "File organization").
4. Name the action with a verb after `action_` (see "Naming conventions").
5. Define the action class: `name()` returns the action name, `run()` does the work
   (see "Action class structure").
6. Read slot values from `tracker.get_slot()`, call external services, handle errors,
   then return `SlotSet` events for the flow to branch on
   (see "Working with the tracker", "Error handling", and "Returning events").
7. Register the action in the domain file under `actions:`
   (see "Domain registration").
8. Validate the project.

## File organization

Before creating new files, check the existing project layout. If the project already
uses a different convention, follow that convention instead.

By default, the action server looks for actions in a file called `actions.py` or a
package directory called `actions/`. Use `--actions my_module` when running the action
server to specify a different module.

```
actions/
├── __init__.py
├── action_scheduling.py     # actions for scheduling flows
├── action_orders.py         # actions for order tracking flows
├── action_payments.py       # actions for payment flows
└── shared/
    ├── __init__.py 
    └── utils.py             # shared utilities (not action classes)
```

Group related actions by business domain. Keep helper functions (API clients, database
connectors) in separate modules so actions stay focused on orchestration.

## Naming conventions

This section proposes default conventions. If the user's project already follows
different conventions, match those instead.

- Action names: `action_` prefix, then a verb — `action_check_inventory`,
  `action_fetch_order_status`, `action_schedule_appointment` (not `action_appointment`)
- Custom ask actions: `action_ask_{slot_name}` — Rasa runs this instead of the static
  `utter_ask_` response for a `collect` step (see "Custom ask actions")
- Validation actions: `validate_{slot_name}` — Rasa runs this automatically when a slot
  is collected (see "Slot validation actions")
- Class names: `PascalCase` — `ActionScheduleAppointment`, `ValidatePhoneNumber`

## Action class structure

Every custom action subclasses `Action` from `rasa_sdk` and implements two methods:

- `name()` — returns the action name as a string. Must match the name in the domain
  and in flows.
- `run(dispatcher, tracker, domain)` — executes the action's logic. Returns a list of
  events (typically `SlotSet`).

```python
from typing import Text, Dict, Any, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

class ActionCheckAvailability(Action):
    def name(self) -> Text:
        return "action_check_availability"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        doctor_id = tracker.get_slot("doctor_id")
        preferred_date = tracker.get_slot("preferred_date")
        slots = await scheduling_api.get_available_slots(doctor_id, preferred_date)
        return [
            SlotSet("available_slots", slots),
            SlotSet("has_availability", len(slots) > 0),
        ]
```

## Working with the tracker

The `tracker` provides read access to the conversation state. In CALM assistants, the
most commonly used methods are `get_slot()` and `sender_id`:

- `tracker.get_slot("slot_name")` — get a slot value (returns `None` if unset)
- `tracker.sender_id` — unique ID of the user
- `tracker.latest_message` — dict with the last user message
- `tracker.events` — full event history

## Error handling

When an action calls external services, always handle failures. Set an error or status
slot and let the flow branch on it — don't hide error-handling logic inside the action.

```python
class ActionFetchOrderStatus(Action):
    def name(self) -> Text:
        return "action_fetch_order_status"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        order_id = tracker.get_slot("order_id")
        try:
            status = await orders_api.get_status(order_id)
            return [
                SlotSet("order_status", status),
                SlotSet("order_lookup_error", False),
            ]
        except Exception:
            return [SlotSet("order_lookup_error", True)]
```

The flow can then branch on `slots.order_lookup_error` to show an error message or
continue — keeping the decision in the flow, not the action.

## Returning events

The `run` method returns a list of events that update the conversation state. In CALM,
`SlotSet` is the primary event — set boolean or categorical slots for the flow to branch
on, rather than making decisions inside the action. All events must be imported from
`rasa_sdk.events`.

| Event                  | Purpose | Example |
|------------------------|---------|---------|
| `SlotSet(key, value)`  | Set a slot value | `SlotSet("has_availability", True)` |
| `SlotSet(key, None)`   | Clear a slot | `SlotSet("selected_slot", None)` |
| `AllSlotsReset()`      | Reset all slots to initial values | `AllSlotsReset()` |
| `FollowupAction(name)` | Force a specific action to run next | `FollowupAction("action_retry")`        |
| `ConversationPaused()` | Pause the conversation (e.g. handoff) | `ConversationPaused()` |

Return an empty list if no state changes are needed: `return []`

## Using the dispatcher

The `dispatcher` sends messages back to the user, but in most cases the flow should
handle messaging via `action: utter_*` steps instead. Defining responses in the domain
and referencing them in flows gives better validation support, variations, and
rephrasing (see the `rasa-writing-responses` skill).

Use the dispatcher primarily in `action_ask_*` actions where content is dynamic (e.g.
buttons fetched from an API). If you do use it, responses are automatically added as
`BotUttered` events — do not return them as explicit events.

```python
dispatcher.utter_message(response="utter_appointment_confirmed")     # domain response
dispatcher.utter_message(response="utter_greet", name="Sara")        # fills {name} in template
dispatcher.utter_message(text="Looking up your order...")             # inline text
dispatcher.utter_message(
    text="Choose a delivery option:",
    buttons=[                                                        # CALM: /SetSlots payload
        {"title": "Standard", "payload": "/SetSlots(delivery=standard)"},
        {"title": "Express", "payload": "/SetSlots(delivery=express)"},
    ],
)
```

## Custom ask actions

When a `collect` step needs dynamic content (e.g. buttons fetched from a database),
define an action named `action_ask_{slot_name}`. Rasa runs it instead of the static
`utter_ask_{slot_name}` response. You cannot have both for the same slot — Rasa will
raise a validation error. See the `rasa-building-flows` skill for how `collect` steps
resolve responses.

```python
class ActionAskDeliveryOption(Action):
    def name(self) -> Text:
        return "action_ask_delivery_option"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        options = await shipping_api.get_options(tracker.get_slot("zip_code"))
        buttons = [
            {"title": opt["label"], "payload": f"/SetSlots(delivery_option={opt['id']})"}
            for opt in options
        ]
        dispatcher.utter_message(text="Choose a delivery option:", buttons=buttons)
        return []
```

## Slot validation actions

In CALM assistants, implement slot validation as a regular `Action` subclass named
`validate_{slot_name}`. Rasa runs it automatically when the slot is collected. The action
reads the slot value from the tracker, validates it, and returns a `SlotSet` — either
with the accepted value or `None` to reject and re-ask.

For simple format or range checks, prefer domain-level `validation.rejections` or
flow-level `rejections` on the `collect` step instead (see the `rasa-managing-slots` and
`rasa-building-flows` skills). Use a validation action when the check requires external
calls or complex logic.

```python
class ValidatePhoneNumber(Action):
    def name(self) -> Text:
        return "validate_phone_number"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        phone = tracker.get_slot("phone_number")
        if await verification_service.is_valid_number(phone):
            return [SlotSet("phone_number", phone)]
        dispatcher.utter_message(response="utter_invalid_phone")
        return [SlotSet("phone_number", None)]        # None triggers re-ask
```

## Domain registration

Every custom action must be listed under `actions:` in the domain. Actions starting with
`utter_` are auto-registered from responses and do not need to be listed.

```yaml
actions:
  - action_check_availability
  - action_fetch_order_status
  - action_ask_delivery_option
  - validate_phone_number
```

## Full reference

<!-- TODO: Add references/actions-reference.md with complete syntax documentation -->
