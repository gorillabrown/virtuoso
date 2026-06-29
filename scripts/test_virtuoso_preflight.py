import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "virtuoso_preflight.py")

EXPECTED_DIRS = [
    "Virtuoso", "Virtuoso/roadmap-reviews", "Virtuoso/roadmap-reviews/checkins",
    "Virtuoso/Close-Outs", "Virtuoso/audits", "Virtuoso/scripts",
]
EXPECTED_FILES = [
    "Virtuoso/.virtuoso", "Virtuoso/Roadmap.md",
    "Virtuoso/SpecRetro.Lessons_Learned.md", "Virtuoso/WORKFLOW_REFERENCE.md",
    "Virtuoso/scripts/recalc.py", "Virtuoso/scripts/build_sprint_queue.py",
    "Virtuoso/scripts/prepare_closeout_files.py",
]


def _run(root, mode):
    # Isolate the plugin-root bridge into the test root so we never touch real $HOME.
    env = dict(os.environ)
    env["VIRTUOSO_HOME"] = str(root)
    subprocess.run([sys.executable, SCRIPT, "--root", str(root), "--mode", mode],
                   check=True, env=env)


def test_create_builds_tree(tmp_path):
    _run(tmp_path, "create")
    for d in EXPECTED_DIRS:
        assert (tmp_path / d).is_dir(), d
    for f in EXPECTED_FILES:
        assert (tmp_path / f).is_file(), f
    # bridge file recorded for skill bodies
    assert (tmp_path / ".virtuoso" / "plugin-root").is_file()


def test_create_is_idempotent_and_nondestructive(tmp_path):
    _run(tmp_path, "create")
    roadmap = tmp_path / "Virtuoso" / "Roadmap.md"
    roadmap.write_text("MY EDITS", encoding="utf-8")
    _run(tmp_path, "create")
    assert roadmap.read_text(encoding="utf-8") == "MY EDITS"  # never overwritten


def test_detect_noop_on_plain_folder(tmp_path):
    _run(tmp_path, "detect")
    assert not (tmp_path / "Virtuoso").exists()  # no marker -> no workspace
    # ...but the bridge is still recorded even on a non-project detect run
    assert (tmp_path / ".virtuoso" / "plugin-root").is_file()


def test_detect_heals_existing_project(tmp_path):
    _run(tmp_path, "create")
    (tmp_path / "Virtuoso" / "Close-Outs").rmdir()  # remove a piece
    _run(tmp_path, "detect")
    assert (tmp_path / "Virtuoso" / "Close-Outs").is_dir()  # healed (marker present)
