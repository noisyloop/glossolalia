#!/bin/sh
# The in-OS agents (kernel/agents.glo): boot headless, no network, and check
# that every round has coder -> runner -> checker with "checker: ok".
set -e
cd "$(dirname "$0")/.."
make -s build/test_agents.iso
out=$(timeout 30 qemu-system-i386 -cdrom build/test_agents.iso -nic none -m 128 -display none \
  -device isa-debug-exit,iobase=0xf4,iosize=0x04 -no-reboot -serial stdio 2>&1 | tr -d '\r') || true
echo "$out"
[ "$(echo "$out" | grep -c '^checker: ok')" = 6 ] && echo "$out" | grep -q '^agents ok' && echo "agents: pass" || { echo "agents: FAIL"; exit 1; }
