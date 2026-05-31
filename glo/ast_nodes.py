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


@dataclass
class StrandLiteral:
    """weave a, b, c — a strand (ordered collection)."""
    elements: List[Any] = field(default_factory=list)
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
class ForEach:
    """repeat <name> in <strand> — walk a strand or glyph."""
    name: str
    iterable: Any = None
    body: List[Any] = field(default_factory=list)
    line: int = 0


@dataclass
class Ritual:
    """ritual ... end — a block with its own scope."""
    body: List[Any] = field(default_factory=list)
    line: int = 0


@dataclass
class Remember:
    """remember <name> as <expr> — write to the deep memory layer."""
    name: str
    value: Any = None
    line: int = 0


@dataclass
class Forget:
    name: str
    line: int = 0


@dataclass
class Sigil:
    """sigil <name> be <expr> — an unchangeable binding."""
    name: str
    value: Any = None
    line: int = 0


@dataclass
class Chant:
    """chant <count> <expr> — speak a value a number of times."""
    count: Any
    value: Any
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
