"""The lexer — turning breath into tokens.

A ``.glo`` scroll is line-oriented. Newlines separate utterances. Words
are either keywords (part of the tongue) or names (things you have
named). Numbers become ``pulse`` (whole) or ``tone`` (decimal). Anything
between quotes is a ``glyph``. A ``~`` begins a comment — a thought the
machine ignores until the end of the line.
"""

from .errors import UtteranceError
from . import limits

# The full tongue. Anything here is a keyword; everything else that looks
# like a word is a NAME (something the speaker named).
KEYWORDS = {
    # commands
    "speak", "hush", "burn", "rise", "fall", "drift", "breathe",
    "silence", "open", "close", "send", "sync", "void",
    # structure
    "let", "be", "set", "to", "by", "with", "takes", "for",
    "add", "subtract", "scale", "modulate",
    # blocks
    "if", "else", "repeat", "until", "incant", "voice", "invoke",
    "call", "end", "echo",
    # comparison / logic
    "is", "not", "above", "below", "and", "or",
    # type casts
    "tone", "pulse", "glyph", "flicker",
    # words that read as keywords in place
    "channel", "voices",
}


class Token:
    __slots__ = ("type", "value", "line")

    def __init__(self, type_, value, line):
        self.type = type_
        self.value = value
        self.line = line

    def __repr__(self):
        return f"Token({self.type!r}, {self.value!r}, line={self.line})"


def _is_name_start(ch):
    return ch.isalpha() or ch == "_"


def _is_name_part(ch):
    return ch.isalnum() or ch == "_"


def tokenize(source):
    """Turn source text into a flat list of tokens ending in EOF.

    NEWLINE tokens are emitted between lines and act as utterance
    terminators. Blank lines and comment-only lines collapse into a
    single NEWLINE so the parser can skip them cleanly.
    """
    n = len(source)
    if limits.MAX_SOURCE_CHARS and n > limits.MAX_SOURCE_CHARS:
        # Refuse oversized input before allocating tokens for it.
        raise UtteranceError(
            "the scroll is too long for the machine to hold at once", 1
        )

    tokens = []
    line = 1
    i = 0
    line_has_content = False

    def push(type_, value):
        nonlocal line_has_content
        if limits.MAX_TOKENS and len(tokens) >= limits.MAX_TOKENS:
            raise UtteranceError(
                "the scroll has more words than the machine can hold", line
            )
        tokens.append(Token(type_, value, line))
        line_has_content = True

    while i < n:
        ch = source[i]

        # End of a physical line.
        if ch == "\n":
            if line_has_content:
                tokens.append(Token("NEWLINE", "\\n", line))
            line += 1
            line_has_content = False
            i += 1
            continue

        # Whitespace (not newline).
        if ch in " \t\r":
            i += 1
            continue

        # Comment to end of line.
        if ch == "~":
            while i < n and source[i] != "\n":
                i += 1
            continue

        # Glyph — a quoted string. Supports \" \\ \n \t escapes.
        if ch == '"':
            i += 1
            chars = []
            start_line = line
            while i < n and source[i] != '"':
                c = source[i]
                if c == "\\" and i + 1 < n:
                    nxt = source[i + 1]
                    chars.append(
                        {"n": "\n", "t": "\t", '"': '"', "\\": "\\"}.get(nxt, nxt)
                    )
                    i += 2
                    continue
                if c == "\n":
                    raise UtteranceError(
                        "a glyph was opened but never closed", start_line
                    )
                chars.append(c)
                i += 1
                if limits.MAX_GLYPH_CHARS and len(chars) > limits.MAX_GLYPH_CHARS:
                    raise UtteranceError(
                        "a glyph is longer than the machine can hold",
                        start_line,
                    )
            if i >= n:
                raise UtteranceError(
                    "a glyph was opened but never closed", start_line
                )
            i += 1  # closing quote
            push("STRING", "".join(chars))
            continue

        # Number — pulse (int) or tone (float). Allows leading minus.
        if ch.isdigit() or (
            ch == "-" and i + 1 < n and source[i + 1].isdigit()
        ):
            start = i
            i += 1
            is_float = False
            while i < n and (source[i].isdigit() or source[i] == "."):
                if source[i] == ".":
                    if is_float:
                        break  # second dot ends the number
                    is_float = True
                i += 1
            text = source[start:i]
            push("NUMBER", float(text) if is_float else int(text))
            continue

        # Parentheses for grouping.
        if ch == "(":
            push("LPAREN", "(")
            i += 1
            continue
        if ch == ")":
            push("RPAREN", ")")
            i += 1
            continue

        # Comma separates arguments and parameters.
        if ch == ",":
            push("COMMA", ",")
            i += 1
            continue

        # A word — keyword or name. Allow ``/`` inside so OSC-ish bare
        # words still tokenize, though addresses are normally glyphs.
        if _is_name_start(ch):
            start = i
            i += 1
            while i < n and _is_name_part(source[i]):
                i += 1
            word = source[start:i]
            if word in KEYWORDS:
                push(word, word)
            else:
                push("NAME", word)
            continue

        # The machine heard a sound it cannot make.
        raise UtteranceError(
            f'the machine did not understand "{ch}"', line
        )

    if line_has_content:
        tokens.append(Token("NEWLINE", "\\n", line))
    tokens.append(Token("EOF", None, line))
    return tokens
