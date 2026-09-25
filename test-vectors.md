# Echo 64 â€” Test Vectors (v1.0)

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

- Expected decoded MÄ