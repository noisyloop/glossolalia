"""The shapes of meaning — AST nodes.

Plain data classes. The parser builds them; the evaluator walks them.
Each carries a ``line`` so runtime errors can still say where they were
spoken.
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional


# ── Expressions ──────────────────────────────────────────────────────

@dataclass
class Literal:
    value: Any
    line: int = 0


@dataclass
class Name:
    name: str
    line: int = 0


@dataclass
class Unary:
    op: str            # "not", or a type cast: "tone"/"pulse"/"glyph"/"flicker"
    operand: Any
    line: int = 0


@dataclass
class Binary:
    op: str            # is above below not(!=) and or scale modulate add subtract
    left: Any
    right: Any
    line: int = 0


@dataclass
class CallExpr:
    name: str
    args: List[Any] = field(default_factory=list)
    line: int = 0


# ── Statements ───────────────────────────────────────────────────────

@dataclass
class Speak:
    value: Any
    line: int = 0


@dataclass
class Hush:
    line: int = 0


@dataclass
class Silence:
    line: int = 0


@dataclass
class Breathe:
    line: int = 0


@dataclass
class Burn:
    freq: Any
    duration: Optional[Any] = None
    line: int = 0


@dataclass
class Drift:
    seconds: Any = None
    line: int = 0


@dataclass
class Step:
    """rise / fall — increment or decrement a name by an amount."""
    name: str
    direction: int          # +1 rise, -1 fall
    amount: Optional[Any] = None
    line: int = 0


@dataclass
class Mutate:
    """add / subtract / scale / modulate a name by an expression."""
    name: str
    op: str                 # add subtract scale modulate
    amount: Any = None
    line: int = 0


@dataclass
class Let:
    name: str
    value: Any
    line: int = 0


@dataclass
class Set:
    name: str
    value: Any
    line: int = 0


@dataclass
class If:
    condition: Any
    body: List[Any]
    otherwise: List[Any] = field(default_factory=list)
    line: int = 0


@dataclass
class Repeat:
    count: Any
    body: List[Any] = field(default_factory=list)
    line: int = 0


@dataclass
class Until:
    condition: Any
    body: List[Any] = field(default_factory=list)
    line: int = 0


@dataclass
class Incant:
    name: str
    params: List[str] = field(default_factory=list)
    body: List[Any] = field(default_factory=list)
    line: int = 0


@dataclass
class CallStmt:
    name: str
    args: List[Any] = field(default_factory=list)
    line: int = 0


@dataclass
class Echo:
    """Return a value from an incantation."""
    value: Any = None
    line: int = 0


@dataclass
class VoidReturn:
    """Return nothing from an incantation (early exit)."""
    line: int = 0


@dataclass
class Voice:
    name: str
    body: List[Any] = field(default_factory=list)
    line: int = 0


@dataclass
class Sync:
    line: int = 0


@dataclass
class OpenChannel:
    target: Optional[Any] = None
    line: int = 0


@dataclass
class CloseChannel:
    line: int = 0


@dataclass
class Send:
    address: Any
    value: Any
    line: int = 0


@dataclass
class Invoke:
    scroll: Any
    line: int = 0


@dataclass
class Program:
    body: List[Any] = field(default_factory=list)
