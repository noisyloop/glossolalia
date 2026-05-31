# Glossolalia — Threat Model (STRIDE)

**Version:** 0.1.0 · applies to the reference interpreter in this repository.

This document describes the security posture of the Glossolalia interpreter
using the **STRIDE** framework (Spoofing, Tampering, Repudiation, Information
disclosure, Denial of service, Elevation of privilege). It states what the
interpreter defends against, how, and what it explicitly does **not**.

---

## 1. System overview & assets

Glossolalia runs a `.glo` *scroll* through four stages: **lexer → parser →
tree-walking evaluator → side-effect backends** (stdout, audio, OSC, the
filesystem via `invoke`).

Assets worth protecting:

| Asset                     | Why it matters                                  |
|---------------------------|-------------------------------------------------|
| The host process & machine| A scroll must not crash, hang, or seize it      |
| Host memory / CPU         | A scroll must not exhaust them                  |
| The host filesystem       | `invoke` reads files; nothing should write/exec |
| Network interfaces        | OSC emits UDP; scope must be intentional        |
| The operator's privacy    | Errors/logs must not leak host internals        |

---

## 2. Trust boundaries

```
   ┌─────────────────────────── host (trusted) ───────────────────────────┐
   │                                                                       │
   │   operator ──runs──▶  glo CLI / Interpreter                           │
   │                              │                                        │
   │            ┌─────────────────┴─────────────────┐                      │
   │   ╔════════▼═════════╗   UNTRUSTED   ╔══════════▼═══════════╗          │
   │   ║  .glo scroll      ║ ────────────▶ ║ lexer/parser/evaluator║         │
   │   ║ (may be 3rd-party)║              ║  (sandboxed by design) ║         │
   │   ╚═══════════════════╝              ╚══════╦═══════╦═════════╝         │
   │                                            │       │                  │
   │                                 invoke (fs read)  send (UDP out)       │
   │                                            │       │                  │
   └────────────────────────────────────────────┼───────┼──────────────────┘
                                                 ▼       ▼
                                          filesystem   network
```

**The central assumption: a scroll is untrusted data.** It is parsed and
walked, never compiled to or evaluated as host code.

---

## 3. The foundational control: no host-code execution

The single most important property of this interpreter:

- **A scroll cannot name, import, or run Python.** There is no `eval`, no
  `exec`, no `__import__`, no FFI, and no statement that reaches the Python
  runtime. The evaluator is a closed dispatch table over a fixed set of AST
  node types (`glo/evaluator.py`, `_EXEC_DISPATCH` / `_EVAL_DISPATCH`). A word
  the grammar does not define cannot become behaviour — it becomes a thematic
  `GrammarError`.
- The interpreter source itself uses **no** `eval`/`exec` to process scroll
  text. Verifiable:

  ```bash
  ! grep -rnE '\b(eval|exec)\s*\(' glo/   # returns nothing
  ```

Everything below builds on this: because scrolls are data, the attack surface
is the small, audited set of side effects the language deliberately exposes.

---

## 4. STRIDE analysis

### S — Spoofing

| Threat | Mitigation | Residual |
|--------|------------|----------|
| One scroll's execution masquerading as another's state; voices reading/writing each other's identity | Each `Interpreter` instance owns its own `globals`, `incantations`, and scroll-dir stack — **no module-level mutable state bleeds between instances**. Parallel runs are isolated by construction. | A single process embedding one `Interpreter` and feeding it multiple users' scrolls would share that instance — callers must use one `Interpreter` per session (the CLI does). |
| `voice` threads forging shared identity | Voices run on isolated child `Environment`s (parent = globals); they share globals intentionally (the language semantics) but cannot fabricate new global identities undetected — every binding is an explicit `let`/`set`. | Shared-global writes are a *feature*; isolate workloads at the `Interpreter` boundary, not within one scroll. |

### T — Tampering

| Threat | Mitigation | Residual |
|--------|------------|----------|
| Scroll injecting unintended syntax/keywords to alter control flow | The grammar is **fixed and closed**. The lexer recognises a hard-coded keyword set; the parser is hand-written recursive descent with no extensibility hooks. Unknown words in statement position raise `GrammarError`; they never silently execute. | — |
| Scroll mutating interpreter internals | Scrolls have no handle to Python objects, the AST, or the interpreter. They manipulate only their own named values. | — |
| `invoke` loading a tampered/unexpected file | Path resolution is explicit and bounded (scroll dir → bundled stdlib). `invoke` only **reads and parses** `.glo` text; it cannot write, and a parsed scroll is still just data. | `invoke` resolves relative to the invoking scroll; treat the directory you run scrolls from as part of the trust boundary (see §5). |

### R — Repudiation

| Threat | Mitigation | Residual |
|--------|------------|----------|
| Inability to tell what a run did | `glo trace` emits a deterministic AST dump + per-node execution trace to stderr. Execution is deterministic given the same scroll and environment (the only nondeterminism is wall-clock `drift` and OS thread scheduling for `voice`). | Trace is opt-in and not a tamper-evident audit log; it is a developer aid. |
| Logs leaking who-did-what secrets | Diagnostic output contains scroll-level constructs only — never credentials, keys, or PII, because the language has no concept of them and the interpreter logs no host context. | — |

### I — Information disclosure

| Threat | Mitigation | Residual |
|--------|------------|----------|
| Python traceback exposing host file paths, env vars, memory addresses | The CLI never surfaces a raw traceback in normal use. Language errors are thematic `GlossolaliaError`s carrying only a message + line number. Unexpected internal errors are caught at the top level and reported as *"the machine faltered in a way it could not name."* Opt back in only with `GLO_DEBUG=1` for interpreter development. (`glo/cli.py::main`) | If a host embeds the library directly (not via the CLI) and prints exceptions itself, it owns that boundary. |
| Errors echoing host paths | Error messages quote scroll-level names (`"chord"`, `"ghost"`) and lines, not host paths. The *"no scroll was found"* message echoes the path the operator typed — their own input, not a discovered internal path. | — |
| Scroll reading host environment / files at will | The language exposes **no** primitive to read env vars, arbitrary files, or process state. The only filesystem reach is `invoke`, restricted to resolving `.glo` scrolls. | `invoke` can read any `.glo`-resolvable path the process can; see §5. |

### D — Denial of service

This is the largest realistic risk for an interpreter of untrusted scrolls and
is addressed by **explicit, configurable resource bounds** in `glo/limits.py`.
Each bound raises a thematic `RitualError`/`UtteranceError` instead of a raw
`RecursionError`, `MemoryError`, or an unbounded hang.

| Vector | Control | Default | Env override (`0` = unbounded) |
|--------|---------|---------|--------------------------------|
| Deep / infinite recursion | `MAX_CALL_DEPTH` checked per incantation call | 1 000 | `GLO_MAX_DEPTH` |
| Non-terminating `until` loop | iteration counter on every `until` | 10 000 000 | `GLO_MAX_ITERATIONS` |
| Huge `repeat` count | count validated before looping | 10 000 000 | `GLO_MAX_ITERATIONS` |
| Oversized `repeat … in` walk / `chant` count | same iteration counter | 10 000 000 | `GLO_MAX_ITERATIONS` |
| Thread/fork bomb via `voice` | `MAX_VOICES` per run | 256 | `GLO_MAX_VOICES` |
| `invoke` recursion / fan-out | import-depth cap + idempotent invoke (each scroll loads once) | 64 | `GLO_MAX_INVOKE_DEPTH` |
| Oversized input (memory) | source-char, total-token, and per-glyph caps **before** allocation | 2 MB / 1e6 / 1e5 | `GLO_MAX_SOURCE`, `GLO_MAX_TOKENS`, `GLO_MAX_GLYPH` |

Bounds are deliberately generous so legitimate scrolls (long drones, deep
tunings) run unhindered, and each is individually relaxable for operators who
knowingly accept the risk (e.g. an intentionally endless live-coding drone with
`GLO_MAX_ITERATIONS=0`).

| Residual | Note |
|----------|------|
| Wall-clock exhaustion via many small `drift`s under a finite loop | bounded by the loop caps above; also set `GLO_TIME_SCALE=0` to neutralise sleeps. |
| Audio/OSC backpressure | backends degrade to printed fallbacks when absent; real backends are opt-in dependencies. |

### E — Elevation of privilege

| Threat | Mitigation | Residual |
|--------|------------|----------|
| Scroll escaping the interpreter to run host commands | No code-exec primitive exists (see §3). There is no `shell`, `system`, `open-for-write`, or FFI keyword. The reserved-word list is reserved for *future language* features, not host access. | — |
| Privilege gained via a backend | Audio (`sounddevice`) and OSC (`python-osc`) are **optional** dependencies; absent them, `burn`/`send` print and do nothing privileged. OSC sends UDP only to a configured host/port. | OSC can emit UDP to `GLO_OSC_HOST:PORT` (default loopback). Operators routing it off-box own that decision. |
| Writing to the filesystem | The language has **no write primitive**. `invoke` is read-only. | — |

---

## 5. Operator responsibilities (the residual trust boundary)

The interpreter sandboxes the *language*. The **operator** still controls the
process boundary, and these remain their responsibility:

1. **Run third-party scrolls under OS-level isolation** (a container, a
   restricted user, or a `chroot`) if you do not trust their author. `invoke`
   can read `.glo`-resolvable paths the *process* can reach; the OS, not the
   language, is the right place to confine that.
2. **Scope the network.** OSC defaults to `127.0.0.1:9000`. Point it off-box
   only intentionally via `GLO_OSC_HOST` / `GLO_OSC_PORT`.
3. **Keep one `Interpreter` per session** when embedding the library, so state
   never bleeds between users (the CLI already does this).
4. **Leave `GLO_DEBUG` off** in production so internal errors stay confidential.

---

## 6. Out of scope (v0.1)

- Cryptographic integrity / signing of scrolls.
- Per-capability permission prompts (e.g. "allow this scroll to send OSC?").
- A formally verified sandbox. The guarantee here is *architectural* (scrolls
  are data, the evaluator is a closed dispatch table), reinforced by resource
  bounds — not a proof.

These are candidates for a future *Scripture* phase.

---

*The circle is drawn. The machine listens, but only within it.*
