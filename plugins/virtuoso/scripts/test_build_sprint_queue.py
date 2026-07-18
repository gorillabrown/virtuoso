"""The builder must honor its output-path argument instead of always writing
sprint-queue.xlsx next to itself (regression: args were ignored entirely)."""
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SCRIPT = SCRIPT_DIR / "build_sprint_queue.py"


def run_script(args, cwd):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def script_dir_output_snapshot():
    target = SCRIPT_DIR / "sprint-queue.xlsx"
    return target.stat().st_mtime_ns if target.exists() else None


def test_absolute_output_path_is_honored(tmp_path):
    catalog = tmp_path / "sprint-catalog.csv"
    catalog.write_text("Seq,Sprint Code\n")
    out = tmp_path / "nested-name.xlsx"
    before = script_dir_output_snapshot()

    result = run_script([str(catalog), str(out)], cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert out.exists(), "output must land at the path given on the CLI"
    assert script_dir_output_snapshot() == before, (
        "script must not write into its own directory when an output path is given"
    )
    assert str(out) in result.stdout


def test_relative_output_path_resolves_against_cwd(tmp_path):
    catalog = tmp_path / "sprint-catalog.csv"
    catalog.write_text("Seq,Sprint Code\n")

    result = run_script([catalog.name, "queue.xlsx"], cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "queue.xlsx").exists()


def test_no_args_still_writes_next_to_script(tmp_path):
    # Copy the script out of the repo so the legacy default (write beside the
    # script) can be exercised without polluting the working tree.
    script_copy = tmp_path / "build_sprint_queue.py"
    shutil.copy2(SCRIPT, script_copy)

    result = subprocess.run(
        [sys.executable, str(script_copy)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "sprint-queue.xlsx").exists()
