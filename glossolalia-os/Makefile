# glossolalia-os — a small offline i386 operating system, and the compiler
# (glossc) that builds it, both written in Glossolalia.
#
#   make test     run every test: interpreter, compiler, headless QEMU boots
#   make iso      build/glossolalia.iso
#   make run      boot it in QEMU (with sound, no network)
#
# Where the reference interpreter lives (the Python one). It is used to build
# glossc the first time; once glossc can compile itself (milestone 7) nothing
# else needs it.
GLOSSOLALIA ?= $(shell if [ -d ../glo ]; then echo ..; else echo ../glossolalia; fi)
export GLOSSOLALIA

PY      ?= python3
GLORUN  := $(PY) tools/glorun.py
NASM    ?= nasm
QEMU    ?= qemu-system-i386

COMPILER := $(wildcard glossc/*.glo)
RUNTIME  := $(wildcard rt/*.glo)
GLUE     := $(wildcard targets/*.asm)

.DELETE_ON_ERROR:
.PHONY: all iso run test test-interpreter test-compiler test-boot clean
all: iso

# ---- building a kernel: scroll -> NASM -> flat binary -> bootable ISO -------
# glossc turns kernel/NAME.glo into one NASM file; nasm makes a flat binary
# (no linker); grub-mkrescue wraps it with GRUB into an ISO.
build/%.asm: kernel/%.glo $(wildcard kernel/*.glo) $(COMPILER) $(RUNTIME) $(GLUE)
	@mkdir -p build
	$(GLORUN) glossc/glossc.glo --target kernel --home . -o $@ $<

build/%.bin: build/%.asm
	$(NASM) -f bin -I./ $< -o $@

build/%.iso: build/%.bin grub.cfg
	rm -rf build/iso-$*
	mkdir -p build/iso-$*/boot/grub
	cp $< build/iso-$*/boot/kernel.bin
	cp grub.cfg build/iso-$*/boot/grub/grub.cfg
	grub-mkrescue -o $@ build/iso-$* 2>/dev/null
	rm -rf build/iso-$*

iso: build/glossolalia.iso
build/glossolalia.iso: build/main.iso
	cp $< $@

# Boot it. Offline forever: -nic none. The sound goes through PipeWire.
run: build/glossolalia.iso
	$(QEMU) -cdrom build/glossolalia.iso -nic none -audiodev pipewire,id=snd -machine pcspk-audiodev=snd

# The interpreter's own tests (milestone 0 added bare-tongue tests there).
test-interpreter:
	cd $(GLOSSOLALIA) && GLO_TIME_SCALE=0 $(PY) -m pytest -q

# glossc running on the interpreter, parity against native binaries.
test-compiler:
	$(PY) -m pytest -q tests/test_compiler.py

# Headless boots: -display none, COM1 on stdout, isa-debug-exit for the
# verdict, and a timeout on every run.
test-boot:
	$(PY) -m pytest -q tests/test_boot.py tests/test_interrupts.py tests/test_sound.py

test: test-interpreter test-compiler test-boot

clean:
	rm -rf build
