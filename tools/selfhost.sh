#!/bin/sh
# Milestone 7: the compiler compiles itself, with no Python in the loop.
#   stage 1: the seed (bootstrap/glossc) compiles glossc's sources
#   stage 2: that compiler compiles the sources again
# The two outputs must be byte for byte the same. With --update the seed is
# replaced by the result.  (The seed itself was first built by the Python
# interpreter: python3 tools/glorun.py glossc/glossc.glo ... see README.)
set -e
cd "$(dirname "$0")/.."
mkdir -p build
SEED=${SEED:-bootstrap/glossc}
echo "stage 1: $SEED compiles glossc"
"$SEED" --target linux --home . -o build/stage1.asm glossc/glossc.glo
nasm -f bin -I./ build/stage1.asm -o build/glossc1 && chmod +x build/glossc1
echo "stage 2: stage 1 compiles glossc"
build/glossc1 --target linux --home . -o build/stage2.asm glossc/glossc.glo
cmp build/stage1.asm build/stage2.asm
nasm -f bin -I./ build/stage2.asm -o build/glossc2 && chmod +x build/glossc2
cmp build/glossc1 build/glossc2
echo "self-hosted: byte-identical ($(wc -c < build/stage2.asm) bytes of assembly)"
if [ "$1" = "--update" ]; then cp build/glossc2 bootstrap/glossc; echo "seed updated"; fi
