"""The congregation — a shared, multiplayer REPL over WebSockets.

These tests stand up a real server on an ephemeral port and join it with
real WebSocket clients, all on one asyncio loop. No threads, no mocks.

``pytest-asyncio`` is not assumed: each test drives its own loop through
``asyncio.run``.
"""

import asyncio
import json

import pytest

pytest.importorskip("websockets")

import websockets
from websockets.asyncio.server import serve as ws_serve

from glo.congregation.server import Congregation


# ── harness ──────────────────────────────────────────────────────────────
async def _with_server(scenario):
    """Run ``scenario(port)`` against a freshly raised congregation."""
    cong = Congregation(time_scale=0)
    consumer = asyncio.ensure_future(cong.run_consumer())
    async with ws_serve(cong.handle, "localhost", 0) as server:
        port = server.sockets[0].getsockname()[1]
        try:
            return await scenario(cong, port)
        finally:
            consumer.cancel()
            try:
                await consumer
            except asyncio.CancelledError:
                pass


async def _join(port):
    return await websockets.connect(f"ws://localhost:{port}")


async def _recv_until(ws, kind, timeout=2.0):
    """Read messages until one of ``kind`` arrives (others are skipped)."""
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout)
        msg = json.loads(raw)
        if msg.get("type") == kind:
            return msg


async def _say(ws, source):
    await ws.send(json.dumps({"type": "say", "source": source}))


def _run(scenario):
    return asyncio.run(_with_server(scenario))


# ── tests ──────────────────────────────────────────────────────────────
def test_loopback_broadcast():
    """One voice speaks; the server echoes the utterance and its output."""

    async def scenario(cong, port):
        ws = await _join(port)
        welcome = await _recv_until(ws, "welcome")
        assert welcome["voice"] == "low"          # first free voice name

        await _say(ws, "speak 432")

        utter = await _recv_until(ws, "utter")
        assert utter["voice"] == "low"
        assert utter["source"] == "speak 432"

        output = await _recv_until(ws, "output")
        assert output["voice"] == "low"
        assert output["text"].strip() == "432"

        await ws.close()

    _run(scenario)


def test_shared_remember_memory():
    """What one voice remembers, another voice can read."""

    async def scenario(cong, port):
        a = await _join(port)
        await _recv_until(a, "welcome")
        b = await _join(port)
        bw = await _recv_until(b, "welcome")
        assert bw["voice"] == "mid"               # second free voice name

        # A remembers; wait for the shared memory to carry the new value.
        await _say(a, "remember x as 1")
        mem = await _recv_until(a, "memory")
        while mem["memory"].get("x") != 1:
            mem = await _recv_until(a, "memory")
        assert mem["memory"]["x"] == 1

        # B, in its own scope, reads the shared memory.
        await _say(b, "speak x")
        out = await _recv_until(b, "output")
        assert out["text"].strip() == "1"

        await a.close()
        await b.close()

    _run(scenario)


def test_local_let_does_not_leak_between_voices():
    """A voice's own ``let`` stays with that voice; it is not shared."""

    async def scenario(cong, port):
        a = await _join(port)
        await _recv_until(a, "welcome")
        b = await _join(port)
        await _recv_until(b, "welcome")

        # `let` touches no shared memory, so wait on the utterance echo
        # (broadcast as the consumer begins running it) to order A before B.
        await _say(a, "let secret be 99")
        await _recv_until(a, "utter")

        await _say(b, "speak secret")
        err = await _recv_until(b, "error")
        assert "secret" in err["text"]

        await a.close()
        await b.close()

    _run(scenario)


def test_sync_blocks_until_breathe():
    """A voice on ``sync voices`` unblocks only once the other breathes."""

    async def scenario(cong, port):
        a = await _join(port)
        await _recv_until(a, "welcome")
        b = await _join(port)
        await _recv_until(b, "welcome")
        await _recv_until(a, "joined")            # A learns of B

        # A blocks on sync voices.
        await _say(a, "sync voices")
        await _recv_until(a, "sync")              # the wait is announced

        # Until B breathes, A must not be released.
        with pytest.raises(asyncio.TimeoutError):
            await _recv_until(a, "synced", timeout=0.4)

        # B breathes; the barrier fills; A is released.
        await _say(b, "breathe")
        synced = await _recv_until(a, "synced", timeout=2.0)
        assert synced["voice"] == "low"

        await a.close()
        await b.close()

    _run(scenario)


def test_disconnect_mid_sync_releases_the_barrier():
    """If a voice goes silent mid-sync, the waiting voice is not stranded."""

    async def scenario(cong, port):
        a = await _join(port)
        await _recv_until(a, "welcome")
        b = await _join(port)
        await _recv_until(b, "welcome")
        await _recv_until(a, "joined")

        await _say(a, "sync voices")
        await _recv_until(a, "sync")

        # B leaves without ever breathing.
        await b.close()

        silent = await _recv_until(a, "silent", timeout=2.0)
        assert "gone silent" in silent["text"]

        await a.close()

    _run(scenario)


def test_evaluator_error_does_not_crash_the_server():
    """A faulty utterance is spoken back as an error; the congregation lives."""

    async def scenario(cong, port):
        ws = await _join(port)
        await _recv_until(ws, "welcome")

        await _say(ws, "speak nonesuch")
        err = await _recv_until(ws, "error")
        assert "nonesuch" in err["text"]

        # The server is still alive and serving.
        await _say(ws, "speak 7")
        out = await _recv_until(ws, "output")
        assert out["text"].strip() == "7"

        await ws.close()

    _run(scenario)


def test_ritual_signals_survive_whitespace_and_comments():
    """`sync  voices` and `breathe ~ note` still register as ritual signals."""

    async def scenario(cong, port):
        a = await _join(port)
        await _recv_until(a, "welcome")
        b = await _join(port)
        await _recv_until(b, "welcome")
        await _recv_until(a, "joined")

        # Extra spacing must not stop the sync from registering.
        await _say(a, "sync   voices")
        await _recv_until(a, "sync")
        with pytest.raises(asyncio.TimeoutError):
            await _recv_until(a, "synced", timeout=0.4)

        # A trailing comment must not stop the breath from registering.
        await _say(b, "breathe   ~ here i am")
        synced = await _recv_until(a, "synced", timeout=2.0)
        assert synced["voice"] == "low"

        await a.close()
        await b.close()

    _run(scenario)


def test_unchanged_memory_is_not_rebroadcast():
    """Memory is published only when an utterance actually changes it."""

    async def scenario(cong, port):
        ws = await _join(port)
        await _recv_until(ws, "welcome")

        # A remember changes memory: it is broadcast.
        await _say(ws, "remember x as 1")
        mem = await _recv_until(ws, "memory")
        assert mem["memory"]["x"] == 1

        # A pure speak changes nothing: no memory message before its output.
        await _say(ws, "speak x")
        saw_memory = False
        while True:
            raw = await asyncio.wait_for(ws.recv(), 2.0)
            msg = json.loads(raw)
            if msg.get("type") == "memory":
                saw_memory = True
            if msg.get("type") == "output":
                break
        assert msg["text"].strip() == "1"
        assert not saw_memory

        await ws.close()

    _run(scenario)
