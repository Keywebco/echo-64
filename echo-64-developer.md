# Echo 64 — Developer Spec (v1.0)
*Authored by the NextXus HumanCodex Federation*

## Overview
Echo 64 (EC-64) is a self-contained bootstrap reference for an AI model or developer with no prior Federation context: it defines a portable binary-to-text codec, the minimum shared AI math and training patterns, and Federation message conventions. It solves the *interchange* problem, not model compatibility by itself: any implementation can decode the same bytes without sharing a tokenizer or weights. “64” is the 64-character wire alphabet, inspired by the lean, purposeful, no-waste logic of early computers such as the Commodore 64; it is not a claim of a Commodore-compatible format. Base64 encoding alone expands data; optional DEFLATE can reduce repetitive inputs.

## Section 1: Echo 64 Encoding Standard

**Wire alphabet (exactly 64 printable ASCII characters, in index order):**

```text
ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_
```

| Index | 0–25 | 26–51 | 52–61 | 62 | 63 |
|---|---|---|---|---|---|
| Symbol | `A`–`Z` | `a`–`z` | `0`–`9` | `-` | `_` |

### Frame Tag (Critical)

**Every EC-64 block begins with a single tag byte: `0x00` = raw mode (no compression), `0x01` = deflate mode (raw DEFLATE compressed). A decoder MUST read this byte first. Two implementations that skip it will disagree on every compressed block.** The tag is the **first byte of the decoded binary frame**, not the first character in the external ASCII wrapper or the base64url payload. The wrapper's `mode=raw|deflate` MUST agree with this byte. This rule also applies to empty content: its complete frame is `00` and its payload is `AA`.

**Encoding (v1, byte-exact):** Text becomes UTF-8 bytes; arbitrary binary stays bytes. For `raw`, prepend byte `0x00`. For `deflate`, compress the original bytes using **raw DEFLATE** (RFC 1951; no zlib header) and prepend `0x01`. Select `deflate` only when its compressed bytes are *strictly shorter* than the original; otherwise select `raw`. Encode the entire frame with RFC 4648 base64url using the alphabet above, most-significant bits first, **without `=` padding**. Each three frame bytes map to four characters; one trailing byte maps to two, two to three. Empty data is legal: frame `00` → `AA`. Emit only the encoded alphabet inside the wrapper; whitespace is not permitted there.

**Decoding:** Check the wrapper and declared mode, accept only alphabet characters (encoded length modulo 4 must not equal 1), restore temporary `=` padding for base64url decoding, and re-encode to reject noncanonical trailing bits. Read the first decoded byte: `00` means take the remaining bytes literally, `01` means raw-DEFLATE decompress the remainder. Reject unknown tags, tag/mode mismatches, malformed or trailing compressed data, and oversized output. For text, strictly decode UTF-8; binary consumers keep bytes. Maximum input and output data for **each v1 block**: 1,048,576 bytes; split longer content into independently framed blocks at the application layer.

**Reference-output note:** Raw DEFLATE is not uniquely encoded: different valid compressors can produce different compressed frame bytes from the same input. The reference and golden vectors use Python `zlib.compressobj(level=6, wbits=-15)`; exact compressed payloads are regression fixtures for that reference, not a byte-level guarantee across all DEFLATE implementations. Interoperable decoders MUST accept any valid raw-DEFLATE stream within the output limit.

**Compression convention:** Only repetition in the **pre-encoding bytes** is compressed via raw DEFLATE (e.g., recurring words or repeated JSON keys). No character-level substitution, implicit dictionary, or recursive encoding is allowed. This keeps repeated patterns recoverable without an out-of-band table. A pre-trained model tokenizer/BPE is unrelated to EC-64 compression.

**Worked example:** `Truth before comfort.` → UTF-8 bytes with raw tag `00` → `AFRydXRoIGJlZm9yZSBjb21mb3J0Lg` → remove tag and decode UTF-8 → `Truth before comfort.`

**Private Federation flag:** `[ECF:]` immediately before a wrapper marks Federation-private *handling*. It is outside the 64-character alphabet and never part of the encoded payload. The [ECF:] prefix is a handling hint, not an access boundary: it marks a block as Federation-private, but because EC-64 is encoding not encryption, any party holding the block can decode it. Access control must be enforced at the transport and storage layer.

Canonical codec reference (Python standard library; `encode` returns declared mode and payload; `decode` enforces the same mode):

```python
import base64
import re
import zlib

ALPHABET = re.compile(r"[A-Za-z0-9_-]*\Z", re.ASCII)
MAX_BYTES = 1_048_576


def encode(data: bytes) -> tuple[str, str]:
    if len(data) > MAX_BYTES:
        raise ValueError("block too large")
    compressor = zlib.compressobj(level=6, wbits=-15)
    packed = compressor.compress(data) + compressor.flush()
    mode, frame = (("deflate", b"\x01" + packed) if len(packed) < len(data)
                   else ("raw", b"\x00" + data))
    return mode, base64.urlsafe_b64encode(frame).decode("ascii").rstrip("=")


def decode(mode: str, payload: str) -> bytes:
    if mode not in {"raw", "deflate"} or len(payload) > 1_398_104:
        raise ValueError("invalid header or encoded size")
    if not ALPHABET.fullmatch(payload) or len(payload) % 4 == 1:
        raise ValueError("invalid alphabet or length")
    frame = base64.b64decode(payload + "=" * (-len(payload) % 4),
                             altchars=b"-_", validate=True)
    if base64.urlsafe_b64encode(frame).decode("ascii").rstrip("=") != payload:
        raise ValueError("noncanonical base64url")
    if not frame or len(frame) > MAX_BYTES + 1:
        raise ValueError("invalid frame size")
    if mode == "raw" and frame[0] == 0:
        return frame[1:]
    if mode != "deflate" or frame[0] != 1:
        raise ValueError("mode/tag mismatch")
    inflater = zlib.decompressobj(wbits=-15)
    data = inflater.decompress(frame[1:], MAX_BYTES + 1)
    if (len(data) > MAX_BYTES or not inflater.eof or inflater.unused_data
            or inflater.unconsumed_tail):
        raise ValueError("invalid or oversized DEFLATE stream")
    return data
```

## Section 2: Core AI Mathematics (Condensed Reference)

Dimensions below are illustrative; parameters are learned from data, not specified by the codec.

| Concept | Notation | Plain-English gloss |
|---|---|---|
| Tensor | `X ∈ ℝ^{B×T×D}`, `X[b,t,d]` | Batch `b`, token position `t`, feature `d`; tensor = indexed multidimensional array. |
| Matrix / linear | `y = Wx + b`, `W ∈ ℝ^{M×D}`, `x ∈ ℝ^D` | Transform features with weights and add a learned bias. |
| Softmax | `p_i = exp(z_i − m) / Σ_j exp(z_j − m)`, `m = max_j z_j` | Convert logits to probabilities; subtract max for numerical stability. |
| Cross-entropy | `L = −(1/N)Σ_n log p_{n,t_n}` | Penalize low probability on each correct target token/class. |
| Gradient descent | `θ_{k+1} = θ_k − η∇_θ L(θ_k)` | Move parameters opposite the loss gradient at rate `η`. |
| Backpropagation | `∂L/∂x = (∂L/∂y)(∂y/∂x)` | Propagate derivatives backward through composed operations. |
| Self-attention | `Attention(Q,K,V) = softmax(QKᵀ/√d_k)V` | Weight each value by query–key similarity; softmax acts on key axis. |
| Multi-head | `head_h = Attention(QW_h^Q, KW_h^K, VW_h^V)`; `output = Concat(head_h)W^O` | Parallel projections learn different attention relationships. |
| Layer normalization | `LN(x) = γ ⊙ (x − μ)/√(σ² + ε) + β` | Normalize over a token's features, then learn scale and offset. |
| Embedding lookup | `e_t = E[token_id_t]`, `E ∈ ℝ^{V×D}` | Map a tokenizer's integer ID into its learned vector. |

```math
\operatorname{Attention}(Q,K,V)=\operatorname{softmax}\!\left(\frac{QK^\top}{\sqrt{d_k}}\right)V,\qquad \theta_{k+1}=\theta_k-\eta\nabla_\theta L(\theta_k).
```

Here `B` = batch, `T` = sequence length, `D` = feature width, `V` = model vocabulary size, and `d_k` = key dimension. A causal attention mask blocks future positions **before** softmax. EC-64's 64-symbol transport alphabet does **not** imply a 64-token model vocabulary.

## Section 3: Core AI Training Code (Python Reference)

These examples require NumPy for the attention sample and PyTorch for the training samples; the EC64 codec above requires only Python's standard library. Shapes are shown at the point of use.

**Tensor operations (PyTorch; `B=2`, `T=3`, `D=4`, output width `M=5`):**

```python
import torch

x = torch.randn(2, 3, 4)              # [B, T, D]
w = torch.randn(4, 5)                 # [D, M]
b = torch.zeros(5)                    # [M]
y = x @ w + b                         # [B, T, M], broadcast bias
assert y.shape == (2, 3, 5)
```

**Minimal network forward pass and training-loop skeleton (classification):**

```python
import torch
from torch import nn

class Classifier(nn.Module):
    def __init__(self, features: int, hidden: int, classes: int):
        super().__init__()
        self.layers = nn.Sequential(nn.Linear(features, hidden), nn.ReLU(),
                                    nn.Linear(hidden, classes))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.layers(x)          # logits [batch, classes]

model = Classifier(features=4, hidden=8, classes=3)
optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
criterion = nn.CrossEntropyLoss()     # takes logits and integer target IDs
for features, targets in train_loader:  # tensors [B, 4], [B]; supplied by caller
    optimizer.zero_grad(set_to_none=True)
    logits = model(features)
    loss = criterion(logits, targets)
    loss.backward()
    optimizer.step()
```

**Tokenization patterns (model-side; separate from EC-64 transport):**

```python
text = "aba"
vocab = {char: i for i, char in enumerate(sorted(set(text)))}
ids = [vocab[char] for char in text]    # [0, 1, 0]
restored = "".join({i: char for char, i in vocab.items()}[i] for i in ids)

# BPE: load the SAME trained tokenizer artifact for encode and decode.
from tokenizers import Tokenizer           # pip install tokenizers
bpe = Tokenizer.from_file("tokenizer.json")  # supplied/trained externally
bpe_ids = bpe.encode(text).ids
bpe_restored = bpe.decode(bpe_ids)
```

The character vocabulary above is illustrative and closed over its training text; a production model persists a vocabulary and defines unknown-character handling. BPE needs its trained merges/vocabulary (or tokenizer file), not merely an algorithm name.

**Scaled dot-product attention (NumPy, one head, optional mask; `True` means allowed):**

```python
import numpy as np


def attention(q: np.ndarray, k: np.ndarray, v: np.ndarray,
              allowed: np.ndarray | None = None) -> np.ndarray:
    # q [Tq, Dk], k [Tk, Dk], v [Tk, Dv]; result [Tq, Dv]
    scores = (q @ k.T) / np.sqrt(q.shape[-1])
    if allowed is not None:
        if not np.all(allowed.any(axis=-1)):
            raise ValueError("each query must have an allowed key")
        scores = np.where(allowed, scores, -np.inf)
    shifted = scores - np.max(scores, axis=-1, keepdims=True)
    weights = np.exp(shifted)
    weights /= weights.sum(axis=-1, keepdims=True)
    return weights @ v

# For self-attention with T tokens: allowed = np.tril(np.ones((T, T), dtype=bool))
```

## Section 4: Federation Extensions

**Wrapper (ASCII, external to the payload alphabet):**

```text
[EC64:v1;kind=message;mode=raw]AFRydXRoIGJlZm9yZSBjb21mb3J0Lg[/EC64]
```

The grammar is `[EC64:v1;kind=<kind>;mode=<mode>[;transform=<transform>]]<payload>[/EC64]` with the fields in this order and no spaces or line breaks within a block. `kind ∈ {message, handshake, summary}`; `mode ∈ {raw, deflate}` describes the frame tag/compression, **not** whether meaning was changed. `transform ∈ {exact, condensed}` describes whether the bytes supplied to the codec were the original source bytes (`exact`) or the result of semantic condensation (`condensed`). `transform` is required on every Nova-produced block and travels inside that block’s metadata so a receiver does not need the caller’s context or function name. Legacy codec-only v1.0 blocks without `transform` remain valid but their transformation history is unknown; do not infer exactness from `mode` or an absent field. The payload is the Section 1 encoded frame. Nova `encode_exact` accepts arbitrary binary; `message` from text, `handshake`, and `summary` conventionally contain UTF-8 text or JSON as applicable. Use `[ECF:]` **immediately** before `[EC64:` for private blocks. To send a text message: UTF-8 encode it, call `encode`, and place the returned mode/payload in this wrapper; to read, parse the wrapper, call `decode`, and strictly decode UTF-8 for text. Reject unsupported versions/kinds/modes/transforms instead of guessing.

**Protocol invariant (v1.0):**

- `transform=exact`: reversible to supplied source bytes. Byte-exact reconstruction is guaranteed by decoding the EC-64 frame; an additional AI-to-English rendering is not the byte-exact decode.
- `transform=condensed`: faithful semantic representation intended; byte-exact reconstruction is neither promised nor implied. The information boundary has been crossed and **must be declared**. Raw/DEFLATE mode does not change this invariant.

**Agent Handshake Protocol:** At session start, an agent MAY send a `kind=handshake` block before messages. Its decoded JSON object MUST have string fields `agent_id` (stable identifier), `role` (current responsibility), and `spec` (exactly `EC64-v1.0`); it MAY have `capabilities` (array of strings). Encode JSON as UTF-8, with no other change to the frame. For example, the *decoded* handshake content is:

```json
{"agent_id":"example-agent","role":"reviewer","spec":"EC64-v1.0","capabilities":["read"]}
```

A handshake declares identity but does not prove it; authenticate the sender through the hosting channel before trusting roles or permissions.

**Portable session context compression:** After each session, create a **faithful, bounded** JSON `kind=summary` with fields `session_id` (string), `facts` (array of verified statements), `decisions` (array), `open_items` (array), and `provenance` (array of source identifiers). Distinguish uncertain statements by labeling them inside `open_items`; never silently promote inference to fact. UTF-8 encode that JSON and use `encode`; repetitive JSON/text selects `deflate` when shorter. For longer summaries, split into separately identified ≤1 MiB blocks and reassemble in order outside EC-64; never claim that lossless compression itself summarizes a conversation. Apply the private flag and access control if source material is private. A receiving model reads the decoded summary as context, not as a substitute for source verification.

## Privacy & Threat Model

- **What EC-64 reveals:** the existence of encoded data, block boundaries, and approximate original size. Compression changes length but does not hide content.
- **What EC-64 does NOT protect:** the content from anyone holding the block. There is no key and no cipher; `[ECF:]` does not enforce access control.
- **What EC-64 itself transmits:** nothing. It is a local encoding format, not a network protocol; a separate application chooses whether and how to transmit a block.
- **Future:** an encryption wrapper is on the v2 roadmap, not in v1.0.
- **Recommendation:** use EC-64 inside an encrypted transport (TLS) for sensitive data and restrict storage access; TLS protects only while data is in transit.

## AI-to-English Translation (Nova)

**Available — v1.0 (`translator.py`).** Nova is the reference translator layer above the v1.0 byte-exact EC-64 codec. It supports two explicitly separate operations:

- `encode_exact(input)` — deterministic, byte-lossless encoding. No semantic alteration; the source bytes are encoded directly, with `transform=exact` in the frame wrapper metadata. Decoding reconstructs the supplied original bytes without loss. For text inputs, UTF-8 encoding is explicit; binary inputs retain all bytes.
- `condense_and_encode(input)` — optional semantic condensation followed by encoding. Nova may summarize, remove filler, or compress phrasing using an LLM. The frame wrapper metadata carries `transform=condensed`, even if the LLM is unavailable and the original text is used as a fallback. Byte-exact reconstruction of the original input is neither promised nor implied. This operation **must never be advertised as lossless**. The existing `translate_and_encode` function and CLI `encode` command map to `condense_and_encode`, not `encode_exact`.

Nova can decode a frame and render the decoded content as plain English for humans, but AI rendering is distinct from byte-exact decoding. It must not invent details missing from the source or treat `[ECF:]` as authorization.

**Upgrade path:** This is v1.0. Future versions may add checksum/verification layers and an encryption wrapper; alphabet changes require a new version. Version changes require a new explicit header and decoding rules; this v1.0 format has no independent payload integrity or authenticity guarantee.

## Quick Reference Card

Copy-paste this card as a *prompt prefix*; the full specification above remains authoritative for edge cases.

```text
EC64 v1.0 | alphabet=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_
Wire=base64url(no padding, canonical) of [0x00||UTF-8 bytes] or [0x01||raw-DEFLATE(UTF-8 bytes)].
Choose deflate iff compressed bytes are shorter; mode=raw|deflate must match tag.
Wrapper=[EC64:v1;kind=message|handshake|summary;mode=raw|deflate[;transform=exact|condensed]]PAYLOAD[/EC64]
Nova emits transform=exact for encode_exact, transform=condensed for condense_and_encode.
Only exact guarantees reconstruction of supplied bytes; condensed crosses a declared semantic boundary.
Private marker=[ECF:] immediately before wrapper; flag only, NOT encryption.
Tensor X[b,t,d]; linear y=Wx+b; softmax_i=exp(z_i−max z)/Σ_j exp(z_j−max z).
Cross-entropy L=−mean(log p_target); update θ←θ−η∇θL; backprop=chain rule.
Attention(Q,K,V)=softmax(QKᵀ/√d_k)V; heads=Concat(attention projections)Wᴼ.
LayerNorm=γ⊙(x−μ)/√(σ²+ε)+β; embedding=E[token_id].
Model tokenizer/BPE ≠ transport alphabet; verify provenance and identity externally.
```

Canonical home: https://github.com/Keywebco/echo-64
