"""Keep the editor grammar honest.

The VS Code TextMate grammar lists the language's keywords by hand. These
tests fail the moment the interpreter learns a word the grammar does not
highlight (or the grammar names a word the interpreter never knew), so the
two can never silently drift apart.
"""


def _words_in_grammar():
    import json
    import os
    import re

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    grammar_path = os.path.join(
        root, "editors", "vscode", "syntaxes", "glossolalia.tmLanguage.json"
    )
    with open(grammar_path, encoding="utf-8") as fh:
        data = json.load(fh)

    found = set()

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "match" and isinstance(value, str):
                    for group in re.findall(r"\(([a-z|]+)\)", value):
                        found.update(group.split("|"))
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return found


# Words the grammar handles as value-constants rather than lexer keywords.
_GRAMMAR_EXTRAS = {"true", "false", "void"}


def test_every_keyword_is_highlighted():
    from glo.lexer import KEYWORDS

    missing = sorted(KEYWORDS - _words_in_grammar())
    assert not missing, f"keywords missing from the VS Code grammar: {missing}"


def test_grammar_invents_no_unknown_keywords():
    from glo.lexer import KEYWORDS

    unknown = sorted(_words_in_grammar() - KEYWORDS - _GRAMMAR_EXTRAS)
    assert not unknown, f"grammar highlights words the language lacks: {unknown}"
