"""Resource bounds — the Denial-of-Service arm of the threat model.

These confirm that the interpreter refuses runaway work with a thematic
RitualError rather than hanging the host or raising a raw Python
RecursionError / MemoryError.
"""

import io
from contextlib import redirect_stdout

import pytest

from glo import limits
from glo.evaluator import Interpreter
from glo.errors import RitualError, UtteranceError
from glo.lexer import tokenize


def run_quiet(source):
    interp = Interpreter(quiet=True)
    with redirect_stdout(io.StringIO()):
        interp.run_source(source)


def test_unbounded_recursion_is_caught(monkeypatch):
    monkeypatch.setattr(limits, "MAX_CALL_DEPTH", 50)
    src = "incant forever takes n\n  echo call forever with n\nend\ncall forever with 1"
    with pytest.raises(RitualError) as exc:
        run_quiet(src)
    assert "recurses deeper" in str(exc.value)


def test_runaway_until_loop_is_caught(monkeypatch):
    monkeypatch.setattr(limits, "MAX_ITERATIONS", 1000)
    # condition never becomes true
    src = "let n be 1\nuntil n is 0\n  rise n\nend"
    with pytest.raises(RitualError) as exc:
        run_quiet(src)
    assert "longer than the machine allows" in str(exc.value)


def test_oversized_repeat_is_refused(monkeypatch):
    monkeypatch.setattr(limits, "MAX_ITERATIONS", 100)
    with pytest.raises(RitualError):
        run_quiet("repeat 1000\n  hush\nend")


def test_too_many_voices_is_refused(monkeypatch):
    monkeypatch.setattr(limits, "MAX_VOICES", 2)
    src = (
        "voice a\n  hush\nend\n"
        "voice b\n  hush\nend\n"
        "voice c\n  hush\nend\n"
        "sync voices"
    )
    with pytest.raises(RitualError) as exc:
        run_quiet(src)
    assert "more voices" in str(exc.value)


def test_oversized_source_is_refused(monkeypatch):
    monkeypatch.setattr(limits, "MAX_SOURCE_CHARS", 32)
    with pytest.raises(UtteranceError):
        tokenize("speak 1\n" * 100)


def test_token_flood_is_refused(monkeypatch):
    monkeypatch.setattr(limits, "MAX_TOKENS", 10)
    with pytest.raises(UtteranceError):
        tokenize("speak 1\n" * 100)


def test_oversized_glyph_is_refused(monkeypatch):
    monkeypatch.setattr(limits, "MAX_GLYPH_CHARS", 16)
    with pytest.raises(UtteranceError):
        tokenize('speak "' + "x" * 100 + '"')


def test_a_zero_limit_means_unbounded(monkeypatch):
    # opting out of the repeat cap lets a large (but finite) loop run
    monkeypatch.setattr(limits, "MAX_ITERATIONS", 0)
    run_quiet("let n be 0\nrepeat 5000\n  rise n\nend")
