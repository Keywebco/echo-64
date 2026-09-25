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
    # The mode is determined by byte length B