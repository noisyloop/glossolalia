#!/usr/bin/env python3
"""Run a .glo scroll on the reference interpreter, sized for a compiler.

    python3 tools/glorun.py [--glossolalia DIR] scroll.glo [words...]

This is a *build tool*, not part of the OS or the compiler. The stock
`glo run` is tuned for music scrolls: it stops a loop after 10 million
turns, an incantation after 1000 nested calls, and Python itself gives up
at about 1000 stack frames. A compiler lexing 100 KB one byte at a time,
recursing through a parser, needs more room than that. So this wrapper

  * lifts the interpreter's resource caps (they exist to contain hostile
    scrolls; we are running our own compiler),
  * raises Python's recursion limit and runs on a thread with a big stack,
  * and then simply calls `glo.cli.main(["run", ...])`, so behaviour,
    messages and exit codes are exactly the interpreter's.
"""
import os
import sys
import threading

here = os.path.dirname(os.path.abspath(__file__))
def _find_interpreter():
    """Beside this repo (../glossolalia) or, when glossolalia-os lives inside
    the glossolalia repo, one level up."""
    for rel in ("..", os.path.join("..", "..", "glossolalia")):
        cand = os.path.join(here, rel)
        if os.path.isdir(os.path.join(cand, "glo")):
            return cand
    return os.path.join(here, "..", "..", "glossolalia")


glo_dir = os.environ.get("GLOSSOLALIA") or _find_interpreter()
argv = sys.argv[1:]
if argv[:1] == ["--glossolalia"]:
    glo_dir, argv = argv[1], argv[2:]

os.environ.setdefault("GLO_MAX_DEPTH", "0")        # 0 = unbounded
os.environ.setdefault("GLO_MAX_ITERATIONS", "0")
os.environ.setdefault("GLO_MAX_SOURCE", "0")
os.environ.setdefault("GLO_MAX_TOKENS", "0")
os.environ.setdefault("GLO_NO_AUDIO", "1")
os.environ.setdefault("GLO_TIME_SCALE", "0")
sys.path.insert(0, os.path.abspath(glo_dir))

from glo import cli  # noqa: E402

result = {"code": 1}


def go():
    result["code"] = cli.main(["-q", "run"] + argv)


sys.setrecursionlimit(2_000_000)
threading.stack_size(1024 * 1024 * 1024)
t = threading.Thread(target=go)
t.start()
t.join()
sys.stdout.flush()
sys.exit(result["code"])
