"""Shared plumbing for the glossolalia-os tests.

Everything is run from the repository root, the way the Makefile runs it.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLORUN = [sys.executable, os.path.join(ROOT, "tools", "glorun.py")]
BUILD = os.path.join(ROOT, "build", "test")
os.makedirs(BUILD, exist_ok=True)


def run(argv, timeout=120, **kw):
    return subprocess.run(argv, capture_output=True, text=True, cwd=ROOT,
                          timeout=timeout, **kw)


def interpret(scroll, *words, timeout=120):
    """Run a scroll on the reference (Python) interpreter."""
    return run(GLORUN + [scroll, *words], timeout=timeout)


def glossc(scroll, asm, target="linux", extra=(), timeout=300):
    """Compile with glossc running on the interpreter. Returns the result;
    on success the NASM source is at `asm`."""
    return interpret(os.path.join(ROOT, "glossc", "glossc.glo"),
                     "--target", target, "--home", ROOT, "-o", asm,
                     *extra, scroll, timeout=timeout)


def assemble(asm, out, fmt="bin"):
    r = run(["nasm", "-f", fmt, "-I", ROOT + "/", asm, "-o", out])
    assert r.returncode == 0, f"nasm failed:\n{r.stderr}"
    os.chmod(out, 0o755)


def build_native(scroll, name, extra=()):
    """glossc + nasm: a Linux ELF at build/test/<name>."""
    asm = os.path.join(BUILD, name + ".asm")
    exe = os.path.join(BUILD, name)
    r = glossc(scroll, asm, extra=extra)
    assert r.returncode == 0, f"glossc failed:\n{r.stdout}\n{r.stderr}"
    assemble(asm, exe)
    return exe


# ── booting kernels in QEMU ──────────────────────────────────────────

import socket
import time

QEMU = os.environ.get("QEMU", "qemu-system-i386")
QEMU_BASE = [QEMU, "-nic", "none", "-m", "128", "-display", "none",
             "-device", "isa-debug-exit,iobase=0xf4,iosize=0x04", "-no-reboot"]


def make(target):
    r = subprocess.run(["make", "-s", target], capture_output=True, text=True,
                       cwd=ROOT, timeout=600)
    assert r.returncode == 0, f"make {target} failed:\n{r.stdout}\n{r.stderr}"
    return os.path.join(ROOT, target)


def boot(iso, timeout=40, extra=()):
    """Boot an ISO headless. COM1 goes to our pipe. Returns (code, text):
    `code` is what the kernel passed to depart (QEMU's isa-debug-exit turns
    it into status (code<<1)|1), or None if QEMU ended some other way."""
    try:
        r = subprocess.run(QEMU_BASE + ["-cdrom", iso, "-serial", "stdio", *extra],
                           capture_output=True, text=True, timeout=timeout,
                           stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"")
        out = out.decode() if isinstance(out, bytes) else out
        raise AssertionError("the kernel never finished within "
                             f"{timeout}s; it said:\n{out}")
    code = (r.returncode >> 1) if r.returncode & 1 else None
    return code, r.stdout.replace("\r\n", "\n")


class Monitor:
    """A QEMU monitor on a unix socket, for poking a running machine."""

    def __init__(self, path):
        self.path = path
        self.sock = None

    def connect(self, timeout=15):
        end = time.time() + timeout
        while time.time() < end:
            try:
                self.sock = socket.socket(socket.AF_UNIX)
                self.sock.connect(self.path)
                self.sock.settimeout(5)
                self._read_until(b"(qemu)")
                return
            except OSError:
                time.sleep(0.1)
        raise AssertionError("could not reach the QEMU monitor")

    def _read_until(self, marker):
        buf = b""
        while marker not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                break
            buf += chunk
        return buf.decode(errors="replace")

    def command(self, line):
        self.sock.sendall(line.encode() + b"\n")
        return self._read_until(b"(qemu)")


def start_vm(iso, tmp_path, extra=()):
    """Boot an ISO that never exits, with serial -> file and a monitor.
    Returns (process, monitor, serial_path)."""
    sock = str(tmp_path / "mon.sock")
    serial = str(tmp_path / "serial.txt")
    p = subprocess.Popen(
        QEMU_BASE + ["-cdrom", iso, "-serial", "file:" + serial,
                     "-monitor", f"unix:{sock},server,nowait", *extra],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL)
    mon = Monitor(sock)
    mon.connect()
    return p, mon, serial


def wait_for_text(path, text, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        try:
            data = open(path, errors="replace").read().replace("\r\n", "\n")
            if text in data:
                return data
        except FileNotFoundError:
            pass
        time.sleep(0.1)
    raise AssertionError(f"never heard {text!r}")


def screen(mon, tmp_path):
    """The text screen as 25 lines of characters plus the colour byte of the
    first cell, read from video memory at 0xB8000."""
    dump = str(tmp_path / "vga.bin")
    mon.command(f'pmemsave 0xb8000 4000 "{dump}"')
    end = time.time() + 10
    while not (os.path.exists(dump) and os.path.getsize(dump) == 4000):
        assert time.time() < end, "the monitor never wrote the video memory"
        time.sleep(0.05)
    data = open(dump, "rb").read()
    rows = []
    for y in range(25):
        rows.append("".join(chr(data[(y * 80 + x) * 2]) for x in range(80)).rstrip())
    return rows, data[1]


KEYNAMES = {" ": "spc", "\n": "ret", "-": "minus", "=": "equal", ".": "dot",
            ",": "comma", "/": "slash", ";": "semicolon", "'": "apostrophe"}


def keys_for(text):
    """QEMU monitor key names for the characters of `text`."""
    for ch in text:
        if ch == "\b":
            yield "backspace"
        elif ch.isupper():
            yield "shift-" + ch.lower()
        elif ch in KEYNAMES:
            yield KEYNAMES[ch]
        else:
            yield ch


def type_text(mon, text):
    for key in keys_for(text):
        mon.command(f"sendkey {key}")
        time.sleep(0.04)


def ask(mon, serial, line, timeout=15):
    """Type a line at the REPL prompt and return what it printed (without the
    echo of the line itself), once the next prompt appears."""
    before = len(open(serial, errors="replace").read())
    type_text(mon, line + "\n")
    end = time.time() + timeout
    while time.time() < end:
        data = open(serial, errors="replace").read().replace("\r\n", "\n")[before:]
        if data.count("glo> ") >= 1 and data.endswith("glo> "):
            body = data[: -len("glo> ")]
            return body.split("\n", 1)[1] if "\n" in body else ""
        time.sleep(0.1)
    raise AssertionError(f"no prompt after {line!r}; got {data!r}")


# ── listening to the PC speaker ──────────────────────────────────────

import statistics
import struct
import wave


def tones(wav_path, window=0.1):
    """Read a WAV recorded from QEMU's speaker and describe it as a list of
    (frequency_hz, seconds) runs. QEMU only records while the speaker is on,
    so silence between notes is simply absent. Frequency is measured by
    counting sign changes in each 100 ms window."""
    w = wave.open(wav_path)
    n, rate = w.getnframes(), w.getframerate()
    raw = w.readframes(n)
    left = struct.unpack("<%dh" % (n * w.getnchannels()), raw)[:: w.getnchannels()]
    win = int(rate * window)
    freqs = []
    for i in range(0, len(left) - win, win):
        seg = left[i:i + win]
        if max(abs(x) for x in seg) < 1000:
            freqs.append(0.0)
            continue
        crossings = sum(1 for a, b in zip(seg, seg[1:]) if (a < 0) != (b < 0))
        freqs.append(crossings / 2 / window)
    runs = []
    for f in freqs:
        if runs and (abs(runs[-1][0] - f) < 0.05 * max(f, 1)):
            runs[-1][1].append(f)
        elif runs and f == 0.0 and runs[-1][0] == 0.0:
            runs[-1][1].append(f)
        else:
            runs.append([f, [f]])
    # drop the first window of a run (it straddles the previous note)
    return [(statistics.median(fs), len(fs) * window) for _, fs in runs if len(fs) >= 3]
