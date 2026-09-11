#!/usr/bin/env python3
"""Execute every ```python code block in the READMEs and assert that any line of
the form `print(EXPR)  # EXPECTED` prints EXPECTED.

Runs each block in a shared namespace with the installed core (+ geo if present).
Fails (exit 1) on any execution error or output mismatch.
"""

import io
import json
import os
import re
import subprocess
import sys
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "packages", "py-core"))
sys.path.insert(0, os.path.join(ROOT, "packages", "py-geo"))

_PRINT_EXPECT = re.compile(r"^\s*print\((?P<expr>.+)\)\s*#\s*(?P<exp>.+?)\s*$")


def _blocks():
    out = subprocess.check_output(
        [sys.executable, os.path.join(ROOT, "tests", "readme", "extract_blocks.py"), "python"]
    )
    return json.loads(out)


def _run_block(block, ns):
    failures = []
    for line in block["code"].splitlines():
        m = _PRINT_EXPECT.match(line)
        if m:
            expr, expected = m.group("expr"), m.group("exp")
            try:
                val = eval(expr, ns)  # noqa: S307 - README-controlled expressions
            except Exception as e:  # noqa: BLE001
                failures.append(f"{block['file']}: `{expr}` raised {e!r}")
                continue
            got = str(val)
            if got != expected:
                failures.append(
                    f"{block['file']}: print({expr}) -> {got!r} != expected {expected!r}"
                )
        else:
            # execute the line (imports, assignments, plain calls) in the namespace
            buf = io.StringIO()
            try:
                with redirect_stdout(buf):
                    exec(line, ns)  # noqa: S102 - README-controlled code
            except Exception as e:  # noqa: BLE001
                failures.append(f"{block['file']}: line `{line.strip()}` raised {e!r}")
    return failures


def main():
    all_failures = []
    ran = 0
    for block in _blocks():
        ns = {}
        all_failures += _run_block(block, ns)
        ran += 1
    if all_failures:
        print("README python examples FAILED:")
        for f in all_failures:
            print("  -", f)
        return 1
    print(f"README python examples OK ({ran} blocks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
