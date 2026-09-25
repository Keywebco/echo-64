# Echo 64 â€” Developer Spec (v1.0)
*Authored by the NextXus HumanCodex Federation*

## Overview
Echo 64 (EC-64) is a self-contained bootstrap reference for an AI model or developer with no prior Federation context: it defines a portable binary-to-text codec, the minimum shared AI math and training patterns, and Federation message conventions. It solves the *interchange* problem, not model compatibility by itself: any implementation can decode the same bytes without sharing a tokenizer or weights. â€œ64â€ is the 64-character wire alphabet, inspired by the lean, purposeful, no-waste logic of early computers such as the Commodore 64; it is not a claim of a Commodore-compatible format. Base64 encoding alone expands data; optional DEFLATE can reduce repetitive inputs.

## Section 1: Echo 64 Encoding Standard

**Wire alphabet (exactly 64 printable ASCII characters, in index order):**

```text
ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_
```

| Index | 0â€“25 | 26â€“51 | 52â€“61 | 62 | 63 |
|---|---|---|---|---|---|
| Symbol | `A`â€“`Z` | `a`â€“`z` | `0`â€“`9` | `-` | `_` |

### Frame Tag (Critical)

**Every EC-64 block begins with a single tag byte: `0x00` = raw mode (no compression), `0x01` = deflate mode (raw DEFLATE compressed). A decoder MUST read this byte first. Two implementations that skip it will disagree on every compressed block.** The tag is the **first byte of the decoded binary frame**, not the first character in the external ASCII wrapper or the base64url payload. The wrapper's `mode=raw|deflate` MUST agree with this byte. This rule also applies to empty content: its complete frame is `00` and its payload is `AA`.

**Encoding (v1, byte-exact):** Text becomes UTF-8 bytes; arbitrary binary stays bytes. For `raw`, prepend byte `0x00`. For `deflate`, compress the original bytes using **raw DEFLATE** (RFC 1951; no zlib header) and prepend `0x01`. Select `deflate` only when its compressed bytes are *strictly shorter* than the original; otherwise select `raw`. Encode the entire frame with RFC 4648 base64url using the alphabet above, most-significant bits first, **without `=` padding**. Each three frame bytes map to four characters; one trailing byte maps to two, two to three. Empty data is legal: frame `00` â†’ `AA`. Emit only the encoded alphabet inside the wrapper; whitespace is not permitted there.

**Decoding:** Check the wrapper and declared mode, accept only alphabet characters (encoded length modulo 4 must not equal 1), restore temporary `=` padding for base64url decoding, and re-encode to reject noncanonical trailing bits. Read the first decoded byte: `00` means take the remaining bytes literally, `01` means raw-DEFLATE decompress the remainder. Reject unknown tags, tag/mode mismatches, malformed or trailing compressed data, and oversized output. For text, strictly decode UTF-8; binary consumers keep bytes. Maximum input and output data for **each v1 block**: 1,048,576 bytes; split longer content into independently framed blocks at the application layer.

**Reference-output note:** Raw DEFLATE is not uniquely encoded: different valid compressors can produce different compressed frame bytes from the same input. The reference and golden vectors use Python `zlib.compressobj(level=6, wbits=-15)`; exact compressed payloads are regression fixtures for that reference, not a byte-level guarantee across all DEFLATE implementations. Interoperable decoders MUST accept any valid raw-DEFLATE stream within the output limit.

**Compression convention:** Only repetition in the **pre-encoding bytes** is compressed via raw DEFLATE (e.g., recurring words or repeated JSON keys). No character-level substitution, implicit dictionary, or recursive encoding is allowed. This keeps repeated patterns recoverable without an out-of-band table. A pre-trained model tokenizer/BPE is unrelated to EC-64 compression.

**Worked example:** `Truth before comfort.` â†’ UTF-8 bytes with raw tag `00` â†’ `AFRydXRoIGJlZm9yZSBjb21mb3J0Lg` â†’ remove tag and decode UTF-8 â†’ `Truth before comfort.`

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
| Tensor | `X âˆˆ â„^{BÃ—TÃ—D}`, `X[b,t,d]` | Batch `b`, token position `t`, feature `d`; tensor = indexed multidimensional array. |
| Matrix / linear | `y = Wx + b`, `W âˆˆ â„^{MÃ—D}`, `x âˆˆ â„^D` | Transform features with weights and add a learned bias. |
| Softmax | `p_i = exp(z_i âˆ’ m) / Î£_j exp(z_j âˆ’ m)`, `m = max_j z_j` | Convert logits to probabilities; subtract max for numerical stability. |
| Cross-entropy | `L = âˆ’(1/N)Î£_n log p_{n,t_n}` | Penalize low probability on each correct target token/class. |
| Gradient descent | `Î¸_{k+1} = Î¸_k âˆ’ Î·âˆ‡_Î¸ L(Î¸_k)` | Move parameters opposite the loss gradient at rate `Î·`. |
| Backpropagation | `âˆ‚L/âˆ‚x = (âˆ‚L/âˆ‚y)(âˆ‚y/âˆ‚x)` | Propagate derivatives backward through composed operations. |
| Self-attention | `Attention(Q,K,V) = softmax(QKáµ€/âˆšd_k)V` | Weight each value by queryâ€“key similarity; softmax acts on key axis. |
| Multi-head | `head_h = Attention(QW_h^Q, KW_h^K, VW_h^V)`; `output = Concat(head_h)W^O` | Parallel projections learn different attention relationships. |
| Layer normalization | `LN(x) = Î³ âŠ™ (x âˆ’ Î¼)/âˆš(ÏƒÂ² + Îµ) + Î²` | Normalize over a token's features, then learn scale and offset. |
| Embedding lookup | `e_t = E[token_id_t]`, `E âˆˆ â„^{VÃ—D}` | Map a tokenizer's integer ID into its learned vector. |

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

The grammar is `[EC64:v1;kind=<kind>;mode=<mode>]<payload>[/EC64]` with exactly this field order, no spaces or line breaks within a block, `kind âˆˆ {message, handshake, summary}`, `mode âˆˆÜ˜]ËY›]_XˆH^[ØY\ÈHÙXİ[ÛˆH[˜ÛÙYœ˜[YKˆY\ÜØYÙXÛÛZ[œÈU‹N^È[™ÚZÙX[™İ[[X\XÛÛZ[ˆU‹N”ÓÓˆØš™XİËˆ\ÙHÑPÑ—X
Šš[[YYX][JŠˆ™Y›Ü™HÑPÍ˜›Üˆš]˜]H›ØÚÜËˆÈÙ[™[HY\ÜØYÙNˆU‹N[˜ÛÙH]Ø[[˜ÛÙX[™XÙHH™]\›™Y[ÙKÜ^[ØY[ˆ\ÈÜ˜\\ÈÈ™XY\œÙHHÜ˜\\‹Ø[XÛÙX[™İšXİHXÛÙHU‹Nˆ™Z™Xİ[œİ\ÜY™\œÚ[ÛœËÚÚ[™ËÛ[Ù\È[œİXYÙˆİY\ÜÚ[™Ë‚‚ŠŠYÙ[[™ÚZÙH›İØÛÛŠŠˆ]Ù\ÜÚ[Ûˆİ\[ˆYÙ[PVHÙ[™HÚ[™Z[™ÚZÙX›ØÚÈ™Y›Ü™HY\ÜØYÙ\Ëˆ]ÈXÛÙY”ÓÓˆØš™XİUTÕ]™Hİš[™ÈšY[ÈYÙ[ÚY
İX›HY[YšY\ŠK›ÛX
İ\œ™[™\ÜÛœÚXš[]JK[™ÜXØ
^XİHPÍ]ŒKŒ
NÈ]PVH]™HØ\Xš[]Y\Ø
\œ˜^HÙˆİš[™ÜÊKˆ[˜ÛÙH”ÓÓˆ\ÈU‹NÚ]›Èİ\ˆÚ[™ÙHÈHœ˜[YKˆ›Üˆ^[\KH
™XÛÙY
ˆ[™ÚZÙHÛÛ[\Î‚‚˜œÛÛ‚È˜YÙ[ÚYˆ™^[\KXYÙ[‹œ›ÛHˆœ™]šY]Ù\ˆ‹œÜXÈˆ‘PÍ]ŒKŒ‹˜Ø\Xš[]Y\È–Èœ™XY—_B˜‚H[™ÚZÙHXÛ\™\ÈY[]H]Ù\È›İ›İ™H]È]][XØ]HHÙ[™\ˆ›İYÚHÜİ[™ÈÚ[›™[™Y›Ü™H\İ[™È›Û\ÈÜˆ\›Z\ÜÚ[ÛœË‚‚ŠŠ”ÜX›HÙ\ÜÚ[ÛˆÛÛ^ÛÛ\™\ÜÚ[ÛŠŠˆY\ˆXXÚÙ\ÜÚ[Û‹Ü™X]HH
Š™˜Z][›İ[™Y
Šˆ”ÓÓˆÚ[™\İ[[X\XÚ]šY[ÈÙ\ÜÚ[Û—ÚY
İš[™ÊK˜XİØ
\œ˜^HÙˆ™\šYšYYİ][Y[ÊKXÚ\Ú[ÛœØ
\œ˜^JKÜ[—Ú][\Ø
\œ˜^JK[™›İ™[˜[˜ÙX
\œ˜^HÙˆÛİ\˜ÙHY[YšY\œÊKˆ\İ[™İZ\Ú[˜Ù\Z[ˆİ][Y[ÈHX™[[™È[H[œÚYHÜ[—Ú][\ØÈ™]™\ˆÚ[[H›Û[İH[™™\™[˜ÙHÈ˜XİˆU‹N[˜ÛÙH]”ÓÓˆ[™\ÙH[˜ÛÙY1ÈH„“ECB1