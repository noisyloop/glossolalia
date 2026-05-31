"""The voice of the machine — turning numbers into tones.

``burn`` asks for a frequency. If a real audio backend is present
(``sounddevice`` + ``numpy``), a sine wave is synthesised and played
directly as PCM — no DAW required. When no device or backend exists
(headless servers, CI, most laptops without configuration), the engine
degrades gracefully to a *visible* tone: a printed glyph so a scroll
still "runs" and "sounds" like something, everywhere.

Set ``GLO_NO_AUDIO=1`` to silence even the visible fallback.
"""

import math
import os
import sys
import threading


class AudioEngine:
    SAMPLE_RATE = 44100
    DEFAULT_DURATION = 0.5
    DEFAULT_AMPLITUDE = 0.2

    def __init__(self, quiet=None):
        self._backend = None        # the sounddevice module, if usable
        self._np = None
        self._open = False
        self._lock = threading.Lock()
        self._probed = False
        if quiet is None:
            quiet = os.environ.get("GLO_NO_AUDIO", "") not in ("", "0", "false")
        self.quiet = quiet

    # ── backend probing ──────────────────────────────────────────
    def _probe(self):
        if self._probed:
            return
        self._probed = True
        if os.environ.get("GLO_NO_AUDIO", "") not in ("", "0", "false"):
            return
        try:
            import numpy as np  # type: ignore
            import sounddevice as sd  # type: ignore
            self._np = np
            self._backend = sd
        except Exception:
            # No backend — visible fallback only. This is not an error.
            self._backend = None

    @property
    def has_backend(self):
        self._probe()
        return self._backend is not None

    # ── channel lifecycle ────────────────────────────────────────
    def open_channel(self, target=None):
        self._open = True
        self._target = target
        if not self.quiet and not self.has_backend:
            label = f' "{target}"' if target else ""
            print(f"~ channel{label} opened (silent — no audio device) ~",
                  file=sys.stderr)

    def close_channel(self):
        self.silence()
        self._open = False

    # ── the act of burning a tone ────────────────────────────────
    def burn(self, freq, duration=None, amplitude=None):
        try:
            freq = float(freq)
        except (TypeError, ValueError):
            freq = 0.0
        duration = self.DEFAULT_DURATION if duration is None else float(duration)
        amplitude = self.DEFAULT_AMPLITUDE if amplitude is None else float(amplitude)

        self._probe()
        if self._backend is not None and self._np is not None:
            self._burn_real(freq, duration, amplitude)
        elif not self.quiet:
            print(self.tone_line(freq, duration), file=sys.stderr)

    @classmethod
    def tone_line(cls, freq, duration):
        """The visible tone — a frequency rendered as an ASCII waveform.

        The single source of truth for how an inaudible ``burn`` looks, so
        the local fallback and the congregation's broadcast never diverge.
        """
        bar = cls._tone_glyph(freq)
        return f"~ {freq:>8.2f}hz  {bar}  ({duration:.2f}s) ~"

    def _burn_real(self, freq, duration, amplitude):
        np = self._np
        sd = self._backend
        n = int(self.SAMPLE_RATE * duration)
        t = np.linspace(0.0, duration, n, endpoint=False)
        wave = amplitude * np.sin(2.0 * math.pi * freq * t)
        # short fade to avoid clicks
        fade = min(int(0.01 * self.SAMPLE_RATE), n // 2) or 1
        envelope = np.ones(n)
        envelope[:fade] = np.linspace(0.0, 1.0, fade)
        envelope[-fade:] = np.linspace(1.0, 0.0, fade)
        wave = (wave * envelope).astype(np.float32)
        with self._lock:
            sd.play(wave, self.SAMPLE_RATE, blocking=True)

    def silence(self):
        if self.has_backend:
            try:
                self._backend.stop()
            except Exception:
                pass

    @staticmethod
    def _tone_glyph(freq):
        """A little spectral bar so tones are visible when inaudible.

        Maps a frequency across a rough audible range to a row of marks.
        """
        lo, hi = 110.0, 1760.0   # A2 .. A6
        if freq <= 0:
            return ""
        pos = (math.log2(max(freq, lo)) - math.log2(lo)) / (
            math.log2(hi) - math.log2(lo)
        )
        pos = max(0.0, min(1.0, pos))
        width = 16
        filled = int(round(pos * width))
        return "▁" * filled + "█" + "▁" * (width - filled)
