"""Functional tests from the report's test table (section XI) plus round trips."""
import string

import pytest

from morse_app import morse as m


def test_dictionary_covers_letters_digits_space():
    assert set(m.MORSE_CODE_DICT) == set(string.ascii_uppercase + string.digits + " ")
    codes = [v for k, v in m.MORSE_CODE_DICT.items() if k != " "]
    assert len(codes) == len(set(codes)), "Morse codes must be unique"


def test_encode_mayday():
    assert m.encode_to_morse("MAYDAY") == "-- .- -.-- -.. .- -.--"


def test_decode_sos():
    assert m.decode_from_morse("... --- ...") == "SOS"


def test_unknown_character_is_skipped():
    assert m.encode_to_morse("A@B") == m.encode_to_morse("AB") == ".- -..."


def test_word_separator():
    assert m.encode_to_morse("HELLO WORLD") == ".... . .-.. .-.. --- / .-- --- .-. .-.. -.."
    assert m.decode_from_morse(".... . .-.. .-.. --- / .-- --- .-. .-.. -..") == "HELLO WORLD"


def test_unknown_symbol_decodes_to_question_mark():
    assert m.decode_from_morse("... ------- ...") == "S?S"


def test_lowercase_and_extra_spaces():
    assert m.encode_to_morse("  sos   sos ") == "... --- ... / ... --- ..."


@pytest.mark.parametrize("text", ["MAYDAY MAYDAY MAYDAY", "SOS", "CQ DE VTZ 123", "THE QUICK BROWN FOX 0987654321"])
def test_round_trip(text):
    assert m.decode_from_morse(m.encode_to_morse(text)) == text


def test_timing_ratios():
    assert m.DASH_DURATION == 3 * m.DOT_DURATION
    assert m.TONE_FREQ == 700


def test_duration():
    # "E" = one dot + intra gap
    assert m.duration_ms(".") == m.DOT_DURATION + m.INTRA_ELEMENT_GAP
    # "... --- ..." = 6 dots, 3 dashes, 9 intra gaps, 2 letter gaps
    assert m.duration_ms("... --- ...") == 6 * 150 + 3 * 450 + 9 * 100 + 2 * 300


def test_is_valid_morse():
    assert m.is_valid_morse("... --- ... / .-")
    assert not m.is_valid_morse("SOS")
    assert not m.is_valid_morse("   ")
