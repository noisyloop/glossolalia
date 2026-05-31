"""The parser — hearing order in the words.

A hand-written recursive-descent parser. It is line-oriented: each
utterance (statement) ends at a NEWLINE. Blocks open with a keyword
(``if`` ``repeat`` ``until`` ``incant`` ``voice``) and close with
``end``.

Operator precedence in expressions, lowest to highest:

    or
    and
    is  not(!=)  above  below
    add(+)  subtract(-)          (postfix:  a add by b)
    scale(*)  modulate(%)        (postfix:  a scale by b)
    not(prefix)  type-casts
    primary  ( call / name / literal / (group) )
"""

from . import ast_nodes as ast
from .errors import GrammarError
from .lexer import tokenize


# Words that, appearing at the start of a line, begin a statement.
_BLOCK_TERMINATORS = {"end", "else"}

# Infix word-operators grouped by precedence tier.
_COMPARE_OPS = {"is", "not", "above", "below"}
_ADDITIVE_OPS = {"add", "subtract"}
_MULTIPLICATIVE_OPS = {"scale", "modulate"}
_CAST_OPS = {"tone", "pulse", "glyph", "flicker"}
# prefix word-operators that take a single operand
_PREFIX_OPS = {"count", "ascend", "descend", "unweave"}
# tokens that can begin an expression (used to detect an empty `weave`)
_EXPR_STARTERS = (
    {"NUMBER", "STRING", "NAME", "void", "call", "LPAREN", "not",
     "weave", "unweave", "count", "ascend", "descend", "fracture",
     "converge"}
    | _CAST_OPS
)


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    # ── token helpers ────────────────────────────────────────────
    @property
    def current(self):
        return self.tokens[self.pos]

    def peek(self, offset=1):
        idx = self.pos + offset
        if idx >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[idx]

    def advance(self):
        tok = self.tokens[self.pos]
        if tok.type != "EOF":
            self.pos += 1
        return tok

    def check(self, type_):
        return self.current.type == type_

    def accept(self, type_):
        if self.check(type_):
            return self.advance()
        return None

    def expect(self, type_, what):
        if self.check(type_):
            return self.advance()
        raise GrammarError(
            f"the machine expected {what} but heard "
            f'"{self._describe(self.current)}"',
            self.current.line,
        )

    @staticmethod
    def _describe(tok):
        if tok.type == "EOF":
            return "the end of the scroll"
        if tok.type == "NEWLINE":
            return "the end of the line"
        return str(tok.value)

    def skip_newlines(self):
        while self.check("NEWLINE"):
            self.advance()

    def end_statement(self):
        """Every statement must end at a NEWLINE or the end of scroll."""
        if self.check("EOF"):
            return
        if self.check("NEWLINE"):
            self.advance()
            return
        raise GrammarError(
            "the machine heard more words than it expected: "
            f'"{self._describe(self.current)}"',
            self.current.line,
        )

    # ── entry point ──────────────────────────────────────────────
    def parse_program(self):
        body = []
        self.skip_newlines()
        while not self.check("EOF"):
            body.append(self.statement())
            self.skip_newlines()
        return ast.Program(body)

    def parse_block(self, terminators=("end",)):
        """Parse statements until a terminator keyword. Returns
        (statements, terminator_token). Consumes the terminator."""
        body = []
        self.skip_newlines()
        while not self.check("EOF") and self.current.type not in terminators:
            body.append(self.statement())
            self.skip_newlines()
        if self.check("EOF"):
            joined = " or ".join(f'"{t}"' for t in terminators)
            raise GrammarError(
                f"the machine waited for {joined} but the scroll ended",
                self.current.line,
            )
        terminator = self.advance()
        return body, terminator

    # ── statements ───────────────────────────────────────────────
    def statement(self):
        tok = self.current
        handler = _STATEMENT_DISPATCH.get(tok.type)
        if handler is None:
            # A bare NAME at statement start is almost always a typo or a
            # word the machine doesn't know in this position.
            raise GrammarError(
                f'the machine did not understand "{self._describe(tok)}"',
                tok.line,
            )
        return handler(self)

    def _speak(self):
        line = self.advance().line
        value = self.expression()
        self.end_statement()
        return ast.Speak(value, line)

    def _hush(self):
        line = self.advance().line
        self.end_statement()
        return ast.Hush(line)

    def _silence(self):
        line = self.advance().line
        self.end_statement()
        return ast.Silence(line)

    def _breathe(self):
        line = self.advance().line
        self.end_statement()
        return ast.Breathe(line)

    def _burn(self):
        line = self.advance().line
        freq = self.expression()
        duration = None
        if self.accept("for"):
            duration = self.expression()
        self.end_statement()
        return ast.Burn(freq, duration, line)

    def _drift(self):
        line = self.advance().line
        seconds = None
        if not self.check("NEWLINE") and not self.check("EOF"):
            seconds = self.expression()
        self.end_statement()
        return ast.Drift(seconds, line)

    def _rise(self):
        return self._step(+1)

    def _fall(self):
        return self._step(-1)

    def _step(self, direction):
        line = self.advance().line
        name = self.expect("NAME", "a name to change").value
        amount = None
        if self.accept("by"):
            amount = self.expression()
        self.end_statement()
        return ast.Step(name, direction, amount, line)

    def _mutate(self):
        op = self.current.type
        line = self.advance().line
        name = self.expect("NAME", "a name to change").value
        self.expect("by", '"by" and an amount')
        amount = self.expression()
        self.end_statement()
        return ast.Mutate(name, op, amount, line)

    def _let(self):
        line = self.advance().line
        name = self.expect("NAME", "a name to bind").value
        self.expect("be", '"be" and a value')
        value = self.expression()
        self.end_statement()
        return ast.Let(name, value, line)

    def _set(self):
        line = self.advance().line
        name = self.expect("NAME", "a name to set").value
        self.expect("to", '"to" and a value')
        value = self.expression()
        self.end_statement()
        return ast.Set(name, value, line)

    def _if(self):
        line = self.advance().line
        condition = self.expression()
        self.end_statement()
        body, terminator = self.parse_block(("end", "else"))
        otherwise = []
        if terminator.type == "else":
            self.end_statement()
            otherwise, _ = self.parse_block(("end",))
        self.end_statement()
        return ast.If(condition, body, otherwise, line)

    def _repeat(self):
        line = self.advance().line
        # foreach form:  repeat <name> in <strand>
        if self.check("NAME") and self.peek().type == "in":
            name = self.advance().value
            self.advance()  # consume "in"
            iterable = self.expression()
            self.end_statement()
            body, _ = self.parse_block(("end",))
            self.end_statement()
            return ast.ForEach(name, iterable, body, line)
        # counted form:  repeat <n>
        count = self.expression()
        self.end_statement()
        body, _ = self.parse_block(("end",))
        self.end_statement()
        return ast.Repeat(count, body, line)

    def _ritual(self):
        line = self.advance().line
        self.end_statement()
        body, _ = self.parse_block(("end",))
        self.end_statement()
        return ast.Ritual(body, line)

    def _remember(self):
        line = self.advance().line
        name = self.expect("NAME", "a name to remember").value
        self.expect("as", '"as" and a value')
        value = self.expression()
        self.end_statement()
        return ast.Remember(name, value, line)

    def _forget(self):
        line = self.advance().line
        name = self.expect("NAME", "a name to forget").value
        self.end_statement()
        return ast.Forget(name, line)

    def _sigil(self):
        line = self.advance().line
        name = self.expect("NAME", "a name for the sigil").value
        self.expect("be", '"be" and a value')
        value = self.expression()
        self.end_statement()
        return ast.Sigil(name, value, line)

    def _chant(self):
        line = self.advance().line
        count = self.unary()       # a primary-ish count, then the value
        value = self.expression()
        self.end_statement()
        return ast.Chant(count, value, line)

    def _until(self):
        line = self.advance().line
        condition = self.expression()
        self.end_statement()
        body, _ = self.parse_block(("end",))
        self.end_statement()
        return ast.Until(condition, body, line)

    def _incant(self):
        line = self.advance().line
        name = self.expect("NAME", "a name for the incantation").value
        params = []
        if self.accept("takes"):
            params.append(self.expect("NAME", "a parameter name").value)
            while self.accept("COMMA") or self.accept("and"):
                params.append(self.expect("NAME", "a parameter name").value)
        self.end_statement()
        body, _ = self.parse_block(("end",))
        self.end_statement()
        return ast.Incant(name, params, body, line)

    def _call(self):
        line = self.advance().line
        name = self.expect("NAME", "the name of an incantation").value
        args = self._call_args()
        self.end_statement()
        return ast.CallStmt(name, args, line)

    def _call_args(self):
        args = []
        if self.accept("with"):
            args.append(self.expression())
            while self.accept("COMMA"):
                args.append(self.expression())
        return args

    def _echo(self):
        line = self.advance().line
        value = None
        if not self.check("NEWLINE") and not self.check("EOF"):
            value = self.expression()
        self.end_statement()
        return ast.Echo(value, line)

    def _void(self):
        # Bare ``void`` as a statement = return nothing.
        line = self.advance().line
        self.end_statement()
        return ast.VoidReturn(line)

    def _voice(self):
        line = self.advance().line
        name = self.expect("NAME", "a name for the voice").value
        self.end_statement()
        body, _ = self.parse_block(("end",))
        self.end_statement()
        return ast.Voice(name, body, line)

    def _sync(self):
        line = self.advance().line
        self.expect("voices", '"voices" after "sync"')
        self.end_statement()
        return ast.Sync(line)

    def _open(self):
        line = self.advance().line
        self.expect("channel", '"channel" after "open"')
        target = None
        if not self.check("NEWLINE") and not self.check("EOF"):
            target = self.expression()
        self.end_statement()
        return ast.OpenChannel(target, line)

    def _close(self):
        line = self.advance().line
        self.expect("channel", '"channel" after "close"')
        self.end_statement()
        return ast.CloseChannel(line)

    def _send(self):
        line = self.advance().line
        address = self.unary()        # primary-ish, so the value can follow
        value = self.expression()
        self.end_statement()
        return ast.Send(address, value, line)

    def _invoke(self):
        line = self.advance().line
        scroll = self.expression()
        self.end_statement()
        return ast.Invoke(scroll, line)

    # ── expressions ──────────────────────────────────────────────
    def expression(self):
        return self.logic_or()

    def logic_or(self):
        node = self.logic_and()
        while self.check("or"):
            line = self.advance().line
            node = ast.Binary("or", node, self.logic_and(), line)
        return node

    def logic_and(self):
        node = self.comparison()
        while self.check("and"):
            line = self.advance().line
            node = ast.Binary("and", node, self.comparison(), line)
        return node

    def comparison(self):
        node = self.additive()
        while self.current.type in _COMPARE_OPS:
            op = self.current.type
            line = self.advance().line
            node = ast.Binary(op, node, self.additive(), line)
        return node

    def additive(self):
        node = self.multiplicative()
        # postfix word form:  a add by b   /   a subtract by b
        while self.current.type in _ADDITIVE_OPS and self.peek().type == "by":
            op = self.current.type
            line = self.advance().line       # consume add/subtract
            self.advance()                   # consume by
            node = ast.Binary(op, node, self.multiplicative(), line)
        return node

    def multiplicative(self):
        node = self.unary()
        # postfix word form:  a scale by b  /  a modulate by b
        while (
            self.current.type in _MULTIPLICATIVE_OPS
            and self.peek().type == "by"
        ):
            op = self.current.type
            line = self.advance().line       # consume scale/modulate
            self.advance()                   # consume by
            node = ast.Binary(op, node, self.unary(), line)
        return node

    def unary(self):
        tok = self.current
        if tok.type == "not":
            line = self.advance().line
            return ast.Unary("not", self.unary(), line)
        if tok.type in _CAST_OPS or tok.type in _PREFIX_OPS:
            op = tok.type
            line = self.advance().line
            return ast.Unary(op, self.unary(), line)
        if tok.type in ("fracture", "converge"):
            op = tok.type
            line = self.advance().line
            operand = self.unary()
            self.expect("by", '"by" and a separator')
            separator = self.unary()
            return ast.Binary(op, operand, separator, line)
        return self.postfix()

    def postfix(self):
        node = self.primary()
        # indexing:  strand at 0   /   glyph at 2
        while self.check("at"):
            line = self.advance().line
            index = self.primary()
            node = ast.Binary("at", node, index, line)
        return node

    def primary(self):
        tok = self.current

        if tok.type == "weave":
            line = self.advance().line
            elements = []
            if self.current.type in _EXPR_STARTERS:
                elements.append(self.expression())
                while self.accept("COMMA"):
                    elements.append(self.expression())
            return ast.StrandLiteral(elements, line)

        if tok.type == "NUMBER":
            self.advance()
            return ast.Literal(tok.value, tok.line)

        if tok.type == "STRING":
            self.advance()
            return ast.Literal(tok.value, tok.line)

        if tok.type == "void":
            self.advance()
            return ast.Literal(None, tok.line)

        if tok.type == "NAME":
            self.advance()
            return ast.Name(tok.value, tok.line)

        if tok.type == "call":
            line = self.advance().line
            name = self.expect("NAME", "the name of an incantation").value
            args = self._call_args()
            return ast.CallExpr(name, args, line)

        if tok.type == "LPAREN":
            self.advance()
            node = self.expression()
            self.expect("RPAREN", "a closing )")
            return node

        raise GrammarError(
            f'the machine expected a value but heard "{self._describe(tok)}"',
            tok.line,
        )


# Dispatch table: first token type → bound statement parser.
_STATEMENT_DISPATCH = {
    "speak": Parser._speak,
    "hush": Parser._hush,
    "silence": Parser._silence,
    "breathe": Parser._breathe,
    "burn": Parser._burn,
    "drift": Parser._drift,
    "rise": Parser._rise,
    "fall": Parser._fall,
    "add": Parser._mutate,
    "subtract": Parser._mutate,
    "scale": Parser._mutate,
    "modulate": Parser._mutate,
    "let": Parser._let,
    "set": Parser._set,
    "if": Parser._if,
    "repeat": Parser._repeat,
    "until": Parser._until,
    "ritual": Parser._ritual,
    "remember": Parser._remember,
    "forget": Parser._forget,
    "sigil": Parser._sigil,
    "chant": Parser._chant,
    "incant": Parser._incant,
    "call": Parser._call,
    "echo": Parser._echo,
    "void": Parser._void,
    "voice": Parser._voice,
    "sync": Parser._sync,
    "open": Parser._open,
    "close": Parser._close,
    "send": Parser._send,
    "invoke": Parser._invoke,
}


def parse(source):
    """Parse source text into a Program AST."""
    return Parser(tokenize(source)).parse_program()
