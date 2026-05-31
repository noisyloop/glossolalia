# glossolalia

> *utterance is execution. the machine listens.*

**Glossolalia** is a real, interpreted programming language. Its syntax reads
like incantation — spoken, rhythmic, intentional. Every keyword was chosen to
sound like something when read aloud. Code is scripture. Execution is ritual.

Tuned to 432hz aesthetics: natural, resonant, slightly outside consensus
reality.

```
speak "glossolalia"
burn 432
drift 1
hush
```

---

## the first utterance

```bash
git clone https://github.com/noisyloop/glossolalia
cd glossolalia
python3 -m glo.cli run examples/hello.glo
```

Or install it and get the `glo` command:

```bash
pip install -e .
glo run examples/hello.glo
glo repl
```

No build step. No transpilation. No toolchain. You speak, and the machine
listens.

---

## the tongue

Names are bound with `let` and changed with `set`:

```
let freq be 432
set freq to 528
add freq by 8
```

Tones are burned. Time drifts. Loops repeat and run until:

```
repeat 8
  burn freq
  drift 0.5
end

until freq below 100
  fall freq by 12
end
```

Functions are **incantations**. They take, they echo:

```
incant fifth takes f
  echo f scale by 1.5
end

speak call fifth with 432     ~ 648.0
```

Values gather into **strands**, and the machine **remembers**:

```
let intervals be weave 1, 1.25, 1.5, 2
repeat ratio in intervals
  burn 432 scale by ratio
end

sigil root be 432          ~ a sigil is fixed; it cannot be changed
remember tonic as root     ~ memory survives every scope

speak ascend root          ~ 864   (an octave up)
speak count intervals      ~ 4
let words be fracture "as above so below" by " "
speak converge words by "-"
chant 3 "resonance"
```

And the choir sings in many threads at once:

```
voice low
  repeat 8
    burn 432
    drift 2
    breathe
  end
end

voice high
  repeat 8
    burn 648
    drift 2
    breathe
  end
end

sync voices
silence
```

---

## the machine speaks when it does not understand

Glossolalia never says `SyntaxError: unexpected token`. It speaks back in its
own tongue:

```
the machine did not understand "flarb" on line 4
an incantation named "chord" has not been spoken yet on line 1
the name "ghost" was set before it was ever spoken with "let" on line 2
```

---

## sound & signal

`burn` synthesises a real sine wave through your speakers when an audio backend
is present:

```bash
pip install -e ".[audio]"      # sounddevice + numpy
```

With no device — a server, CI, a quiet laptop — `burn` falls back to a
**visible tone**, so every scroll runs everywhere:

```
~   432.00hz  ▁▁▁▁▁▁▁▁█▁▁▁▁▁▁▁▁  (0.50s) ~
```

And it bridges to Ableton and friends over OSC:

```bash
pip install -e ".[osc]"        # python-osc
```

```
send "/glo/freq" 432
send "/glo/trigger" 1
```

---

## the commands

| Command                 | Does                                       |
|-------------------------|--------------------------------------------|
| `glo run <scroll>`      | execute a scroll                           |
| `glo repl`              | live interactive utterance                 |
| `glo check <scroll>`    | validate syntax without running            |
| `glo trace <scroll>`    | run, printing the AST + an execution trace |
| `glo serve [--port]`    | raise a congregation — a shared live REPL  |
| `glo join <host>`       | add your voice to a congregation           |

---

## the scrolls

Each `.glo` file is a scroll. Bring another scroll's incantations into yours
with `invoke`:

```
invoke "tunings"
speak call solfeggio with 3
```

Bundled standard-library scrolls: `tunings`, `rhythms`, `waveforms`.

---

## the congregation — many voices, one machine

A congregation is a live, multiplayer REPL. One process holds a single
interpreter; many terminals speak into it over WebSockets. What one voice
utters, every machine hears and executes.

```bash
pip install -e .            # websockets ships with the interpreter now
glo serve                   # raise a congregation on :7432
```

In another terminal — or on another machine — add your voice:

```bash
glo join localhost
```

Each voice is given a name from the choir (`low`, `mid`, `high`, `root`,
`fifth`, `ghost`) and a colour. Then:

```
low ⟫ remember tonic as 432      ~ shared truth: every voice reads it
mid ⟫ speak tonic                ~ 432
low ⟫ burn ascend tonic          ~ the waveform appears in every terminal
mid ⟫ let mine be 7              ~ local — yours alone, never broadcast
low ⟫ sync voices                ~ blocks until everyone breathes
mid ⟫ breathe                    ~ … and the congregation moves as one
mid ⟫ \who                       ~ list the gathered voices
low ⟫ \part                      ~ leave gracefully
```

`remember` and `sigil` are the congregation's shared state; local
`let`/`set` stay with the voice that spoke them. If a voice goes silent
mid-`sync`, the barrier releases and the machine says so. The shared
evaluator never crashes the choir — a faulty utterance is spoken back as an
error and the gathering plays on.

---

## learn the whole language

- **[SPEC.md](SPEC.md)** — the complete language specification.
- **[THREAT_MODEL.md](THREAT_MODEL.md)** — the STRIDE threat model and the
  interpreter's security posture.
- **[examples/](examples/)** — scrolls to run and read.

---

## the shape of the work

| Phase            | What                                              | Status |
|------------------|---------------------------------------------------|--------|
| 1 — Utterance    | lexer, parser, evaluator, primitives, `glo run`   | ✅     |
| 2 — Tongue       | math, control flow, bindings, incantations        | ✅     |
| 3 — Choir        | voices, audio, OSC, the scroll/`invoke` system    | ✅     |
| 4 — Scripture    | `repl` / `check` / `trace`, spec, packaging       | ✅     |
| 5 — Congregation | shared live REPL over WebSockets — `serve` / `join` | ✅   |

---

*glossolalia — noisyloop. tuned to 432.*
