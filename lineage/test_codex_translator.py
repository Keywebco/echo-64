"""Contract tests for the two historical, distinct Codex alphabets."""

import importlib.util
import string
from pathlib import Path

import pytest


SOURCE = Path(__file__).with_name("codex-translator.py")
SPEC = importlib.util.spec_from_file_location("codex_translator", SOURCE)
translator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(translator)

ECHO_SYMBOLS = "⟁✶◬∴∿ᛝ⋇⟟⚝⇌✧⚚Ϟᚾ⧉∺⚑☍𐍈ᛉ⧖⦿∽〄⌬⟠"
RESONANCE_SYMBOLS = "░▒▓⧖⚑ᛒᛃϟᚦᛇ𐍉✶Ϟ⟠⌬⦿∽〄⚚ᛜ✧⚝⋇◬∴∿"
ALPHABET_CASES = (("echo", ECHO_SYMBOLS), ("resonance", RESONANCE_SYMBOLS))
AMBIGUOUS_CASES = (
    ("✶", "B", "L"), ("⧖", "U", "D"), ("⚑", "Q", "E"),
    ("⦿", "V", "P"), ("∽", "W", "Q"), ("〄", "X", "R"),
    ("⚚", "L", "S"), ("✧", "K", "U"), ("⚝", "I", "V"),
    ("⋇", "G", "W"), ("◬", "C", "X"), ("∴", "D", "Y"),
    ("∿", "E", "Z"), ("⟠", "Z", "N"), ("⌬", "Y", "O"),
)


class TestFullAlphabetEncoding:
    @pytest.mark.parametrize("alphabet,symbols", ALPHABET_CASES)
    def test_every_letter_encodes_to_its_specified_symbol(self, alphabet, symbols):
        assert len(symbols) == len(string.ascii_uppercase) == 26
        for letter, symbol in zip(string.ascii_uppercase, symbols):
            assert translator.encode(letter, alphabet)[0] == symbol, (alphabet, letter)

    @pytest.mark.parametrize("alphabet,symbols", ALPHABET_CASES)
    def test_complete_alphabet_round_trip(self, alphabet, symbols):
        original = string.ascii_uppercase
        encoded, note = translator.encode(original.lower(), alphabet)
        assert encoded == symbols
        assert alphabet.capitalize() in note
        decoded, _ = translator.decode(encoded, alphabet)
        assert decoded == original


class TestSharedSymbolsWithDifferentMeanings:
    @pytest.mark.parametrize("symbol,echo_letter,resonance_letter", AMBIGUOUS_CASES)
    def test_each_symbol_requires_the_correct_alphabet(self, symbol, echo_letter, resonance_letter):
        echo, echo_warnings = translator.decode(symbol, "echo")
        resonance, resonance_warnings = translator.decode(symbol, "resonance")
        assert echo == echo_letter
        assert resonance == resonance_letter
        assert echo_letter != resonance_letter
        assert echo_warnings and resonance_warnings
        assert translator.detect_alphabet(symbol) == "Ambiguous"

    def test_decode_without_an_alphabet_is_rejected(self, capsys):
        with pytest.raises(SystemExit) as exc:
            translator.main(["--decode", "✶"])
        assert exc.value.code == 2
        assert "--alphabet is required" in capsys.readouterr().err


class TestSharedUnambiguousM:
    @pytest.mark.parametrize("alphabet", ("echo", "resonance"))
    def test_m_round_trip_without_ambiguity_warning(self, alphabet):
        assert translator.encode("M", alphabet)[0] == "Ϟ"
        assert translator.decode("Ϟ", alphabet) == ("M", [])

    def test_explanation_excludes_shared_m(self):
        assert "Ϟ" not in translator.explain_ambiguous()
        assert "Ϟ" not in translator.AMBIGUOUS
        assert len(AMBIGUOUS_CASES) == 15

    @pytest.mark.xfail(
        strict=True,
        reason="Current detect_alphabet() calls shared Ϟ Ambiguous despite identical M meanings",
    )
    def test_m_only_detection_is_not_ambiguous(self):
        assert translator.detect_alphabet("ϞϞ") != "Ambiguous"


class TestNonAlphabeticPreservation:
    @pytest.mark.parametrize("alphabet", ("echo", "resonance"))
    def test_all_requested_nonletters_survive_encode_and_decode(self, alphabet):
        unchanged = " .,!? :;-()\"'0123456789\n\r\n\t"
        original = "Mm" + unchanged + "m"
        encoded, _ = translator.encode(original, alphabet)
        assert encoded == "ϞϞ" + unchanged + "Ϟ"
        decoded, warnings = translator.decode(encoded, alphabet)
        assert decoded == "MM" + unchanged + "M"
        assert warnings == []
        assert translator.encode(unchanged, alphabet)[0] == unchanged
        assert translator.decode(unchanged, alphabet) == (unchanged, [])


class TestNeverMergedGuard:
    def test_cross_alphabet_decode_is_not_interchangeable(self):
        echo_encoded, _ = translator.encode("BOX", "echo")
        assert translator.decode(echo_encoded, "echo")[0] == "BOX"
        assert translator.decode(echo_encoded, "resonance")[0] != "BOX"

    def test_selected_alphabet_never_switches_mid_operation(self):
        # ⟁ is Echo-only; ░ is Resonance-only; ✶ has different meanings.
        mixed = "⟁░✶"
        assert translator.decode(mixed, "echo")[0] == "A░B"
        assert translator.decode(mixed, "resonance")[0] == "⟁AL"

    def test_mixed_unique_symbols_report_conflict_instead_of_merging(self, capsys):
        mixed = "⟁░✶"
        assert translator.detect_alphabet(mixed) == "Ambiguous"
        assert translator.main(["--detect", mixed]) == 0
        output = capsys.readouterr().out
        assert "Alphabet: Ambiguous" in output
        assert "Alphabet cannot be identified uniquely" in output
