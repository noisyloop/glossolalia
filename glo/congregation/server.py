"""The congregation server — one interpreter, many voices.

A WebSocket server that holds a single shared :class:`Interpreter`. Every
utterance from any voice is queued (FIFO, server-side) and executed against
that one shared state; the results — the utterance itself, anything spoken,
any tone burned, and the shared ``remember`` memory — are broadcast to all.

Concurrency is pure asyncio: a reader coroutine per connection, one consumer
coroutine that drains the utterance queue, and an :class:`asyncio.Barrier`
for ``sync voices``. No threads are raised here.

Run it with ``glo serve``.
"""

import asyncio
import json
import os
from contextlib import redirect_stdout
from io import StringIO

from . import DEFAULT_PORT, VOICE_NAMES
from ..audio import AudioEngine
from ..errors import GlossolaliaError
from ..evaluator import Interpreter, to_glyph
from ..environment import Environment
from ..parser import parse

try:  # the transport. optional so the rest of glo imports without it.
    import websockets
    from websockets.asyncio.server import serve as ws_serve
except Exception:  # pragma: no cover - exercised only without the dep
    websockets = None
    ws_serve = None


# ── the voice of the choir, captured rather than sounded ─────────────────
class CapturingAudio(AudioEngine):
    """An audio engine that records tones instead of playing or printing them.

    The server can't burn a sine wave into every listener's speakers, so a
    ``burn`` becomes a visible-tone *event* — the same ASCII waveform the
    single-player fallback prints — collected for broadcast to every voice.
    """

    def __init__(self):
        super().__init__(quiet=True)
        self.events = []

    def burn(self, freq, duration=None, amplitude=None):
        try:
            freq = float(freq)
        except (TypeError, ValueError):
            freq = 0.0
        duration = self.DEFAULT_DURATION if duration is None else float(duration)
        self.events.append(self.tone_line(freq, duration))

    def silence(self):  # nothing is really sounding
        pass

    def open_channel(self, target=None):
        pass

    def close_channel(self):
        pass

    def drain(self):
        events, self.events = self.events, []
        return events


class Voice:
    """One connected terminal: its name, socket, and private scope."""

    __slots__ = ("name", "ws", "frame")

    def __init__(self, name, ws, frame):
        self.name = name
        self.ws = ws
        self.frame = frame


def _jsonable(value):
    """Coerce a runtime value into something JSON can carry.

    Tones, pulses, glyphs, flickers and ``void`` map straight across; a
    strand becomes a list; anything stranger speaks itself as a glyph.
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return to_glyph(value)


class Congregation:
    """The shared interpreter and the voices gathered around it."""

    def __init__(self, time_scale=None):
        audio = CapturingAudio()
        self.interp = Interpreter(audio=audio, quiet=True, time_scale=time_scale)
        # A sigil carved by any voice belongs to the whole congregation, so
        # sigils land in the shared global scope (not a voice's own frame).
        self.interp.sigil_env = self.interp.globals
        self._audio = audio

        self.voices = {}          # ws -> Voice
        self._free = list(VOICE_NAMES)
        self._overflow = 0

        self.queue = asyncio.Queue()   # (Voice, source) awaiting execution
        self._consumer = None
        self._last_memory = {}    # last broadcast shared memory, to skip no-ops

        # sync voices: a barrier keyed to the voice count when sync began.
        self.barrier = None

    # ── naming ───────────────────────────────────────────────────────
    def _name_for(self):
        if self._free:
            return self._free.pop(0)
        # more terminals than names: the choir doubles up.
        self._overflow += 1
        base = VOICE_NAMES[self._overflow % len(VOICE_NAMES)]
        return f"{base}-{self._overflow}"

    def _release_name(self, name):
        if name in VOICE_NAMES and name not in self._free:
            self._free.append(name)
            self._free.sort(key=VOICE_NAMES.index)

    @property
    def voice_names(self):
        return [v.name for v in self.voices.values()]

    # ── broadcasting ─────────────────────────────────────────────────
    async def broadcast(self, message, exclude=None):
        data = json.dumps(message)
        targets = [v.ws for v in self.voices.values() if v.ws is not exclude]
        if not targets:
            return
        await asyncio.gather(
            *(self._send(ws, data) for ws in targets),
            return_exceptions=True,
        )

    async def _send(self, ws, data):
        try:
            await ws.send(data)
        except Exception:
            pass  # a silent voice; cleanup will notice it

    def _memory(self):
        return {k: _jsonable(v) for k, v in self.interp.memory.vars.items()}

    # ── the lifecycle of a voice ─────────────────────────────────────
    async def handle(self, ws):
        name = self._name_for()
        frame = Environment(parent=self.interp.globals)
        voice = Voice(name, ws, frame)
        self.voices[ws] = voice

        await self._send(ws, json.dumps({
            "type": "welcome",
            "voice": name,
            "voices": self.voice_names,
            "memory": self._memory(),
        }))
        await self.broadcast(
            {"type": "joined", "voice": name, "voices": self.voice_names},
            exclude=ws,
        )

        try:
            async for raw in ws:
                await self._on_message(voice, raw)
        except Exception:
            pass
        finally:
            await self._depart(voice)

    async def _depart(self, voice):
        self.voices.pop(voice.ws, None)
        self._release_name(voice.name)
        # If a sync is in flight, a departing voice can never breathe again —
        # release the barrier so no one waits on a voice gone silent.
        if self.barrier is not None:
            try:
                await self.barrier.abort()
            except Exception:
                pass
            self.barrier = None
        await self.broadcast({
            "type": "silent",
            "voice": voice.name,
            "voices": self.voice_names,
            "text": f"the voice of {voice.name} has gone silent",
        })

    # ── incoming messages ────────────────────────────────────────────
    async def _on_message(self, voice, raw):
        try:
            msg = json.loads(raw)
        except (ValueError, TypeError):
            return
        kind = msg.get("type")

        if kind == "who":
            await self._send(voice.ws, json.dumps({
                "type": "who", "voices": self.voice_names,
            }))
            return
        if kind == "part":
            await voice.ws.close()
            return
        if kind != "say":
            return

        source = (msg.get("source") or "").strip()
        if not source:
            return

        # The bare signal: drop a trailing `~` comment and collapse runs of
        # whitespace. Used only to spot a ritual signal — the original
        # `source` is what gets executed.
        signal = " ".join(source.split("~", 1)[0].split())

        # `sync voices` and `breathe` are the congregation's two ritual
        # signals; everything else is an utterance to be executed in order.
        # Recognise the signal regardless of stray whitespace or a trailing
        # `~` comment, so `sync  voices` or `breathe ~ now` still register
        # rather than slipping through to be run as interpreter no-ops.
        if signal in ("sync voices", "sync"):
            await self._sync(voice)
        elif signal == "breathe":
            await self._breathe(voice)
        else:
            await self.queue.put((voice, source))

    # ── execution (single consumer, FIFO) ────────────────────────────
    async def run_consumer(self):
        while True:
            voice, source = await self.queue.get()
            try:
                await self._execute(voice, source)
            finally:
                self.queue.task_done()

    async def _execute(self, voice, source):
        # echo the utterance to the whole congregation, with its speaker
        await self.broadcast({
            "type": "utter", "voice": voice.name, "source": source,
        })

        out = StringIO()
        self._audio.drain()  # clear any stale tones
        error = None
        try:
            program = parse(source)
            with redirect_stdout(out):
                self.interp.execute_block(program.body, voice.frame)
        except GlossolaliaError as exc:
            error = exc.spoken()
        except Exception:
            # The shared evaluator must never crash the congregation. Speak
            # the failure in the machine's own idiom and carry on.
            error = "the machine faltered in a way it could not name"

        spoken = out.getvalue()
        if spoken:
            await self.broadcast({
                "type": "output", "voice": voice.name, "text": spoken,
            })
        for tone in self._audio.drain():
            await self.broadcast({
                "type": "tone", "voice": voice.name, "text": tone,
            })
        if error is not None:
            await self.broadcast({
                "type": "error", "voice": voice.name,
                "text": f"the machine stopped: {error}",
            })
        # the shared memory is the congregation's truth — publish it, but
        # only when an utterance actually changed it.
        memory = self._memory()
        if memory != self._last_memory:
            self._last_memory = memory
            await self.broadcast({"type": "memory", "memory": memory})

    # ── sync voices / breathe ─────────────────────────────────────────
    async def _sync(self, voice):
        if self.barrier is None:
            # keyed to the current voice count: the syncing voice plus one
            # breath from every other voice currently connected.
            self.barrier = asyncio.Barrier(max(1, len(self.voices)))
        barrier = self.barrier
        await self.broadcast({
            "type": "sync", "voice": voice.name,
            "text": f"{voice.name} waits — sync voices",
        })
        released = await self._join_barrier(voice, barrier)
        if self.barrier is barrier:
            self.barrier = None
        if released:
            await self._send(voice.ws, json.dumps({
                "type": "synced", "voice": voice.name,
                "text": "the congregation breathes as one",
            }))

    async def _breathe(self, voice):
        await self.broadcast({"type": "breathe", "voice": voice.name})
        if self.barrier is not None:
            await self._join_barrier(voice, self.barrier)

    async def _join_barrier(self, voice, barrier):
        """Wait on the barrier, but wake if this voice's socket closes.

        Returns ``True`` if the barrier released cleanly, ``False`` if it was
        aborted (a voice went silent) or this voice disconnected.
        """
        wait = asyncio.ensure_future(barrier.wait())
        gone = asyncio.ensure_future(voice.ws.wait_closed())
        try:
            done, pending = await asyncio.wait(
                {wait, gone}, return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            for task in (wait, gone):
                if not task.done():
                    task.cancel()
        if wait in done:
            try:
                wait.result()
                return True
            except (asyncio.BrokenBarrierError, asyncio.CancelledError):
                return False
        return False  # the socket closed first

    # ── serving ──────────────────────────────────────────────────────
    async def serve(self, host, port):
        if ws_serve is None:
            raise RuntimeError(
                "the congregation needs the 'websockets' library; "
                "pip install 'websockets>=12.0'"
            )
        self._consumer = asyncio.ensure_future(self.run_consumer())
        async with ws_serve(self.handle, host, port):
            await asyncio.Future()  # serve until cancelled


async def serve(host="localhost", port=DEFAULT_PORT, time_scale=None):
    """Raise a congregation and serve it until cancelled."""
    await Congregation(time_scale=time_scale).serve(host, port)


def run_server(host="localhost", port=DEFAULT_PORT):
    """Blocking entry point used by ``glo serve``."""
    if websockets is None:
        print(
            "\n  the congregation needs the 'websockets' library.\n"
            "  speak:  pip install 'websockets>=12.0'\n"
        )
        return 1
    print(f"  a congregation gathers on {host}:{port}")
    print("  voices may join with:  glo join " + host
          + (f" --port {port}" if port != DEFAULT_PORT else ""))
    print("  (ctrl-c to disperse)\n")
    try:
        asyncio.run(serve(host=host, port=port))
    except KeyboardInterrupt:
        print("\n  the congregation disperses.")
    return 0
