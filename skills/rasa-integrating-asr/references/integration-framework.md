# Custom ASR Integration Framework

Read this file while evaluating and implementing a provider.

## Documentation review

Extract and record:

- WebSocket URL and whether it is per call, per utterance, or reconnectable
- authentication mechanism and required environment variables
- accepted encodings, sample rates, channel count, and container/header requirements
- binary versus encoded audio input and any start/config/end control messages
- interim transcript, final fragment, and end-of-turn message shapes
- provider errors, close codes, keep-alive requirements, and reconnect rules
- language/model options and concurrent-session limits

Do not infer undocumented fields from an SDK example. If the supplied page is an
overview, follow its official links to the provider's protocol reference.

## Feasibility checklist

Evaluate all checks before deciding whether to implement:

1. The provider has a documented streaming connection usable by the installed
   `ASREngine` contract.
2. Audio can be sent while the user is speaking.
3. The provider emits a documented end-of-utterance/end-of-turn signal.
4. That signal includes or follows enough transcript data to emit one
   `NewTranscript`.
5. Input audio is compatible with a Rasa-supported format or can be converted without
   losing framing or timing.
6. Authentication works non-interactively in a server deployment.
7. Message schemas and lifecycle rules are documented.
8. Session and concurrency constraints are compatible with one engine connection per
   active voice conversation.

Run every check even after finding a blocker. If any check fails, give the user one
complete incompatibility report with the provider evidence and the affected Rasa
contract. Do not implement a partial engine.

## Audio formats

`RasaAudioBytes` is Rasa's intermediate audio representation. Depending on the channel,
it can carry:

- 8-bit 8 kHz μ-law mono;
- linear 16-bit 24 kHz PCM mono;
- linear 16-bit 48 kHz PCM mono.

Inspect the installed `RasaAudioBytes` implementation and channel configuration rather
than assuming one format. Preserve chunk boundaries unless the provider requires
buffering. Make encoding, sample rate, and channel count explicit in the provider's
start message or connection parameters.

If conversion is needed, use an existing project/Rasa conversion utility when
available. Test the conversion with representative bytes and document added latency.

## Event mapping

Build a mapping from documented provider frames before writing code:

- partial/interim transcript → `UserIsSpeaking(text)`;
- final transcript fragment before turn end → accumulate if required by the protocol;
- end-of-utterance/end-of-turn → `NewTranscript(complete_text)`;
- explicit no-speech/silence result → `UserSilence`, when semantically equivalent;
- provider error → the installed engine's expected exception/error path;
- metadata-only/acknowledgement frame → `None`.

Do not equate a provider's `is_final` field with turn completion unless its
documentation says it ends the utterance. Some providers finalize several fragments
within a single turn.

Protect these invariants:

- emit no empty transcript;
- emit exactly one `NewTranscript` per provider turn;
- do not repeat already committed fragments;
- clear per-turn state after commit and on reconnect;
- tolerate documented acknowledgements and metadata frames.

## Configuration design

Use the installed base config and add only provider-specific fields. Establish safe
defaults for endpoints and timeouts, but do not default secrets.

Use `language_map` when the provider's language/model varies with the assistant's active
language. Keys must match `config.yml`; values hold provider language/model identifiers.
Keep deprecated top-level language/model fields only when compatibility with the
installed Rasa API requires them.

## Test checklist

Use recorded synthetic messages, not live credentials, for unit tests:

- config parsing and defaults;
- partial transcript mapping;
- one or multiple final fragments followed by turn end;
- empty and metadata-only messages;
- provider error and malformed frames;
- accumulator reset between turns and after reconnect;
- audio conversion for every supported input format;
- end-of-audio control message;
- language selection, when supported.

Mock the WebSocket boundary. Add a small opt-in integration test only if the project
already has a secure pattern for provider tests.

## Implementation report

At handoff, state:

- documentation pages used;
- provider turn-end event and Rasa event mapping;
- accepted/output audio format and any conversion;
- required environment variables and packages;
- module path configured in `credentials.yml`;
- checks run and their results;
- provider limitations such as absent interim transcripts or session limits.
