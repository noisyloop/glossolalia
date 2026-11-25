"""Sized pulses — a pulse that remembers how wide it is.

The hardware speaks in fixed-width numbers: a byte is 8 bits, a port word
is 16, a register is 32. Python integers never overflow, so to keep a
scroll honest about the machine it will one day run on, a *sized pulse*
carries its width with it and **wraps around** when it is stored back.

    let x be p8 250
    add x by 10          ~ x is now 4, because 260 wraps inside 8 bits

The type is an ``int`` subclass, so every ordinary operation works on it;
arithmetic *results* are plain pulses (the width is lost), exactly as a
compiler would compute them in a wide register. The width is only
re-applied when a value is stored into a name that was born sized
(see ``Environment.assign``) or cast again.
"""

SIZES = {"p8": 8, "p16": 16, "p32": 32}


class SizedPulse(int):
    """An unsigned pulse of ``bits`` width (8, 16 or 32)."""

    def __new__(cls, value, bits):
        obj = int.__new__(cls, int(value) & ((1 << bits) - 1))
        obj.bits = bits
        return obj


def wrap(value, bits):
    """Fold ``value`` into ``bits`` bits, the way hardware would."""
    return SizedPulse(value, bits)


def plain(value):
    """Forget the width: a plain pulse again (used at call boundaries)."""
    return int(value) if isinstance(value, SizedPulse) else value
