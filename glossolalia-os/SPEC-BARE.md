# Glossolalia Specification v0.2 — the two tongues

**Extends:** `../glossolalia/SPEC.md` (v0.1.0, the interpreter's language)
**Implemented by:** the interpreter (milestone 0) and `glossc` (this repo)

> *The bare tongue speaks to the machine. The full tongue speaks through it.*

> **Implementation status.** The bare tongue, `rite`, `ward`, the machine words,
> both targets and `burn`/`drift` are implemented and tested (milestones 0-4).
> The **full tongue's compiled form** (§1, §6.2, §6.3: tagged values, glyphs and
> strands, the heap, voices) is the *design* for milestones 5-7, which are not
> built yet. The interpreter already runs the full tongue.

v0.1 describes a language that lives on top of Python: unbounded integers,
garbage-collected strings and lists, threads, a sound card. An operating
system has none of that. v0.2 therefore splits the language in two:

| | **Bare tongue** | **Full tongue** |
|---|---|---|
| Heap | none | yes (a bump/free-list heap the OS provides) |
| Values | `pulse`, `p8`, `p16`, `p32`, `flicker` — raw machine words | `pulse`, `glyph`, `strand`, `flicker`, `void` — tagged words |
| Glyph / strand | no (a glyph *literal* is allowed only as the thing `speak` says) | yes |
| Voices | no | yes (cooperative, milestone 6) |
| Hardware words | yes, inside a `rite` | no — it calls bare incantations |
| Who runs it | the CPU, directly | the CPU, with the runtime (`rt/`) underneath |

The full tongue is today's language (SPEC.md) *minus* what a machine with no
floating point and no OS cannot give it (see §9). The bare tongue is the
floor the full tongue stands on: the allocator, the glyph and strand
runtime, the console and the interrupt handlers are all written in it.

Both tongues share one grammar (SPEC.md §1–§4). Everything below is
*additions*.

---

## 1. Declaring a tongue

A scroll is **full** unless its first comment line says otherwise:

```
~ tongue: bare
```

`glossc` reads that comment; to the interpreter it is just a comment. A
program is a set of scrolls pulled together with `invoke`; each scroll has
its own tongue. **The bare tongue may never call into the full tongue**
(it has no heap to build the arguments in). The full tongue may call bare
incantations; the compiler converts arguments and results at the border
(§6.3).

## 2. Pulses

All numbers are whole. A *plain* `pulse` is a signed 32-bit two's-complement
word. Three **sized pulses** are unsigned and exactly as wide as their name:

| type | width | range |
|---|---|---|
| `p8` | 8 bit | 0 … 255 |
| `p16` | 16 bit | 0 … 65535 |
| `p32` | 32 bit | 0 … 4294967295 |

**Hex literals.** `0xB8000`, `0xff`, `0x0` are pulses. (Lowercase `x`; hex
digits either case; there is no negative hex literal — write `0 subtract by 1`.)

**Casts.** `p8 e`, `p16 e`, `p32 e` are prefix operators (precedence tier 6,
like `pulse e`). They **wrap around**: `p8 300` is `44`, `p8 -1` is `255`.

**A name remembers the size it was born with.**

```
let x be p8 250       ~ x is a p8 because its first value was one
add x by 10           ~ 260 wraps inside 8 bits: x is 4
set x to 1000         ~ 232
```

Every store into a sized name wraps to its size — `set`, `rise`, `fall`,
`add by` and the other change-in-place statements. **Expressions are computed
wide**; the width is re-applied only on a store, a cast, or an `inscribe`.
So `speak x add by 10` says `14` when x is 4, not a wrapped value.

*The static type of an expression* (the compiler needs it; the interpreter
carries the same information in the value):

| expression | type |
|---|---|
| `p8 e`, `p16 e`, `p32 e` | that size |
| `peek p8 a` … | that size; plain `peek a` is a plain `pulse` |
| `listen p16 port n` … | that size; plain `listen port n` is `p8` |
| a name | the size it was born with (its **latest** `let`) |
| a literal, `call`, arithmetic, anything else | plain `pulse` |
| comparison, `and`, `or`, `not`, `flicker e` | `flicker` |

Parameters and results of incantations are always plain pulses — a callee
does not know how wide the caller's name was.

`speak` prints a plain pulse as signed decimal, a sized pulse as unsigned
decimal, a flicker as `true` / `false`. `above` / `below` compare unsigned
when either side is a `p32`, signed otherwise. `modulate` is the machine's
remainder (truncating); behaviour for a negative left side is the CPU's, not
Python's — keep to non-negative operands where the interpreter must agree.

Plain pulses wrap at 32 bits when compiled; in the interpreter they are
unbounded. Use `p32` where overflow is meant.

## 3. The new words

Five words reach the machine and one marks code that may use them. **They
are ordinary names outside a `rite`** — so an existing scroll with an
incantation called `peek` keeps working — and become words of the language
only inside one.

### 3.1 `rite … end`

```
rite
  ...raw code...
end
```

Marks raw code. `inscribe`, `peek`, `whisper`, `listen` are legal only inside
a rite (lexically — an incantation *declared* inside a rite counts); using one
elsewhere is a grammar error: `the machine will not "inscribe" outside a rite`.
Unlike a `ritual`, a rite opens **no scope**: names and incantations it
declares belong to the scroll around it. That is what lets a whole library
of incantations sit inside one rite.

### 3.2 Memory

```
inscribe <value> at <address>      ~ statement
peek [p8|p16|p32] <address>        ~ expression
```

`inscribe` writes the value's bytes, **little-endian**, at the address. How
many bytes is decided by the value's static size: `inscribe p8 65 at a`
writes one byte, `p16` two, `p32` or an unsized pulse four.
`peek p8 a` reads one byte (a `p8`); `peek p32 a` four (unsigned); plain
`peek a` four, as a signed plain pulse. Memory nobody wrote reads `0` in the
interpreter (which simulates RAM as a sparse byte map); on the machine it
reads whatever is there.

`peek`, like `count` and `bones`, is a **prefix operator**: it takes the
following *primary* as its address. Write `peek (base add by 2)`, not
`peek base add by 2` (which is `(peek base) add by 2`).
In `inscribe <value> at <addr>` the word `at` ends the value (it does not
mean "index"); parenthesise a value that needs indexing.

### 3.3 Ports

```
whisper <value> to port <port>     ~ statement:  outb / outw / outl
listen [p8|p16|p32] port <port>    ~ expression: inb  / inw  / inl
```

`whisper` is as wide as its value (`p8` → `out dx, al`). `listen` is `p8`
unless a size is given. In the interpreter and in the **Linux target** a port
is a latch: `listen` returns what `whisper` last wrote (masked to width),
initially 0 — Linux will not let a normal process touch real ports, and this
keeps the two worlds comparable. On the kernel target they are the real
instructions.

### 3.4 `ward <vector> … end`

```
ward 33
  rite
    let key be listen port 0x60
    whisper p8 0x20 to port 0x20
  end
end
```

An interrupt handler for IDT vector `<vector>` (a literal pulse). The
compiler emits a stub that saves all registers, calls the body, restores
them and executes `iretd`; for the CPU exceptions that push an error code
(8, 10–14, 17, 21, 29, 30) the stub discards it. **It does not acknowledge
the interrupt controller** — a hardware handler does that itself with
`whisper`. The address of the stub is `call ward_addr with 33` (§7).
Under the interpreter a `ward` is recorded and never fires; on the Linux
target it compiles but is never installed.

## 4. Statements of the bare tongue

`speak` (a pulse expression, or a glyph *literal*), `hush`, `let`, `set`,
`rise`, `fall`, `add/subtract/scale/modulate … by`, `if/else`, `repeat <n>`,
`until`, `incant`, `call`, `echo`, `void`, `sigil`, `invoke`, `depart`,
`rite`, `ward`, `inscribe`, `whisper`.

Expressions: pulse literals (decimal, hex), names, `call`, `not`,
`p8/p16/p32/pulse/flicker` casts, `peek`, `listen`, and the binary
operators `or and is not above below add subtract scale modulate`.

There is **no heap**: no `weave`, `at`, `count`, `fracture`, glyph values,
`glyph` cast, or strand. A glyph literal is accepted in exactly two places:
as the whole operand of `speak`, and as the operand of `say` (§7). A bare
incantation takes and returns pulses.

`speak "text"` prints the text and a newline; `speak n` prints a pulse and
a newline. Where it prints is the target's business: standard output on
Linux, the screen and COM1 in the kernel.

## 5. Where ownership would go

The ask is to *design for* Rust-style ownership and borrowing without
implementing it. The design:

* Every heap value (glyph, strand) is already an **immutable view** — a
  16-byte header `{kind, length, data, buffer}` pointing into a shared
  buffer (§6.2). Views are never mutated, only created. That is exactly the
  shape a borrow needs: a shared view is a *shared borrow*; the buffer's
  single "owner" is whoever holds the view that ends at the buffer's end
  (the one the append fast path may extend).
* The check would be a **separate compiler pass** between parsing and code
  generation (`glossc/check.glo`, *not written*): walk each incantation's
  AST with a map `name → {owned | moved | borrowed}`. `let a be b` would move
  `b` (unless `b` is a pulse, which is `Copy`); passing a strand to an
  incantation would borrow it for the call; using a moved name would be a
  grammar error spoken in the machine's voice.
* **Reserved words** (nothing parses them yet): `lend` (explicit shared
  borrow), `claim` (explicit move), `yield` is *not* reserved — `echo`
  already means return.
* The code generator would need **no change**: ownership is erased after the
  check, as in Rust. The hook is one line in `glossc.glo`'s driver, marked
  `~ OWNERSHIP: borrow check would run here`.

## 6. How the compiled tongues work

### 6.1 Calling convention (both tongues)

Arguments are pushed **left to right** (so evaluation order is source order);
the callee finds parameter *i* of *n* at `[ebp + 8 + 4·(n−1−i)]`; the result
is in `eax`; the **caller** removes the arguments. Locals live at
`[ebp − 4·k]`. Incantation `name` is the label `g_name`. Every global
(`let` at the top of a scroll) is a 32-bit cell `v_name`.

### 6.2 Full-tongue values (tagged words)

A value is one 32-bit word:

| word | meaning |
|---|---|
| odd (`…1`) | a **pulse**, the word shifted right by one (31-bit signed) |
| `0` | `void` |
| `4` / `8` | `false` / `true` |
| any multiple of 4 ≥ 16 | pointer to a heap or static **object** |

An object is a 16-byte header `{kind, length, data, buffer}`; `kind` is 1
(glyph, `data` points at bytes) or 2 (strand, `data` at 4-byte words).
`buffer` points at a block `{capacity, used}` the view lives in (0 for a
literal). `a add by b` on two strands or glyphs **appends in place** when
`a`'s view ends exactly at the buffer's `used` mark and there is room —
returning a *new header* over the same buffer, so the old value is
untouched. That turns repeated appends from O(n²) into amortised O(1),
which is what lets the self-hosted compiler build a megabyte of assembly
without a garbage collector. There is no garbage collector: the heap only
grows (the allocator can `free`; the runtime never does).

Glyphs are **byte strings** (UTF-8 on the way in and out); `count`, `at`
count bytes. Compiler sources are ASCII, so the interpreter (which counts
characters) and the compiled code agree.

### 6.3 Crossing from full to bare

A full call to a bare incantation checks each argument is a pulse (else:
`the bare incantation "put" was given something that is not a pulse`),
passes it untagged, and tags the result (a result that does not fit 31 bits
is a limitation — addresses and ports always do).

### 6.4 Errors

Compile errors speak the machine's voice, as in SPEC.md §8, and `glossc`
exits 1:

```
the machine did not understand "@" on line 4
the machine will not "inscribe" outside a rite on line 9
the bare tongue has no strands on line 3
an incantation named "chord" has not been spoken yet on line 12
the sigil "root" is fixed and cannot be changed on line 7
```

A *compiled* program that fails at run time says
`the machine stopped: <reason> on line N` on standard error (Linux) or the
console (kernel) and exits 1 (the kernel power-cycles QEMU with status 1 when
a test device is present).

## 7. Machine words (intrinsics)

A **call to one of these names is compiled in line** unless the program
defines an incantation of the same name (then yours wins — that is how the
interpreter can run the reference versions in `rt/bits.glo`). They exist
because the grammar has no bit operators and no division.

| call | meaning |
|---|---|
| `shl x, n` `shr x, n` `sar x, n` | shift left / logical right / arithmetic right |
| `band a, b` `bor a, b` `bxor a, b` | bitwise and / or / xor |
| `udiv a, b` `umod a, b` `sdiv a, b` | unsigned quotient / remainder, signed quotient |
| `say "text"` | write the text, **no newline** (a glyph *literal* only) |
| `text_addr "text"` `text_len "text"` | address / byte length of a static text |
| `ward_addr v` | address of the stub of `ward v` |

Target-supplied words (declared by the target, implemented in its hand-written
assembly glue; the compiler only needs to know the name and arity):

| target | words |
|---|---|
| kernel | `load_gdt base, limit` · `load_idt base, limit` · `sti` · `cli` · `hlt` · `switch_stacks save_at, to` |
| linux | `syscall nr, a, b, c` |

## 8. Targets

* **linux** — a static i386 ELF, no libc, `int 0x80` system calls. Exists so
  the compiler can be tested without a VM, and so it can compile itself. Heap
  by `brk`; files, `heed`, `depart` and the standard streams work.
* **kernel** — a Multiboot 1 image for GRUB: flat binary with the
  address-fields header, loaded at 1 MiB, protected mode. `speak` goes to
  the VGA text screen and COM1. No files, no `heed`; `depart` stops the
  machine (writes the QEMU `isa-debug-exit` device).

Both are one flat NASM file (`nasm -f bin`) — **there is no linker**.

## 9. What the compiled tongues do not do

Compared with the interpreter (SPEC.md): no `tone` (floats): no decimal
literals, `tone` cast, `ascend`, `descend`; no `open`/`close channel`, `send`,
`remember`/`forget`, `ritual`, `chant`, `fracture`, `converge` *yet*;
pulses in the full tongue are 31-bit. `burn` and `drift` exist in the kernel
tongue but take **whole milliseconds** and whole hertz (the interpreter takes
seconds and tones): `burn 440 for 500`, `drift 250`. Using something the
compiler does not speak is an error in the machine's voice:
`the compiler does not yet speak "ritual" on line 3`.

## 10. Design options considered (and what was picked)

Where a choice was genuinely open, the options and the pick are recorded here.

**A. How a scroll says which tongue it is.**
(1) A first-line comment `~ tongue: bare` — **picked**: zero new words, the
interpreter needs no change. (2) A keyword `tongue bare` — needs the
interpreter to learn it. (3) A file extension (`.bglo`) — invisible when a
scroll is pasted or `invoke`d by name.

**B. Where a pulse's size lives.**
(1) A name inherits the size of its first value (`let x be p8 250`) —
**picked**: no new syntax, one rule, works identically in a Python
interpreter (value carries its width) and a compiler (static type).
(2) A declaration form `let x as p8 be 250` — explicit, but a second way to
bind. (3) Casts only, no automatic wrapping — simplest, but then "wrap-around
overflow" is something every programmer must remember to write.

**C. How the hardware words are exposed.**
(1) Contextual words legal only inside `rite` — **picked**: an existing test
scroll already calls an incantation `peek`, and a word that is only a word
inside a rite cannot break anyone. (2) Global keywords — breaks that scroll.
(3) Built-in incantations (`call peek with a`) — hides that they are special
and cannot take a size.

**D. How the full tongue represents values, given heterogeneous strands**
(`weave "binary", op, left, right` mixes glyphs, pulses and strands).
(1) Tag every word (odd = pulse, else pointer/immediate) — **picked**: a few
lines of tag logic in the runtime, whole language works. (2) Box everything —
simpler tags, every `1 add by 1` allocates. (3) Static typing, rejecting
heterogeneous strands — a much smaller runtime, but the compiler's own AST
would not compile.

**E. Division and bit operations**, which the grammar lacks and a compiler,
an itoa and a GDT all need.
(1) Compiler machine words (§7) with portable reference definitions
(`rt/bits.glo`) so the interpreter can run the same programs — **picked**.
(2) New operators (`divide by`, …) — five more words in every tongue and the
interpreter. (3) Write them as loops everywhere — correct, ~30× slower, and
the self-hosted compiler uses them for every tagged number.

**F. Units for `burn … for` and `drift`.**
(1) Seconds, as in SPEC.md — needs floats, which the OS does not have.
(2) Whole milliseconds / hertz in the compiled tongues — **picked**.
(3) Fixed-point tones — a new numeric type for two statements.

**G. Ports on the Linux test target.** (1) Latches that remember the last
write — **picked**, identical to the interpreter's. (2) `ioperm` and real
ports — needs root and hardware. (3) Reject the words — loses all parity
tests for code that drives hardware.

**H. One compile or separate objects.** (1) One whole-program flat NASM file —
**picked**: no linker, no object format, no symbol export rules.
(2) Per-scroll objects plus `ld` — real separate compilation, a toolchain
dependency, and a lot of format.
