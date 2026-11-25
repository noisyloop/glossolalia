---
name: build-iso
description: Build the bootable glossolalia-os ISO (build/glossolalia.iso) quickly and with minimal output. Use when asked for the ISO, to build the OS, or to rebuild after kernel/compiler changes.
---

# build-iso

Builds `build/glossolalia.iso` (i386, GRUB/Multiboot, offline) from `kernel/*.glo`
via glossc -> NASM -> flat binary -> grub-mkrescue.

1. Tools: need `nasm`, `python3`, `grub-mkrescue`, `xorriso`. If `grub-mkrescue` is missing:
   `apt-get update -q && apt-get install -y -q --no-install-recommends grub-pc-bin grub-common xorriso mtools`
   (needs `apt-get update` first in a fresh container).
2. Build, quietly: `make iso 2>&1 | tail -5` (the repo's Makefile, run from the repo root; no -j needed, it is a few seconds).
3. Verify: `ls -la build/glossolalia.iso` (~5 MB).
4. Deliver with SendUserFile (display: attach). Do not cat or read the binary.
5. Optional boot check (only if `qemu-system-i386` exists): `make test-boot`. Skip otherwise; do not install QEMU unless asked.

Keep it cheap: no exploration, no re-reading specs, don't rebuild if the ISO is newer than every file in kernel/, glossc/, rt/, targets/.
Milestones 5-7 (heap, choir, self-hosting) are not built; the ISO reflects milestones 0-4 (boot, interrupts, keyboard REPL, PC-speaker sound).
