"""Milestone 0 — the interpreter learns the words the bare tongue needs.

Hex literals, sized pulses that wrap, memory and ports (simulated), rites,
wards, scrolls on disk, bytes, the command line, and exit codes. See
SPEC-BARE.md in glossolalia-os for why each exists.
"""

import os
import subprocess
import sys

import pytest

from glo.errors import GrammarError, RitualError
from glo.evaluator import Departure, Interpreter
from helpers import lines, run

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ── hex literals ─────────────────────────────────────────────────────

def test_hex_literals_are_pulses():
    assert lines("speak 0xB8000\nspeak 0xff\nspeak 0x0") == ["753664", "255", "0"]


def test_hex_literal_works_in_expressions():
    assert run("speak 0x10 add by 0x01") == "17\n"


def test_a_lone_zero_x_is_not_a_number():
    with pytest.raises(Exception):
        run("speak 0x")


# ── sized pulses wrap ────────────────────────────────────────────────

def test_cast_wraps_inside_its_width():
    assert lines("speak p8 300\nspeak p16 70000\nspeak p32 4294967297") == [
        "44", "4464", "1",
    ]


def test_negative_wraps_to_unsigned():
    assert lines("speak p8 -1\nspeak p16 -1\nspeak p32 -1") == [
        "255", "65535", "4294967295",
    ]


def test_a_sized_name_stays_sized_when_changed():
    src = (
        "let x be p8 250\n"
        "add x by 10\nspeak x\n"        # 260 -> 4
        "rise x by 255\nspeak x\n"      # 4 + 255 = 259 -> 3
        "set x to 1000\nspeak x\n"      # 1000 mod 256 = 232
        "subtract x by 233\nspeak x\n"  # -1 -> 255
    )
    assert lines(src) == ["4", "3", "232", "255"]


def test_arithmetic_results_are_plain_pulses():
    # the expression is computed wide; only the *store* into x wraps
    assert lines("let x be p8 250\nspeak x add by 10") == ["260"]


def test_let_from_a_sized_name_inherits_the_size():
    assert lines("let a be p8 200\nlet b be a\nadd b by 100\nspeak b") == ["44"]


def test_a_plain_name_does_not_wrap():
    assert lines("let n be 250\nadd n by 10\nspeak n") == ["260"]


def test_parameters_and_results_are_plain():
    src = (
        "incant bump takes v\n"
        "  add v by 10\n"
        "  echo v\n"
        "end\n"
        "let x be p8 250\n"
        "speak call bump with x\n"       # the callee sees a plain 250
    )
    assert lines(src) == ["260"]


# ── memory: inscribe / peek (in a rite) ──────────────────────────────

def test_inscribe_and_peek_roundtrip_little_endian():
    src = (
        "rite\n"
        "  inscribe p32 0x11223344 at 100\n"
        "  speak peek p8 100\n"       # lowest byte first
        "  speak peek p8 103\n"
        "  speak peek p16 100\n"
        "  speak peek p32 100\n"
        "end\n"
    )
    assert lines(src) == [str(0x44), str(0x11), str(0x3344), str(0x11223344)]


def test_unsized_value_is_written_as_32_bits_and_read_signed():
    src = "rite\n  inscribe -2 at 8\n  speak peek 8\n  speak peek p32 8\nend\n"
    assert lines(src) == ["-2", "4294967294"]


def test_unwritten_memory_reads_zero():
    assert lines("rite\n  speak peek p8 12345\nend") == ["0"]


def test_inscribe_width_follows_the_value():
    src = (
        "rite\n"
        "  inscribe p32 0xFFFFFFFF at 0\n"
        "  inscribe p8 0 at 1\n"          # only byte 1 changes
        "  speak peek p32 0\n"
        "  speak peek 0\n"
        "end\n"
    )
    assert lines(src) == [str(0xFFFF00FF), str(0xFFFF00FF - (1 << 32))]


def test_inscribe_value_can_be_a_parenthesised_expression_and_address_math():
    src = (
        "let base be 0x200\n"
        "rite\n"
        "  inscribe p8 (3 add by 4) at base add by 2\n"
        "  speak peek p8 (base add by 2)\n"
        "end\n"
    )
    assert lines(src) == ["7"]


# ── ports ────────────────────────────────────────────────────────────

def test_whisper_and_listen_use_a_latch_per_port():
    src = (
        "rite\n"
        "  whisper p8 0x2A to port 0xE9\n"
        "  speak listen port 0xE9\n"
        "  speak listen port 0x60\n"       # never written
        "  whisper p16 0x1FF to port 0x70\n"
        "  speak listen p16 port 0x70\n"
        "end\n"
    )
    assert lines(src) == ["42", "0", "511"]


# ── rites gate the hardware ──────────────────────────────────────────

@pytest.mark.parametrize("src", [
    "inscribe p8 1 at 0",
    "whisper p8 1 to port 1",
    "speak peek 0",
    "speak listen port 1",
])
def test_hardware_words_need_a_rite(src):
    with pytest.raises(GrammarError) as err:
        run(src)
    assert "outside a rite" in str(err.value)


def test_the_hardware_words_are_still_ordinary_names_elsewhere():
    # an existing scroll may call an incantation "peek" or name a pulse "port"
    src = "let port be 3\nincant peek\n  speak port\nend\ncall peek"
    assert lines(src) == ["3"]


def test_a_rite_opens_no_scope():
    src = "rite\n  let seen be 5\nend\nspeak seen"
    assert lines(src) == ["5"]


def test_incantations_declared_in_a_rite_belong_to_the_scroll():
    src = (
        "rite\n"
        "  incant put takes at_addr, v\n"
        "    inscribe p8 v at at_addr\n"
        "  end\n"
        "end\n"
        "call put with 7, 65\n"
        "rite\n  speak peek p8 7\nend\n"
    )
    assert lines(src) == ["65"]


def test_a_ward_is_registered_not_run():
    interp = Interpreter(quiet=True)
    interp.run_source("ward 0x21\n  speak \"keyboard\"\nend\n")
    assert 0x21 in interp.wards


# ── bytes ────────────────────────────────────────────────────────────

def test_bones_and_flesh_roundtrip():
    assert lines('speak bones "AB"\nspeak flesh weave 72, 105') == [
        "weave 65, 66", "Hi",
    ]


def test_bones_of_a_non_glyph_is_refused():
    with pytest.raises(RitualError):
        run("speak bones 5")


def test_flesh_refuses_non_bytes():
    with pytest.raises(RitualError):
        run("speak flesh weave 300")
    with pytest.raises(RitualError):
        run("speak flesh weave 1, \"a\"")


def test_bones_walk():
    assert lines('let t be 0\nrepeat b in bones "abc"\n  add t by b\nend\nspeak t') == [
        str(97 + 98 + 99)
    ]


# ── scrolls on disk ──────────────────────────────────────────────────

def test_engrave_and_unseal(tmp_path):
    f = str(tmp_path / "out.txt")
    src = (
        f'engrave "first\\n" to "{f}"\n'
        f'engrave "second\\n" onto "{f}"\n'
        f'speak count unseal "{f}"\n'
        f'engrave "fresh" to "{f}"\n'       # `to` truncates
        f'speak unseal "{f}"\n'
    )
    assert lines(src) == ["13", "fresh"]
    assert open(f, "rb").read() == b"fresh"


def test_unseal_missing_file_speaks_in_voice(tmp_path):
    with pytest.raises(RitualError) as err:
        run(f'speak unseal "{tmp_path}/nope"')
    assert "could not unseal" in str(err.value)


def test_engrave_needs_a_glyph(tmp_path):
    with pytest.raises(RitualError):
        run(f'engrave 5 to "{tmp_path}/x"')


def test_engrave_handles_unicode_as_utf8(tmp_path):
    f = str(tmp_path / "u.txt")
    run(f'engrave "é" to "{f}"')
    assert open(f, "rb").read() == "é".encode("utf-8")
    assert lines(f'speak bones unseal "{f}"') == ["weave 195, 169"]


# ── the command line and leaving ─────────────────────────────────────

def _glo(*argv, input_=None):
    env = dict(os.environ, GLO_NO_AUDIO="1", GLO_TIME_SCALE="0",
               PYTHONPATH=ROOT)
    return subprocess.run(
        [sys.executable, "-m", "glo.cli", *argv],
        capture_output=True, text=True, env=env, cwd=ROOT, input=input_,
    )


def test_depart_sets_the_exit_code(tmp_path):
    scroll = tmp_path / "d.glo"
    scroll.write_text('speak "bye"\ndepart 7\nspeak "never"\n')
    result = _glo("run", str(scroll))
    assert result.returncode == 7
    assert result.stdout == "bye\n"


def test_depart_with_no_code_is_zero(tmp_path):
    scroll = tmp_path / "d.glo"
    scroll.write_text("depart\n")
    assert _glo("run", str(scroll)).returncode == 0


def test_depart_from_inside_an_incantation(tmp_path):
    scroll = tmp_path / "d.glo"
    scroll.write_text("incant out\n  depart 2\nend\ncall out\nspeak 1\n")
    result = _glo("run", str(scroll))
    assert (result.returncode, result.stdout) == (2, "")


def test_depart_raises_for_embedders():
    with pytest.raises(Departure) as err:
        run("depart 5")
    assert err.value.code == 5


def test_heed_hands_over_the_command_line(tmp_path):
    scroll = tmp_path / "h.glo"
    scroll.write_text("speak heed\nspeak count heed\n")
    result = _glo("run", str(scroll), "alpha", "--flag", "x.glo")
    assert result.stdout.splitlines() == [
        "weave alpha, --flag, x.glo", "3",
    ]


def test_heed_is_empty_without_words(tmp_path):
    scroll = tmp_path / "h.glo"
    scroll.write_text("speak count heed\n")
    assert _glo("run", str(scroll)).stdout == "0\n"


def test_an_ordinary_error_still_exits_one(tmp_path):
    scroll = tmp_path / "e.glo"
    scroll.write_text("speak ghost\n")
    result = _glo("run", str(scroll))
    assert result.returncode == 1
    assert "the machine stopped" in result.stderr
