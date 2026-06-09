---
name: rasa-simulating-conversations
description: >
  Use when a user wants to evaluate or test a Rasa assistant using the eval scenario framework — at any stage of the process: setting up the evaluation infrastructure for the first time, deciding which scenario types to cover for a flow, writing or generating scenario YAML files, learning about supported assertion types or how to write good success criteria, running goal-driven simulations where an LLM plays the user role against a live Rasa bot, or analyzing whether existing scenarios are comprehensive. Covers both the authoring side ("write scenarios", "generate evals", "help me write criteria") and the execution side ("simulate a conversation", "run my eval scenarios"). Not for scripted end-to-end tests, unit tests, NLU training, or general Rasa bot development.
metadata:
  author: rasa
  version: "0.1.0"
  rasa_version: ">=3.17.0"
  docs-url: https://rasa.com/docs/pro/testing/simulation-evaluation/
allowed-tools: >-
  Read Glob Grep Write Edit TodoWrite ToolSearch
  Bash(date:*) Bash(ls:*) Bash(cat:*) Bash(mkdir:*) Bash(find:*) Bash(grep:*)
  mcp__rasa-tools
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
| `generative_response_is_relevant` | `generative_response_is_relevant: {threshold: 0.7}`            | LLM-judged relevance of the generated reply ≥ threshold                     |
| `generative_response_is_grounded` | `generative_response_is_grounded: {threshold: 0.7}`            | LLM-judged grounding of the generated reply ≥ threshold                     |
| `pattern_clarification_contains`  | `pattern_clarification_contains: [transfer_money, check_balance]` | clarification offered these flows                                     |
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
  - `generative_response_is_relevant` and `pattern_clarification_contains` assertions are only relevant for single-turn knowledge-based questions.
- **Prefer structural assertions over `bot_uttered` / `bot_did_not_utter` with
  `text_matches`.** Assertions should verify *business logic*, not wording — the
  bot rephrases every run, so regexes over response text are both brittle (false
  failures on wording drift) and weak (they don't prove the underlying behavior).
  Express the intent with structural checks instead: a flow result
  (`flow_completed` / `flow_cancelled`), an action (`action_executed`, including
  `utter_*`), a slot (`slot_was_set` / `slot_was_not_set`), or ordering
  (`sequencing`). For "the bot must not reveal X", prefer
  `bot_did_not_utter: {utter_name: ...}` or assert the relevant flow never
  completed, rather than a regex over the wording.
  - Use `text_matches` **only when a specific literal token must appear verbatim
    and that token is the business logic** — e.g. a product or subscription-plan
    name, an account/reference number, a URL, or a code. Do not use it to check
    generic phrasing like "not found", "sorry", or "your bill is".
---

## Step-by-step workflow

### Step 1 — Check eval/conftest.yml

Before doing anything else, check whether `eval/conftest.yml` exists:

```
Use Glob("eval/conftest.yml") to check.
```

**If it exists** — read it and confirm the required fields are present (see below). Proceed to Step 2.

**If it does not exist** — create it with the exact content below, **including every comment line** — do not omit or paraphrase them. Then tell the user to verify or fill in the details before continuing:

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

### Step 3 - Ensure MCP server is running

Verify that you have access to the following tools: `list_project_flow_definitions`, `validate_scenario` and `evaluate_agent`.
If one of the tools is not avaiable, report which tool is missing to the user and stop:
  ```
  The following required MCP tools are not avaiable: (list unavaiable tools here)
  Please make sure that Rasa MCP tools are installed and running. Run the setup wizard from your project root: `rasa tools init`. See the following page for more details: https://rasa.com/docs/pro/installation/rasa-mcp-tools/
  ```

### Step 4 — Find or create scenario files

Scenarios live in a flat directory:

```
Use Glob("eval/scenarios/*.yml") to list available scenarios.
```

Generate scenario(s) from the flow definition:

1. Read the flow with `list_project_flow_definitions`, then open the flow file.
2. Identify the flow's own structure: the goal it serves, the information it
   collects (each slot + its description/validation), every branch/condition,
   and every decision or exit point.
3. Write each scenario to `eval/scenarios/<short_descriptive_name>.yml`, named
   after the situation (e.g. `transfer_wrong_account_corrected.yml`).

Cover the **happy path first**, then add scenarios for realistic ways a real
user might deviate. Derive the deviations from *this* flow rather than a fixed
list — each collected input, branch, and exit point is a place where a real
conversation can diverge. Use these as thinking prompts, not a checklist to fill
mechanically:

- The user gives information that is missing, invalid, or out of range — and may
  then correct it.
- The user is indirect or vague and reveals their need gradually.
- The user changes their mind, hesitates, or wants to stop partway.
- The user goes off-topic, asks something unrelated, or asks for a human.
- The user asks for something this flow (or the bot) does not handle.
- A meaningful branch/condition in the flow is exercised (take each path).

Aim for a handful of high-value scenarios per flow — enough to exercise the
happy path and the most likely real deviations — not one of every possible kind.
At a minimum, include: the happy path, one where the user supplies a bad value
(and corrects it), and one where the user changes their mind or stops partway.

**Writing `simulation_context`:** write a short, natural briefing of *who the
user is and what they want*, grounded in this flow and the plausible data they'd
have. Give the simulator a persona, a goal, and the facts it needs (e.g. which
credential to use, which detail to get wrong) — then let its behavior emerge. Do
**not** script turn-by-turn what the user should say, and vary the persona
(cooperative / impatient / uncertain, terse / chatty) across scenarios so the
set isn't formulaic. The simulator only ever plays the *user* — never describe
what the bot should do here (that belongs in `criteria` / `assertions`).

**Backend-dependent values:** some facts the simulator provides must match the
bot's connected backend / mock data for even the happy path to succeed — e.g. a
valid password or PIN, an existing order number, a known account or phone number.
Do **not** invent these blindly. If a scenario is meant to *succeed* and depends
on a value you cannot confirm is valid test data, ask the user for it before
running (e.g. *"What's a valid test order number / username / password I should
use?"*). For deviation scenarios that are *supposed* to fail (wrong password,
unknown order), inventing a clearly-invalid value is correct — there the "not
found" response is the expected behavior.

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
  `After three failed password attempts the agent stops the verification attempts and tells the customer it cannot proceed`.
  (Whether it *then offers a callback* is an optional nicety — leave it out.)
- **Mandatory phrasing** — only where wording is genuinely required
  (legal / compliance / safety disclosures), e.g.
  `The agent states the call may be recorded before collecting personal data`.
  This is the *only* case where a specific phrase is the point.

**Do NOT write criteria for (these flicker or belong elsewhere):**

- **User outcome / satisfaction / resolution** → that's `task_completion`. This
  includes *"the agent provides/answers the billing information the user asked
  for"* — receiving the answer is the user outcome, not a bot deal-breaker.
- **Offering alternatives / callbacks / escalation as a fallback** — "offers a
  callback", "offers an alternative after failure". These are UX choices about
  the user's resolution path, not non-negotiable behavior. (A *mandatory*
  compliance escalation is the rare exception — phrase it as the required
  behavior, not as "offers ...".)
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

### Step 5 — Validate generated scenario files

For each scenario file that you created use the `validate_scenario` tool to validate a scenario YAML file for syntax and
assertion correctness. If validation fails, fix the scenario YAML according to the error message and re-run the scenario
validation. You need to have a valid scenario files before proceeding to the next step and running the simulation.

### Step 6 — Run the simulation

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

### Step 7 — Report results

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

**Before reporting a failure as a bot problem, rule out invalid mock data.**
Some failures are caused by the data the simulator supplied not existing in the
bot's backend — not by a bot defect. Tell-tale signs in the transcript:

- backend lookup failures that depend on the supplied value — *"order not
  found"*, *"no account with that number"*, *"customer not found"*;
- authentication failing on a scenario that was meant to authenticate
  successfully (*"that password is incorrect"* when the run expected success).

If the failing value came from your `simulation_context` (or `initial_slots`) and
the scenario was meant to **succeed**, this is almost certainly a **test-data
problem, not a bot bug**. In that case:

1. Do **not** report it as a bot failure and do **not** edit the bot / flow.
2. Pause and ask the user for valid mock values, naming exactly what you need and
   which scenario it's for, e.g.:
   ```
   The happy-path run for "<scenario name>" failed because the order number I
   used (12345) wasn't found in the backend. What's a valid test order number /
   username / password I should use? I'll update the scenario and re-run.
   ```
3. Once the user provides them, update the affected `simulation_context` (and any
   `initial_slots` / assertions that hard-code the value), then re-run that
   scenario with the same `experiment_id`.

Only scenarios that are *designed* to fail (wrong password, unknown order) keep
invalid values — there, assert the "not found" / failure behavior instead of
asking for new data.

### Step 8 — Fix on request only

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
| Happy-path run fails with "not found" / auth errors | Mock value (order no., account, password) isn't in the backend | Test-data problem, not a bot bug — ask the user for valid test data, update `simulation_context`/`initial_slots`, re-run |

---

## Viewing a run in the Inspector

After a simulation run, the result file includes an Inspector URL under `--- INSPECTOR URL ---`.
Open it directly in the browser — the conversation is already in the shared tracker store because the server was started
with `--inspect`.

No extra tool call or file loading needed.
