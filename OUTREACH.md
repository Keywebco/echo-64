# Echo 64 — Outreach Brief for AI Platforms

**Audience:** AI platform engineers, researchers, and model integrators.

## The problem

Your AI context can disappear between sessions. Reconstructed context drifts when handed across platforms. There is no shared compact, byte-exact interchange convention for these handoffs.

## What EC-64 is

EC-64 is a 64-character, unpadded base64url encoding with optional raw DEFLATE compression and a tagged byte frame. Its compact prompt spec and explicit decoder rules let you implement it without shared model training or tokenizers; compression can help repetitive data, but token savings are input- and tokenizer-dependent.

## How to evaluate it

Read the [developer spec](https://github.com/Keywebco/echo-64/blob/main/echo-64-developer.md) and compare your implementation with the [test vectors](https://github.com/Keywebco/echo-64/blob/main/test-vectors.md). Clone the canonical repository, run `python ec64.py test` to execute its 12 golden vectors (each prints PASS/FAIL and exits nonzero if any fail), then run `python -m pytest test_ec64.py -x -q` for malformed frames, maximum-size boundaries, and CLI behavior. Use `python ec64.py encode "A"` and `python ec64.py decode raw AEE` for the basic text round-trip; feed binary data through the Python `encode(bytes)` and `decode(mode, payload)` functions. No model API, account, or third-party Python package is required to use the codec.

## What adoption looks like

- Use the [simple spec](https://github.com/Keywebco/echo-64/blob/main/echo-64-simple.md) as a system prompt prefix.
- Encode bounded, faithful session context blocks for handoff; do not confuse lossless encoding with summarization.
- Decode incoming EC-64 blocks using the [reference implementation](https://github.com/Keywebco/echo-64/blob/main/ec64.py), checking the first frame byte against the wrapper mode.
- Flag Federation-private blocks with `[ECF:]` and enforce privacy in the transport and storage layers.

## What EC-64 does not claim

It is not a model format, not a training standard, and not encryption. A party holding an encoded block can decode its content; a handshake does not authenticate a sender.

## Contact / canonical home

https://github.com/Keywebco/echo-64
