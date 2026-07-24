# Custom TTS Integration Framework

Read this file while evaluating and implementing a provider.

## Documentation review

Extract and record:

- API transport, endpoint, and whether the connection is per request or long-lived
- authentication mechanism and required environment variables
- whether text input is complete-request or incremental
- request, flush/end, audio, metadata, error, and cancel message shapes
- audio encoding, sample rate, channel count, and container/header behavior
- voice, language, model, speed, and timeout options
- provider errors, close codes, keep-alive requirements, reconnect rules, and limits

Do not infer undocumented messages from an SDK implementation. If the supplied page is
an overview, follow its official links to the provider's protocol reference.

## Capability analysis

Confirm all required facts before implementing:

1. The provider can synthesize text through a server-side API.
2. Audio can be returned in chunks or buffered and yielded safely.
3. Output audio is compatible with a Rasa-supported format or can be converted
   correctly.
4. Authentication works non-interactively in a server deployment.
5. Request completion, provider errors, and resource cleanup are documented.
6. Session and concurrency limits fit the assistant's deployment.

Then classify these independent capabilities:

- **Streaming text input:** the provider accepts multiple text chunks in one synthesis
  session. This controls `streaming_input`.
- **Streaming audio output:** the provider returns audio before the complete synthesis
  is available. This controls when `synthesize()` or `stream_audio()` can yield.
- **In-band interruption:** the provider defines a cancel/clear operation that stops
  queued synthesis without destroying the connection. This controls
  `signal_interrupt`.

A provider may stream audio output without accepting streaming text input. Do not
conflate the two.

## Audio formats

`RasaAudioBytes` is Rasa's intermediate audio representation. Depending on the channel,
it can carry:

- 8-bit 8 kHz μ-law mono;
- linear 16-bit 24 kHz PCM mono;
- linear 16-bit 48 kHz PCM mono.

Inspect the installed `RasaAudioBytes` implementation and channel configuration rather
than assuming one format. Negotiate a provider output that matches the channel when
possible. Otherwise convert encoding and sample rate deliberately.

Check whether each provider chunk contains raw samples or a repeated file/container
header. Strip or preserve headers according to the installed Rasa audio contract; do
not concatenate incompatible framed chunks blindly.

If conversion is needed, use an existing project/Rasa conversion utility when
available. Test the conversion with representative bytes and document added latency.

## Non-streaming input pattern

Use this mode when one complete text value starts synthesis:

1. Merge the optional per-call config with engine defaults using the installed API.
2. Send one synthesis request.
3. Check HTTP status or the provider's initial acknowledgement.
4. Decode each audio response chunk and convert it to `RasaAudioBytes`.
5. Yield non-empty chunks.
6. Close per-request resources in `finally`.

The response may still be streamed. Leave `streaming_input` false.

## Streaming input pattern

Use this mode only for documented incremental text input:

1. Open the session with authentication and synthesis configuration.
2. Send text chunks in order without silently dropping whitespace.
3. Send the provider's documented flush/end-of-input operation.
4. Consume audio, metadata, completion, and error frames until the synthesis completes.
5. Convert and yield audio frames only.
6. Reuse or close the connection according to documented lifecycle rules.
7. Ensure cancellation unblocks both sender and receiver tasks.

Guard shared sockets and mutable state if one engine instance can receive overlapping
requests. Follow existing project/Rasa locking patterns.

## Interruption

Implement `signal_interrupt` only for a documented in-band operation such as cancel or
clear. Test that:

- queued audio for the interrupted utterance is not yielded afterward;
- the connection remains in the state promised by the provider;
- the next utterance does not receive stale audio.

If the API has no such operation, keep the base implementation and document that
provider-side synthesis cannot be cleared during barge-in. Closing the socket is not an
equivalent unless the provider explicitly defines it as the interruption protocol.

## Configuration design

Use the installed base config and add only provider-specific fields. Establish safe
defaults for endpoints and timeouts, but do not default secrets.

Use `language_map` when voice/language/model varies with the assistant's active
language. Keys must match `config.yml`; values hold provider identifiers. Keep
deprecated top-level fields only when compatibility with the installed Rasa API
requires them.

## Test checklist

Use synthetic provider responses, not live credentials, for unit tests:

- config parsing, defaults, and per-call overrides;
- request/start and flush/end messages;
- binary and base64 audio frames, as applicable;
- empty, metadata-only, completion, malformed, and provider-error frames;
- audio conversion for every supported output format;
- cleanup after success, provider error, and cancellation;
- incremental text ordering when `streaming_input` is true;
- interrupt behavior when supported;
- language/voice/model selection.

Mock the HTTP/WebSocket boundary. Add a small opt-in integration test only if the
project already has a secure pattern for provider tests.

## Implementation report

At handoff, state:

- documentation pages used;
- streaming-text, streaming-audio, and interrupt capabilities;
- provider output format and any conversion;
- required environment variables and packages;
- module path configured in `credentials.yml`;
- checks run and their results;
- provider limitations such as no in-band interruption or concurrency limits.
