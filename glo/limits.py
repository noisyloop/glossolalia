"""Resource bounds — the machine's circle of protection.

Glossolalia runs whole scrolls, which may be untrusted. These limits cap
the work a single scroll can demand so a runaway or hostile scroll cannot
exhaust memory or wedge the host (the Denial-of-Service arm of the
threat model). Every limit is a generous default and individually
overridable by an environment variable; a value of ``0`` means
"unbounded" for callers who knowingly opt out (e.g. an endless drone).

See THREAT_MODEL.md for the full rationale.
"""

import os


def _read(name, default):
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# ── lexer caps (token-size / memory exhaustion) ──────────────────────
# Largest scroll, in characters, the lexer will read at once.
MAX_SOURCE_CHARS = _read("GLO_MAX_SOURCE", 2_000_000)
# Largest single glyph (string literal), in characters.
MAX_GLYPH_CHARS = _read("GLO_MAX_GLYPH", 100_000)
# Largest number of tokens a single scroll may produce.
MAX_TOKENS = _read("GLO_MAX_TOKENS", 1_000_000)

# ── evaluator caps (DoS) ─────────────────────────────────────────────
# Deepest incantation call stack before the machine refuses.
MAX_CALL_DEPTH = _read("GLO_MAX_DEPTH", 1_000)
# Most iterations a single loop may run (repeat / until). 0 == unbounded.
MAX_ITERATIONS = _read("GLO_MAX_ITERATIONS", 10_000_000)
# Most concurrent voices that may be spawned across a run.
MAX_VOICES = _read("GLO_MAX_VOICES", 256)
# Deepest chain of invoked scrolls (import depth).
MAX_INVOKE_DEPTH = _read("GLO_MAX_INVOKE_DEPTH", 64)
