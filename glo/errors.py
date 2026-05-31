"""Errors that speak the language.

Glossolalia never says ``SyntaxError: unexpected token``. The machine
speaks back in its own tongue. Every failure is a sentence.
"""


class GlossolaliaError(Exception):
    """Base of every utterance the machine refuses.

    Carries an optional ``line`` so the machine can say *where* it
    stopped listening.
    """

    def __init__(self, message, line=None):
        self.raw_message = message
        self.line = line
        super().__init__(self.spoken())

    def spoken(self):
        if self.line is not None:
            return f"{self.raw_message} on line {self.line}"
        return self.raw_message


class UtteranceError(GlossolaliaError):
    """The lexer heard a sound it cannot make.

    e.g. ``the machine did not understand "flarb" on line 4``
    """


class GrammarError(GlossolaliaError):
    """The parser heard words in an order that has no meaning."""


class RitualError(GlossolaliaError):
    """The evaluator could not perform the rite at runtime.

    e.g. ``an incantation named "chord" has not been spoken yet``
    """
