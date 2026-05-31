"""The congregation — a live, multiplayer collaborative REPL.

Many terminals share a single interpreter. What one voice speaks, all the
machines hear and execute. Memory (``remember``) and constants (``sigil``)
are the congregation's shared truth; local ``let``/``set`` bindings stay
with the voice that spoke them.

    glo serve [--port 7432]      raise a congregation
    glo join <host> [--port]     add your voice to one

The transport is WebSockets; coordination is pure asyncio. See
``server.py`` and ``client.py``.
"""

# The voices a congregation can hold. Each connecting terminal is given the
# next free name; the metaphor is reused from the language's own `voice`.
VOICE_NAMES = ["low", "mid", "high", "root", "fifth", "ghost"]

DEFAULT_PORT = 7432

__all__ = ["VOICE_NAMES", "DEFAULT_PORT"]
