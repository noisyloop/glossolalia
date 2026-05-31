"""Phase-expansion vocabulary: strands, memory, sigils, rituals, and the
new tone-craft / glyph-craft operators."""

import pytest

from glo.errors import RitualError, GrammarError
from helpers import run, lines


# ── strands (collections) ────────────────────────────────────────────

def test_weave_builds_a_strand():
    assert run("speak weave 432, 528, 639") == "weave 432, 528, 639\n"


def test_empty_weave():
    assert run("let s be weave\nspeak count s") == "0\n"


def test_count_of_strand_and_glyph():
    assert lines("speak count weave 1, 2, 3\nspeak count \"abcd\"") == ["3", "4"]


def test_at_indexes_strand_and_glyph():
    # `at` binds to an element, so a literal strand is indexed via a name
    # (or parentheses); a glyph indexes directly.
    assert lines('let s be weave 10, 20, 30\nspeak s at 0\nspeak "glo" at 2') == [
        "10",
        "o",
    ]


def test_at_indexes_a_parenthesised_strand():
    assert run("speak (weave 5, 6, 7) at 2") == "7\n"


def test_at_out_of_range_speaks():
    with pytest.raises(RitualError) as exc:
        run("let s be weave 1, 2\nspeak s at 9")
    assert "not that long" in str(exc.value)


def test_unweave_reverses():
    assert lines('speak unweave weave 1, 2, 3\nspeak unweave "abc"') == [
        "weave 3, 2, 1",
        "cba",
    ]


def test_repeat_in_walks_a_strand():
    src = "let total be 0\nrepeat n in weave 1, 2, 3, 4\n  add total by n\nend\nspeak total"
    assert run(src) == "10\n"


def test_repeat_in_walks_a_glyph():
    src = 'let out be ""\nrepeat c in "abc"\n  set out to out add by c\nend\nspeak out'
    assert run(src) == "abc\n"


# ── glyph-craft ──────────────────────────────────────────────────────

def test_fracture_splits_a_glyph():
    assert run('speak fracture "a-b-c" by "-"') == "weave a, b, c\n"


def test_converge_joins_a_strand():
    assert run('speak converge weave "a", "b", "c" by " "') == "a b c\n"


def test_fracture_then_converge_roundtrips():
    src = 'speak converge (fracture "1.2.3" by ".") by "-"'
    assert run(src) == "1-2-3\n"


# ── tone-craft ───────────────────────────────────────────────────────

def test_ascend_and_descend_are_octaves():
    assert lines("speak ascend 432\nspeak descend 432") == ["864", "216.0"]


# ── memory ───────────────────────────────────────────────────────────

def test_remember_persists_across_incant_frames():
    src = (
        "remember anchor as 432\n"
        "incant peek\n  speak anchor\nend\n"
        "call peek"
    )
    assert run(src) == "432\n"


def test_forget_removes_from_memory():
    with pytest.raises(RitualError):
        run("remember x as 1\nforget x\nspeak x")


def test_forget_unknown_speaks():
    with pytest.raises(RitualError) as exc:
        run("forget nothing")
    assert "nothing named" in str(exc.value)


# ── sigils (constants) ───────────────────────────────────────────────

def test_sigil_holds_a_value():
    assert run("sigil pi be 3.14\nspeak pi") == "3.14\n"


def test_sigil_cannot_be_set():
    with pytest.raises(RitualError) as exc:
        run("sigil base be 432\nset base to 528")
    assert "fixed and cannot be changed" in str(exc.value)


def test_sigil_cannot_be_stepped():
    with pytest.raises(RitualError):
        run("sigil base be 432\nrise base")


def test_sigil_cannot_be_recarved():
    with pytest.raises(RitualError):
        run("sigil base be 1\nsigil base be 2")


# ── rituals (scoped blocks) ──────────────────────────────────────────

def test_ritual_has_its_own_scope():
    src = "let x be 1\nritual\n  let x be 99\n  speak x\nend\nspeak x"
    assert lines(src) == ["99", "1"]


# ── chant ────────────────────────────────────────────────────────────

def test_chant_speaks_n_times():
    assert lines('chant 3 "om"') == ["om", "om", "om"]


def test_chant_zero_is_silent():
    assert run('chant 0 "om"') == ""


# ── keywords are reserved ────────────────────────────────────────────

def test_reserved_word_cannot_be_a_name():
    with pytest.raises(GrammarError):
        run("let count be 3")
