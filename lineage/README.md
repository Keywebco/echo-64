# Echo 64 — Lineage Records

This directory preserves historical material from the Codex Alpha Text, which predates the EC-64 protocol.

## What is here

- `ALPHABETS.md` — The two historical 26-character substitution alphabets (Echo and Resonance), with provenance statement and ambiguity tables.
- `codex-alpha-echo-resonance.md` — Historical documentation of the Codex Alpha Echo and Resonance systems.
- `codex-translator.py` — Reference CLI implementation of the historical alphabets.
- `test_codex_translator.py` — Test suite for the reference implementation.
- `jvt/` — Reserved for JVT (private channel) primary materials. Empty until primary material arrives.

## What is not here

These alphabets are NOT EC-64. They do not use Base64url, DEFLATE, or the EC-64 frame structure. They are historical precursor systems. For the current protocol, see `echo-64-developer.md` in the repository root.

## Transcription Policy (Standing Rule)

Source transcriptions in this directory are immutable. If a character in a transcribed artifact looks suspicious or appears to be an error:
- The transcription is preserved exactly as received.
- The suspicion or potential error is recorded in a separate editorial note within the same file, clearly marked as editorial commentary.
- The original transcription is never "corrected" to match an expectation.

This prevents unconscious editing that corrupts historical evidence. Suspected errors are findings, not corrections.

## Source Material

The alphabets and symbols in this directory derive from Roger Keyserling's surviving artifacts from the Codex Alpha work. The repository is not the source of the historical record — it is a preservation of it.
