# Rasa Agent Skills

A collection of skills for AI coding agents working with [Rasa CALM](https://rasa.com/docs/). Skills are packaged instructions that guide agents through building, configuring, and testing Rasa conversational AI agents.

Skills follow the [Agent Skills](https://agentskills.io/) format.

## Available Skills

### rasa-building-flows

Build conversation flows for Rasa CALM agents in YAML. Covers flow design, branching logic, collect and action steps, descriptions, and connecting flows with `call` and `link` steps.

**Use when:**
- Creating or editing conversation flows
- Designing flow architecture and scoping flows
- Adding branching logic with conditions
- Writing flow and collect step descriptions
- Connecting flows with `call` and `link` steps

**Topics covered:**
- Scoping a flow (one user goal per flow)
- File organization and naming conventions
- Writing effective descriptions for flows and collect steps
- Slots, collect steps, and rejections
- Branching and conditions (`if`/`then`/`else`)
- `call` vs `link` for connecting flows
- Flow guards

### rasa-configuring-assistant

Configure `config.yml` and `endpoints.yml` for Rasa CALM agents. Covers pipeline components, policies, action endpoint, and language settings.

**Use when:**
- Setting up a new Rasa CALM project
- Modifying pipeline components (command generators, flow retrieval)
- Configuring policies (`FlowPolicy`)
- Setting the action endpoint or language

**Topics covered:**
- Minimal CALM configuration
- Pipeline (command generators, embeddings, input limits)
- Policies (`FlowPolicy`)
- Language and multilingual setup
- Model groups, action endpoint, NLG server

### rasa-configuring-model-groups

Configure `model_groups` in `endpoints.yml` for LLM and embedding providers. Covers single and multi-deployment setups, routing strategies, failover, self-hosted models, and caching.

**Use when:**
- Adding or changing LLM providers (OpenAI, Azure, self-hosted)
- Setting up multi-LLM routing and failover
- Configuring embedding providers for flow retrieval or enterprise search
- Enabling response caching

**Topics covered:**
- Supported providers (OpenAI, Azure, self-hosted, Ollama, LiteLLM)
- Single and multi-deployment configuration
- Routing strategies (shuffle, least-busy, latency, cost, usage)
- Router customization and Redis-backed strategies
- Self-hosted models (vLLM, Llama.cpp, Ollama)

### rasa-managing-slots

Define and manage slots in Rasa CALM domain files. Covers slot types, mappings, validation, and how slots are filled and persist across flows.

**Use when:**
- Creating or editing slot definitions
- Choosing slot types and mappings
- Configuring slot validation
- Controlling how slots get filled and persist

**Topics covered:**
- Slot types (`text`, `bool`, `categorical`, `float`, `any`, `list`)
- Slot mappings (`from_llm`, `controlled`, `from_entity`, `from_intent`)
- Initial values and persistence
- Validation strategies (domain-level, flow-level, custom actions)
- Naming conventions

### rasa-rephrasing-responses

Enable and configure the LLM-powered Contextual Response Rephraser. Covers `endpoints.yml` setup, per-response metadata, and prompt customization.

**Use when:**
- Setting up or tuning the Contextual Response Rephraser
- Choosing rephrasing scope (all responses vs specific ones)
- Customizing rephrasing prompts

**Topics covered:**
- Endpoints configuration (`nlg: type: rephrase`)
- Conversation history modes (summary vs transcript)
- Rephrasing scope (specific, all, all-except)
- Global and per-response prompt customization

### rasa-setting-up-enterprise-search

Add knowledge-base search to a Rasa CALM agent using `EnterpriseSearchPolicy`. Connect vector stores (Faiss, Milvus, Qdrant) and configure generative or extractive search.

**Use when:**
- Setting up RAG / enterprise search
- Connecting a vector store
- Overriding `pattern_search`
- Implementing a custom information retriever

**Topics covered:**
- `SearchReadyLLMCommandGenerator` setup
- `EnterpriseSearchPolicy` (generative and extractive modes)
- Triggering search via `pattern_search` or from within flows
- Vector stores (Faiss, Milvus, Qdrant)
- Prompt customization
- Custom information retrievers

### rasa-writing-custom-actions

Write custom actions in Python using the Rasa SDK. Covers API calls from flows, slot validation actions, and dynamic ask actions.

**Use when:**
- Creating or editing custom action files
- Calling external APIs from flows
- Implementing slot validation actions (`validate_{slot_name}`)
- Building dynamic ask actions (`action_ask_{slot_name}`)

**Topics covered:**
- Action class structure (`name()` and `run()`)
- Working with the tracker (`get_slot`, `sender_id`)
- Error handling patterns
- Returning events (`SlotSet`, `FollowupAction`, etc.)
- Using the dispatcher
- Custom ask actions and slot validation actions
- Domain registration

### rasa-writing-e2e-tests

Write and maintain end-to-end tests for Rasa CALM in YAML. Covers test cases, assertions, fixtures, stubbing custom actions, and validating flows, slots, and generative responses.

**Use when:**
- Creating or editing E2E test cases
- Adding assertions for flows, slots, and actions
- Setting up fixtures and mocking datetime
- Stubbing custom actions for isolated testing

**Topics covered:**
- Test case structure (`user`, `bot`, `utter`, `slot_was_set` steps)
- Assertions (`flow_started`, `flow_completed`, `action_executed`, `bot_uttered`)
- Generative response assertions (relevance and grounding)
- Fixtures and `conftest.yml`
- Stubbing custom actions
- Running tests and coverage reports

### rasa-writing-responses

Write response templates in Rasa CALM domain files. Covers variations, buttons, images, conditional and channel-specific content, and overriding default pattern responses.

**Use when:**
- Creating or editing response templates
- Adding variations, buttons, or images
- Writing conditional or channel-specific responses
- Overriding default pattern responses
- Enabling response rephrasing

**Topics covered:**
- Response basics and slot variables
- Response variations
- Rich responses (buttons, images, custom payloads)
- Conditional and channel-specific variations
- Overriding default pattern responses
- Voice-specific properties (`allow_interruptions`)

## Installation

TODO

## Usage

Skills are automatically available once installed. The agent will use them when relevant tasks are detected.

**Examples:**
```
Create a flow for booking an appointment
```
```
Add a custom action to fetch order status from our API
```
```
Set up enterprise search with Qdrant
```
```
Write E2E tests for the transfer money flow
```

## Skill Structure

Each skill contains:
- `SKILL.md` - Instructions for the agent
- `references/` - Supporting documentation (optional)

## License

Apache-2.0
