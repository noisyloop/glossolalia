"""Phase 3 — choir: voices, invoke, audio/OSC fallbacks."""

import io
from contextlib import redirect_stdout

from glo.evaluator import Interpreter


class RecordingOSC:
    def __init__(self):
        self.sent = []

    def send(self, address, value):
        self.sent.append((address, value))


def test_voices_run_and_sync_joins_them():
    src = (
        "let hits be 0\n"
        "voice a\n  rise hits\nend\n"
        "voice b\n  rise hits\nend\n"
        "sync voices\n"
        "speak hits"
    )
    interp = Interpreter(quiet=True)
    out = io.StringIO()
    with redirect_stdout(out):
        interp.run_source(src)
    assert out.getvalue() == "2\n"


def test_voice_error_surfaces_at_sync():
    src = "voice bad\n  set ghost to 1\nend\nsync voices"
    interp = Interpreter(quiet=True)
    import pytest
    from glo.errors import RitualError
    with pytest.raises(RitualError):
        interp.run_source(src)


def test_send_routes_to_osc_bridge():
    osc = RecordingOSC()
    interp = Interpreter(quiet=True, osc=osc)
    interp.run_source('send "/glo/freq" 432\nsend "/glo/trigger" 1')
    assert osc.sent == [("/glo/freq", 432), ("/glo/trigger", 1)]


def test_invoke_brings_in_stdlib_incantations(tmp_path):
    scroll = tmp_path / "main.glo"
    scroll.write_text('invoke "tunings"\nspeak call fifth with 432\n')
    interp = Interpreter(quiet=True)
    out = io.StringIO()
    with redirect_stdout(out):
        interp.run_file(str(scroll))
    assert out.getvalue() == "648.0\n"


def test_invoke_is_idempotent(tmp_path):
    helper = tmp_path / "helper.glo"
    helper.write_text('speak "loaded"\n')
    scroll = tmp_path / "main.glo"
    scroll.write_text('invoke "helper"\ninvoke "helper"\n')
    interp = Interpreter(quiet=True)
    out = io.StringIO()
    with redirect_stdout(out):
        interp.run_file(str(scroll))
    assert out.getvalue() == "loaded\n"
