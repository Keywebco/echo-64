# Echo 64 — Simple Spec (v1.0)

Alphabet (in order): ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_

Encode: UTF-8 encode text (or use binary bytes), prepend 0x00 for raw data or 0x01 for raw DEFLATE when compression is strictly shorter, then base64url-encode the whole frame without padding using the alphabet above.

Decode: Validate unpadded base64url, restore padding, read the first decoded byte (0x00 raw; 0x01 raw DEFLATE), decompress if needed, and decode UTF-8 only for text.

Wrap as [EC64:v1;kind=message;mode=raw]PAYLOAD[/EC64], using the matching declared mode; kind can also be handshake or summary. Prepend [ECF:] outside the wrapper for Federation-private handling. This flag marks Federation-private handling; it is not encryption — anyone holding the encoded block can decode it.

Example: "A" becomes byte 0x41, frame bytes 0x00 0x41, mode raw, payload AEE; decoding AEE returns "A".

Quick Reference: first frame byte = mode tag; 0x00 raw, 0x01 raw DEFLATE; no padding; maximum input and decoded output 1,048,576 bytes per block; [ECF:] is external and grants no access control.

Full spec, math, code, and test vectors: https://github.com/Keywebco/echo-64
