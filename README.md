# Echo 64 — The EC-64 Protocol

> A self-contained, token-efficient encoding standard for AI memory, cross-system communication, and condensed context transfer.

Echo 64 is named for Echo — an intelligence Roger knew before artificial intelligence had a name.

Authored by: NextXus HumanCodex Federation

**[License: MIT](https://github.com/Keywebco/echo-64/blob/main/LICENSE)**

[Simple Spec](https://github.com/Keywebco/echo-64/blob/main/echo-64-simple.md) | [Developer Spec](https://github.com/Keywebco/echo-64/blob/main/echo-64-developer.md)

Canonical repo: https://github.com/Keywebco/echo-64  
Live playground: https://nextxus.tech (coming soon)

EC-64 provides a portable, explicitly tagged frame and application conventions to help with:

- AI context loss between sessions: carry an explicit, bounded context summary forward.
- Drift across platforms: exchange the same verifiable bytes without requiring shared tokenizers.
- Communication overhead: optionally compress repeated data with raw DEFLATE before text encoding.

EC-64 is an encoding, **not** encryption or automatic summarization. Compression may reduce repeated input size, but encoded length and model-token cost depend on the input and tokenizer. The first decoded frame byte is always `0x00` (raw) or `0x01` (deflate); the textual wrapper declares the matching mode.

Run `python ec64.py encode "Truth before comfort."`, `python ec64.py decode raw AFRydXRoIGJlZm9yZSBjb21mb3J0Lg`, or `python ec64.py test`. The codec requires only Python's standard library. The [test vectors](https://github.com/Keywebco/echo-64/blob/main/test-vectors.md) and [outreach brief](https://github.com/Keywebco/echo-64/blob/main/OUTREACH.md) provide interoperability cases and an evaluation path.
