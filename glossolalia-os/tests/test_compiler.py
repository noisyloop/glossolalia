"""Milestone 1 — glossc v0 compiles the bare tongue.

The parity suite: every program under examples/ runs twice,

    1. on the reference interpreter (Python), and
    2. as a native Linux i386 binary, compiled by glossc (which is itself
       a .glo scroll running on that same interpreter),

and the two must agree on everything they print and on the exit status.
"""
import glob
import os
import subprocess

import pytest

from helpers import BUILD, ROOT, build_native, glossc, interpret, run

EXAMPLES = sorted(glob.glob(os.path.join(ROOT, "examples", "*.glo")))


def names():
    return [os.path.basename(p)[:-4] for p in EXAMPLES]


@pytest.mark.parametrize("path", EXAMPLES, ids=names())
def test_native_matches_interpreter(path):
    name = os.path.basename(path)[:-4]
    expected = interpret(path)
    exe = build_native(path, name)
    got = subprocess.run([exe], capture_output=True, text=True, timeout=20)
    assert got.stdout == expected.stdout, (
        f"{name}: native output differs from the interpreter's")
    assert got.returncode == expected.returncode


def test_machine_words_agree_with_their_reference_definitions():
    """bitops.glo invokes rt/bits (the slow reference). Strip that line and the
    compiler uses the one-instruction versions: same answers."""
    src = open(os.path.join(ROOT, "examples", "bitops.glo")).read()
    fast = os.path.join(BUILD, "bitops_fast.glo")
    open(fast, "w").write(src.replace('invoke "rt/bits"\n', ""))
    expected = interpret(os.path.join(ROOT, "examples", "bitops.glo")).stdout
    assert "invoke" not in open(fast).read()
    exe = build_native(fast, "bitops_fast")
    got = subprocess.run([exe], capture_output=True, text=True, timeout=20)
    assert got.stdout == expected
    # and the reference itself, compiled, agrees too
    exe2 = build_native(os.path.join(ROOT, "examples", "bitops.glo"), "bitops_ref")
    got2 = subprocess.run([exe2], capture_output=True, text=True, timeout=20)
    assert got2.stdout == expected


# ── the machine's voice: compile errors ──────────────────────────────

def compile_error(tmp_path, source):
    scroll = tmp_path / "bad.glo"
    scroll.write_text("~ tongue: bare\n" + source)
    r = glossc(str(scroll), str(tmp_path / "bad.asm"))
    assert r.returncode == 1, r.stdout
    return r.stdout.strip()


@pytest.mark.parametrize("source, message", [
    ("inscribe p8 1 at 0\n",
     'the machine will not "inscribe" outside a rite on line 2'),
    ("speak peek 0\n",
     'the machine will not "peek" outside a rite on line 2'),
    ("speak ghost\n",
     'the machine has never heard the name "ghost" on line 2'),
    ("call nothing\n",
     'an incantation named "nothing" has not been spoken yet on line 2'),
    ("incant f takes a, b\n  echo a\nend\ncall f with 1\n",
     'the incantation "f" takes 2 but was given 1 on line 5'),
    ("sigil root be 432\nset root to 1\n",
     'the sigil "root" is fixed and cannot be changed on line 3'),
    ("speak 1.5\n",
     'the compiler does not yet speak tones (decimal numbers) on line 2'),
    ("let s be weave 1, 2\n",
     'the bare tongue has no heap, so no strands on line 2'),
    ('let g be "hi"\n',
     'the bare tongue holds no glyphs; only speak and say may name one on line 2'),
    ("speak 1 @ 2\n",
     'the machine did not understand "@" on line 2'),
    ("speak\n",
     'the machine expected a value but heard "the end of the line" on line 2'),
    ("let x 5\n",
     'the machine expected "be" and a value but heard "5" on line 2'),
    ("if 1\n  speak 1\n",
     'the machine waited for "end" or "else" but the scroll ended on line 4'),
    ('speak "open\n',
     'a glyph was opened but never closed on line 2'),
    ("ritual\n  speak 1\nend\n",
     'the compiler does not yet speak "ritual" on line 2'),
    ("incant f\n  speak 1\nend\nincant f\n  speak 2\nend\n",
     'an incantation named "f" was already spoken on line 5'),
])
def test_errors_speak_in_the_machines_voice(tmp_path, source, message):
    assert compile_error(tmp_path, source) == message


def test_grammar_errors_say_what_the_interpreter_says(tmp_path):
    """The parse errors are the interpreter's words, verbatim."""
    for source in ("speak\n", "let x 5\n", "if 1\n  speak 1\n", "speak 1 2\n"):
        scroll = tmp_path / "g.glo"
        scroll.write_text(source)
        want = interpret(str(scroll)).stderr
        got = compile_error(tmp_path, source.replace("\n", "\n", 1))
        # compare the message text, ignoring line numbers shifted by the marker
        msg = got.rsplit(" on line ", 1)[0]
        assert msg in want, (msg, want)


def test_no_scroll_is_a_usage_error(tmp_path):
    r = interpret(os.path.join(ROOT, "glossc", "glossc.glo"))
    assert r.returncode == 1
    assert "heard no scroll" in r.stdout
