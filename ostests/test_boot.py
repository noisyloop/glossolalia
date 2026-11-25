"""Milestone 2 — first boot.

Each test boots a real ISO (GRUB + the compiled kernel) in QEMU with no
window: -display none, COM1 on a pipe, no network, a timeout on every run.
"""
import os

from helpers import boot, make, screen, start_vm, wait_for_text


def test_the_kernel_boots_and_speaks_on_serial():
    code, text = boot(make("build/test_boot.iso"))
    assert text.splitlines() == [
        "glossolalia-os",
        "the machine listens.",
        "12345",
        "-7",
        "boot ok",
    ]
    assert code == 16            # `depart 16` in kernel/test_boot.glo


def test_the_iso_is_a_cdrom_grub_can_boot():
    iso = make("build/test_boot.iso")
    assert os.path.getsize(iso) > 1_000_000       # GRUB's own image is in there


def test_vga_text_screen_shows_the_output_and_scrolls(tmp_path):
    iso = make("build/test_vga.iso")
    p, mon, serial = start_vm(iso, tmp_path)
    try:
        wait_for_text(serial, "screen ok")
        rows, attr = screen(mon, tmp_path)
    finally:
        p.kill()
        p.wait()
    # 1 banner + 30 numbered lines + "screen ok" = 32 lines; the screen holds
    # 24 of them plus the row the cursor sits on, so the first 8 scrolled off.
    assert rows[0] == "line 8"
    assert rows[22] == "line 30"
    assert rows[23] == "screen ok"
    assert rows[24] == ""
    assert attr == 0x0B          # light cyan on black
