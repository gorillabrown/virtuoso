"""cwd-independent launcher for the roadmap board.

`generate_board --root .` regenerates the registered board; `--create` is
roadmap-review D.7: it registers the role when missing and creates the page.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.roadmap_visualizer.generate import board_main

if __name__ == "__main__":
    raise SystemExit(board_main())
