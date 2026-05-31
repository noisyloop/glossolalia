import pytest

from glo.errors import RitualError, GrammarError
from helpers import run, lines


# ── Phase 1: utterance ───────────────────────────────────────────────

def test_speak_a_glyph():
    assert run('speak "glossolalia"') == "glossolalia\n"


def test_hush_is_a_noop():
    assert run("hush") == ""


def test_speak_numbers_keep_their_type():
    assert lines("speak 8\nspeak 0.5") == ["8", "0.5"]


def test_rise_and_fall():
    assert lines("let n be 0\nrise n\nspeak n\nfall n by 3\nspeak n") == ["1", "-2"]


# ── Phase 2: tongue ──────────────────────────────────────────────────

def test_let_and_set():
    assert lines("let freq be 432\nset freq to 528\nspeak freq") == ["528"]


def test_set_before_let_is_a_ritual_error():
    with pytest.raises(RitualError):
        run("set ghost to 1")


def test_arithmetic_mutations():
    src = (
        "let v be 10\n"
        "add v by 5\nspeak v\n"
        "subtract v by 3\nspeak v\n"
        "scale v by 2\nspeak v\n"
        "modulate v by 7\nspeak v\n"
    )
    assert lines(src) == ["15", "12", "24", "3"]


def test_expression_operators_and_precedence():
    # scale binds tighter than add: 2 + (3 * 4) = 14
    assert run("speak 2 add by 3 scale by 4") == "14\n"


def test_comparison_words():
    assert lines(
        "speak 5 above 3\nspeak 5 below 3\nspeak 5 is 5\nspeak 5 not 4"
    ) == ["true", "false", "true", "true"]


def test_logic_and_or_not():
    assert lines(
        "speak 1 and 0\nspeak 1 or 0\nspeak not 0"
    ) == ["false", "true", "true"]


def test_if_else():
    src = (
        "let f be 432\n"
        "if f above 400\n  speak \"high\"\nelse\n  speak \"low\"\nend"
    )
    assert run(src) == "high\n"


def test_repeat():
    assert lines("repeat 3\n  speak \"x\"\nend") == ["x", "x", "x"]


def test_until_counts_down():
    src = "let v be 3\nuntil v is 0\n  speak v\n  fall v\nend"
    assert lines(src) == ["3", "2", "1"]


def test_incant_and_call_with_echo_return():
    src = (
        "incant double takes n\n  echo n scale by 2\nend\n"
        "speak call double with 21"
    )
    assert run(src) == "42\n"


def test_incant_recursion():
    src = (
        "incant fib takes n\n"
        "  if n below 2\n    echo n\n  end\n"
        "  echo (call fib with n subtract by 1) add by (call fib with n subtract by 2)\n"
        "end\n"
        "speak call fib with 10"
    )
    assert run(src) == "55\n"


def test_void_returns_nothing_early():
    src = (
        "incant guard takes n\n"
        "  if n below 0\n    void\n  end\n"
        "  speak \"positive\"\n"
        "end\n"
        "call guard with -1\ncall guard with 5"
    )
    assert run(src) == "positive\n"


def test_wrong_argument_count_speaks():
    with pytest.raises(RitualError):
        run("incant one takes a\n  echo a\nend\ncall one with 1, 2")


def test_calling_unspoken_incantation():
    with pytest.raises(RitualError) as exc:
        run("call chord with 432")
    assert "has not been spoken yet" in str(exc.value)


# ── type casts ───────────────────────────────────────────────────────

def test_type_casts():
    assert lines(
        "speak pulse 4.9\nspeak tone 4\nspeak glyph 7\nspeak flicker 0"
    ) == ["4", "4.0", "7", "false"]


# ── grammar errors ───────────────────────────────────────────────────

def test_unexpected_word_in_statement_position():
    with pytest.raises(GrammarError):
        run("freq 432")


def test_missing_be_in_let():
    with pytest.raises(GrammarError):
        run("let freq 432")
