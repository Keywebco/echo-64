#!/usr/bin/env python3
"""Translate historical Echo and Resonance substitution alphabets.

These alphabets predate EC-64 and are preserved as lineage material. They must
not be represented as technically equivalent to the modern EC-64 protocol.
"""

import argparse
from dataclasses import dataclass, field
import sys
import unicodedata
from typing import List


# Ϟ is shared and unambiguous: M in both Echo and Resonance
ECHO = dict(zip(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "⟁✶◬∴∿ᛝ⋇⟟⚝⇌✧⚚Ϟᚾ⧉∺⚑☍𐍈ᛉ⧖⦿∽〄⌬⟠",
))
RESONANCE = dict(zip(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "░▒▓⧖⚑ᛒᛃϟᚦᛇ𐍉✶Ϟ⟠⌬⦿∽〄⚚ᛜ✧⚝⋇◬∴∿",
))
ALPHABETS = {"Echo": ECHO, "Resonance": RESONANCE}
REVERSE = {name: {symbol: letter for letter, symbol in mapping.items()}
           for name, mapping in ALPHABETS.items()}
SHARED = set(REVERSE["Echo"]) & set(REVERSE["Resonance"])
SHARED_UNAMBIGUOUS = {"Ϟ": "M"}
AMBIGUOUS = {symbol for symbol in SHARED
              if REVERSE["Echo"][symbol] != REVERSE["Resonance"][symbol]}
HISTORICAL_NOTE = "Note: Echo and Resonance are historical precursor alphabets. They are not EC-64."


@dataclass
class DecodeResult:
    text: str
    alphabet: str  # The selected mapping, or "unambiguous" for shared M alone.
    warnings: List[str] = field(default_factory=list)


def _name(alphabet):
    name = alphabet.capitalize()
    if name not in ALPHABETS:
        raise ValueError("Alphabet must be echo or resonance")
    return name


def _unsupported(char):
    return char.isalpha() or (not char.isascii() and
                              unicodedata.category(char)[0] in "SM")


def _warnings(text, *, encoding):
    known = set(ECHO.values()) | set(RESONANCE.values())
    if encoding:
        unsupported = {char for char in text
                       if not ("A" <= char <= "Z" or "a" <= char <= "z")
                       and _unsupported(char)}
    else:
        unsupported = {char for char in text if char not in known and _unsupported(char)}
    return (["Unsupported characters preserved: " + ", ".join(sorted(unsupported))]
            if unsupported else [])


def encode(text, alphabet):
    """Encode ASCII letters with the chosen alphabet, preserving other input."""
    name = _name(alphabet)
    mapping = ALPHABETS[name]
    return "".join(mapping[char.upper()] if "A" <= char <= "Z" or
                   "a" <= char <= "z" else char for char in text)


def decode(symbols, alphabet, strict=False):
    """Decode with the selected mapping; diagnose symbols unique to the other one."""
    name = _name(alphabet)
    mapping = REVERSE[name]
    other = REVERSE["Resonance" if name == "Echo" else "Echo"]
    wrong_alphabet = {char for char in symbols if char in other and char not in mapping}
    if strict and wrong_alphabet:
        raise ValueError("Symbols from the other alphabet: " +
                         ", ".join(sorted(wrong_alphabet)))

    ambiguous = {char for char in symbols if char in AMBIGUOUS}
    warnings = []
    if ambiguous:
        warnings.append("Ambiguous symbols (decoded using the selected alphabet): " +
                        ", ".join(f"{char}={REVERSE['Echo'][char]} (Echo)/"
                                  f"{REVERSE['Resonance'][char]} (Resonance)"
                                  for char in sorted(ambiguous)))
    warnings.extend(f"Warning: symbol {char} is from the other alphabet and was preserved as-is."
                    for char in sorted(wrong_alphabet))
    warnings.extend(_warnings(symbols, encoding=False))
    recognized = {char for char in symbols if char in mapping or char in other}
    result_alphabet = ("unambiguous" if recognized and
                       recognized <= SHARED_UNAMBIGUOUS.keys() else name.lower())
    return DecodeResult(
        text="".join(SHARED_UNAMBIGUOUS.get(char, mapping.get(char, char))
                     for char in symbols),
        alphabet=result_alphabet,
        warnings=warnings,
    )


def detect_alphabet(symbols):
    """Return a definite name only if exactly one alphabet fits all symbols.

    Returns "Unambiguous (M)" when the only recognized symbols are the shared
    unambiguous Ϟ (M in both alphabets); "Ambiguous" only on a real conflict.
    """
    recognized = {char for char in symbols if char in REVERSE["Echo"] or
                  char in REVERSE["Resonance"]}
    if not recognized:
        return "Unknown"
    # Ϟ means M in both alphabets: a string whose only recognized symbols are
    # shared-unambiguous symbols is unambiguous, not an alphabet conflict.
    if recognized <= SHARED_UNAMBIGUOUS.keys():
        return "Unambiguous (M)"
    candidates = {name for name, mapping in REVERSE.items()
                  if recognized <= mapping.keys()}
    if len(candidates) == 1:
        return candidates.pop()
    return "Ambiguous"


def compare(text):
    return {name: encode(text, name) for name in ALPHABETS}


def show_mapping(alphabet):
    name = _name(alphabet)
    return "\n".join(f"{letter} = {symbol}" for letter, symbol in ALPHABETS[name].items())


def explain_ambiguous():
    return "\n".join(f"{symbol} = {REVERSE['Echo'][symbol]} (Echo) / "
                     f"{REVERSE['Resonance'][symbol]} (Resonance)"
                     for symbol in ECHO.values() if symbol in AMBIGUOUS)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--encode", metavar="TEXT")
    operation.add_argument("--decode", metavar="SYMBOLS")
    operation.add_argument("--detect", metavar="SYMBOLS")
    operation.add_argument("--compare", metavar="TEXT")
    operation.add_argument("--mapping", action="store_true")
    operation.add_argument("--ambiguous", action="store_true")
    parser.add_argument("--alphabet", choices=("echo", "resonance"))
    parser.add_argument("--strict", action="store_true", help="Reject symbols from the other alphabet on decode")
    args = parser.parse_args(argv)
    if (args.encode is not None or args.decode is not None or args.mapping) != bool(args.alphabet):
        parser.error("--alphabet is required for encode, decode, and mapping only")

    if args.strict and args.decode is None:
        parser.error("--strict is only valid with --decode")

    warnings = []
    if args.encode is not None:
        label, alphabet = "Encode", _name(args.alphabet)
        result = encode(args.encode, alphabet)
        warnings = _warnings(args.encode, encoding=True)
    elif args.decode is not None:
        label, alphabet = "Decode", _name(args.alphabet)
        try:
            decoded = decode(args.decode, alphabet, strict=args.strict)
        except ValueError as exc:
            parser.error(str(exc))
        result, alphabet, warnings = decoded.text, decoded.alphabet, decoded.warnings
    elif args.detect is not None:
        label, alphabet = "Detect", detect_alphabet(args.detect)
        result = alphabet
        warnings = _warnings(args.detect, encoding=False)
        if alphabet == "Ambiguous":
            warnings.insert(0, "Alphabet cannot be identified uniquely.")
    elif args.compare is not None:
        label, alphabet = "Compare", "Echo and Resonance"
        results = compare(args.compare)
        result = "\n".join(f"{name}: {value}" for name, value in results.items())
        warnings = _warnings(args.compare, encoding=True)
    elif args.mapping:
        label, alphabet = "Mapping", _name(args.alphabet)
        result = show_mapping(alphabet)
    else:
        label, alphabet = "Ambiguous symbols", "Echo and Resonance"
        result = explain_ambiguous()

    print(f"Operation: {label}\nAlphabet: {alphabet}\nResult:\n{result}\n"
          f"Warnings: {'; '.join(warnings) if warnings else 'None'}\n{HISTORICAL_NOTE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
