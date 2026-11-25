# glossolalia-os

A small, offline, 32-bit x86 operating system written in
[Glossolalia](https://github.com/noisyloop/glossolalia), plus a compiler for
Glossolalia written in Glossolalia itself. It is a **learning project**: the
code is meant to be read, every file says *why* it exists, and where there
was a simple way and a fast way, the simple way won.

> The deliverable is a bootable ISO that runs in QEMU. No network stack, no
> NIC drivers, no sockets — QEMU runs with `-nic none`, forever.

## What is in the box

| path | what |
|---|---|
| `SPEC-BARE.md` | language spec v0.2: the **bare** and **full** tongues, and every design choice with its alternatives |
| `glossc/` | the compiler, in `.glo`: `lexer` → `parser` → `gen` (NASM) |
| `rt/` | the runtime, in the bare tongue: console, numbers, bit-operation definitions |
| `targets/` | the only non-`.glo` code: short, line-by-line-commented NASM glue (`linux.asm`, `kernel.asm`) |
| `kernel/` | the operating system, in `.glo` (`main.glo`), and the self-test kernels (`test_*.glo`) |
| `examples/` | programs that run on the interpreter *and* as native binaries |
| `tools/glorun.py` | runs a scroll on the interpreter with room for a compiler to breathe |
| `tests/` | `pytest`: parity, compiler errors, (later) headless QEMU boots |
| `JOURNAL.md` | what each milestone taught about how an operating system works |

## The bootstrap plan

`glossc` is written in `.glo`. At first it runs on the existing Python
interpreter (`../glossolalia`). Once it can compile itself (milestone 7),
the interpreter is no longer needed to build anything.

```
glossc.glo --(Python interpreter)--> glossc.asm --nasm--> glossc (native, stage 1)
glossc.glo --(stage 1)-----------> glossc.asm  ==  the asm above, byte for byte
```

## Packages (Arch Linux)

```
sudo pacman -S nasm qemu-system-x86 qemu-audio-pipewire grub libisoburn mtools python python-pytest
```

(`libisoburn` provides `xorriso`, which `grub-mkrescue` needs; `mtools`
makes the FAT image GRUB's EFI part uses.) On Debian/Ubuntu: `nasm
qemu-system-x86 grub-pc-bin grub-common xorriso mtools python3 python3-pytest`.
You also need the interpreter, either checked out next to this repo, or (as in
the `glossolalia` repository, where this directory lives) one level up:

```
git clone https://github.com/noisyloop/glossolalia ../glossolalia
```

## Commands

```
make iso      # build/glossolalia.iso  (glossc -> nasm -> grub-mkrescue)
make run      # boot it: qemu-system-i386 -cdrom ... -nic none, sound via PipeWire
make test     # interpreter tests + compiler tests + headless QEMU boots
make clean
```

`make run` is exactly

```
qemu-system-i386 -cdrom build/glossolalia.iso -nic none -audiodev pipewire,id=snd -machine pcspk-audiodev=snd
```

The tests boot ISOs with `-display none -serial stdio` and QEMU's
`isa-debug-exit` device (port `0xf4`): a kernel that calls `depart N` ends
QEMU with status `(N<<1)|1`, which is how a test kernel reports pass/fail.
Every boot has a timeout. A few tests also ask the QEMU monitor to dump
video memory, so they read the actual screen.

Compile a program for Linux and run it:

```
python3 tools/glorun.py glossc/glossc.glo --target linux --home . -o /tmp/h.asm examples/hello.glo
nasm -f bin -I ./ /tmp/h.asm -o /tmp/h && chmod +x /tmp/h && /tmp/h
```

## What you see when you boot it

```
glossolalia-os
the machine listens.
type help for commands.
glo> help
commands:
  help             this list
  echo <text>      say it back
  add <a> <b>      add two numbers (decimal or 0x hex)
  peek <address>   read a byte of memory
  ticks            milliseconds since boot
  uptime           seconds since boot
  burn <hz> [ms]   sound a tone (until silence, or for ms)
  silence          stop the tone
  halt             stop the machine
```

The same text appears on the screen (VGA text mode) and on COM1.

## Status

| milestone | | |
|---|---|---|
| 0 | interpreter: hex, sized pulses, bare words, files, bytes, argv, exit codes | done (on branch `claude/glossolalia-os` of `../glossolalia`) |
| 1 | glossc v0: bare tongue → NASM → Linux ELF, parity suite | done |
| 2 | first boot: Multiboot stub, VGA text + COM1, `make iso`, headless boot tests | done |
| 3 | GDT, IDT, PIC remap, `ward` handlers, PIT-driven `drift`, PS/2 keyboard (with timeouts), REPL | done |
| 4 | sound: `burn` / `silence` through the PC speaker (PIT channel 2); tests measure the pitch from a recorded WAV | done |
| 5 | heap allocator; glyphs and strands in compiled code | **not started** (design in SPEC-BARE.md §6.2) |
| 6 | the choir: cooperative `voice` / `breathe` / `sync voices` | **not started** |
| 7 | self-hosting: glossc compiles itself, byte-identical | **not started** |
| stretch | glossc inside the OS, GRUB-module ramdisk | not attempted |

What works today: a bootable, offline, GRUB-loaded kernel written entirely in
the bare tongue, compiled by a compiler written in Glossolalia (running on the
Python interpreter), with interrupts, timer, keyboard, a REPL and sound.
What does not exist yet: the compiler cannot compile itself, so the Python
interpreter is still needed to build everything (milestone 7 removes that).
