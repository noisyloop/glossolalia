"""glossolalia — utterance is execution.

A real, interpreted programming language whose syntax reads like
incantation. This package is the interpreter: lexer, parser, evaluator,
and the audio / OSC voices of the machine.

Public surface::

    from glo import run_source, run_file, Interpreter

Or use the ``glo`` command line (see ``glo.cli``).
"""

__version__ = "0.1.0"

from .errors import (  # noqa: E402
    GlossolaliaError,
    GrammarError,
    RitualError,
    UtteranceError,
)


def run_source(source, **kwargs):
    """Parse and evaluate a string of glossolalia."""
    from .evaluator import Interpreter

    interp = Interpreter(**kwargs)
    interp.run_source(source)
    return interp


def run_file(path, **kwargs):
    """Parse and evaluate a ``.glo`` scroll from disk."""
    from .evaluator import Interpreter

    interp = Interpreter(**kwargs)
    interp.run_file(path)
    return interp


__all__ = [
    "__version__",
    "run_source",
    "run_file",
    "GlossolaliaError",
    "UtteranceError",
    "GrammarError",
    "RitualError",
]
