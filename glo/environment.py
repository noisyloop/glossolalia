"""Memory — where names are kept.

A simple lexical scope chain. ``let`` binds a name in the current scope.
``set`` (and the arithmetic mutations) find an existing binding by
walking outward toward the global scroll.
"""

from .errors import RitualError


class Environment:
    def __init__(self, parent=None):
        self.vars = {}
        self.parent = parent

    def define(self, name, value):
        """let — bind (or rebind) in this scope."""
        self.vars[name] = value

    def assign(self, name, value, line=None):
        """set — reassign an existing binding, searching outward."""
        env = self
        while env is not None:
            if name in env.vars:
                env.vars[name] = value
                return
            env = env.parent
        raise RitualError(
            f'the name "{name}" was set before it was ever spoken with "let"',
            line,
        )

    def get(self, name, line=None):
        env = self
        while env is not None:
            if name in env.vars:
                return env.vars[name]
            env = env.parent
        raise RitualError(
            f'the machine has never heard the name "{name}"', line
        )

    def has(self, name):
        env = self
        while env is not None:
            if name in env.vars:
                return True
            env = env.parent
        return False
