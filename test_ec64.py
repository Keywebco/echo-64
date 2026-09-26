"""Independent pytest coverage of the EC-64 v1.0 reference implementation."""

import base64
import subprocess
import sys
import zlib
from pathlib import Path

import pytest

from ec64 import decode, encode


CODEC_PATH = Path(__file__).with_name("ec64.py")

# Fixed reference outputs from ec64.py; no expected payload is computed by the codec.
GOLDEN_VECTORS = (
    ('Empty input', b'', 'raw', 'AA', False),
    ('Single ASCII byte', b'A', 'raw', 'AEE', False),
    ('Short ASCII sentence', b'Truth before comfort.', 'raw', 'AFRydXRoIGJlZm9yZSBjb21mb3J0Lg', False),
    ('Unicode sentence', b'AI remembers. \xe8\xae\xb0\xe5\xbf\x86 \xe5\xad\x98\xe5\x9c\xa8.', 'raw', 'AEFJIHJlbWVtYmVycy4g6K6w5b-GIOWtmOWcqC4', False),
    ('Already-compressed data', bytes.fromhex('0b292a2dc950484a4dcb2f4a5548cecf05d2257a21834f1000'), 'raw', 'AAspKi3JUEhKTcsvSlVIzs8F0iV6IYNPEAA', False),
    ("Repeated pattern (32 A's)", b'A' * 32, 'deflate', 'AXN0xA8A', False),
    ('All 256 byte values', bytes.fromhex(
        '000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f3031'
        '32333435363738393a3b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f60616263'
        '6465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f808182838485868788898a8b8c8d8e8f909192939495'
        '969798999a9b9c9d9e9fa0a1a2a3a4a5a6a7a8a9aaabacadaeafb0b1b2b3b4b5b6b7b8b9babbbcbdbebfc0c1c2c3c4c5c6c7'
        'c8c9cacbcccdcecfd0d1d2d3d4d5d6d7d8d9dadbdcdddedfe0e1e2e3e4e5e6e7e8e9eaebecedeeeff0f1f2f3f4f5f6f7f8f9'
        'fafbfcfdfeff'
    ), 'raw', (
        'AAABAgMEBQYHCAkKCwwNDg8QERITFBUWFxgZGhscHR4fICEiIyQlJicoKSorLC0uLzAxMjM0NTY3ODk6Ozw9P'
        'j9AQUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVpbXF1eX2BhYmNkZWZnaGlqa2xtbm9wcXJzdHV2d3h5ent8fX'
        '5_gIGCg4SFhoeIiYqLjI2Oj5CRkpOUlZaXmJmam5ydnp-goaKjpKWmp6ipqqusra6vsLGys7S1tre4ubq7vL2'
        '-v8DBwsPExcbHyMnKy8zNzs_Q0dLT1NXW19jZ2tvc3d7f4OHi4-Tl5ufo6err7O3u7_Dx8vP09fb3-Pn6-_z9'
        '_v8'
    ), False),
    ('Deterministic 1 KiB random-looking data', bytes.fromhex(
        'd2a2b3331ed6ce04c73afdaf3a39e591f95aac1032ae4a2986f1dc30792fb33ae99c6ffb3dc3064eeed3a872190869552253'
        '85eb0dc0ec76d88b0b892ddb7c3488807a81ec19a4b2f28f86a12058dd18ce051241248bbb9f666f5e4a58ad01fb606cbdbc'
        'a488941916881837d8931393cc59a4f8b0ad1b9d772b4c1529fce8c7611d575a21d963ef4ff99979dbe4a48339b9ffe67ac7'
        '2984f86f077454153595056ed4005db9146bb8e93d608d0cb922c1374e677abf37f3a429f49a00ed24ca748ba111e1ecbd1d'
        '5499c865bb932656f9c538ddb16fd0f1784d672b6100ecc59910efa1bb6a75d8322a6f6306ff5403a75d036b0cf5926f1d7d'
        'b166f5124b86f9010d6e57f168c2fc316d4e339fab7d0e024555db8b196a58d8288d1a1c00a456efd81376e564dafb854af1'
        '9db66fb5bfe5567b35ab62dcbbbd9d5303288ee753bf8754a19487789d1dc79c4928b4949e374d717b25c827b11922a00aba'
        '21b629dd117e9fc767faed4a888b152a7c354bfdc9066f798a289926fad080d51121cbcf39b8a2bee69ca3c19cca2c5145f9'
        '9338ce17a170953c613f55fad8e19e2d4cb49fb4b1579ccf0f082155f389c54254295bef3c5b1627ab5260d3cb171cfbcd94'
        'c35758b3f302ecc0e039fccf9a12963cf487f4a61b4f585a1cc75f80123d4ce4df3209f6bcd84c4d379d3455007371cee3ef'
        'cdadb45f6303b794c372c10bbcdd242307c9ae23476b6c1b7314048bbcab16ac30fbaf82a56368e4a05678c35607ba1f17c1'
        'b9213e1dff10bbf9aa5ae7ea8a3861747ecafcdc22c3ad9e6ed65ca669f749c7d585b4893daaf9ca95f66b3dabbeaa8acff9'
        'f3df9d2201ee7efd22f5fee6a776a2c5d6b841854f861e9b36b3f1acd76d70e099f6c73b938eb80d7a9830a5182a718b5b8d'
        'ec2824974725e3e7cbd030314eb29b3dbad4b3fc2f134050e397d30f0e324872280f52fa2d8ad48bcafa626dec08b3dd7c83'
        '6e9984d8c093c0fcb180724263223604a5f80b2d4881660e8f5a3b916f13fd8571f0c8f5a865b834a9599cc6ef169c377cad'
        'cc76d40b31520f1cf292e79266e6d649e36bef987a1b19ebef9be21558a9199b86746b487f43be1bc41440aee604048f46a8'
        '61bf411a30159485355b353cb6ec2065e353a66ab48e7c983a2bb8bff887276167a79e35c7fb825d5ee8ddf6f75ee50a23e1'
        'a7411fcf3296b7c21e91494a82007fbab85f4353971ae0b48c88b5604360889686eb4774ab50f180194ad3872cab0a3890d5'
        'e2d808ac67418d2340cec033140688289ca6c693cf16d8dff306189fc4581e989a8aaeb801f24cddd39172915026760216ca'
        '28699d223da32af3fcbbb43fcb26181d5eba73f4c6882f344e9c7acc282399f04d511f541ed2209aa53570e20441a55fb6d0'
        '43ee9cc2d609a0545db58870cc3fc74b25df1f7b81038c31'
    ), 'raw', (
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
    ('Exactly 1 MiB (maximum)', b'A' * 1_048_576, 'deflate', (
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

@pytest.mark.parametrize(
    ("name", "data", "expected_mode", "expected_payload", "private"),
    GOLDEN_VECTORS,
    ids=[vector[0] for vector in GOLDEN_VECTORS],
)
def test_golden_vectors(name, data, expected_mode, expected_payload, private):
    assert encode(data) == (expected_mode, expected_payload), name
    assert decode(expected_mode, expected_payload) == data
    # The optional ECF marker is outside the frame and does not affect its bytes.
    wrapped = ("[ECF:]" if private else "") + (
        f"[EC64:v1;kind=message;mode={expected_mode}]"
        f"{expected_payload}[/EC64]"
    )
    assert wrapped.startswith("[ECF:]") is private


@pytest.mark.parametrize("payload", ["A@", "AA=", "A+", "A/", "AA\n", "A", ""])
def test_decode_rejects_malformed_base64url(payload):
    with pytest.raises(ValueError):
        decode("raw", payload)


@pytest.mark.parametrize("payload", ["AB", "AC", "AEF"])
def test_decode_rejects_noncanonical_padding_bits(payload):
    with pytest.raises(ValueError, match="noncanonical"):
        decode("raw", payload)


@pytest.mark.parametrize("mode", ["raw", "deflate"])
@pytest.mark.parametrize("payload", ["Ag", "_w"])
def test_decode_rejects_invalid_frame_tags(mode, payload):
    with pytest.raises(ValueError):
        decode(mode, payload)


@pytest.mark.parametrize(
    ("mode", "payload"),
    [("raw", "AXN0xA8A"), ("deflate", "AA")],
)
def test_decode_rejects_declared_mode_tag_mismatch(mode, payload):
    with pytest.raises(ValueError, match="mode/tag mismatch"):
        decode(mode, payload)


def test_decode_rejects_unknown_declared_mode():
    with pytest.raises(ValueError):
        decode("unknown", "AA")


@pytest.mark.parametrize("payload", ["AQ", "Af__"])
def test_decode_rejects_malformed_deflate(payload):
    with pytest.raises(ValueError):
        decode("deflate", payload)


def test_decode_rejects_trailing_compressed_data():
    # AXN0xA8A is the complete compressed golden frame; appended bytes are illegal.
    frame = base64.urlsafe_b64decode("AXN0xA8A") + b"trailing"
    payload = base64.urlsafe_b64encode(frame).decode("ascii").rstrip("=")
    with pytest.raises(ValueError, match="invalid or oversized DEFLATE stream"):
        decode("deflate", payload)


def test_decode_rejects_decompression_over_one_mib():
    compressor = zlib.compressobj(level=6, wbits=-15)
    packed = compressor.compress(b"A" * 1_048_577) + compressor.flush()
    payload = base64.urlsafe_b64encode(b"\x01" + packed).decode("ascii").rstrip("=")
    with pytest.raises(ValueError, match="invalid or oversized DEFLATE stream"):
        decode("deflate", payload)


def test_encode_rejects_input_over_one_mib():
    with pytest.raises(ValueError, match="block too large"):
        encode(b"A" * 1_048_577)


def test_exact_one_mib_boundary_succeeds():
    mode, payload = encode(b"A" * 1_048_576)
    assert mode == "deflate"
    assert (mode, payload) == GOLDEN_VECTORS[10][2:4]
    assert decode(mode, payload) == b"A" * 1_048_576


@pytest.mark.parametrize(
    "data",
    [b"", b"a", b"\x00\xff\x80\x00", "记忆 存在".encode("utf-8"),
     b"z" * 4096, bytes.fromhex("00ff1020807f")],
)
def test_round_trip_varied_bytes(data):
    mode, payload = encode(data)
    assert decode(mode, payload) == data


def test_cli_exit_code_zero_on_success():
    result = subprocess.run(
        [sys.executable, str(CODEC_PATH), "test"],
        text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0
    assert result.stdout.count("PASS") == 12
    assert "FAIL" not in result.stdout


@pytest.mark.parametrize(
    ("arguments", "expected_stdout"),
    [(["encode", "A"], "mode=raw\npayload=AEE\n"),
     (["decode", "raw", "AEE"], "A\n")],
)
def test_cli_encode_decode_exit_code_zero(arguments, expected_stdout):
    result = subprocess.run(
        [sys.executable, str(CODEC_PATH), *arguments],
        text=True, capture_output=True, check=False,
    )
    assert result.returncode == 0
    assert result.stdout == expected_stdout


@pytest.mark.parametrize(
    "arguments",
    [["decode", "raw", "A@"], ["decode", "deflate", "AA"], ["unknown"]],
)
def test_cli_exit_code_nonzero_on_error(arguments):
    result = subprocess.run(
        [sys.executable, str(CODEC_PATH), *arguments],
        text=True, capture_output=True, check=False,
    )
    assert result.returncode != 0
    assert result.stderr
