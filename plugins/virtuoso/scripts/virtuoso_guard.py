#!/usr/bin/env python3
"""Hook entry for the cost guards: reads the host's hook input on stdin, prints the host's
expected output or nothing, and exits 0. It acts only where a Virtuoso registry exists;
any error lets the step through.

Usage (from the plugin's hook files): ``python virtuoso_guard.py --host claude-code``
"""
from __future__ import annotations

import json
import os
import sys

# The plugin root is found from this file's own place, never from the working folder.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main(argv: list[str]) -> int:
    host = argv[argv.index("--host") + 1] if "--host" in argv[:-1] else "claude-code"
    try:
        hook = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    try:
        from tools.governance import changes, guards
        answer = guards.handle(hook, host, changes.plugin_version())
    except Exception:
        return 0
    if answer:
        sys.stdout.write(json.dumps(answer))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
