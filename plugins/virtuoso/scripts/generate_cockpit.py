"""cwd-independent launcher for the roadmap planning cockpit.

`tools/` is a namespace package under this script's parent (plugins/virtuoso/),
so we put that directory on sys.path before importing. This lets the tool run
from any working directory — `python plugins/virtuoso/scripts/generate_cockpit.py`.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.roadmap_visualizer.generate import main

if __name__ == "__main__":
    raise SystemExit(main())
