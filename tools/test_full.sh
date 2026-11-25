#!/bin/sh
# Milestones 5 and 7, no Python: every examples/full/*.glo is compiled by the
# native compiler and must print what examples/full/NAME.out says; then the
# compiler must compile itself byte for byte (tools/selfhost.sh).
set -e
cd "$(dirname "$0")/.."
mkdir -p build/test
fail=0
for f in examples/full/*.glo; do
  n=$(basename "$f" .glo)
  bootstrap/glossc --target linux --home . -o "build/test/full_$n.asm" "$f"
  nasm -f bin -I./ "build/test/full_$n.asm" -o "build/test/full_$n"
  chmod +x "build/test/full_$n"
  "build/test/full_$n" > "build/test/full_$n.got"
  if cmp -s "build/test/full_$n.got" "examples/full/$n.out"; then echo "ok   $n"; else echo "FAIL $n"; diff "examples/full/$n.out" "build/test/full_$n.got" | head -5; fail=1; fi
done
sh tools/selfhost.sh
exit $fail
