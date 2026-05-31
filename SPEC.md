# Glossolalia Language Specification

**Version:** 0.1.0 · **Extension:** `.glo` · **Repository:** noisyloop/glossolalia

> *Utterance is execution.*

Glossolalia is a real, interpreted programming language whose syntax reads
like incantation. This document specifies the language as implemented by the
reference interpreter in this repository.

---

## 1. Lexical structure

A scroll is UTF-8 text, read line by line. A **newline ends an utterance**
(statement). Blank lines and comment-only lines are ignored.

### 1.1 Comments

A `~` begins a comment that runs to the end of the line.

```
~ this is a thought the machine ignores
speak "but this is spoken"
```

### 1.2 Glyphs (strings)

Text between double quotes. Supported escapes: `\n`, `\t`, `\"`, `\\`.

```
speak "the machine\nlistens"
```

An unclosed glyph is an error: *a glyph was opened but never closed*.

### 1.3 Numbers

- A number **without** a decimal point is a `pulse` (integer): `8`, `432`.
- A number **with** a decimal point is a `tone` (float): `0.5`, `432.0`.
- A leading `-` denotes a negative literal: `-3`, `-0.1`.

### 1.4 Words

A word is a run of letters, digits and underscores beginning with a letter or
underscore. A word is either a **keyword** (part of the tongue) or a **name**
(something you have named). Names are case-sensitive.

### 1.5 Other tokens

`(` `)` group expressions. `,` separates arguments and parameters.

---

## 2. Types

| Type      | Python value | Meaning                          |
|-----------|--------------|----------------------------------|
| `tone`    | `float`      | frequency, amplitude, any decimal|
| `pulse`   | `int`        | beat, count, index               |
| `glyph`   | `str`        | text                             |
| `flicker` | `bool`       | truth — `true` / `false`         |
| `void`    | `None`       | nothing                          |

The type names double as **conversion operators** in expressions:

```
speak pulse 4.9     ~ 4      (truncates)
speak tone 4        ~ 4.0
speak glyph 432     ~ "432"
speak flicker 0     ~ false
```

### 2.1 Truth

`void`, `0`, `0.0`, `false`, and the empty glyph `""` are **false**. Everything
else is **true**.

---

## 3. Expressions

Operators are words. Precedence, lowest to highest:

| Tier | Operators                       | Meaning                       |
|------|---------------------------------|-------------------------------|
| 1    | `or`                            | logical or (short-circuit)    |
| 2    | `and`                           | logical and (short-circuit)   |
| 3    | `is` `not` `above` `below`      | `==` `!=` `>` `<`             |
| 4    | `add by` `subtract by`          | `+` `-`                       |
| 5    | `scale by` `modulate by`        | `*` `%`                       |
| 6    | `not` (prefix), type casts      | logical negation, conversion  |
| 7    | literals, names, `call`, `( )`  | primaries                     |

The arithmetic operators are **postfix word operators**: the operand comes
first.

```
speak 2 add by 3 scale by 4     ~ 14   (scale binds tighter)
burn root scale by 1.5          ~ a perfect fifth above root
speak phase modulate by 0.333   ~ phase wrapped into [0, 0.333)
```

`add` between glyphs concatenates: `"4" add by "32"` → `"432"`.

`is` compares any two values for equality; `not` as a binary operator means
*is not*. `above` / `below` compare tones and pulses by magnitude.

---

## 4. Statements

### 4.1 Commands

| Statement              | Effect                                            |
|------------------------|---------------------------------------------------|
| `speak <expr>`         | print the value                                   |
| `hush`                 | no-op — intentional silence                       |
| `burn <expr>`          | emit a tone at the given frequency                |
| `burn <expr> for <e>`  | emit a tone for a number of seconds               |
| `rise <name>`          | increment by 1                                    |
| `rise <name> by <e>`   | increment by an amount                            |
| `fall <name>`          | decrement by 1                                    |
| `fall <name> by <e>`   | decrement by an amount                            |
| `drift <expr>`         | pause execution for a number of seconds           |
| `breathe`              | yield within a loop (cooperative pause)           |
| `silence`              | stop all sounding tones                           |

### 4.2 Bindings

```
let freq be 432        ~ bind a new name in the current scope
set freq to 528        ~ reassign an existing name
```

`set` on a name that was never `let` is an error: *the name "x" was set before
it was ever spoken with "let"*.

### 4.3 Arithmetic mutations

These change a name in place:

```
add freq by 8
subtract vol by 0.1
scale freq by 2
modulate phase by 0.333
```

### 4.4 Control flow

```
if freq above 400
  speak "high"
else
  speak "low"
end

repeat 8
  burn freq
  drift 0.5
end

until vol is 0       ~ loop while the condition is false
  fall vol
end
```

`else` is optional. `repeat <n>` runs its body `n` times (`n` is rounded to a
whole pulse). `until <cond>` repeats its body until the condition becomes true.

### 4.5 Incantations (functions)

```
incant chord takes root
  burn root
  burn root scale by 1.25
  burn root scale by 1.5
end

call chord with 432
```

- Parameters after `takes` are separated by commas (or `and`):
  `incant pulse takes f, n`.
- Arguments after `with` are separated by commas: `call pulse with 432, 8`.
- `echo <expr>` returns a value; `void` returns nothing (an early exit).
- `call` is also an **expression**, so incantations compose:
  `speak call fib with 10`.

Calling an unknown incantation: *an incantation named "chord" has not been
spoken yet*. Giving the wrong number of arguments is likewise an error.

Incantations are lexically global: they see the global scroll scope plus their
own parameters.

---

## 5. The choir — concurrency, audio, OSC, scrolls

### 5.1 Voices (threads)

Each `voice` block runs in its own thread, started where it is declared.
`sync voices` joins all voices started since the last sync.

```
voice low
  repeat 8
    burn base
    drift 2
    breathe
  end
end

voice high
  repeat 8
    burn base scale by 1.5
    drift 2
    breathe
  end
end

sync voices
```

Voices share the global scope. An error raised inside a voice surfaces from
`sync voices`.

### 5.2 Audio

`burn` synthesises a sine wave and plays it as PCM when a backend
(`sounddevice` + `numpy`) is available. With no backend or device, `burn`
degrades to a **visible tone** printed to stderr, so scrolls run everywhere.

```
open channel "default"
burn 432 for 2.0
silence
close channel
```

Set `GLO_NO_AUDIO=1` to skip the backend; add `-q` / `--quiet` to silence even
the visible fallback.

### 5.3 OSC

`send <address> <value>` emits an OSC message over UDP via `python-osc` to
`GLO_OSC_HOST:GLO_OSC_PORT` (default `127.0.0.1:9000`). Without the library the
message is printed, so scrolls remain runnable and traceable.

```
send "/glo/freq" 432
send "/glo/trigger" 1
```

### 5.4 Scrolls (modules)

Each `.glo` file is a scroll. `invoke "<name>"` loads and evaluates another
scroll into the **current global scope**, making its incantations and bindings
available. Resolution order: relative to the invoking scroll, then the bundled
standard-library scrolls (`tunings`, `rhythms`, `waveforms`). Invoking the same
scroll twice is a no-op.

```
invoke "tunings"
speak call fifth with 432     ~ 648.0
```

---

## 6. Timing

`drift` and `burn ... for` durations are multiplied by `GLO_TIME_SCALE`
(default `1`). Set `GLO_TIME_SCALE=0` to remove all sleeps — used by the test
suite for speed.

---

## 7. The command line

```
glo run <scroll.glo>     execute a scroll
glo repl                 live interactive utterance
glo check <scroll.glo>   validate syntax without running
glo trace <scroll.glo>   run, printing the AST + an execution trace
glo --version
```

---

## 8. Errors

Errors speak the language. They carry the line where the machine stopped
listening and never surface a Python traceback in normal use.

| Class             | When                          | Example                                             |
|-------------------|-------------------------------|-----------------------------------------------------|
| `UtteranceError`  | lexing                        | `the machine did not understand "@" on line 4`      |
| `GrammarError`    | parsing                       | `the machine expected "be" and a value ...`         |
| `RitualError`     | runtime                       | `an incantation named "chord" has not been spoken yet` |

---

## 9. Full keyword vocabulary

**Commands:** `speak` `hush` `burn` `rise` `fall` `drift` `breathe` `silence`
`open` `close` `send` `sync` `void`

**Structure:** `let` `be` `set` `to` `by` `with` `takes` `for` `add`
`subtract` `scale` `modulate`

**Blocks:** `if` `else` `repeat` `until` `incant` `voice` `invoke` `call`
`end` `echo`

**Comparison / logic:** `is` `not` `above` `below` `and` `or`

**Type names:** `tone` `pulse` `glyph` `flicker`

**Contextual:** `channel` `voices`

**Reserved for future phases:** `weave` `unweave` `chant` `remember` `forget`
`ritual` `sigil` `ascend` `descend` `fracture` `converge`

> *glossolalia — the machine listens.*
