# JOURNAL — what each milestone taught about how an operating system works

Written at the end of milestone 4 (v0.2.0 adds a heap/glyph runtime and the choir as libraries; self-hosting still fails). The last
section says what they would have taught and how the design is laid out for them.

## Milestone 0 — teaching the interpreter to talk to a machine

*Nothing here is an OS yet, and that is the lesson:* an OS is mostly **numbers
at addresses**. The CPU's whole interface to the world is "store this number
at that address" (memory, including the screen) and "write this number to that
port" (devices). So the language needs only four verbs — `inscribe`, `peek`,
`whisper`, `listen` — plus the right *widths*. Width is the interesting part:
hardware registers are 8, 16 or 32 bits, and writing a byte is a different
operation from writing a word. Hence sized pulses that **wrap**: `p8 250 + 10`
is 4 because that is what an 8-bit register does. Simulating RAM and ports in
the interpreter meant every hardware program could be tested on a laptop first.
A small surprise: an existing test used `peek` as a *name*, so the hardware
words became contextual (words only inside a `rite`) — compatibility is a
design constraint even for toy languages.

## Milestone 1 — a compiler, and a machine to run it on

A compiler is a translator with one hard rule: **decide where every value
lives**. Locals go on the stack at `[ebp-4k]`, globals in fixed cells, and every
expression's result goes in one register (`eax`). Once that is decided, code
generation is mechanical — a stack machine in thirty lines. The Linux target
taught what a "program" even is: an ELF file is a 52-byte header, a 32-byte
program header saying "map these bytes here, readable-writable-executable", and
code. `int 0x80` is just the one instruction that hands control to the kernel.
Skipping the linker (one flat NASM file, `-f bin`) removed a whole world of
object formats, and writing the ELF header by hand made the format stop being
magic. Testing the *same* programs on the interpreter and as native binaries
caught real bugs immediately (a label named `R11` is a register in NASM).

## Milestone 2 — what a bootloader hands you

GRUB leaves the CPU in 32-bit protected mode with flat segments, interrupts
off, and an unspecified stack. Everything else is yours. The Multiboot header
is nothing but a magic number, flags, a checksum and — in the "address fields"
form — the load addresses, so a flat binary boots without ELF or a linker. The
screen turned out to be *memory*: 80x25 cells of (character, colour) at
`0xB8000`; "printing" is `inscribe`. Scrolling is a memory copy. COM1 is the
second console, and the first one a program can read: that is what made
headless tests possible (QEMU's `isa-debug-exit` port turns `depart N` into a
process exit status). Reading video memory back through the QEMU monitor made
the screen driver *testable*, not just viewable.

## Milestone 3 — the CPU as something that gets interrupted

Interrupts invert the picture: the CPU does not poll, the world taps it on the
shoulder. To receive taps you must build three tables/devices in the right
order: a **GDT** (even "flat" mode runs through segments), an **IDT** (vector ->
handler), and a remapped **PIC** (its defaults collide with CPU exception
vectors 8-15), and only then `sti`. A handler is not a function: it must save
*every* register and return with `iretd`, and CPU exceptions with an error code
need it discarded first — so the compiler writes the stub for `ward`. The
timer made time exist (`drift` is "halt until the next tick"); the keyboard
showed that hardware speaks scancodes (make/break), not letters, and that real
devices need **timeouts** on every wait because a dead 8042 would otherwise hang
the kernel. A divide by zero reaching `ward 0` was the moment "exceptions are
interrupts too" became concrete.

## Milestone 4 — sound without a sound card

The PC speaker is one wire the CPU can flip, optionally fed from PIT channel 2
— the same chip that counts milliseconds. A pitch is `1193182 / N`, so a note
is: set the mode, write a 16-bit count in two bytes, open a gate. Verifying it
meant recording QEMU's speaker to a WAV and counting zero crossings: 440.0 Hz
and 880.0 Hz, exactly. Hardware you can *measure* is the best kind to learn on.

## Milestones 5-7 — not built

* **5 (heap, glyphs, strands):** the design is in SPEC-BARE.md §6.2: tagged
  words (odd = pulse), 16-byte object headers as immutable views over a shared
  buffer, so repeated appends are amortised O(1) without a garbage collector;
  the allocator and runtime are bare-tongue scrolls. Lesson it would teach:
  what a `malloc` is, and why a language needs a type tag at run time.
* **6 (the choir):** cooperative multitasking is one assembly routine that swaps
  stack pointers; `breathe` calls it. Lesson: a "thread" is a stack plus saved
  registers.
* **7 (self-hosting):** `glossc` is already written in the subset the compiler
  can compile (no tones, no rituals); what is missing is the full-tongue back
  end of milestone 5. Lesson: a compiler compiling itself is the strongest test
  there is — the output of stage 1 and stage 2 must match byte for byte.
