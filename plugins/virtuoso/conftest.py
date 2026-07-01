"""Pin the import root so `tools.roadmap_visualizer` resolves regardless of the
directory pytest is invoked from. `tools/` is a namespace package (no __init__.py),
so its parent (this file's directory) must be on sys.path."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
