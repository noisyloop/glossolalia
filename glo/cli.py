"""The mouth of the machine — the ``glo`` command line.

    glo run <scroll.glo>     execute a scroll
    glo repl                 live interactive utterance
    glo check <scroll.glo>   validate syntax without running
    glo trace <scroll.glo>   run, printing AST + execution trace
"""

import argparse
import sys

from . import __version__
from .errors import GlossolaliaError
from .evaluator import Interpreter
from .parser import parse


def _print_error(exc):
    print(f"\n  the machine stopped: {exc.spoken()}\n", file=sys.stderr)


def cmd_run(args):
    interp = Interpreter(quiet=args.quiet)
    try:
        interp.run_file(args.scroll)
    except GlossolaliaError as exc:
        _print_error(exc)
        return 1
    except FileNotFoundError:
        print(f"\n  no scroll was found at \"{args.scroll}\"\n", file=sys.stderr)
        return 1
    return 0


def cmd_check(args):
    try:
        with open(args.scroll, "r", encoding="utf-8") as fh:
            source = fh.read()
        parse(source)
    except GlossolaliaError as exc:
        _print_error(exc)
        return 1
    except FileNotFoundError:
        print(f"\n  no scroll was found at \"{args.scroll}\"\n", file=sys.stderr)
        return 1
    print(f"  the scroll \"{args.scroll}\" is well-formed. it may be spoken.")
    return 0


def _dump_ast(node, indent=0):
    pad = "  " * indent
    import dataclasses
    if dataclasses.is_dataclass(node):
        print(f"{pad}{type(node).__name__}")
        for f in dataclasses.fields(node):
            value = getattr(node, f.name)
            if f.name == "line":
                continue
            if isinstance(value, list):
                if value:
                    print(f"{pad}  {f.name}:")
                    for item in value:
                        _dump_ast(item, indent + 2)
            elif dataclasses.is_dataclass(value):
                print(f"{pad}  {f.name}:")
                _dump_ast(value, indent + 2)
            else:
                print(f"{pad}  {f.name}: {value!r}")
    else:
        print(f"{pad}{node!r}")


def cmd_trace(args):
    try:
        with open(args.scroll, "r", encoding="utf-8") as fh:
            source = fh.read()
        program = parse(source)
    except GlossolaliaError as exc:
        _print_error(exc)
        return 1
    except FileNotFoundError:
        print(f"\n  no scroll was found at \"{args.scroll}\"\n", file=sys.stderr)
        return 1

    print("── the shape of the scroll ──", file=sys.stderr)
    for stmt in program.body:
        _dump_ast(stmt)
    print("\n── the speaking of the scroll ──", file=sys.stderr)
    interp = Interpreter(quiet=args.quiet, trace=True)
    import os
    try:
        interp.run_source(source,
                          scroll_dir=os.path.dirname(os.path.abspath(args.scroll)))
    except GlossolaliaError as exc:
        _print_error(exc)
        return 1
    return 0


def cmd_repl(args):
    interp = Interpreter(quiet=args.quiet)
    print("glossolalia — utterance is execution")
    print(f"  v{__version__}.  speak, and the machine listens.")
    print("  (an empty line, or \"end\", closes a block; ctrl-d departs)\n")
    buffer = []
    depth = 0
    _openers = {"if", "repeat", "until", "incant", "voice"}
    while True:
        prompt = "... " if buffer else ">>> "
        try:
            line = input(prompt)
        except EOFError:
            print("\n  the machine falls silent.")
            break
        except KeyboardInterrupt:
            print("\n  (interrupted)")
            buffer = []
            depth = 0
            continue

        stripped = line.strip()
        first = stripped.split(" ", 1)[0] if stripped else ""
        if first in _openers:
            depth += 1
        if first == "end" and depth > 0:
            depth -= 1
        buffer.append(line)

        # keep collecting while inside a block
        if depth > 0:
            continue
        # blank line with nothing buffered: ignore
        source = "\n".join(buffer).strip()
        buffer = []
        if not source:
            continue
        try:
            interp.run_source(source)
        except GlossolaliaError as exc:
            _print_error(exc)
        except Exception as exc:  # keep the repl alive
            print(f"  the machine faltered: {exc}", file=sys.stderr)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="glo",
        description="glossolalia — utterance is execution",
    )
    parser.add_argument("--version", action="version",
                        version=f"glossolalia {__version__}")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="silence the visible tone/OSC fallbacks")
    sub = parser.add_subparsers(dest="command")

    p_run = sub.add_parser("run", help="execute a scroll")
    p_run.add_argument("scroll")
    p_run.set_defaults(func=cmd_run)

    p_check = sub.add_parser("check", help="validate syntax without running")
    p_check.add_argument("scroll")
    p_check.set_defaults(func=cmd_check)

    p_trace = sub.add_parser("trace", help="print AST + execution trace")
    p_trace.add_argument("scroll")
    p_trace.set_defaults(func=cmd_trace)

    p_repl = sub.add_parser("repl", help="live interactive utterance")
    p_repl.set_defaults(func=cmd_repl)

    return parser


def main(argv=None):
    import os

    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except GlossolaliaError as exc:
        # Belt-and-braces: thematic errors never reach here as tracebacks.
        _print_error(exc)
        return 1
    except KeyboardInterrupt:
        print("\n  the machine falls silent.", file=sys.stderr)
        return 130
    except Exception:
        # Anti-information-disclosure: never surface a host traceback, file
        # path, or memory address to the user. Set GLO_DEBUG=1 to opt in
        # while developing the interpreter itself.
        if os.environ.get("GLO_DEBUG", "") not in ("", "0", "false"):
            raise
        print("\n  the machine faltered in a way it could not name.\n",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
