---
name: rasa-integrating-asr
description: >
  Integrates a custom automatic speech recognition (ASR/STT) provider with Rasa voice
  channels from provider documentation. Use when implementing an ASREngine, mapping
  streaming transcripts and turn detection to Rasa events, or configuring custom ASR
  credentials.
license: Apache-2.0
arguments: [documentation]
metadata:
  author: rasa
  version: "0.1.0"
  rasa_version: ">=3.16.0"
  docs-url: https://rasa.com/docs/reference/integrations/speech-integrations/
---

# Integrating a Custom ASR Provider

The provider documentation is: **$documentation**

Use the documentation as the source of truth for the provider protocol. If it is
missing, ask for the provider's streaming ASR API documentation before implementing.
Follow links from it only when needed to resolve authentication, WebSocket messages,
audio formats, endpointing, or limits.

## Workflow

1. Inspect the assistant's installed Rasa version and the actual `ASREngine`,
   `ASREngineConfig`, `ASREvent`, and `RasaAudioBytes` APIs. Follow those signatures
   when they differ from examples.
2. Review existing custom speech components and project conventions before choosing a
   module path. Default to `addons/custom_asr.py` only when no convention exists.
3. Read the provider documentation and complete the feasibility checks in
   [references/integration-framework.md](references/integration-framework.md).
4. If a hard requirement is unsupported or undocumented, report every incompatibility
   found and stop. Do not invent protocol messages, transcript semantics, or
   client-side endpointing.
5. Design the configuration and event mapping, then implement the custom `ASREngine`.
6. Configure its fully qualified class path under the voice channel's `asr` key in
   `credentials.yml`. Keep secrets in environment variables.
7. Add focused tests for provider-message mapping, transcript accumulation, audio
   conversion, and malformed/error events.
8. Run the project's relevant tests, lint/type checks, and Rasa configuration
   validation. Report any validation that could not be run.

## Feasibility gate

A custom ASR integration must have:

- a documented real-time streaming API compatible with the `ASREngine` connection
  lifecycle;
- a documented end-of-utterance or end-of-turn signal that can produce exactly one
  `NewTranscript`;
- an audio encoding and sample rate that the provider accepts directly or that can be
  converted safely from `RasaAudioBytes`;
- documented authentication suitable for a server process;
- clear partial, final, error, and connection-close message semantics.

Interim transcripts are recommended but not mandatory. If they are unavailable, note
that `UserIsSpeaking` cannot carry partial text and that barge-in behavior may be less
responsive. Provider-side turn detection is mandatory: do not fabricate it with an
arbitrary silence timer.

## Implementation contract

- Subclass the installed version's `ASREngine` and use its matching configuration
  type.
- Implement every abstract/required method in that installed version. This commonly
  includes connection creation, config construction, audio conversion, provider-event
  conversion, end-of-audio signaling, and default configuration.
- Map partial speech to `UserIsSpeaking`, completed turns to `NewTranscript`, and
  explicit silence to `UserSilence` only when the provider semantics support it.
- Accumulate final fragments only when the provider sends multiple fragments for one
  turn. Reset accumulation after emitting `NewTranscript`.
- Treat provider error frames and unexpected socket closure explicitly. Never log API
  keys, authorization headers, or raw credentials.
- Declare `required_env_vars` and `required_packages` when supported by the installed
  base class. Prefer the project's existing WebSocket stack over a vendor SDK when both
  expose the same documented protocol.
- Keep provider-specific settings in the config type. Prefer `language_map` for
  multilingual assistants when supported by the installed Rasa version.
- Do not edit Rasa's built-in engine registry for a project-level integration.

## Configuration

Reference the custom class by module path:

```yaml
# credentials.yml
browser_audio:
  # ... channel configuration
  asr:
    name: addons.custom_asr.MyASR
    endpoint: wss://api.example.com/v1/speech
    language: en-US
```

The module must be importable from the process that starts Rasa. Put secret values in
environment variables, document the required variable names, and never commit them to
`credentials.yml`.

For multilingual assistants, ensure every `language_map` key matches `language` or
`additional_languages` in `config.yml`.

## Done criteria

- The provider protocol is supported by cited documentation.
- A documented provider turn-end event maps to one `NewTranscript`.
- Audio encoding, sample rate, and channel expectations are compatible.
- The custom class imports and is referenced correctly from `credentials.yml`.
- Secrets stay outside source-controlled configuration.
- Tests and available project validation pass.
