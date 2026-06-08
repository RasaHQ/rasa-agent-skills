---
name: rasa-simulating-conversations
description: >
  Use when a user wants to evaluate or test a Rasa assistant using the eval scenario framework — at any stage of the process: setting up the evaluation infrastructure for the first time, deciding which scenario types to cover for a flow, writing or generating scenario YAML files, learning about supported assertion types or how to write good success criteria, running goal-driven simulations where an LLM plays the user role against a live Rasa bot, or analyzing whether existing scenarios are comprehensive. Covers both the authoring side ("write scenarios", "generate evals", "help me write criteria") and the execution side ("simulate a conversation", "run my eval scenarios"). Not for scripted end-to-end tests, unit tests, NLU training, or general Rasa bot development.
---

# Goal-Driven Simulation for Rasa

Simulate realistic user conversations against a live Rasa assistant to catch
flow failures, missing slot handling, and poor bot responses — before shipping.

---

## How this works

1. You write (or generate) a **scenario YAML** in `eval/scenarios/`
2. This skill calls the `evaluate_agent` MCP tool
3. The tool uses an LLM to play the user role, driving the conversation via the REST API
4. After each run it checks **assertions** (deterministic) and **success criteria** (LLM judge)
5. Results land in `eval/results/<timestamp>/<scenario-name>/run_N.txt`

---

## Scenario YAML format

Currently only the text-based simulation is supported.

```yaml
scenario:
  name: User successfully completes <flow name>

  simulation_context: >
    <Prose block combining persona, goal, and any conversation guidance.
    Write as a briefing to the simulator — e.g. "You are a cooperative user who wants
    to transfer money. You have already authenticated. Provide details when asked.">

  setup:
    initial_slots:                  # injected before conversation starts
      authenticated: true           # set any slots that should be pre-filled

  goals:
    criteria:                       # evaluated by LLM judge
      - Agent collects all required information without confusion
      - Agent confirms the task was completed successfully
      - Conversation ends naturally
    assertions:                       # deterministic checks against the tracker
      - flow_started:
          flow_ids: [<flow_id>]       # one or more flow ids
          operator: any               # any | all
      - flow_completed:
          flow_id: <flow_id>          # singular; map; optional flow_step_id
          flow_step_id: <step_id>     # optional
      - flow_cancelled:
          flow_id: <flow_id>
      - action_executed: <action_name>
      - slot_was_set:
          - name: <slot_name>         # set to any non-null value
          - name: <slot_name>
            value: "<expected_value>" # set to an exact value
      - slot_was_not_set:
          - name: <slot_name>
      - bot_uttered:
          utter_name: <utter_response_id>   # any of utter_name / text_matches / buttons
          text_matches: "regex pattern"
      - bot_did_not_utter:
          text_matches: "I don't know"
      - sequencing:                    # ordered: each step matches an event strictly after the previous step's match
          - flow_started: transfer_money
          - slot_was_set: recipient    # slot name only (string); no value match
          - action_executed: action_submit_transfer
          - flow_completed: <flow_id>  # NOTE: plain string inside sequencing
                                       # also available as steps: flow_cancelled, flow_interrupted
```

### Supported assertion types
Every assertion is a single-key item. These are the ONLY supported types
(validated by `validate_scenario`); anything else fails schema validation.
| Type                              | Example                                                          | What it checks                                                              |
|-----------------------------------|-----------------------------------------------------------------|----------------------------------------------------------------------------|
| `flow_started`                    | `flow_started: {flow_ids: [transfer_money], operator: any}`     | one/all of these flows started                                             |
| `flow_completed`                  | `flow_completed: {flow_id: transfer_money}`                     | flow completed (optionally at `flow_step_id`)                               |
| `flow_cancelled`                  | `flow_cancelled: {flow_id: transfer_money}`                     | flow was cancelled                                                          |
| `action_executed`                 | `action_executed: action_submit_transfer`                      | this action or `utter_*` ran                                              |
| `slot_was_set`                    | `slot_was_set: [{name: recipient, value: "John"}]`             | slot set (to `value` if given) at any point — checked over event history    |
| `slot_was_not_set`                | `slot_was_not_set: [{name: recipient}]`                        | slot was never set (to `value` if given)                                    |
| `bot_uttered`                     | `bot_uttered: {text_matches: "balance"}`                       | bot sent a response matching `utter_name` / `text_matches` (regex) / `buttons` |
| `bot_did_not_utter`               | `bot_did_not_utter: {text_matches: "I don't know"}`            | bot did not send such a response                                            |
| `sequencing`                      | see example above                                               | the listed steps occurred in order (values are plain strings)              |

Notes:
- `flow_started` uses **plural `flow_ids` + `operator`**; `flow_completed` /
  `flow_cancelled` use **singular `flow_id`** in a map. The terse
  `flow_started: <flow_id>` string form still works but is **deprecated**.
- `sequencing` supports exactly these six step types, each a single-key item
  with a **plain string** value: `action_executed`, `slot_was_set`,
  `flow_started`, `flow_completed`, `flow_cancelled`, `flow_interrupted`.
  - Inside `sequencing` the value is always a bare string — even
    `flow_completed`/`flow_cancelled` (top-level these need a `{flow_id: ...}`
    map), and `slot_was_set` (top-level this needs a `[{name, value}]` list;
    here it is just the slot name and does not check the value).
  - `flow_interrupted` is available **only** inside `sequencing`.
  - It checks **order only** (each step after the previous, not necessarily
    adjacent), not slot/response values.

---

## Step-by-step workflow

### Step 1 — Check eval/conftest.yml

Before doing anything else, check whether `eval/conftest.yml` exists:

```
Use Glob("eval/conftest.yml") to check.
```

**If it exists** — read it and confirm the required fields are present (see below). Proceed to Step 2.

**If it does not exist** — create it with the exact content below, **including every comment line** — do not omit or
paraphrase them. Then tell the user to fill in the details before continuing:

```yaml
# eval/conftest.yml — simulation configuration

# LLM used to drive the user simulator (generates user turns)
simulation:
  llm:
    provider: openai       # openai | anthropic | azure | ...
    model: gpt-5.1
    timeout: 30
    reasoning_effort: "none"
    cache:
      no-cache: true

# LLM used to evaluate success criteria (LLM judge)
evaluation:
  llm:
    provider: openai
    model: gpt-5.1
    timeout: 30
    reasoning_effort: "none"
    cache:
      no-cache: true
  # Prompt overrides — paths are relative to the project root.
  # Use these to customise how the judge scores conversations.
  # prompt_template: prompt_templates/judge.jinja2              # overrides text/criteria judge (variables: simulation_context, criteria_text, transcript)

```

Stop and tell the user:

```
eval/conftest.yml has been created. Fill in the provider and model details,
then say "continue" and I'll pick up from here.
```

Do not proceed until the user confirms.

### Step 2 — Ensure the bot is trained and running

Before simulating, verify the assistant is live:

```
Use talk_to_assistant with message ["hello"] to verify the bot responds.
If it fails, ask the user to run:
  rasa run --enable-api --inspect --cors "*" --credentials credentials.yml
```

The `--inspect` flag loads the Inspector in the same process, so a single server is all that's needed — no separate
`rasa inspect` command.

**After retraining:** always check `agent_reloaded` in the `train_rasa_assistant` response.

- If `agent_reloaded: true` — the server picked up the new model, proceed to simulate.
- If `agent_reloaded: false` — the server is not running. Do NOT attempt workarounds (e.g. SlotSet in custom actions).
  Tell the user:
  ```
  The model was trained but the server is not running. Start it with:
    rasa run --enable-api --inspect --cors "*"
  Then say "re-run the simulation" and I'll continue from here.
  ```
  Stop and wait — do not re-run the simulation until the user confirms the server is up.

### Step 3 — Find or create scenario files

Scenarios live in a flat directory:

```
Use Glob("eval/scenarios/*.yml") to list available scenarios.
```

Generate scenario(s) from flow definition:

1. Read the flow definition with `list_project_flow_definitions` and then read the file
2. Extract: flow name, slots being collected (name + description), branching conditions
3. Write scenario YAML to `eval/scenarios/<scenario_type>.yml`

For each flow, generate scenario types covering the happy path and supported conversation repair patterns:

| Type              | Persona               | Goal variation                                  |
|-------------------|-----------------------|-------------------------------------------------|
| `happy_path`      | Cooperative, friendly | Provides all info directly when asked           |
| `correction`      | Careful user          | Provides wrong value, then corrects it          |
| `vague_user`      | Indirect user         | Starts vague, reveals intent gradually          |
| `abandon_restart` | Impatient user        | Abandons mid-flow, restarts with different goal |
| `chitchat`        | Off-topic user        | Sends chitchat mid-flow                         |
| `clarification`   | Ambiguous user        | Intent matches multiple flows                   |
| `cancel_flow`     | Changed mind          | Cancels the flow mid-way                        |
| `human_handoff`   | Frustrated user       | Requests a human agent                          |
| `skip_question`   | Evasive user          | Tries to skip a required slot                   |
| `cannot_handle`   | Out-of-scope user     | Sends something the bot can't handle            |

### Writing success criteria — bot-side deal-breakers

**Division of labor — keep these strictly separate:**

- **`criteria`** capture **bot-side performance**: the *non-negotiables* of an
  acceptable conversation. Rule of thumb: **if a criterion fails, a fix is
  definitely required.** They are judged independently of whether the user
  ultimately got their answer.
- **`task_completion`** is a separate **binary** metric (`true`/`false`, scored
  automatically by the metrics judge — you do **not** author it here). It
  captures the **actual user outcome**: did the user get what they came for?
- Do not restate the outcome as a criterion. "The user got their answer / was
  satisfied / the issue was resolved" is `task_completion`, **not** a criterion.

**Good criteria (deal-breakers) target one of these:**

- **Step ordering / preconditions** — e.g.
  `The agent verifies the customer's identity before disclosing any billing details`.
- **Correct behind-the-scenes tool calls** — e.g.
  `The agent calls the billing-lookup tool before quoting any figures`
  (assert it deterministically when you can — see below).
- **Flow adherence** — the required handling of a path, e.g.
  `After three failed password attempts the agent locks the account and offers a callback`.
- **Mandatory phrasing** — only where wording is genuinely required
  (legal / compliance / safety disclosures), e.g.
  `The agent states the call may be recorded before collecting personal data`.
  This is the *only* case where a specific phrase is the point.

**Do NOT write criteria for (these flicker or belong elsewhere):**

- **User outcome / satisfaction / resolution** → that's `task_completion`.
- **Optional niceties** — closing pleasantries, "offers further help", upsells.
  If the bot can skip it and still be correct, it is not a criterion.
- **Exact wording that isn't mandated** — the bot rephrases every run, so a
  literal-phrase criterion flips when wording drifts. Describe the behavior,
  not the sentence (except mandatory phrasing above).
- **Conversation-closure gates** — "ends naturally", "conversation ends": where
  the simulated user stops varies run-to-run, so these flicker.

**Two more rules:**

- **One non-negotiable per criterion.** Compound criteria ("calls the tool
  **and** explains clearly") fail ambiguously — split them.
- **Put anything deterministic in `assertions`, not `criteria`.** A tool call, a
  slot set, a completed flow, step ordering — assert these against the tracker;
  assertions don't flicker. Reserve `criteria` for non-negotiable behavior that
  still needs an LLM to judge (e.g. "explained *why* it could not proceed").

> Rule of thumb: every criterion must be a **deal-breaker** — if it fails, the
> bot needs fixing. If a criterion could fail while the bot did everything right
> (wording drift, where the conversation stopped, an optional nicety), or if it
> is really about whether the *user* succeeded, it does not belong in
> `criteria`.

### Step 4 — Validate generated scenario files

For each scenario file that you created use the `validate_scenario` tool to validate a scenario YAML file for syntax and
assertion correctness. If validation fails, fix the scenario YAML according to the error message and re-run the scenario
validation. You need to have a valid scenario files before proceeding to the next step and running the simulation.

### Step 4 — Run the simulation

Before the first call, generate a shared experiment ID by running this Bash command so all scenarios from this session land in the same results folder:

```bash
date +%Y-%m-%d_%H-%M-%S
```
Use the output as the `experiment_id` for all `evaluate_agent` calls. If you encounter a permission error, use the currentDate from the system context.

Run scenarios sequentially using `evaluate_agent`, passing the same `experiment_id`
to every call.

```
evaluate_agent(
  scenario_path="eval/scenarios/<scenario_type>.yml",
  experiment_id=experiment_id
)
```

### Step 5 — Report results

After the tool returns, summarize clearly:

**If all runs passed:**

```
3/3 runs passed for "<scenario name>"
Naturalness: 8.2/10 — responses were warm and clear.
Result file: eval/results/<timestamp>/<scenario-name>/run_N.txt
```

**If some runs failed:**

```
1/3 runs passed for "<scenario name>"

Run 2 failed:
  ✗ slot_filled: <slot_name>
       slot '<slot_name>' = None

Run 3 failed:
  ✗ success_criteria: "Agent confirms the task was completed successfully"
       Bot did not send a confirmation message before ending the conversation.

Naturalness: 6.1/10 — functional but robotic tone.
Result file: eval/results/<timestamp>/<scenario-name>/run_N.txt
```

Do not attempt to fix failures unless the user asks. Report what failed and where, then wait.

### Step 6 — Fix on request only

If the user asks to fix a failure:

1. Identify the root cause: wrong response template? missing slot handling? flow routing issue?
2. Point to the specific file and line
3. Propose the fix
4. After the fix, re-run the failing scenario to confirm it passes

---

## Config reference

| Field                            | Required   | Default                      |
|----------------------------------|------------|------------------------------|
| `simulation.llm`                 | Yes        | —                            |
| `evaluation.llm`                 | Yes        | —                            |
| WebSocket URL                    | No         | Derived from Rasa server URL |
| Sample rate, turn timing         | No         | Built-in defaults            |

---

## Common issues

| Symptom                                    | Likely cause                                 | Fix                                                                                |
|--------------------------------------------|----------------------------------------------|------------------------------------------------------------------------------------|
| `Scenario file not found`                  | Wrong path or missing file                   | Check with Glob using the right pattern (see Step 2), create file if needed        |
| Bot returns empty responses (text)         | Rasa not running or not trained              | Ask user to run `rasa run --enable-api --inspect --credentials credentials.yml`    |
| `response_contains_any` fails unexpectedly | Bot uses different phrasing                  | Read the transcript in the result file, update assertions or flow response         |
| Simulation hits max turns (20)             | Bot stuck in loop or user simulator confused | Read transcript, check if bot keeps re-asking same question                        |
| All criteria pass but assertions fail      | Slot not being filled                        | Check tracker slots in result file, verify slot mappings in domain                 |

---

## Viewing a run in the Inspector

After a simulation run, the result file includes an Inspector URL under `--- INSPECTOR URL ---`.
Open it directly in the browser — the conversation is already in the shared tracker store because the server was started
with `--inspect`.

No extra tool call or file loading needed.
