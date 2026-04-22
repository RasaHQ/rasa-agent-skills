---
name: rasa-simulating-conversations
description: >
  Run goal-driven simulations against a live Rasa CALM assistant.
  Reads scenario YAML files from eval/scenarios/, calls the evaluate_agent
  MCP tool which uses an LLM to simulate a user, drives the conversation
  through the Rasa REST API, checks deterministic assertions against the tracker,
  scores success criteria with an LLM judge, and writes results to eval/results/.
  Use when asked to simulate, stress-test, evaluate, or run eval scenarios.
---

# Goal-Driven Simulation for Rasa CALM

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

### Text (default)

```yaml
scenario:
  name: User successfully completes <flow name>
  modality: text

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
    assertions:                     # deterministic checks against tracker
      - slot_filled: <slot_name>                        # non-null check
      - slot_filled:                                    # exact value check
          name: <slot_name>
          value: "<expected_value>"
      - tool_called: <action_name>
      - tool_called_with:
          tool: <action_name>
          params:
            <slot_name>: "<expected_value>"
      - skill_completed: true
      - sequencing:
          before: <action_that_must_come_first>
          after: <action_that_must_come_after>
      - response_not_contains: "I don't know"
```

### Voice

Set `modality: voice` — everything else is identical to the text format. All voice
configuration (TTS, ASR, WebSocket URL, sample rate) comes from `eval/conftest.yml`.

```yaml
scenario:
  name: User successfully completes <flow name> via voice
  modality: voice

  simulation_context: >
    You are a cooperative caller who wants to complete the task.
    Speak naturally in short phrases as you would on a phone call.

  setup:
    initial_slots:                  # injected after handshake, before first user turn
      authenticated: true

  goals:
    criteria:
      - Agent collects all required information without confusion
      - Agent confirms the task was completed successfully
    assertions:
      - slot_filled: <slot_name>
      - skill_completed: true
```

The LLM judge scores 5 voice-specific dimensions: Naturalness, Turn-taking, Brevity, Repair quality, Helpfulness.

### Supported assertion types

| Type | Example | What it checks |
|---|---|---|
| `slot_filled` | `slot_filled: recipient_name` | Slot was set to a non-null value at any point during the conversation — checked against tracker event history, not final state |
| `skill_completed` | `skill_completed: true` | `flow_completed` event found in tracker |
| `action_executed` | `action_executed: action_submit_transfer` | Named action appears in tracker events |
| `response_not_contains` | `response_not_contains: "I don't know"` | Phrase absent from all bot responses |
| `response_contains_any` | `response_contains_any: ["insufficient", "balance"]` | At least one phrase present in any bot response |

---

## Step-by-step workflow

### Step 1 — Check eval/conftest.yml

Before doing anything else, check whether `eval/conftest.yml` exists:

```
Use Glob("eval/conftest.yml") to check.
```

**If it exists** — read it and confirm the required fields are present (see below). Proceed to Step 2.

**If it does not exist** — create it with the exact content below, **including every comment line** — do not omit or paraphrase them. Then tell the user to fill in the details before continuing:

```yaml
# eval/conftest.yml — simulation configuration

# LLM used to drive the user simulator (generates user turns)
simulation:
  llm:
    provider: openai       # openai | anthropic | azure | ...
    model: gpt-4o

# LLM used to evaluate success criteria (LLM judge)
evaluation:
  llm:
    provider: openai
    model: gpt-4o
  # Prompt overrides — paths are relative to the project root.
  # Use these to customise how the judge scores conversations.
  # prompt_template: prompt_templates/judge.jinja2              # overrides text/criteria judge (variables: simulation_context, criteria_text, transcript)
  # voice_prompt_template: prompt_templates/voice_judge.jinja2  # overrides voice quality judge (variables: simulation_context, transcript)

# Required for voice simulations — not needed for text
tts:
  provider: openai         # openai | deepgram
  model: tts-1             # tts-1 | tts-1-hd (openai) | aura-asteria-en (deepgram)
  voice: alloy             # alloy | echo | fable | onyx | nova | shimmer (openai)

# Required for voice simulations — not needed for text
asr:
  provider: openai         # openai | deepgram
  model: whisper-1         # whisper-1 (openai) | nova-2 (deepgram)
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

For **voice simulation**, both `rest` and `browser_audio` connectors must be in `credentials.yml`. Starting with `--connector browser_audio` disables the REST channel and will break text simulation.

The `--inspect` flag loads the Inspector in the same process, so a single server is all that's needed — no separate `rasa inspect` command.

**After retraining:** always check `agent_reloaded` in the `train_rasa_assistant` response.
- If `agent_reloaded: true` — the server picked up the new model, proceed to simulate.
- If `agent_reloaded: false` — the server is not running. Do NOT attempt workarounds (e.g. SlotSet in custom actions). Tell the user:
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

There are two ways to create scenarios. Choose based on what the user asked:

---

#### Option A — Generate from flow definition (default)

Use this when the user asks to simulate a flow without mentioning real conversations.

1. Read the flow definition with `list_project_flow_definitions` and then read the file
2. Extract: flow name, slots being collected (name + description), branching conditions
3. Write scenario YAML to `eval/scenarios/<scenario_type>.yml`

For each flow, generate scenario types covering the happy path and CALM conversation repair patterns:

| Type | Persona | Goal variation |
|---|---|---|
| `happy_path` | Cooperative, friendly | Provides all info directly when asked |
| `correction` | Careful user | Provides wrong value, then corrects it |
| `vague_user` | Indirect user | Starts vague, reveals intent gradually |
| `abandon_restart` | Impatient user | Abandons mid-flow, restarts with different goal |
| `chitchat` | Off-topic user | Sends chitchat mid-flow |
| `clarification` | Ambiguous user | Intent matches multiple flows |
| `cancel_flow` | Changed mind | Cancels the flow mid-way |
| `human_handoff` | Frustrated user | Requests a human agent |
| `skip_question` | Evasive user | Tries to skip a required slot |
| `cannot_handle` | Out-of-scope user | Sends something the bot can't handle |

For **voice scenarios**, add a `channel` block and use short spoken phrases in `key_steps`. `setup.initial_slots` works the same as text.

---

#### Option B — Seed from real conversations

Use this when the user asks to simulate from real/production conversations, or says something like "simulate based on what real users did" or "seed scenarios from real conversations".

1. Call `fetch_conversations` with the flow name to get real conversation IDs:
   ```
   fetch_conversations(flow_name="<flow_name>", limit=5)
   ```
2. For each conversation returned, call `seed_scenario_from_conversation`:
   ```
   seed_scenario_from_conversation(sender_id="<sender_id>", flow_name="<flow_name>")
   ```
   This fetches the real transcript, infers persona/goal/key_steps with an LLM, and writes the scenario YAML automatically to `eval/scenarios/`.
3. Collect all the generated `scenario_path` values — these are ready to simulate.

If `fetch_conversations` returns no results, fall back to Option A and tell the user no real conversations were found.

### Step 4 — Run the simulation

Before the first call, generate a shared experiment ID so all scenarios from this
session land in the same results folder:

```
experiment_id = datetime.now().strftime("%Y%m%d_%H%M%S")
```

Run scenarios sequentially using `evaluate_agent`, passing the same `experiment_id`
to every call. The tool reads `modality` from the scenario YAML and routes to text
or voice automatically.

```
evaluate_agent(
  scenario_path="eval/scenarios/<scenario_type>.yml",
  experiment_id=experiment_id
)
```

When seeding produced multiple scenarios (Option B), run each one in turn, reusing
the same `experiment_id`.

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

| Field | Required | Default |
|---|---|---|
| `simulation.llm` | Yes | — |
| `evaluation.llm` | Yes | — |
| `tts` (provider + model + voice) | Voice only | — |
| `asr` (provider + model) | Voice only | — |
| WebSocket URL | No | Derived from Rasa server URL |
| Sample rate, turn timing | No | Built-in defaults |

---

## Common issues

| Symptom | Likely cause | Fix |
|---|---|---|
| `Scenario file not found` | Wrong path or missing file | Check with Glob using the right pattern (see Step 2), create file if needed |
| Bot returns empty responses (text) | Rasa not running or not trained | Ask user to run `rasa run --enable-api --inspect --credentials credentials.yml` |
| `response_contains_any` fails unexpectedly | Bot uses different phrasing | Read the transcript in the result file, update assertions or flow response |
| Simulation hits max turns (20) | Bot stuck in loop or user simulator confused | Read transcript, check if bot keeps re-asking same question |
| All criteria pass but assertions fail | Slot not being filled | Check tracker slots in result file, verify slot mappings in domain |
| Voice: WebSocket connection refused | `browser_audio` connector not loaded | Add `browser_audio:` to `credentials.yml`; do not pass `--connector` flag |
| Voice: bot transcription empty | Bot returned no audio (latency/TTS issue) | Check server logs; try increasing `turn_timeout` in the `channel` block |
| Voice: no inspector section in report | `sender_id` not received from handshake | Ensure the Rasa server is using the current build (handshake includes `sender_id`) |

---

## Viewing a run in the Inspector

After a simulation run, the result file includes an Inspector URL under `--- INSPECTOR URL ---`.
Open it directly in the browser — the conversation is already in the shared tracker store because the server was started with `--inspect`.

No extra tool call or file loading needed.
