import io
from contextlib import redirect_stdout

from glo.evaluator import Interpreter


def run(source):
    """Run a snippet quietly and return everything it spoke (stdout)."""
    interp = Interpreter(quiet=True)
    out = io.StringIO()
    with redirect_stdout(out):
        interp.run_source(source)
    return out.getvalue()


def lines(source):
    return run(source).splitlines()
