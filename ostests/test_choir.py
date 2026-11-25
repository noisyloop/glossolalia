"""Milestone 6 — the choir: cooperative voices swapping stacks."""
from helpers import boot, make


def test_three_voices_take_turns():
    code, text = boot(make("build/test_choir.iso"))
    assert text.splitlines() == [
        "main 1", "alto 1", "bass 1", "main 2", "alto 2", "bass 2",
        "main 3", "choir ok",
    ]
    assert code == 16
