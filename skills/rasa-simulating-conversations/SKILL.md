---
name: rasa-simulating-conversations
description: >
  Use when a user wants to evaluate or test a Rasa assistant using the eval scenario framework — at any stage of the process: setting up the evaluation infrastructure for the first time, deciding which scenario types to cover for a flow, writing or generating scenario YAML files, learning about supported assertion types or how to write good success criteria, running goal-driven simulations where an LLM plays the user role against a live Rasa bot, or analyzing whether existing scenarios are comprehensive. Covers both the authoring side ("write scenarios", "generate evals", "help me write criteria") and the execution side ("simulate a conversation", "run my eval scenarios"). Not for scripted end-to-end tests, unit tests, NLU training, or general Rasa bot development.
license: Apache-2.0
metadata:
  author: rasa
  version: "0.2.0"
  rasa_version: ">=3.21.0"
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


| Type                              | Example                                                           | What it checks                                                                 |
| --------------------------------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `flow_started`                    | `flow_started: {flow_ids: [transfer_money], operator: any}`       | one/all of these flows started                                                 |
| `flow_completed`                  | `flow_completed: {flow_id: transfer_money}`                       | flow completed (optionally at `flow_step_id`)                                  |
| `flow_cancelled`                  | `flow_cancelled: {flow_id: transfer_money}`                       | flow was cancelled                                                             |
| `action_executed`                 | `action_executed: action_submit_transfer`                         | this action or `utter_*` ran                                                   |
| `slot_was_set`                    | `slot_was_set: [{name: recipient, value: "John"}]`                | slot set (to `value` if given) at any point — checked over event history       |
| `slot_was_not_set`                | `slot_was_not_set: [{name: recipient}]`                           | slot was never set (to `value` if given)                                       |
| `bot_uttered`                     | `bot_uttered: {text_matches: "balance"}`                          | bot sent a response matching `utter_name` / `text_matches` (regex) / `buttons` |
| `bot_did_not_utter`               | `bot_did_not_utter: {text_matches: "I don't know"}`               | bot did not send such a response                                               |
| `generative_response_is_relevant` | `generative_response_is_relevant: {threshold: 0.7}`               | LLM-judged relevance of the generated reply ≥ threshold                        |
| `generative_response_is_grounded` | `generative_response_is_grounded: {threshold: 0.7}`               | LLM-judged grounding of the generated reply ≥ threshold                        |
| `pattern_clarification_contains`  | `pattern_clarification_contains: [transfer_money, check_balance]` | clarification offered these flows                                              |
| `sequencing`                      | see example above                                                 | the listed steps occurred in order (values are plain strings)                  |


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
  - `generative_response_is_relevant` assertions are only relevant for single-turn knowledge-based questions.
  - `pattern_clarification_contains` scans the full event list for clarification offers and works in multi-turn scenarios too.
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
  # Prompt template override — path is relative to the project root.
  # simulated_user_prompt: prompt_templates/my_simulated_user_prompt.jinja2    # (variable: simulation_context)

# LLM used to evaluate success criteria and quality metrics (LLM judge)
evaluation:
  llm:
    provider: openai
    model: gpt-5.1
    timeout: 30
    reasoning_effort: "none"
    cache:
      no-cache: true
  # Prompt templates overrides — paths are relative to the project root.
  # Use these to customise how the judge scores conversations.
  # criteria_judge_prompt: prompt_templates/my_criteria_judge_prompt.jinja2    # (variables: criteria_text, transcript, event_ledger)
  # metrics_judge_prompt: prompt_templates/metrics_judge.jinja2      # (variable: transcript)

```

Stop and tell the user:

```
eval/conftest.yml has been created. Fill in the provider and model details,
then say "continue" and I'll pick up from here.
```

Do not proceed until the user confirms.

### Step 2 — Ensure the bot is trained and Rasa server is running

Before running simulation, verify `credentials.yml` and that the assistant is live.

**Check `credentials.yml` first.** Read the file and confirm it contains both:

- `rest:` — enables the REST input channel used by simulation and `talk_to_assistant`
- `inspector:` — required when starting the server with `--inspect` (Inspector URLs in run reports)

If either block is missing, tell the user which one(s) are absent and that they need to add them and restart the Rasa server — do **not** edit `credentials.yml` yourself unless the user explicitly asks you to. Stop and wait for confirmation before continuing.

Then verify the bot responds:

```
Use talk_to_assistant with message ["hello"] to verify the bot responds.
```

**If the endpoint is not reachable** (connection refused, timeout, or similar) — the server is probably not running. Tell the user to start it:

```
The Rasa server doesn't appear to be running. Start it with:
  rasa run --inspect --credentials credentials.yml
Then say "continue" and I'll pick up from here.
```

Stop and wait — do not proceed until the user confirms the server is up.

**If the call returns 404** — even with `rest:` present, the REST webhook may not be active yet (server started without `--credentials`, or not restarted after editing `credentials.yml`). Confirm `rest:` is in `credentials.yml`, then ask the user to restart with `--credentials credentials.yml` if needed.

The `--inspect` flag loads the Inspector in the same process, so a single server is all that's needed — no separate
`rasa inspect` command.

**After retraining:** if the user asked you to retrain and you called `train_rasa_assistant`, always check
`agent_reloaded` in its response. (After a fix in Step 8 the user retrains and restarts themselves — you do
not retrain on your own.)

- If `agent_reloaded: true` — the server picked up the new model, proceed to simulate.
- If `agent_reloaded: false` — **the running server is still serving the old model.** This does *not* on its
  own mean the server is down. Hot-reload only works when the bot is served by the Rasa builder service;
  with a standalone `rasa run`, there is no reload endpoint to call, so a newly trained model is picked up
  only on restart. Do NOT attempt workarounds (e.g. SlotSet in custom actions) and do not simulate against
  the old model. Tell the user:
  ```
  The model trained, but the running server is still on the old model. Restart it with:
    rasa run --inspect --credentials credentials.yml
  Then say "re-run the simulation" and I'll continue from here.
  ```
  Stop and wait — do not re-run the simulation until the user confirms the server is back up.
  If `talk_to_assistant` is unreachable too, the server really is down; the same restart covers both cases.

### Step 3 - Ensure MCP server is running

Verify that you have access to the following tools: `list_project_flow_definitions`, `validate_scenario` and `evaluate_agent`.
If one of the tools is not available, report which tool is missing to the user and stop:
  ```
  The following required MCP tools are not available: (list unavailable tools here)
  Please make sure that Rasa MCP tools are installed and running. Run the setup wizard from your project root: `rasa tools init`. See the following page for more details: https://rasa.com/docs/pro/installation/rasa-mcp-tools/
  Then restart your agentic IDE (e.g. Cursor or Claude Code) so it picks up the new MCP configuration, and say "continue" when you're ready.
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

**Before writing `simulation_context`:** read `config.yml` and check whether it
defines a `language` property. If it does, that value is the bot's main
language — add **one short instruction** to every `simulation_context`, e.g.
*"Speak in German."* or *"Speak in Spanish."*, so the user simulator knows which
language to use for its **messages**. Without that instruction, the simulator
defaults to English even when the bot expects another language.

Write the rest of `simulation_context` in **English by default** — persona, goal,
and test data stay in English. Do **not** translate the whole briefing into the
bot language; only the simulator's spoken turns should follow the *"Speak in …"*
instruction. Do **not** use `additional_languages` from `config.yml` unless the
user explicitly asks for that. Only write `simulation_context` itself in another
language if the user explicitly requests it.

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
on a value you cannot confirm is valid test data:
1. **First check the existing scenarios** in `eval/scenarios/*.yml` — a working
   happy-path scenario usually already embeds valid test data in its
   `simulation_context` or `initial_slots` (e.g. a phone number + password that
   authenticate). Reuse those known-good values instead of guessing.
2. Only if no existing scenario provides them, **ask the user** before running
   (e.g. *"What's a valid test order number / username / password I should
   use?"*).

For deviation scenarios that are *supposed* to fail (wrong password, unknown
order), inventing a clearly-invalid value is correct — there the "not found"
response is the expected behavior.

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
- **Required system behavior / result production** — that the bot actually
  *performed* the action, framed as what the **bot did** (the judge can verify
  this against the runtime event ledger of tool calls / flows / actions), e.g.
  `The agent retrieves the account data via its tools and presents the breakdown
  it returned`. Frame it as the bot's action, **not** as what the user got —
  *"the agent retrieves and presents X"* (keep) vs *"the user was able to see X"*
  (that's the outcome — exclude; see below).
- **Flow adherence** — the required handling of a path, e.g.
  `After three failed password attempts the agent stops the verification attempts and tells the customer it cannot proceed`.
  (Whether it *then offers a callback* is an optional nicety — leave it out.)
- **Mandatory phrasing** — only where wording is genuinely required
  (legal / compliance / safety disclosures), e.g.
  `The agent states the call may be recorded before collecting personal data`.
  This is the *only* case where a specific phrase is the point.

**Do NOT write criteria for (these flicker or belong elsewhere):**

- **User outcome / satisfaction / resolution** → that's `task_completion`. The
  test is *whose* end state the criterion is about. If it is about the **user** —
  *"the user got their answer / was able to view X / was satisfied / the issue
  was resolved"* — exclude it: it is scored from the transcript by the separate
  (non-gating) `task_completion` metric and can fail for reasons outside the
  bot's control (user leaves, empty backend). **Reframing from the bot's side
  keeps it**, though: *"the agent retrieved X and presented it"* is a
  system-behavior criterion the judge checks against the event ledger — write
  that instead of *"the user received X"*.
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

**Before you keep a criterion, run this self-check.** Answer each — any "yes"
before the last means rewrite it as an assertion, move it to the right place, or
drop it:

1. *Could this fail even though the bot did everything correctly?* (wording
   varied, the user stopped early, a step the bot may legitimately skip) → drop.
2. *Is it about the **user's** end state — what they received, felt, or whether
   they were satisfied / resolved?* → that's `task_completion`, not a criterion →
   drop. (But if the point is really a **bot action**, reframe it from the bot's
   side — *"the agent retrieved and presented X"* instead of *"the user got X"* —
   and keep it.)
3. *Is it an offer of help, an alternative, an escalation, or a fallback?* →
   drop, unless it is a **mandated** step; then phrase it as the required
   behavior under a trigger ("when `<condition>`, the agent `<does X>`"), never
   as "offers …".
4. *Could a machine check it from the tracker* (a tool call, a slot value, a
   flow that started/completed, an ordering)? → move it to `assertions`.
5. *Does it name a non-negotiable behavior that genuinely needs a human-like
   judgment of the bot's conduct?* → **keep it.**

**Phrasing red-flags.** These openings almost always signal an outcome, a
nicety, or something assertable rather than a deal-breaker — re-check any
criterion that starts like one: *"provides / gives / answers …"*, *"offers …"*,
*"successfully / is able to …"*, *"ensures the user …"*, *"makes the user feel
…"*, *"asks if the user wants …"*. Prefer constraints framed as *"the agent does
**not** …"* or *"before `<X>`, the agent `<Y>`"*.

**Keep the set small.** A few strong deal-breakers beat a long list. If a
scenario has many criteria you are probably restating the goal or adding
niceties — cut back to the ones whose failure clearly means the bot is broken.

> Rule of thumb: every criterion must be a **deal-breaker** — if it fails, the
> bot needs fixing. If a criterion could fail while the bot did everything right
> (wording drift, where the conversation stopped, an optional nicety), or if it
> is really about whether the *user* succeeded, it does not belong in
> `criteria`.

### Step 5 — Validate generated scenario files

For each scenario file that you created use the `validate_scenario` tool to validate a scenario YAML file for syntax and
assertion correctness. If validation fails, fix the scenario YAML according to the error message and re-run the scenario
validation. You need to have a valid scenario files before proceeding to the next step and running the simulation.

**Scenarios are stable after creation.** Once a scenario file is written and passes
`validate_scenario`, treat it as a fixed test fixture. Do **not** silently change
`simulation_context`, `criteria`, `assertions`, or `initial_slots` because an eval
run failed — even when you think you know the fix (bad mock data, flaky criterion,
assertion too strict, simulator wording drift). Instead:

1. Report what failed and where.
2. If a scenario edit seems warranted, explain **why** (with evidence from the
   run report / transcript).
3. Propose the exact change you would make.
4. **Wait for user confirmation** before editing the scenario file or re-running.

The only exception during initial authoring is fixing `validate_scenario` errors
while the scenario is still being created in Step 4–5.

### Step 6 — Run the simulation

Before the first call, generate a shared experiment ID by running this Bash command so all scenarios from this session land in the same results folder:

```bash
date +%Y-%m-%d_%H-%M-%S
```

Use the output as the `experiment_timestamp` for all `evaluate_agent` calls. If you encounter a permission error, use the currentDate from the system context.

Call `evaluate_agent` **once**, passing every scenario path for this session as `scenario_paths`. Scenarios and their repeated runs are evaluated concurrently; do not loop and call the tool per file.
Use `run_count` (1–10, default 3) to run each scenario multiple times — repeated runs surface flakiness in LLM-driven conversations.
Use `parallelism` (default 3, max 8) to cap how many runs execute at once. Leave it at the default unless the user asks for something different: one run is many LLM calls, not one — a simulation call per conversation turn, the agent's own calls behind each turn, then one or two evaluation calls — so provider and server load is a large multiple of this number.

```
evaluate_agent(
  scenario_paths=[
    "eval/scenarios/<scenario_type>.yml",
    "eval/scenarios/<other_scenario_type>.yml"
  ],
  experiment_timestamp=experiment_timestamp,
  run_count=3,
  parallelism=3
)
```

A single scenario is just a one-element list.

The call is rejected before anything runs if two paths share the same filename,
compared ignoring case (`a/checkout.yml` and `b/Checkout.yml` collide), because
results are keyed on the filename and one would overwrite the other. Rename one
scenario or evaluate them in separate calls — do not retry the same batch.

A batch is also capped at 50 scenarios. If a session has more, split them across
several calls that share the same `experiment_timestamp`, so they still land in
one results folder.

### Step 7 — Report results

The tool returns `scenario_results` — one entry per scenario in the batch, each
with `scenario_name`, `runs_total`, `runs_passed` and `runs_errored`. Lead with
the batch total, then break down per scenario.

**Check `runs_errored` before reporting anything as an agent failure.** It counts
runs that failed for harness reasons rather than on their merits — a timeout, a
cancellation, or an error reaching the Rasa server or the LLM provider. Those runs
never produced a verdict, so they say nothing about the agent. Report them
separately, as an evaluation problem, and do not present them as the agent
failing.

`success: false` means either the setup failed (unreadable `eval/conftest.yml`, a
bad scenario path) or *every* run failed that way, so nothing was evaluated at
all. A batch where only some runs errored is still `success: true` — which is why
`runs_errored` has to be read, not just `success`.

**If all runs passed:**

```
6/6 runs passed across 2 scenarios

"<scenario name>" — 3/3
"<other scenario name>" — 3/3

Quality (avg across runs): bot_quality 4.2/5 | helpfulness 4/5 | coherence 5/5 | repair_quality 4/5 | tone 4/5 | task_completion PASS
Result files: eval/results/<timestamp>/<scenario-name>/run_N.txt (plus run_N.json)
```

**If some runs failed:**

```
4/6 runs passed across 2 scenarios

"<scenario name>" — 1/3
  Run 2 failed:
    ✗ slot_was_set: <slot_name>
         slot '<slot_name>' = None
         turn 3 — bot moved on to confirmation without ever asking for <slot_name>

  Run 3 failed:
    ✗ success_criteria: "Agent confirms the task was completed successfully"
         Bot did not send a confirmation message before ending the conversation.
         turn 6 — bot ended after "anything else?" with no confirmation

"<other scenario name>" — 3/3

Quality (avg across runs): bot_quality 2.8/5 | helpfulness 3/5 | coherence 3/5 | repair_quality 2/5 | tone 3/5 | task_completion FAIL
Result files: eval/results/<timestamp>/<scenario-name>/run_N.txt (plus run_N.json)
```

Errored runs count as failures in `runs_passed` vs `runs_total`, and each still
has a `run_N.txt` — a placeholder recording what ended it when the run was
cancelled, or an ordinary report carrying the error. Open that file to say *why*
a run errored rather than reporting it as a plain failure.

**If `runs_errored` is greater than zero, say so before the pass/fail numbers.**
For example:

```
0/6 runs passed across 2 scenarios — but all 6 runs errored before reaching the
agent (connection refused to http://localhost:5005). This is an evaluation
problem, not a result for the agent. Check the Rasa server is running, then re-run.
```

For each failing run, say **where** it went wrong, not just which check failed: name the conversation turn
from the transcript in `run_N.txt` (the bot turn that broke the assertion, or the point the criterion stopped
being satisfiable), as in the `turn N` lines above.

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
2. **First check the other `eval/scenarios/*.yml`** for known-good values — a
   passing happy-path scenario may already carry valid credentials/IDs you can
   reuse. If you find them, **propose** updating the failing scenario with those
   values and ask for confirmation before editing.
3. Otherwise, pause and ask the user for valid mock values, naming exactly what
   you need and which scenario it's for, e.g.:
   ```
   The happy-path run for "<scenario name>" failed because the order number I
   used (12345) wasn't found in the backend. What's a valid test order number /
   username / password I should use? Once you confirm, I'll update the scenario
   and ask before re-running.
   ```
4. Only after the user confirms (and provides values if needed), update the
   affected `simulation_context` (and any `initial_slots` / assertions that
   hard-code the value), then ask whether to re-run (Step 8) — this is a
   scenario-only edit, so no retrain or restart is needed. On a yes, re-run that
   scenario on its own: a one-element `scenario_paths` list with the same
   `experiment_timestamp`.

Only scenarios that are *designed* to fail (wrong password, unknown order) keep
invalid values — there, assert the "not found" / failure behavior instead of
asking for new data.

**Do not edit the bot, a flow, a prompt or a scenario while reporting.** Report what failed and where, then
continue into Step 8 — root-cause analysis and a proposed fix follow **every** genuine failure automatically,
without the user having to ask. Nothing is changed until the user picks a fix.

### Step 8 — Analyze every failure and propose a fix

This step is **not** optional and does not wait to be asked. Whenever a run fails on its merits, analyze it
and propose a fix. Analyzing is not changing: you never edit anything until the user picks a fix.

**First, exclude errored runs.** A run counted in `runs_errored` never produced a verdict — it timed out, was
cancelled, or could not reach the Rasa server or the LLM provider. Do not root-cause it and do not put it in
a bucket; suggesting a flow fix for a server that was not running wastes the user's time. Report it as an
evaluation problem (Step 7) and stop there for that run.

**Group before analyzing.** Several failing runs usually share one root cause — the same assertion failing in
runs 1, 2 and 3 is one finding, not three. Group identical failures, analyze each distinct root cause once,
and say how many runs it accounts for. With many distinct causes, lead with the ones that explain the most
failed runs.

**Then classify each genuine failure into exactly one bucket:**

| Bucket | What it means | Typical evidence | Where to look |
| ------ | ------------- | ---------------- | ------------- |
| **Flow issue** | The flow is missing a path, has a gap, or is ambiguous | Bot dead-ends, loops, or routes to the wrong flow; `flow_completed` / `action_executed` assertions fail | The flow YAML under `data/`, plus slot/mapping definitions in the domain |
| **Prompt issue** | The agent needs clearer instructions | Bot picks a plausible-but-wrong step, ignores context it was given, or answers off-task | The prompt template referenced from `config.yml`, and any flow/step descriptions the command generator reads |
| **Scenario issue** | The scenario is unrealistic, outdated, or too strict | Assertion hard-codes phrasing the bot no longer uses; a criterion demands behavior the bot was never meant to have; **invalid test data** as triaged above belongs here | The scenario YAML in `eval/scenarios/` |
| **Tool/mock issue** | The tool contract or the mocked response is wrong | Tool called with the right arguments but returns a value the bot can't use, or the backend contradicts what the scenario assumes | The custom action / API the tool calls, and its endpoint config |

Note that scenario-level mocking of tool calls does not exist yet, so a "tool/mock" failure today means the
real tool or backend behaved unusably — there is no mock definition in the scenario to correct. Say so plainly
rather than proposing an edit to something that isn't there.

If a failure genuinely spans two buckets, name the one you would fix first and say why.

**Then, for each distinct root cause:**

1. **Name the bucket and the evidence** — the failing assertion/criterion, the turn it happened on, the
   `run_N.txt` path, and the specific file and line you believe is at fault.
2. **Propose the fix.** If more than one fix is plausible, list them and ask which the user wants — do not
   silently pick one.
3. **Wait for confirmation before editing anything — in every bucket.** This includes flows, prompts,
   domain and response templates, not just scenarios. Scenario edits carry the extra bar from Step 5:
   explain why the scenario itself is wrong, with evidence from the run.
4. **Apply only the fix the user chose.**
5. **Hand back — do not retrain, restart or re-run on your own.**

**Handing back after a fix**

What the user has to do before a re-run means anything depends on what you changed:

| What you changed | What it takes to pick the change up |
| ---------------- | ----------------------------------- |
| Flows, domain, responses, prompt templates, `config.yml` | `rasa train`, **then** restart the Rasa server |
| Custom action code | Restart the **action server** only — no retrain |
| `endpoints.yml` / `credentials.yml` | Restart the Rasa server — no retrain |
| Scenario YAML | Nothing |

A running `rasa run` keeps serving the model it started with (see Step 2), so a re-run before the retrain and
restart tests the *old* model and produces a misleading result. Say exactly which of the steps above applies —
do not tell the user to retrain for a change that doesn't need it. For a model-affecting fix:

```
I've updated <file>. That change only takes effect after a retrain, so before re-running:

  1. rasa train
  2. Restart the server:  rasa run --inspect --credentials credentials.yml

Tell me when you'd like the evals re-run and I'll re-run "<scenario name>".
```

Do not call `train_rasa_assistant` yourself unless the user asks you to. It trains a new model but cannot
restart the server, so it leaves the same manual step outstanding.

A **scenario-only** edit needs neither a retrain nor a restart, so there just ask:

```
I've updated <scenario file>. No retrain needed — want me to re-run "<scenario name>"?
```

When the user asks for the re-run, call `evaluate_agent` with a one-element `scenario_paths` list and the same
`experiment_timestamp`, not the whole batch.

---

## Config reference


| Field                                  | Required | Default          |
| -------------------------------------- | -------- | ---------------- |
| `simulation.llm`                       | Yes      | —                |
| `evaluation.llm`                       | Yes      | —                |
| `simulation.simulated_user_prompt`     | No       | Built-in default |
| `evaluation.criteria_judge_prompt`     | No       | Built-in default |
| `evaluation.metrics_judge_prompt`      | No       | Built-in default |


---

## Common issues


| Symptom                                             | Likely cause                                                   | Fix                                                                                                                      |
| --------------------------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `Scenario file not found`                           | Wrong path or missing file                                     | Check with Glob using the right pattern (see Step 2), create file if needed                                              |
| `talk_to_assistant` returns 404 / bot not reachable on REST webhook | `credentials.yml` missing the REST input channel | Read `credentials.yml` and check for a `rest:` block. If absent, tell the user to add it and restart the Rasa server — do **not** edit `credentials.yml` yourself unless the user explicitly asks you to. |
| `bot_uttered` with `text_matches` fails unexpectedly | Bot uses different phrasing                                   | Read the transcript in the result file; prefer structural assertions (`flow_completed`, `action_executed`) over regex     |
| Simulation hits max turns (20)                      | Bot stuck in loop or user simulator confused                   | Read transcript, check if bot keeps re-asking same question                                                              |
| All criteria pass but assertions fail               | Slot not being filled                                          | Check tracker slots in result file, verify slot mappings in domain                                                       |
| Happy-path run fails with "not found" / auth errors | Mock value (order no., account, password) isn't in the backend | Test-data problem, not a bot bug — ask the user for valid test data, update `simulation_context`/`initial_slots`, ask before re-running |
| `agent_reloaded: false` after training, but the bot still answers | Standalone `rasa run` has no reload endpoint, so it keeps serving the model it started with | Not a "server down" error — ask the user to restart the server, then re-run (Step 2) |
| Fix applied, re-run fails identically | Model wasn't retrained/restarted, so the run tested the old model | Hand back after a fix: user retrains and restarts, then asks for the re-run (Step 8) |


---

## Viewing a run in the Inspector

After a simulation run, the result file includes an Inspector URL under `--- Inspector URL ---`.
Open it directly in the browser — the conversation is already in the shared tracker store because the server was started
with `--inspect`.

No extra tool call or file loading needed.
