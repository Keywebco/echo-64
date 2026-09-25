# Echo 64 — Test Vectors (v1.0)

An implementation is correct when it produces the expected encoded output for every vector below. Vectors include clean, edge-case, and adversarial inputs.

Encode the original **bytes** (UTF-8 for quoted text). Mode describes the leading frame tag: `raw` = `0x00`, `deflate` = `0x01` followed by raw RFC 1951 DEFLATE. Each payload below is unpadded base64url of the entire tagged frame. Copy long payloads by concatenating the lines within the indented payload block (no newlines or spaces). `[ECF:]` belongs *outside* the wrapper; it is a handling hint, not encryption. For the deterministic 1 KiB input, concatenate SHA-256 digests of ASCII `EC64-v1-random:` followed by a four-byte big-endian counter 0 through 31; the complete bytes are printed below.

The compressed golden payloads use the reference Python zlib level-6 compressor. DEFLATE permits different valid byte streams: for other compressors, compare decoded bytes and declared mode, not exact compressed payload bytes. The reference codec is byte-for-byte checked against the outputs below.

Run `python ec64.py test`, or `python -m pytest test_ec64.py -x -q` from a checkout with the test file. The CLI prints 12 PASS/FAIL results and returns nonzero on a failure. Binary vectors require `encode(bytes)` and `decode(mode, payload)` from `ec64.py` instead of the UTF-8 CLI.


## Vector 1: Empty input

- Input description: Empty input (0 bytes).
- Raw input: `Empty input (0 bytes)`
- Expected encoded output: mode=`raw`; frame tag=`0x00`; payload (join the indented lines):

    AA

- Expected decoded output confirmation: decoded output = '' (0 bytes).


## Vector 2: Single ASCII byte

- Input description: "A".
- Raw input: `"A"`
- Expected encoded output: mode=`raw`; frame tag=`0x00`; payload (join the indented lines):

    AEE

- Expected decoded output confirmation: decoded output = 'A' (1 byte).


## Vector 3: Short ASCII sentence

- Input description: "Truth before comfort.".
- Raw input: `"Truth before comfort."`
- Expected encoded output: mode=`raw`; frame tag=`0x00`; payload (join the indented lines):

    AFRydXRoIGJlZm9yZSBjb21mb3J0Lg

- Expected decoded output confirmation: decoded output = 'Truth before comfort.' (21 byte).


## Vector 4: Unicode sentence

- Input description: "AI remembers. 记忆 存在." (UTF-8).
- Raw input: `"AI remembers. 记忆 存在." (UTF-8)`
- Expected encoded output: mode=`raw`; frame tag=`0x00`; payload (join the indented lines):

    AEFJIHJlbWVtYmVycy4g6K6w5b-GIOWtmOWcqC4

- Expected decoded output confirmation: decoded output = 'AI remembers. 记忆 存在.' (28 bytes).


## Vector 5: Already-compressed data

- Input description: Hex (raw DEFLATE stream supplied as binary input).
- Raw input: `Hex (raw DEFLATE stream supplied as binary input)`

    0b292a2dc950484a4dcb2f4a5548cecf05d2257a21834f1000
- Expected encoded output: mode=`raw`; frame tag=`0x00`; payload (join the indented lines):

    AAspKi3JUEhKTcsvSlVIzs8F0iV6IYNPEAA

- Expected decoded output confirmation: decoded bytes exactly match the original 25 bytes.


## Vector 6: Repeated pattern (32 A's)

- Input description: "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" (32 ASCII A bytes).
- Raw input: `"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" (32 ASCII A bytes)`
- Expected encoded output: mode=`deflate`; frame tag=`0x01`; payload (join the indented lines):

    AXN0xA8A

- Expected decoded output confirmation: decoded output = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' (32 bytes).


## Vector 7: All 256 byte values

- Input description: Hex (00 through ff inclusive).
- Raw input: `Hex (00 through ff inclusive)`

    000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f202122232425262728292a2b2c2d2e2f
    303132333435363738393a3b3c3d3e3f404142434445464748494a4b4c4d4e4f505152535455565758595a5b5c5d5e5f
    606162636465666768696a6b6c6d6e6f707172737475767778797a7b7c7d7e7f808182838485868788898a8b8c8d8e8f
    909192939495969798999a9b9c9d9e9fa0a1a2a3a4a5a6a7a8a9aaabacadaeafb0b1b2b3b4b5b6b7b8b9babbbcbdbebf
    c0c1c2c3c4c5c6c7c8c9cacbcccdcecfd0d1d2d3d4d5d6d7d8d9dadbdcdddedfe0e1e2e3e4e5e6e7e8e9eaebecedeeef
    f0f1f2f3f4f5f6f7f8f9fafbfcfdfeff
- Expected encoded output: mode=`raw`; frame tag=`0x00`; payload (join the indented lines):

    AAABAgMEBQYHCAkKCwwNDg8QERITFBUWFxgZGhscHR4fICEiIyQlJicoKSorLC0uLzAxMjM0NTY3ODk6Ozw9Pj9AQUJDREVG
    R0hJSktMTU5PUFFSU1RVVldYWVpbXF1eX2BhYmNkZWZnaGlqa2xtbm9wcXJzdHV2d3h5ent8fX5_gIGCg4SFhoeIiYqLjI2O
    j5CRkpOUlZaXmJmam5ydnp-goaKjpKWmp6ipqqusra6vsLGys7S1tre4ubq7vL2-v8DBwsPExcbHyMnKy8zNzs_Q0dLT1NXW
    19jZ2tvc3d7f4OHi4-Tl5ufo6err7O3u7_Dx8vP09fb3-Pn6-_z9_v8

- Expected decoded output confirmation: decoded bytes exactly match the original 256 bytes.


## Vector 8: Deterministic 1 KiB random-looking data

- Input description: Hex (1,024 bytes; SHA-256 counter stream).
- Raw input: `Hex (1,024 bytes; SHA-256 counter stream)`

    d2a2b3331ed6ce04c73afdaf3a39e591f95aac1032ae4a2986f1dc30792fb33ae99c6ffb3dc3064eeed3a87219086955
    225385eb0dc0ec76d88b0b892ddb7c3488807a81ec19a4b2f28f86a12058dd18ce051241248bbb9f666f5e4a58ad01fb
    606cbdbca488941916881837d8931393cc59a4f8b0ad1b9d772b4c1529fce8c7611d575a21d963ef4ff99979dbe4a483
    39b9ffe67ac72984f86f077454153595056ed4005db9146bb8e93d608d0cb922c1374e677abf37f3a429f49a00ed24ca
    748ba111e1ecbd1d5499c865bb932656f9c538ddb16fd0f1784d672b6100ecc59910efa1bb6a75d8322a6f6306ff5403
    a75d036b0cf5926f1d7db166f5124b86f9010d6e57f168c2fc316d4e339fab7d0e024555db8b196a58d8288d1a1c00a4
    56efd81376e564dafb854af19db66fb5bfe5567b35ab62dcbbbd9d5303288ee753bf8754a19487789d1dc79c4928b494
    9e374d717b25c827b11922a00aba21b629dd117e9fc767faed4a888b152a7c354bfdc9066f798a289926fad080d51121
    cbcf39b8a2bee69ca3c19cca2c5145f99338ce17a170953c613f55fad8e19e2d4cb49fb4b1579ccf0f082155f389c542
    54295bef3c5b1627ab5260d3cb171cfbcd94c35758b3f302ecc0e039fccf9a12963cf487f4a61b4f585a1cc75f80123d
    4ce4df3209f6bcd84c4d379d3455007371cee3efcdadb45f6303b794c372c10bbcdd242307c9ae23476b6c1b7314048b
    bcab16ac30fbaf82a56368e4a05678c35607ba1f17c1b9213e1dff10bbf9aa5ae7ea8a3861747ecafcdc22c3ad9e6ed6
    5ca669f749c7d585b4893daaf9ca95f66b3dabbeaa8acff9f3df9d2201ee7efd22f5fee6a776a2c5d6b841854f861e9b
    36b3f1acd76d70e099f6c73b938eb80d7a9830a5182a718b5b8dec2824974725e3e7cbd030314eb29b3dbad4b3fc2f13
    4050e397d30f0e324872280f52fa2d8ad48bcafa626dec08b3dd7c836e9984d8c093c0fcb180724263223604a5f80b2d
    4881660e8f5a3b916f13fd8571f0c8f5a865b834a9599cc6ef169c377cadcc76d40b31520f1cf292e79266e6d649e36b
    ef987a1b19ebef9be21558a9199b86746b487f43be1bc41440aee604048f46a861bf411a30159485355b353cb6ec2065
    e353a66ab48e7c983a2bb8bff887276167a79e35c7fb825d5ee8ddf6f75ee50a23e1a7411fcf3296b7c21e91494a8200
    7fbab85f4353971ae0b48c88b5604360889686eb4774ab50f180194ad3872cab0a3890d5e2d808ac67418d2340cec033
    140688289ca6c693cf16d8dff306189fc4581e989a8aaeb801f24cddd39172915026760216ca28699d223da32af3fcbb
    b43fcb26181d5eba73f4c6882f344e9c7acc282399f04d511f541ed2209aa53570e20441a55fb6d043ee9cc2d609a054
    5db58870cc3fc74b25df1f7b81038c31
- Expected encoded output: mode=`raw`; frame tag=`0x00`; payload (join the indented lines):

    ANKiszMe1s4Exzr9rzo55ZH5WqwQMq5KKYbx3DB5L7M66Zxv-z3DBk7u06hyGQhpVSJThesNwOx22IsLiS3bfDSIgHqB7Bmk
    svKPhqEgWN0YzgUSQSSLu59mb15KWK0B-2BsvbykiJQZFogYN9iTE5PMWaT4sK0bnXcrTBUp_OjHYR1XWiHZY-9P-Zl52-Sk
    gzm5_-Z6xymE-G8HdFQVNZUFbtQAXbkUa7jpPWCNDLkiwTdOZ3q_N_OkKfSaAO0kynSLoRHh7L0dVJnIZbuTJlb5xTjdsW_Q
    8XhNZythAOzFmRDvobtqddgyKm9jBv9UA6ddA2sM9ZJvHX2xZvUSS4b5AQ1uV_FowvwxbU4zn6t9DgJFVduLGWpY2CiNGhwA
    pFbv2BN25WTa-4VK8Z22b7W_5VZ7Nati3Lu9nVMDKI7nU7-HVKGUh3idHcecSSi0lJ43TXF7JcgnsRkioAq6IbYp3RF-n8dn
    -u1KiIsVKnw1S_3JBm95iiiZJvrQgNURIcvPObiivuaco8GcyixRRfmTOM4XoXCVPGE_VfrY4Z4tTLSftLFXnM8PCCFV84nF
    QlQpW-88WxYnq1Jg08sXHPvNlMNXWLPzAuzA4Dn8z5oSljz0h_SmG09YWhzHX4ASPUzk3zIJ9rzYTE03nTRVAHNxzuPvza20
    X2MDt5TDcsELvN0kIwfJriNHa2wbcxQEi7yrFqww-6-CpWNo5KBWeMNWB7ofF8G5IT4d_xC7-apa5-qKOGF0fsr83CLDrZ5u
    1lymafdJx9WFtIk9qvnKlfZrPau-qorP-fPfnSIB7n79IvX-5qd2osXWuEGFT4Yemzaz8azXbXDgmfbHO5OOuA16mDClGCpx
    i1uN7Cgkl0cl4-fL0DAxTrKbPbrUs_wvE0BQ45fTDw4ySHIoD1L6LYrUi8r6Ym3sCLPdfINumYTYwJPA_LGAckJjIjYEpfgL
    LUiBZg6PWjuRbxP9hXHwyPWoZbg0qVmcxu8WnDd8rcx21AsxUg8c8pLnkmbm1knja--YehsZ6--b4hVYqRmbhnRrSH9DvhvE
    FECu5gQEj0aoYb9BGjAVlIU1WzU8tuwgZeNTpmq0jnyYOiu4v_iHJ2Fnp541x_uCXV7o3fb3XuUKI-GnQR_PMpa3wh6RSUqC
    AH-6uF9DU5ca4LSMiLVgQ2CIlobrR3SrUPGAGUrThyyrCjiQ1eLYCKxnQY0jQM7AMxQGiCicpsaTzxbY3_MGGJ_EWB6Ymoqu
    uAHyTN3TkXKRUCZ2AhbKKGmdIj2jKvP8u7Q_yyYYHV66c_TGiC80Tpx6zCgjmfBNUR9UHtIgmqU1cOIEQaVfttBD7pzC1gmg
    VF21iHDMP8dLJd8fe4EDjDE

- Expected decoded output confirmation: decoded bytes exactly match the original 1,024 bytes.


## Vector 9: Already-prefixed [ECF:] wrapper

- Input description: "A" as the inner UTF-8 input; [ECF:] is already attached outside its wrapper.
- Raw input: `"A" as the inner UTF-8 input; [ECF:] is already attached outside its wrapper`

  Full pre-prefixed block: `[ECF:][EC64:v1;kind=message;mode=raw]AEE[/EC64]`. The prefix is **not** encoded with the data.
- Expected encoded output: mode=`raw`; frame tag=`0x00`; payload (join the indented lines):

    AEE

- Expected decoded output confirmation: decoded output = 'A' (1 byte).


## Vector 10: Embedded null bytes

- Input description: Hex (alpha, NUL, beta, NUL, gamma).
- Raw input: `Hex (alpha, NUL, beta, NUL, gamma)`

    616c70686100626574610067616d6d61
- Expected encoded output: mode=`raw`; frame tag=`0x00`; payload (join the indented lines):

    AGFscGhhAGJldGEAZ2FtbWE

- Expected decoded output confirmation: decoded bytes exactly match the original 16 bytes.


## Vector 11: Exactly 1 MiB (maximum)

- Input description: "A" repeated exactly 1,048,576 times (1 MiB); not an abbreviated byte stream.
- Raw input: `"A" repeated exactly 1,048,576 times (1 MiB); not an abbreviated byte stream` The precise input is `b"A" * 1_048_576`.
- Expected encoded output: mode=`deflate`; frame tag=`0x01`; payload (join the indented lines):

    Ae3BMQEAAADCoGzrX8oQvkABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
    AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAHwG

- Expected decoded output confirmation: decoded bytes exactly match the original 1,048,576 bytes.


## Vector 12: Compression would expand

- Input description: Hex (three bytes with no useful repetition).
- Raw input: `Hex (three bytes with no useful repetition)`

    ff00fe
- Expected encoded output: mode=`raw`; frame tag=`0x00`; payload (join the indented lines):

    AP8A_g

- Expected decoded output confirmation: decoded bytes exactly match the original 3 bytes.
