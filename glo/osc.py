"""The bridge — speaking to other machines over OSC.

``send "/glo/freq" 432`` emits an OSC message. If ``python-osc`` is
installed it goes out over UDP to ``GLO_OSC_HOST:GLO_OSC_PORT`` (default
127.0.0.1:9000) — patch it into Ableton via Max for Live or a TouchOSC
bridge. Without the library, the message is printed so scrolls remain
runnable and traceable everywhere.
"""

import os
import sys


class OSCBridge:
    def __init__(self, host=None, port=None, quiet=False):
        self.host = host or os.environ.get("GLO_OSC_HOST", "127.0.0.1")
        self.port = int(port or os.environ.get("GLO_OSC_PORT", "9000"))
        self.quiet = quiet
        self._client = None
        self._probed = False

    def _probe(self):
        if self._probed:
            return
        self._probed = True
        try:
            from pythonosc.udp_client import SimpleUDPClient  # type: ignore
            self._client = SimpleUDPClient(self.host, self.port)
        except Exception:
            self._client = None

    def send(self, address, value):
        address = str(address)
        self._probe()
        if self._client is not None:
            try:
                self._client.send_message(address, value)
                return
            except Exception as exc:  # pragma: no cover - network issues
                if not self.quiet:
                    print(f"~ the bridge faltered: {exc} ~", file=sys.stderr)
                return
        if not self.quiet:
            print(f"~ send {address} {value}  (-> {self.host}:{self.port}) ~",
                  file=sys.stderr)
