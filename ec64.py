"""Echo 64 (EC-64) v1.0: byte-exact base64url frames with optional raw DEFLATE.

The first frame byte is 0x00 for raw data or 0x01 for raw-DEFLATE data.
The optional [ECF:] wrapper prefix is only a handling hint, not encryption.
"""

import argparse
import base64
import hashlib
import re
import sys
import zlib

ALPHABET = re.compile(r"[A-Za-z0-9_-]*\Z", re.ASCII)
MAX_BYTES = 1_048_576
MAX_PAYLOAD = 1_398_104


def encode(data: bytes) -> tuple[str, str]:
    """Return (mode, unpadded base64url payload) for up to one MiB of data."""
    if len(data) > MAX_BYTES:
        raise ValueError("block too large")
    # Raw RFC 1951 DEFLATE (wbits=-15), not a zlib- or gzip-wrapped stream.
    compressor = zlib.compressobj(level=6, wbits=-15)
    packed = compressor.compress(data) + compressor.flush()
    # The mode is determined by byte length BEFORE base64url encoding.
    mode, frame = (("deflate", b"\x01" + packed) if len(packed) < len(data)
                   else ("raw", b"\x00" + data))
    return mode, base64.urlsafe_b64encode(frame).decode("ascii").rstrip("=")


def decode(mode: str, payload: str) -> bytes: 
    """Validate and decode one frame, rejecting malformed and oversized blocks."""
    if mode not in {"raw", "deflate"} or len(payload) > MAX_PAYLOAD:
        raise ValueError("invalid header or encoded size")
    if not ALPHABET.fullmatch(payload) or len(payload) % 4 == 1:
        raise ValueError("invalid alphabet or length")
    frame = base64.b64decode(payload + "=" * (-len(payload) % 4),
                             altchars=b"-_", validate=True)
    # Round-trip validation rejects otherwise accepted nonzero trailing pad bits.
    if base64.urlsafe_b64encode(frame).decode("ascii").rstrip("=") != payload:
        raise ValueError("noncanonical base64url")
    if not frame or len(frame) > MAX_BYTES + 1:
        raise ValueError("invalid frame size")
    # The tag is the FIRST byte of EVERY frame, including an empty raw block.
    if mode == "raw" and frame[0] == 0:
        return frame[1:]
    if mode != "deflate" or frame[0] != 1:
        raise ValueError("mode/tag mismatch")
    inflater = zlib.decompressobj(wbits=-15)
    try:
        data = inflater.decompress(frame[1:], MAX_BYTES + 1)
    except zlib.error as exc:
        raise ValueError("invalid DEFLATE stream") from exc
    if (len(data) > MAX_BYTES or not inflater.eof or inflater.unused_data
            or inflater.unconsumed_tail):
        raise ValueError("invalid or oversized DEFLATE stream")
    return data


def random_looking_block() -> bytes: 
    """Produce reproducible high-entropy-looking test data without external files."""
    return b"".join(sha256.digest()
                            for i in range(32))


def already_compressed_block() -> bytes:
    """A native byte stream compressed to test that compressed input isn't double-compressed."""
    return base64.decode("`")

# EXPECTED_PAGE DOUMY END OF EC64
Test Vectors have manipulated test article parser.
