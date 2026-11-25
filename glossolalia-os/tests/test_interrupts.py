"""Milestone 3 — interrupts: GDT, IDT, PIC, timer, keyboard, REPL."""
import time

from helpers import ask, boot, make, start_vm, type_text, wait_for_text


def test_timer_keyboard_timeout_and_exception_ward():
    code, text = boot(make("build/test_irq.iso"))
    assert text.splitlines() == [
        "interrupts on",
        "timer ok",                    # drift 100 took ~100 timer ticks
        "keyboard timeout ok",         # kb_getc_timeout gave up with -1
        "about to divide by zero",
        "exception: divide error",     # the CPU fault reached `ward 0`
    ]
    assert code == 99


def test_repl_reads_the_keyboard_and_obeys(tmp_path):
    iso = make("build/glossolalia.iso")
    p, mon, serial = start_vm(iso, tmp_path)
    try:
        wait_for_text(serial, "glo> ")
        # Before anything scrolls, the first cell of the screen holds the
        # banner's "g" (103): the REPL can read the screen it is writing to.
        assert ask(mon, serial, "peek 0xb8000").strip() == "103"
        assert "commands:" in ask(mon, serial, "help")
        assert ask(mon, serial, "add 2 3").strip() == "5"
        assert ask(mon, serial, "add 0x10 0xff").strip() == "271"
        assert ask(mon, serial, "echo hello there").strip() == "hello there"
        # Backspace erases: "ecz" BS "ho yo" is "echo yo"
        assert ask(mon, serial, "ecz\bho yo").strip().endswith("yo")
        # Shift gives capitals
        assert ask(mon, serial, "echo AbC").strip() == "AbC"
        assert int(ask(mon, serial, "ticks").strip()) > 500
        assert "unknown command" in ask(mon, serial, "dance")
        assert ask(mon, serial, "").strip() == ""          # empty line: just a prompt
        # halt ends the machine (through the test device)
        type_text(mon, "halt\n")
        p.wait(timeout=20)
        assert p.returncode == 1                           # depart 0 -> (0<<1)|1
    finally:
        if p.poll() is None:
            p.kill()
            p.wait()
