#!/usr/bin/env python3
"""Extract fenced code blocks from the project READMEs so the README-as-tests
harness can execute them. Emits JSON: [{file, lang, code}].

Covers the root README and all 4 package READMEs.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

READMES = [
    "README.md",
    "packages/py-core/README.md",
    "packages/py-geo/README.md",
    "packages/node-core/README.md",
    "packages/node-geo/README.md",
]

_FENCE = re.compile(r"```(\w+)\n(.*?)```", re.DOTALL)


def extract(lang_filter):
    blocks = []
    for rel in READMES:
        path = os.path.join(ROOT, rel)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for m in _FENCE.finditer(text):
            lang, code = m.group(1), m.group(2)
            if lang in lang_filter:
                blocks.append({"file": rel, "lang": lang, "code": code})
    return blocks


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which == "python":
        langs = {"python"}
    elif which == "node":
        langs = {"javascript", "js"}
    else:
        langs = {"python", "javascript", "js"}
    print(json.dumps(extract(langs), indent=2))
