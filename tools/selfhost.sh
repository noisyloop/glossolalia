#!/bin/sh
# Milestone 7: stage 1 = glossc (on the interpreter) compiles glossc; stage 2 =
# that native glossc compiles glossc again; the two outputs must be identical.
set -e
mkdir -p build
echo "stage 1: interpreter -> glossc.asm"
python3 tools/glorun.py glossc/glossc.glo --target linux --home . -o build/stage1.asm glossc/glossc.glo
nasm -f bin -I./ build/stage1.asm -o build/glossc1 && chmod +x build/glossc1
echo "stage 2: native glossc -> glossc.asm"
build/glossc1 --target linux --home . -o build/stage2.asm glossc/glossc.glo
cmp build/stage1.asm build/stage2.asm && echo "self-hosted: byte-identical"
