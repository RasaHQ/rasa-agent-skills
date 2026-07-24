---
name: rasa-integrating-tts
description: >
  Integrates a custom text-to-speech (TTS) provider with Rasa voice channels from
  provider documentation. Use when implementing a TTSEngine, adding streaming or
  non-streaming speech synthesis, converting provider audio to RasaAudioBytes, or
  configuring custom TTS credentials.
license: Apache-2.0
arguments: [documentation]
metadata:
  author: rasa
  version: "0.1.0"
  rasa_version: ">=3.16.0"
  docs-url: https://rasa.com/docs/reference/integrations/speech-integrations/
---

# Integrating a Custom TTS Provider

The provider documentation is: **$documentation**

Use the documentation as the source of truth for the provider protocol. If it is
missing, ask for the provider's TTS API documentation before implementing. Follow links
from it only when needed to resolve authentication, request/response messages, audio
formats, streaming behavior, interruption, or limits.

## Workflow

1. Inspect the assistant's installed Rasa version and the actual `TTSEngine`,
   `TTSEngineConfig`, and `RasaAudioBytes` APIs. Follow those signatures when they
   differ from examples.
2. Review existing custom speech components and project conventions before choosing a
   module path. Default to `addons/custom_tts.py` only when no convention exists.
3. Read the provider documentation and complete the protocol analysis in
   [references/integration-framework.md](references/integration-framework.md).
4. Choose streaming or non-streaming input from documented provider behavior. Do not
   mark an engine as streaming merely because its response audio arrives in chunks.
5. Design the configuration and audio conversion, then implement the custom
   `TTSEngine`.
6. Configure its fully qualified class path under the voice channel's `tts` key in
   `credentials.yml`. Keep secrets in environment variables.
7. Add focused tests for configuration, request messages, audio conversion, lifecycle,
   and provider errors.
8. Run the project's relevant tests, lint/type checks, and Rasa configuration
   validation. Report any validation that could not be run.

## Select the synthesis mode

Use non-streaming input when the provider requires the complete text before synthesis:

- keep `streaming_input` false;
- implement `synthesize()` as the complete text-to-audio lifecycle;
- yield `RasaAudioBytes` as provider audio becomes available.

Use streaming input only when the provider accepts multiple incremental text chunks in
one synthesis session:

- set `streaming_input = True`;
- implement the installed contract's connection, text-chunk, text-done, and audio
  streaming methods;
- preserve ordering and flush semantics documented by the provider.

Streaming audio output and streaming text input are different capabilities. A provider
that accepts one full text request and streams audio back still uses non-streaming
input.

## Implementation contract

- Subclass the installed version's `TTSEngine` and use its matching configuration type.
- Implement every abstract/required method in that installed version. This commonly
  includes `synthesize`, audio conversion, config construction, and default config.
- Convert every provider audio chunk to the channel-compatible `RasaAudioBytes` format.
  Account for encoding, sample rate, channel count, and container headers.
- Implement connection and streaming methods only when the selected mode needs them.
- Implement `signal_interrupt` only when the provider documents an in-band cancel,
  clear, or equivalent operation. Otherwise retain the base no-op and report the
  limitation; do not invent socket-close/reconnect behavior.
- Close WebSockets and HTTP sessions reliably on completion, cancellation, and errors.
- Translate provider failures into the installed engine's expected TTS error type while
  preserving actionable context and excluding secrets.
- Declare `required_env_vars` and `required_packages` when supported by the installed
  base class. Prefer existing project dependencies when they fit the documented API.
- Keep provider-specific settings in the config type. Prefer `language_map` for
  multilingual assistants when supported by the installed Rasa version.
- Do not edit Rasa's built-in engine registry for a project-level integration.

## Configuration

Reference the custom class by module path:

```yaml
# credentials.yml
browser_audio:
  # ... channel configuration
  tts:
    name: addons.custom_tts.MyTTS
    endpoint: wss://api.example.com/v1/speak
    language: en-US
    voice: example-voice
```

The module must be importable from the process that starts Rasa. Put secret values in
environment variables, document the required variable names, and never commit them to
`credentials.yml`.

For multilingual assistants, ensure every `language_map` key matches `language` or
`additional_languages` in `config.yml`.

## Done criteria

- The selected synthesis mode matches documented provider behavior.
- Audio encoding, sample rate, and channel expectations are compatible.
- Resource cleanup and provider error handling are explicit.
- Interrupt support exists only when backed by a documented provider operation.
- The custom class imports and is referenced correctly from `credentials.yml`.
- Secrets stay outside source-controlled configuration.
- Tests and available project validation pass.
