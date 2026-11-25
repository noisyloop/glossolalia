"""Milestone 4 — sound. The PC speaker is driven from PIT channel 2; QEMU
records it to a WAV (-audiodev wav) and the test measures the pitch."""
import os

from helpers import QEMU_BASE, ask, make, start_vm, tones, type_text, wait_for_text
import subprocess


def audio_args(wav):
    return ["-audiodev", f"wav,id=snd,path={wav}", "-machine", "pcspk-audiodev=snd"]


def test_burn_plays_the_right_pitch_for_the_right_time(tmp_path):
    wav = str(tmp_path / "out.wav")
    iso = make("build/test_sound.iso")
    r = subprocess.run(QEMU_BASE + ["-cdrom", iso, "-serial", "stdio", *audio_args(wav)],
                       capture_output=True, text=True, timeout=60,
                       stdin=subprocess.DEVNULL)
    assert r.returncode == (16 << 1) | 1
    assert r.stdout.replace("\r\n", "\n").splitlines() == ["tuning", "sound ok"]
    runs = tones(wav)
    assert len(runs) == 2, runs
    (f1, d1), (f2, d2) = runs
    assert abs(f1 - 440) < 8 and abs(f2 - 880) < 12, runs
    # burn ... for 1200: about 1.2 s each (the speaker clock is the host's)
    assert 0.9 < d1 < 1.6 and 0.9 < d2 < 1.6, runs


def test_burn_from_the_repl_then_silence(tmp_path):
    wav = str(tmp_path / "repl.wav")
    iso = make("build/glossolalia.iso")
    p, mon, serial = start_vm(iso, tmp_path, extra=audio_args(wav))
    try:
        wait_for_text(serial, "glo> ")
        assert ask(mon, serial, "burn 660 700").strip() == "660"
        type_text(mon, "burn 1000\n")                    # no duration: until silence
        wait_for_text(serial, "burn 1000")
        import time
        time.sleep(0.8)
        ask(mon, serial, "silence")
        type_text(mon, "halt\n")
        p.wait(timeout=20)
    finally:
        if p.poll() is None:
            p.kill()
            p.wait()
    runs = tones(wav)
    freqs = [round(f) for f, d in runs]
    assert any(abs(f - 660) < 10 for f in freqs), runs
    assert any(abs(f - 1000) < 15 for f in freqs), runs
