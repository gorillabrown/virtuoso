#!/usr/bin/env python3
"""Deprecated name of dispatch_guards.py, kept for one release (1.15); removed in the next major."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dispatch_guards  # noqa: E402

if __name__ == "__main__":
    print("sprint_guards is deprecated: run dispatch_guards (same arguments); "
          "the old name goes in the next major release", file=sys.stderr)
    sys.exit(dispatch_guards.main())
