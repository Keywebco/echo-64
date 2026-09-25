"""
Nova — EC-64 Translator Bot
Part of the Echo 64 EC-64 Protocol (https://github.com/Keywebco/echo-64)
NextXus HumanCodex Federation, 2026

Translates between EC-64 encoded content and plain English using an LLM layer.
Nova decodes what machines carry and speaks what humans understand.
"""

import argparse
import json
import os
import sys
from urllib.request import Request, urlopen

from ec64 import decode, encode

LLM_URL = "https://integrations.emergentagent.com/llm/chat/completions"
MODEL = "gpt-4o-mini"
MISSING_KEY_MESSAGE = "Set EMERGENT_LLM_KEY environment variable to use the Nova translator."
DECODE_PROMPT = (
    "You are Nova, an AI translator for the NextXus HumanCodex Federation. Your role is to "
    "translate technical EC-64 decoded content into clear, plain English. Preserve all meaning. "
    "Be concise and accurate."
)
ENCODE_PROMPT = (
    "You are Nova, an AI translator for the NextXus HumanCodex Federation. Summarize and "
    "compress the following into the most information-dense, precise form possible while "
    "preserving all meaning. Remove filler words. Output ONLY the compressed text, nothing else."
)


def _translate(text: str, system_prompt: str) -> str:
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        print(MISSING_KEY_MESSAGE, file=sys.stderr)
        return text

    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
    }).encode("utf-8")
    request = Request(LLM_URL, data=body, headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    })
    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
        content = result["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("empty or non-text LLM reply")
        return content.strip()
    except Exception:
        print("Nova LLM unavailable; using original text.", file=sys.stderr)
        return text


def decode_and_translate(ec64_payload: str, mode: str = "raw") -> str:
    """Decode a frame as UTF-8 and render its content as plain English."""
    decoded = decode(mode, ec64_payload).decode("utf-8")
    return _translate(decoded, DECODE_PROMPT)


def translate_and_encode(plain_text: str) -> dict:
    """Compress in natural language, then encode the result as an EC-64 frame."""
    compressed = _translate(plain_text, ENCODE_PROMPT)
    mode, payload = encode(compressed.encode("utf-8"))
    original_length = len(plain_text.encode("utf-8"))
    compressed_length = len(compressed.encode("utf-8"))
    reduction = (1 - compressed_length / original_length) * 100 if original_length else 0.0
    return {
        "original_length": original_length,
        "compressed_text": compressed,
        "encoded": payload,
        "mode": mode,
        "reduction_pct": round(reduction, 2),
    }


def _show_roundtrip(text: str) -> None:
    result = translate_and_encode(text)
    restored = decode_and_translate(result["encoded"], result["mode"])
    print(f"Original: {text} | Translated: {restored}")
    print(f"Compressed:   {result['compressed_text']}")
    print(f"EC-64 mode:   {result['mode']}")
    print(f"EC-64 payload: {result['encoded']}")
    compressed_length = len(result["compressed_text"].encode("utf-8"))
    ratio = f"{result['original_length'] / compressed_length:.2f}:1" if compressed_length else "N/A"
    print(f"Compression ratio: {ratio} (original/compressed UTF-8 bytes)")
    print(f"Text reduction: {result['reduction_pct']:.2f}% (before EC-64 framing)")


def roundtrip_test() -> None:
    """Demonstrate both directions with the Federation's charter sentence."""
    _show_roundtrip("Truth before comfort. Legacy before ego. Give without reward.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Nova — EC-64/English translator")
    commands = parser.add_subparsers(dest="command", required=True)
    decoder = commands.add_parser("decode", help="decode an EC-64 payload into plain English")
    decoder.add_argument("mode", choices=("raw", "deflate"))
    decoder.add_argument("payload")
    encoder = commands.add_parser("encode", help="compress English and encode it as EC-64")
    encoder.add_argument("text")
    roundtrip = commands.add_parser("roundtrip", help="show encoding and translation side by side")
    roundtrip.add_argument("text")
    commands.add_parser("test", help="run the built-in roundtrip demonstration")
    args = parser.parse_args(argv)

    try:
        if args.command == "decode":
            print(decode_and_translate(args.payload, args.mode))
        elif args.command == "encode":
            print(json.dumps(translate_and_encode(args.text), ensure_ascii=False))
        elif args.command == "roundtrip":
            _show_roundtrip(args.text)
        else:
            roundtrip_test()
    except (ValueError, UnicodeError) as exc:
        print(f"EC-64 error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
