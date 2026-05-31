"""The congregation client — add your voice to the choir.

``glo join <host>`` opens a terminal session into a running congregation.
What you speak is sent to the shared interpreter; what every voice speaks
is rendered here, each voice in its own colour.

    \\who     list the voices currently gathered
    \\part    leave the congregation

Input uses ``prompt_toolkit`` when present (so output from other voices
never garbles your prompt) and falls back to plain input otherwise.
"""

import asyncio
import json

from . import DEFAULT_PORT, VOICE_NAMES

try:
    import websockets
    from websockets.asyncio.client import connect as ws_connect
except Exception:  # pragma: no cover
    websockets = None
    ws_connect = None

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.formatted_text import ANSI
    from prompt_toolkit.patch_stdout import patch_stdout
    _HAVE_PTK = True
except Exception:  # pragma: no cover - graceful fallback to input()
    _HAVE_PTK = False


RESET = "\033[0m"
DIM = "\033[2m"
RED = "\033[31m"

# Each voice gets a distinct, stable colour.
_VOICE_COLOR = {
    "low": "\033[36m",     # cyan
    "mid": "\033[32m",     # green
    "high": "\033[33m",    # yellow
    "root": "\033[35m",    # magenta
    "fifth": "\033[34m",   # blue
    "ghost": "\033[90m",   # bright black
}
_FALLBACK_COLORS = ["\033[36m", "\033[32m", "\033[33m", "\033[35m",
                    "\033[34m", "\033[90m", "\033[31m", "\033[95m"]


def color_for(voice):
    if voice in _VOICE_COLOR:
        return _VOICE_COLOR[voice]
    return _FALLBACK_COLORS[hash(voice) % len(_FALLBACK_COLORS)]


def paint(voice):
    return f"{color_for(voice)}{voice}{RESET}"


class Client:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.ws = None
        self.voice = None
        self.voices = []
        self._memory = {}
        self._running = True

    # ── rendering incoming messages ──────────────────────────────────
    def render(self, msg):
        kind = msg.get("type")
        voice = msg.get("voice")

        if kind == "welcome":
            self.voice = voice
            self.voices = msg.get("voices", [])
            self._memory = msg.get("memory", {})
            others = [v for v in self.voices if v != voice]
            print(f"\n  you are the {paint(voice)} voice.")
            if others:
                print("  also gathered: "
                      + ", ".join(paint(v) for v in others))
            else:
                print("  yours is the first voice here.")
            if self._memory:
                print(f"  {DIM}the congregation remembers: "
                      f"{self._fmt_memory()}{RESET}")
            print(f"  {DIM}\\who lists voices · \\part departs{RESET}\n")

        elif kind == "joined":
            self.voices = msg.get("voices", self.voices)
            print(f"  {paint(voice)} joins the congregation")

        elif kind == "silent":
            self.voices = msg.get("voices", self.voices)
            print(f"  {DIM}{msg.get('text', voice + ' has gone silent')}{RESET}")

        elif kind == "utter":
            print(f"{paint(voice)} {DIM}❯{RESET} {msg.get('source', '')}")

        elif kind == "output":
            text = msg.get("text", "")
            for line in text.splitlines():
                print(f"{color_for(voice)}│{RESET} {line}")

        elif kind == "tone":
            print(f"{color_for(voice)}│{RESET} {msg.get('text', '')}")

        elif kind == "error":
            print(f"{color_for(voice)}│{RESET} {RED}{msg.get('text', '')}{RESET}")

        elif kind == "memory":
            new = msg.get("memory", {})
            if new != self._memory:
                self._memory = new
                print(f"  {DIM}≈ memory: {self._fmt_memory()}{RESET}")

        elif kind == "sync":
            print(f"  {DIM}{msg.get('text', voice + ' waits')}{RESET}")

        elif kind == "breathe":
            print(f"  {DIM}{paint(voice)} breathes{RESET}")

        elif kind == "synced":
            print(f"  {DIM}{msg.get('text', 'synced')}{RESET}")

        elif kind == "who":
            self.voices = msg.get("voices", self.voices)
            print("  voices gathered: "
                  + ", ".join(paint(v) for v in self.voices))

    def _fmt_memory(self):
        if not self._memory:
            return "(nothing yet)"
        return ", ".join(f"{k}={v}" for k, v in self._memory.items())

    # ── the two coroutines: listen, and speak ─────────────────────────
    async def _listen(self):
        try:
            async for raw in self.ws:
                try:
                    msg = json.loads(raw)
                except (ValueError, TypeError):
                    continue
                self.render(msg)
        except Exception:
            pass
        finally:
            self._running = False

    async def _prompt(self):
        prompt_text = f"{color_for(self.voice or '')}{self.voice or '...'}{RESET} ⟫ "
        if _HAVE_PTK:
            session = PromptSession()
            while self._running:
                try:
                    with patch_stdout():
                        line = await session.prompt_async(ANSI(prompt_text))
                except (EOFError, KeyboardInterrupt):
                    break
                if not await self._handle_input(line):
                    break
        else:  # pragma: no cover - only without prompt_toolkit
            loop = asyncio.get_event_loop()
            while self._running:
                try:
                    line = await loop.run_in_executor(None, input, prompt_text)
                except (EOFError, KeyboardInterrupt):
                    break
                if not await self._handle_input(line):
                    break

    async def _handle_input(self, line):
        """Act on one line of input. Returns False to stop the session."""
        line = (line or "").strip()
        if not line:
            return True
        if line in ("\\part", "\\leave", "\\quit", "\\q"):
            await self._safe_send({"type": "part"})
            return False
        if line in ("\\who", "\\voices"):
            await self._safe_send({"type": "who"})
            return True
        await self._safe_send({"type": "say", "source": line})
        return True

    async def _safe_send(self, message):
        try:
            await self.ws.send(json.dumps(message))
        except Exception:
            self._running = False

    async def run(self):
        uri = f"ws://{self.host}:{self.port}"
        print(f"  reaching for a congregation at {uri} ...")
        async with ws_connect(uri) as ws:
            self.ws = ws
            listener = asyncio.ensure_future(self._listen())
            try:
                await self._prompt()
            finally:
                listener.cancel()
                try:
                    await self.ws.close()
                except Exception:
                    pass
        print("\n  you step away from the congregation.")


def run_client(host, port=DEFAULT_PORT):
    """Blocking entry point used by ``glo join``."""
    if websockets is None:
        print(
            "\n  joining a congregation needs the 'websockets' library.\n"
            "  speak:  pip install 'websockets>=12.0'\n"
        )
        return 1
    try:
        asyncio.run(Client(host, port).run())
    except KeyboardInterrupt:
        print("\n  you step away from the congregation.")
    except OSError as exc:
        print(f"\n  no congregation answered at {host}:{port}  ({exc})\n")
        return 1
    return 0
