import pytest

from glo.lexer import tokenize
from glo.errors import UtteranceError


def types(source):
    return [t.type for t in tokenize(source)]


def test_keywords_and_names_are_distinguished():
    toks = tokenize("let freq be 432")
    assert [t.type for t in toks] == ["let", "NAME", "be", "NUMBER", "NEWLINE", "EOF"]


def test_pulse_vs_tone_numbers():
    toks = tokenize("speak 8\nspaek 0.5")  # value types, not keyword check
    nums = [t.value for t in toks if t.type == "NUMBER"]
    assert nums == [8, 0.5]
    assert isinstance(nums[0], int)
    assert isinstance(nums[1], float)


def test_negative_numbers():
    toks = tokenize("set x to -3")
    assert toks[-3].value == -3


def test_glyph_with_escapes():
    toks = tokenize(r'speak "a\nb"')
    assert toks[1].value == "a\nb"


def test_comments_are_ignored():
    assert types("~ a thought\nspeak 1") == ["speak", "NUMBER", "NEWLINE", "EOF"]


def test_blank_lines_collapse():
    # leading blank lines and comments do not produce stray NEWLINEs
    assert types("\n\n~hi\nhush") == ["hush", "NEWLINE", "EOF"]


def test_unclosed_glyph_is_an_utterance_error():
    with pytest.raises(UtteranceError):
        tokenize('speak "open')


def test_unknown_symbol_speaks():
    with pytest.raises(UtteranceError) as exc:
        tokenize("speak @")
    assert "did not understand" in str(exc.value)
