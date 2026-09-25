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
            assert translator.encode(letter, alphabet) == symbol, (alphabet, letter)

    @pytest.mark.parametrize("alphabet,symbols", ALPHABET_CASES)
    def test_complete_alphabet_round_trip(self, alphabet, symbols):
        original = string.ascii_uppercase
        encoded = translator.encode(original.lower(), alphabet)
        assert encoded == symbols
        decoded = translator.decode(encoded, alphabet)
        assert decoded.text == original


class TestSharedSymbolsWithDifferentMeanings:
    @pytest.mark.parametrize("symbol,echo_letter,resonance_letter", AMBIGUOUS_CASES)
    def test_each_symbol_requires_the_correct_alphabet(self, symbol, echo_letter, resonance_letter):
        echo = translator.decode(symbol, "echo")
        resonance = translator.decode(symbol, "resonance")
        assert echo.text == echo_letter
        assert resonance.text == resonance_letter
        assert echo_letter != resonance_letter
        assert echo.warnings and resonance.warnings
        assert translator.detect_alphabet(symbol) == "Ambiguous"

    def test_decode_without_an_alphabet_is_rejected(self, capsys):
        with pytest.raises(SystemExit) as exc:
            translator.main(["--decode", "✶"])
        assert exc.value.code == 2
        assert "--alphabet is required" in capsys.readouterr().err


class TestSharedUnambiguousM:
    @pytest.mark.parametrize("alphabet", ("echo", "resonance"))
    def test_m_round_trip_without_ambiguity_warning(self, alphabet):
        assert translator.encode("M", alphabet) == "Ϟ"
        assert translator.decode("Ϟ", alphabet).text == "M"
        assert translator.decode("Ϟ", alphabet).warnings == []

    def test_explanation_excludes_shared_m(self):
        assert "Ϟ" not in translator.explain_ambiguous()
        assert "Ϟ" not in translator.AMBIGUOUS
        assert len(AMBIGUOUS_CASES) == 15

    @pytest.mark.parametrize("symbols", ("Ϟ", "ϞϞ", "Ϟ Ϟ\nϞ"))
    def test_m_only_detection_is_not_ambiguous(self, symbols):
        assert translator.detect_alphabet(symbols) != "Ambiguous"
        assert translator.detect_alphabet(symbols) == "Unambiguous (M)"

    def test_m_only_detect_cli_reports_no_conflict(self, capsys):
        assert translator.main(["--detect", "ϞϞ"]) == 0
        output = capsys.readouterr().out
        assert "Alphabet: Unambiguous (M)" in output
        assert "Alphabet cannot be identified uniquely" not in output

    def test_m_does_not_mask_real_detection(self):
        assert translator.detect_alphabet("Ϟ⟁") == "Echo"
        assert translator.detect_alphabet("Ϟ░") == "Resonance"
        assert translator.detect_alphabet("Ϟ✶") == "Ambiguous"


class TestNonAlphabeticPreservation:
    @pytest.mark.parametrize("alphabet", ("echo", "resonance"))
    def test_all_requested_nonletters_survive_encode_and_decode(self, alphabet):
        unchanged = " .,!? :;-()\"'0123456789\n\r\n\t"
        original = "Mm" + unchanged + "m"
        encoded = translator.encode(original, alphabet)
        assert encoded == "ϞϞ" + unchanged + "Ϟ"
        decoded = translator.decode(encoded, alphabet)
        assert decoded.text == "MM" + unchanged + "M"
        assert decoded.warnings == []
        assert translator.encode(unchanged, alphabet) == unchanged
        assert translator.decode(unchanged, alphabet).text == unchanged
        assert translator.decode(unchanged, alphabet).warnings == []


class TestNeverMergedGuard:
    def test_cross_alphabet_decode_is_not_interchangeable(self):
        echo_encoded = translator.encode("BOX", "echo")
        assert translator.decode(echo_encoded, "echo").text == "BOX"
        assert translator.decode(echo_encoded, "resonance").text != "BOX"

    def test_selected_alphabet_never_switches_mid_operation(self):
        # ⟁ is Echo-only; ░ is Resonance-only; ✶ has different meanings.
        mixed = "⟁░✶"
        assert translator.decode(mixed, "echo").text == "A░B"
        assert translator.decode(mixed, "resonance").text == "⟁AL"

    def test_mixed_unique_symbols_report_conflict_instead_of_merging(self, capsys):
        mixed = "⟁░✶"
        assert translator.detect_alphabet(mixed) == "Ambiguous"
        assert translator.main(["--detect", mixed]) == 0
        output = capsys.readouterr().out
        assert "Alphabet: Ambiguous" in output
        assert "Alphabet cannot be identified uniquely" in output


class TestCrossAlphabetDiagnostics:
    @pytest.mark.parametrize("alphabet,other_symbol,expected", (
        ("echo", "░", "A░B"),
        ("resonance", "⟁", "⟁AL"),
    ))
    def test_other_only_symbol_is_preserved_and_warned(self, alphabet, other_symbol, expected):
        result = translator.decode("⟁░✶", alphabet)
        assert result.text == expected
        assert any(other_symbol in warning and "other alphabet" in warning
                   for warning in result.warnings)
        assert not any("symbol ✶ is from the other alphabet" in warning
                       for warning in result.warnings)

    @pytest.mark.parametrize("alphabet,symbol", (("echo", "⟁"), ("resonance", "░")))
    def test_target_only_symbol_has_no_warning(self, alphabet, symbol):
        assert translator.decode(symbol, alphabet).warnings == []

    @pytest.mark.parametrize("alphabet", ("echo", "resonance"))
    def test_shared_ambiguous_symbol_does_not_get_wrong_alphabet_warning(self, alphabet):
        result = translator.decode("✶", alphabet)
        assert not any("other alphabet" in warning for warning in result.warnings)
        assert any("Ambiguous symbols" in warning for warning in result.warnings)

    @pytest.mark.parametrize("alphabet,symbol", (("echo", "░"), ("resonance", "⟁")))
    def test_strict_rejects_other_only_symbol(self, alphabet, symbol):
        with pytest.raises(ValueError, match="other alphabet"):
            translator.decode(symbol, alphabet, strict=True)
        assert translator.decode("Ϟ✶", alphabet, strict=True).text.startswith("M")

    def test_repeated_other_symbol_warns_once_and_preserves_both(self):
        result = translator.decode("░░", "echo")
        assert result.text == "░░"
        assert len(result.warnings) == 1

    def test_strict_cli_rejects_mixed_input(self, capsys):
        with pytest.raises(SystemExit) as exc:
            translator.main(["--decode", "░", "--alphabet", "echo", "--strict"])
        assert exc.value.code == 2
        assert "other alphabet" in capsys.readouterr().err


class TestDecodeResultStructure:
    @pytest.mark.parametrize("alphabet,symbol,expected", (
        ("echo", "⟁", "A"), ("resonance", "░", "A"),
        ("echo", "Ϟ", "M"), ("resonance", "Ϟ", "M"),
    ))
    def test_structured_result_and_alphabet(self, alphabet, symbol, expected):
        result = translator.decode(symbol, alphabet)
        assert isinstance(result, translator.DecodeResult)
        assert result.text == expected
        assert result.alphabet == ("unambiguous" if symbol == "Ϟ" else alphabet)
        assert isinstance(result.warnings, list)

    def test_warnings_list_is_not_shared_between_results(self):
        first = translator.decode("░", "echo")
        second = translator.decode("⟁", "echo")
        first.warnings.append("new warning")
        assert "new warning" not in second.warnings
        assert isinstance(translator.encode("A", "echo"), str)

    def test_cli_renders_structured_result_fields(self, capsys):
        expected = translator.decode("⟁░", "echo")
        assert translator.main(["--decode", "⟁░", "--alphabet", "echo"]) == 0
        output = capsys.readouterr().out
        assert f"Alphabet: {expected.alphabet}" in output
        assert f"Result:\n{expected.text}" in output
        for warning in expected.warnings:
            assert warning in output

    def test_cli_renders_unambiguous_alphabet(self, capsys):
        assert translator.main(["--decode", "Ϟ", "--alphabet", "echo"]) == 0
        assert "Alphabet: unambiguous" in capsys.readouterr().out


class TestTranslatorAmbiguitySetSync:
    def test_dynamic_set_matches_expected_15_symbols(self):
        expected_symbols = {symbol for symbol, _, _ in AMBIGUOUS_CASES}
        assert len(translator.AMBIGUOUS) == 15
        assert translator.AMBIGUOUS == expected_symbols
        assert translator.AMBIGUOUS == {
            symbol for symbol in translator.REVERSE["Echo"].keys() & translator.REVERSE["Resonance"].keys()
            if translator.REVERSE["Echo"][symbol] != translator.REVERSE["Resonance"][symbol]
        }


class TestD9730C5Regression:
    """Permanent regression for shared-M defect fixed in d9730c5."""

    @pytest.mark.parametrize("alphabet", ("echo", "resonance"))
    def test_shared_m_has_no_warning_and_no_ambiguity(self, alphabet):
        result = translator.decode("Ϟ", alphabet)
        assert result.text == "M"
        assert result.warnings == []
        assert translator.detect_alphabet("ϞϞ") == "Unambiguous (M)"
        assert "Ϟ" not in translator.explain_ambiguous()
