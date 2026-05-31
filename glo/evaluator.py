"""The evaluator — execution as ritual.

A tree-walking interpreter. It walks the AST the parser built and makes
each utterance happen: prints, tones, loops, incantations, voices.
"""

import os
import sys
import time

from . import ast_nodes as ast
from . import limits
from .audio import AudioEngine
from .environment import Environment
from .errors import RitualError
from .osc import OSCBridge
from .parser import parse


class ReturnSignal(Exception):
    """Carries a value (or nothing) back out of an incantation."""

    def __init__(self, value=None):
        self.value = value


class Closure:
    __slots__ = ("decl",)

    def __init__(self, decl):
        self.decl = decl


def to_glyph(value):
    """Render a runtime value the way the machine speaks it."""
    if value is None:
        return "void"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, float):
        # 432.0 stays 432.0 (a tone), but 0.5 stays 0.5
        return repr(value)
    return str(value)


def is_truthy(value):
    if value is None or value is False:
        return False
    if value is True:
        return True
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return len(value) > 0
    return True


class Interpreter:
    def __init__(self, audio=None, osc=None, quiet=False, time_scale=None,
                 trace=False):
        self.globals = Environment()
        self.incantations = {}
        self.audio = audio if audio is not None else AudioEngine(quiet=quiet)
        self.osc = osc if osc is not None else OSCBridge(quiet=quiet)
        self.quiet = quiet
        self.trace = trace
        if time_scale is None:
            time_scale = float(os.environ.get("GLO_TIME_SCALE", "1") or "1")
        self.time_scale = time_scale
        self._scroll_dirs = [os.getcwd()]
        self._invoked = set()
        self._voice_threads = []
        self._call_depth = 0
        self._voices_spawned = 0

    # ── public entry points ──────────────────────────────────────
    def run_source(self, source, scroll_dir=None):
        program = parse(source)
        if scroll_dir:
            self._scroll_dirs.append(scroll_dir)
        try:
            self.execute_block(program.body, self.globals)
        finally:
            if scroll_dir:
                self._scroll_dirs.pop()

    def run_file(self, path):
        with open(path, "r", encoding="utf-8") as fh:
            source = fh.read()
        self.run_source(source, scroll_dir=os.path.dirname(os.path.abspath(path)))

    # ── block / statement execution ──────────────────────────────
    def execute_block(self, statements, env):
        for stmt in statements:
            self.execute(stmt, env)

    def execute(self, node, env):
        if self.trace:
            print(f"  · {type(node).__name__} (line {getattr(node, 'line', '?')})",
                  file=sys.stderr)
        method = _EXEC_DISPATCH.get(type(node))
        if method is None:  # pragma: no cover - defensive
            raise RitualError(
                f"the machine cannot perform {type(node).__name__}",
                getattr(node, "line", None),
            )
        return method(self, node, env)

    # ── statements ───────────────────────────────────────────────
    def _exec_speak(self, node, env):
        value = self.evaluate(node.value, env)
        print(to_glyph(value), file=sys.stdout)

    def _exec_hush(self, node, env):
        pass  # the no-op. intentional silence.

    def _exec_silence(self, node, env):
        self.audio.silence()

    def _exec_breathe(self, node, env):
        # yield to other voices
        time.sleep(0)

    def _exec_burn(self, node, env):
        freq = self.evaluate(node.freq, env)
        duration = None
        if node.duration is not None:
            duration = self.evaluate(node.duration, env)
            if duration is not None:
                duration = float(duration) * self.time_scale
        self.audio.burn(freq, duration)

    def _exec_drift(self, node, env):
        seconds = 0.0
        if node.seconds is not None:
            seconds = float(self.evaluate(node.seconds, env))
        seconds *= self.time_scale
        if seconds > 0:
            time.sleep(seconds)

    def _exec_step(self, node, env):
        current = env.get(node.name, node.line)
        amount = 1
        if node.amount is not None:
            amount = self.evaluate(node.amount, env)
        env.assign(node.name, current + node.direction * amount, node.line)

    def _exec_mutate(self, node, env):
        current = env.get(node.name, node.line)
        amount = self.evaluate(node.amount, env)
        if node.op == "add":
            result = current + amount
        elif node.op == "subtract":
            result = current - amount
        elif node.op == "scale":
            result = current * amount
        elif node.op == "modulate":
            result = self._modulo(current, amount, node.line)
        else:  # pragma: no cover
            raise RitualError(f"unknown change {node.op}", node.line)
        env.assign(node.name, result, node.line)

    def _exec_let(self, node, env):
        env.define(node.name, self.evaluate(node.value, env))

    def _exec_set(self, node, env):
        env.assign(node.name, self.evaluate(node.value, env), node.line)

    def _exec_if(self, node, env):
        if is_truthy(self.evaluate(node.condition, env)):
            self.execute_block(node.body, env)
        elif node.otherwise:
            self.execute_block(node.otherwise, env)

    def _exec_repeat(self, node, env):
        count = self.evaluate(node.count, env)
        try:
            count = int(count)
        except (TypeError, ValueError):
            raise RitualError(
                "repeat needs a count, a whole number of times", node.line
            )
        if limits.MAX_ITERATIONS and count > limits.MAX_ITERATIONS:
            raise RitualError(
                "repeat was asked to run more times than the machine allows",
                node.line,
            )
        for _ in range(max(0, count)):
            self.execute_block(node.body, env)

    def _exec_until(self, node, env):
        spins = 0
        cap = limits.MAX_ITERATIONS
        while not is_truthy(self.evaluate(node.condition, env)):
            self.execute_block(node.body, env)
            spins += 1
            if cap and spins >= cap:
                raise RitualError(
                    "the until-loop spun longer than the machine allows; "
                    "it may never come to rest",
                    node.line,
                )

    def _exec_incant(self, node, env):
        self.incantations[node.name] = Closure(node)

    def _exec_call_stmt(self, node, env):
        self.invoke_incant(node.name, node.args, env, node.line)

    def _exec_echo(self, node, env):
        value = None
        if node.value is not None:
            value = self.evaluate(node.value, env)
        raise ReturnSignal(value)

    def _exec_void(self, node, env):
        raise ReturnSignal(None)

    def _exec_voice(self, node, env):
        import threading

        if limits.MAX_VOICES and self._voices_spawned >= limits.MAX_VOICES:
            raise RitualError(
                "more voices were raised than the machine can hold at once",
                node.line,
            )
        self._voices_spawned += 1
        holder = {"error": None}

        def run():
            child = Environment(parent=self.globals)
            try:
                self.execute_block(node.body, child)
            except ReturnSignal:
                pass
            except RitualError as exc:
                holder["error"] = exc

        thread = threading.Thread(target=run, name=f"voice:{node.name}",
                                  daemon=True)
        self._voice_threads.append((node.name, thread, holder))
        thread.start()

    def _exec_sync(self, node, env):
        pending = self._voice_threads
        self._voice_threads = []
        self._voices_spawned = 0  # the cap counts voices sounding at once
        for name, thread, holder in pending:
            thread.join()
        for name, thread, holder in pending:
            if holder["error"] is not None:
                raise holder["error"]

    def _exec_open_channel(self, node, env):
        target = None
        if node.target is not None:
            target = self.evaluate(node.target, env)
        self.audio.open_channel(target)

    def _exec_close_channel(self, node, env):
        self.audio.close_channel()

    def _exec_send(self, node, env):
        address = self.evaluate(node.address, env)
        value = self.evaluate(node.value, env)
        self.osc.send(address, value)

    def _exec_invoke(self, node, env):
        if (
            limits.MAX_INVOKE_DEPTH
            and len(self._scroll_dirs) > limits.MAX_INVOKE_DEPTH
        ):
            raise RitualError(
                "scrolls invoke one another deeper than the machine allows",
                node.line,
            )
        name = self.evaluate(node.scroll, env)
        path = self._resolve_scroll(name, node.line)
        if path in self._invoked:
            return  # already invoked; do not re-evaluate
        self._invoked.add(path)
        with open(path, "r", encoding="utf-8") as fh:
            source = fh.read()
        program = parse(source)
        self._scroll_dirs.append(os.path.dirname(path))
        try:
            # invoked scrolls share the global scope: their incantations
            # and bindings become available to the caller.
            self.execute_block(program.body, self.globals)
        finally:
            self._scroll_dirs.pop()

    # ── incantation calls ────────────────────────────────────────
    def invoke_incant(self, name, arg_nodes, env, line):
        closure = self.incantations.get(name)
        if closure is None:
            raise RitualError(
                f'an incantation named "{name}" has not been spoken yet', line
            )
        decl = closure.decl
        args = [self.evaluate(a, env) for a in arg_nodes]
        if len(args) != len(decl.params):
            raise RitualError(
                f'the incantation "{name}" takes {len(decl.params)} '
                f"but was given {len(args)}",
                line,
            )
        if limits.MAX_CALL_DEPTH and self._call_depth >= limits.MAX_CALL_DEPTH:
            raise RitualError(
                f'the incantation "{name}" recurses deeper than the machine '
                "can follow",
                line,
            )
        frame = Environment(parent=self.globals)
        for param, value in zip(decl.params, args):
            frame.define(param, value)
        self._call_depth += 1
        try:
            self.execute_block(decl.body, frame)
        except ReturnSignal as ret:
            return ret.value
        finally:
            self._call_depth -= 1
        return None

    # ── expressions ──────────────────────────────────────────────
    def evaluate(self, node, env):
        method = _EVAL_DISPATCH.get(type(node))
        if method is None:  # pragma: no cover - defensive
            raise RitualError(
                f"the machine cannot read {type(node).__name__}",
                getattr(node, "line", None),
            )
        return method(self, node, env)

    def _eval_literal(self, node, env):
        return node.value

    def _eval_name(self, node, env):
        return env.get(node.name, node.line)

    def _eval_call(self, node, env):
        return self.invoke_incant(node.name, node.args, env, node.line)

    def _eval_unary(self, node, env):
        value = self.evaluate(node.operand, env)
        op = node.op
        if op == "not":
            return not is_truthy(value)
        if op == "tone":
            return self._cast_tone(value, node.line)
        if op == "pulse":
            return self._cast_pulse(value, node.line)
        if op == "glyph":
            return to_glyph(value)
        if op == "flicker":
            return is_truthy(value)
        raise RitualError(f"unknown sign {op}", node.line)  # pragma: no cover

    def _eval_binary(self, node, env):
        op = node.op
        # short-circuit logic
        if op == "and":
            left = self.evaluate(node.left, env)
            if not is_truthy(left):
                return False
            return is_truthy(self.evaluate(node.right, env))
        if op == "or":
            left = self.evaluate(node.left, env)
            if is_truthy(left):
                return True
            return is_truthy(self.evaluate(node.right, env))

        left = self.evaluate(node.left, env)
        right = self.evaluate(node.right, env)

        if op == "is":
            return left == right
        if op == "not":      # binary "not" reads as "is not"
            return left != right
        if op == "above":
            return self._numeric(left, node.line) > self._numeric(right, node.line)
        if op == "below":
            return self._numeric(left, node.line) < self._numeric(right, node.line)
        if op == "add":
            if isinstance(left, str) or isinstance(right, str):
                return to_glyph(left) + to_glyph(right)
            return left + right
        if op == "subtract":
            return left - right
        if op == "scale":
            return left * right
        if op == "modulate":
            return self._modulo(left, right, node.line)
        raise RitualError(f"unknown sign {op}", node.line)  # pragma: no cover

    # ── helpers ──────────────────────────────────────────────────
    def _modulo(self, left, right, line):
        try:
            return left % right
        except ZeroDivisionError:
            raise RitualError("the machine cannot modulate by nothing", line)

    @staticmethod
    def _numeric(value, line):
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return value
        raise RitualError("only tones and pulses can be compared by size", line)

    @staticmethod
    def _cast_tone(value, line):
        try:
            return float(value)
        except (TypeError, ValueError):
            raise RitualError(f'"{value}" cannot become a tone', line)

    @staticmethod
    def _cast_pulse(value, line):
        try:
            return int(value)
        except (TypeError, ValueError):
            raise RitualError(f'"{value}" cannot become a pulse', line)

    def _resolve_scroll(self, name, line):
        name = str(name)
        candidates = []
        bases = list(reversed(self._scroll_dirs))
        stdlib = os.path.join(os.path.dirname(__file__), "scrolls")
        for base in bases:
            candidates.append(os.path.join(base, name))
            candidates.append(os.path.join(base, name + ".glo"))
        candidates.append(os.path.join(stdlib, name))
        candidates.append(os.path.join(stdlib, name + ".glo"))
        for path in candidates:
            if os.path.isfile(path):
                return os.path.abspath(path)
        raise RitualError(
            f'no scroll named "{name}" could be found to invoke', line
        )


# Statement dispatch: node type → bound method.
_EXEC_DISPATCH = {
    ast.Speak: Interpreter._exec_speak,
    ast.Hush: Interpreter._exec_hush,
    ast.Silence: Interpreter._exec_silence,
    ast.Breathe: Interpreter._exec_breathe,
    ast.Burn: Interpreter._exec_burn,
    ast.Drift: Interpreter._exec_drift,
    ast.Step: Interpreter._exec_step,
    ast.Mutate: Interpreter._exec_mutate,
    ast.Let: Interpreter._exec_let,
    ast.Set: Interpreter._exec_set,
    ast.If: Interpreter._exec_if,
    ast.Repeat: Interpreter._exec_repeat,
    ast.Until: Interpreter._exec_until,
    ast.Incant: Interpreter._exec_incant,
    ast.CallStmt: Interpreter._exec_call_stmt,
    ast.Echo: Interpreter._exec_echo,
    ast.VoidReturn: Interpreter._exec_void,
    ast.Voice: Interpreter._exec_voice,
    ast.Sync: Interpreter._exec_sync,
    ast.OpenChannel: Interpreter._exec_open_channel,
    ast.CloseChannel: Interpreter._exec_close_channel,
    ast.Send: Interpreter._exec_send,
    ast.Invoke: Interpreter._exec_invoke,
}

# Expression dispatch.
_EVAL_DISPATCH = {
    ast.Literal: Interpreter._eval_literal,
    ast.Name: Interpreter._eval_name,
    ast.CallExpr: Interpreter._eval_call,
    ast.Unary: Interpreter._eval_unary,
    ast.Binary: Interpreter._eval_binary,
}
