"""Every shipped scroll must run without the machine stumbling."""

import io
import os
import glob
from contextlib import redirect_stdout

import pytest

from glo.evaluator import Interpreter

EXAMPLES = sorted(
    glob.glob(os.path.join(os.path.dirname(__file__), "..", "examples", "*.glo"))
)


@pytest.mark.parametrize("path", EXAMPLES, ids=[os.path.basename(p) for p in EXAMPLES])
def test_example_runs(path):
    interp = Interpreter(quiet=True)
    out = io.StringIO()
    with redirect_stdout(out):
        interp.run_file(path)  # should not raise


def test_check_validates_every_example():
    from glo.parser import parse
    for path in EXAMPLES:
        with open(path, encoding="utf-8") as fh:
            parse(fh.read())  # should not raise
