"""Deprecated alias of `generate_board`, kept for one release; the planning cockpit is retired.

It runs `generate_board` with the same arguments, writes no cockpit page, and leaves an
existing `Virtuoso/reports/planning-cockpit.html` alone. The release after this one
removes it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.roadmap_visualizer.generate import board_main

if __name__ == "__main__":
    code = board_main()
    # After board_main, which sets up UTF-8 stdio first.
    print("generate_cockpit is retired: it runs generate_board now; call generate_board instead",
          file=sys.stderr)
    raise SystemExit(code)
