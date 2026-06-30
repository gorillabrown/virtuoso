"""The launcher must run from any working directory, including the repo root,
where `tools.roadmap_visualizer` is otherwise not importable."""
import subprocess
import sys
from pathlib import Path

# scripts -> virtuoso -> plugins -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
LAUNCHER = REPO_ROOT / "plugins" / "virtuoso" / "scripts" / "generate_cockpit.py"


def test_launcher_help_runs_from_repo_root():
    result = subprocess.run(
        [sys.executable, str(LAUNCHER), "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "planning cockpit" in result.stdout.lower()
