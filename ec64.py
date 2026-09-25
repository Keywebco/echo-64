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
    return b"".join(hashlib.sha256(b"EC64-v1-random:" + i.to_bytes(4, "big")).digest()
                    for i in range(32))


def already_compressed_block() -> bytes:
    """A raw DEFLATE stream, presented as ordinary binary input to encode."""
    compressor = zlib.compressobj(level=6, wbits=-15)
    data = b"Truth before comfort." * 8
    return compressor.compress(data) + compressor.flush()


# Expected payloads are fixed golden outputs, not computed by encode at test time.
# The final boolean says whether the application wrapper uses the external [ECF:] flag.
TEST_VECTORS: tuple[tuple[str, bytes, str, str, bool], ...] = (
    ('Empty input', b'', 'raw', 'AA', False),
    ('Single ASCII byte', b'A', 'raw', 'AEE', False),
    ('Short ASCII sentence', b'Truth before comfort.', 'raw', 'AFRydXRoIGJlZm9yZSBjb21mb3J0Lg', False),
    ('Unicode sentence', b'AI remembers. \xe8\xae\xb0\xe5\xbf\x86 \xe5\xad\x98\xe5\x9c\xa8.', 'raw', 'AEFJIHJlbWVtYmVycy4g6K6w5b-GIOWtmOWcqC4', False),
    ('Already-compressed data', already_compressed_block(), 'raw', 'AAspKi3JUEhKTcsvSlVIzs8F0iV6IYNPEAA', False),
    ("Repeated pattern (32 A's)", b'A' * 32, 'deflate', 'AXN0xA8A', False),
    ('All 256 byte values', bytes(range(256)), 'raw', (
        'AAABAgMEBQYHCAkKCwwNDg8QERITFBUWFxgZGhscHR4fICEiIyQlJicoKSorLC0uLzAxMjM0NTY3ODk6Ozw9P'
        'j9AQUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVpbXF1eX2BhYmNkZWZnaGlqa2xtbm9wcXJzdHV2d3h5ent8fX'
        '5_gIGCg4SFhoeIiYqLjI2Oj5CRkpOUlZaXmJmam5ydnp-goaKjpKWmp6ipqqusra6vsLGys7S1tre4ubq7vL2'
        '-v8DBwsPExcbHyMnKy8zNzs_Q0dLT1NXW19jZ2tvc3d7f4OHi4-Tl5ufo6err7O3u7_Dx8vP09fb3-Pn6-_z9'
        '_v8'
    ), False),
    ('Deterministic 1 KiB random-looking data', random_looking_block(), 'raw', (
        'ANKiszMe1s4Exzr9rzo55ZH5WqwQMq5KKYbx3DB5L7M66Zxv-z3DBk7u06hyGQhpVSJThesNwOx22IsLiS3bf'
        'DSIgHqB7BmksvKPhqEgWN0YzgUSQSSLu59mb15KWK0B-2BsvbykiJQZFogYN9iTE5PMWaT4sK0bnXcrTBUp_O'
        'jHYR1XWiHZY-9P-Zl52-Skgzm5_-Z6xymE-G8HdFQVNZUFbtQAXbkUa7jpPWCNDLkiwTdOZ3q_N_OkKfSaAO0'
        'kynSLoRHh7L0dVJnIZbuTJlb5xTjdsW_Q8XhNZythAOzFmRDvobtqddgyKm9jBv9UA6ddA2sM9ZJvHX2xZvUS'
        'S4b5AQ1uV_FowvwxbU4zn6t9DgJFVduLGWpY2CiNGhwApFbv2BN25WTa-4VK8Z22b7W_5VZ7Nati3Lu9nVMDK'
        'I7nU7-HVKGUh3idHcecSSi0lJ43TXF7JcgnsRkioAq6IbYp3RF-n8dn-u1KiIsVKnw1S_3JBm95iiiZJvrQgN'
        'URIcvPObiivuaco8GcyixRRfmTOM4XoXCVPGE_VfrY4Z4tTLSftLFXnM8PCCFV84nFQlQpW-88WxYnq1Jg08s'
        'XHPvNlMNXWLPzAuzA4Dn8z5oSljz0h_SmG09YWhzHX4ASPUzk3zIJ9rzYTE03nTRVAHNxzuPvza20X2MDt5TD'
        'csELvN0kIwfJriNHa2wbcxQEi7yrFqww-6-CpWNo5KBWeMNWB7ofF8G5IT4d_xC7-apa5-qKOGF0fsr83CLDr'
        'Z5u1lymafdJx9WFtIk9qvnKlfZrPau-qorP-fPfnSIB7n79IvX-5qd2osXWuEGFT4Yemzaz8azXbXDgmfbHO5'
        'OOuA16mDClGCpxi1uN7Cgkl0cl4-fL0DAxTrKbPbrUs_wvE0BQ45fTDw4ySHIoD1L6LYrUi8r6Ym3sCLPdfIN'
        'umYTYwJPA_LGAckJjIjYEpfgLLUiBZg6PWjuRbxP9hXHwyPWoZbg0qVmcxu8WnDd8rcx21AsxUg8c8pLnkmbm'
        '1knja--YehsZ6--b4hVYqRmbhnRrSH9DvhvEFECu5gQEj0aoYb9BGjAVlIU1WzU8tuwgZeNTpmq0jnyYOiu4v'
        '_iHJ2Fnp541x_uCXV7o3fb3XuUKI-GnQR_PMpa3wh6RSUqCAH-6uF9DU5ca4LSMiLVgQ2CIlobrR3SrUPGAGU'
        'rThyyrCjiQ1eLYCKxnQY0jQM7AMxQGiCicpsaTzxbY3_MGGJ_EWB6YmoquuAHyTN3TkXKRUCZ2AhbKKGmdIj2'
        'jKvP8u7Q_yyYYHV66c_TGiC80Tpx6zCgjmfBNUR9UHtIgmqU1cOIEQaVfttBD7pzC1gmgVF21iHDMP8dLJd8f'
        'e4EDjDE'
    ), False),
    ('Already-prefixed [ECF:] wrapper', b'A', 'raw', 'AEE', True),
    ('Embedded null bytes', b'alpha\x00beta\x00gamma', 'raw', 'AGFscGhhAGJldGEAZ2FtbWE', False),
    ('Exactly 1 MiB (maximum)', b'A' * MAX_BYTES, 'deflate', (
        'Ae3BMQEAAADCoGzrX8oQvkABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
        'AAAAAAAAAAAAAAAAAHwG'
    ), False),
    ('Compression would expand', b'\xff\x00\xfe', 'raw', 'AP8A_g', False),
)

def test_vectors() -> bool:
    """Print PASS/FAIL for each golden vector; return True only when all pass."""
    passed = True
    for number, (name, data, expected_mode, expected_payload, private) in enumerate(
            TEST_VECTORS, 1):
        try:
            mode, payload = encode(data)
            wrapped = ("[ECF:]" if private else "") + (
                f"[EC64:v1;kind=message;mode={mode}]{payload}[/EC64]")
            prefix_ok = wrapped.startswith("[ECF:]") == private
            decoded = decode(mode, payload)
            ok = (mode, payload) == (expected_mode, expected_payload)
            ok = ok and decoded == data and prefix_ok
        except (ValueError, zlib.error) as exc:
            ok = False
            print(f"FAIL {number:02d}: {name}: {exc}")
        else:
            print(f"{'PASS' if ok else 'FAIL'} {number:02d}: {name}")
        passed &= ok
    return passed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("test", help="run the 12 golden test vectors")
    encode_parser = commands.add_parser("encode", help="encode a UTF-8 string")
    encode_parser.add_argument("text", help="text to encode")
    decode_parser = commands.add_parser("decode", help="decode to UTF-8 text")
    decode_parser.add_argument("mode", choices=("raw", "deflate"))
    decode_parser.add_argument("payload", help="frame payload without wrapper")
    args = parser.parse_args(argv)
    try:
        if args.command == "test":
            return 0 if test_vectors() else 1
        if args.command == "encode":
            mode, payload = encode(args.text.encode("utf-8"))
            print(f"mode={mode}\npayload={payload}")
        else:
            print(decode(args.mode, args.payload).decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        parser.exit(2, f"error: {exc}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
