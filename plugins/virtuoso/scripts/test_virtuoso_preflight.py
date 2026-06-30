import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "virtuoso_preflight.py")

DOC_DIRS = [
    "Project Documentation/1 governance",
    "Project Documentation/2 operational",
    "Project Documentation/3 temp",
    "Project Documentation/4 Outside Audits",
    "Project Documentation/5 Reference",
]
PLUGIN_ONLY_DIRS = [
    "Virtuoso", "Virtuoso/scripts", *DOC_DIRS,
    "Project Documentation/2 operational/roadmap-reviews",
    "Project Documentation/2 operational/roadmap-reviews/checkins",
    "Project Documentation/2 operational/Close-Outs",
    "Project Documentation/2 operational/Issues",
]
CANONICAL_DIRS = [
    "Virtuoso", "Virtuoso/scripts",
    *[f"Virtuoso/{d}" for d in DOC_DIRS],
    "Virtuoso/Project Documentation/2 operational/roadmap-reviews",
    "Virtuoso/Project Documentation/2 operational/roadmap-reviews/checkins",
    "Virtuoso/Project Documentation/2 operational/Close-Outs",
    "Virtuoso/Project Documentation/2 operational/Issues",
]
PLUGIN_ONLY_FILES = [
    "Virtuoso/.virtuoso", "Virtuoso/workspace-layout.json",
    "Project Documentation/1 governance/Roadmap.md",
    "Project Documentation/1 governance/SpecRetro.Lessons_Learned.md",
    "Project Documentation/5 Reference/WORKFLOW_REFERENCE.md",
    "Virtuoso/scripts/recalc.py", "Virtuoso/scripts/prepare_closeout_files.py",
]
CANONICAL_FILES = [
    "Virtuoso/.virtuoso", "Virtuoso/workspace-layout.json",
    "Virtuoso/Project Documentation/1 governance/Roadmap.md",
    "Virtuoso/Project Documentation/1 governance/SpecRetro.Lessons_Learned.md",
    "Virtuoso/Project Documentation/5 Reference/WORKFLOW_REFERENCE.md",
    "Virtuoso/scripts/recalc.py", "Virtuoso/scripts/prepare_closeout_files.py",
]


def _run(root, mode, layout=None):
    # Isolate the plugin-root bridge into the test root so we never touch real $HOME.
    env = dict(os.environ)
    env["VIRTUOSO_HOME"] = str(root)
    cmd = [sys.executable, SCRIPT, "--root", str(root), "--mode", mode]
    if layout:
        cmd.extend(["--layout", layout])
    subprocess.run(cmd, check=True, env=env)


def test_create_builds_tree(tmp_path):
    _run(tmp_path, "create")
    for d in PLUGIN_ONLY_DIRS:
        assert (tmp_path / d).is_dir(), d
    for f in PLUGIN_ONLY_FILES:
        assert (tmp_path / f).is_file(), f
    # bridge file recorded for skill bodies
    assert (tmp_path / ".virtuoso" / "plugin-root").is_file()
    assert not (tmp_path / "Virtuoso" / "Project Documentation").exists()


def test_create_is_idempotent_and_nondestructive(tmp_path):
    _run(tmp_path, "create")
    roadmap = tmp_path / "Project Documentation" / "1 governance" / "Roadmap.md"
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
    (tmp_path / "Project Documentation" / "2 operational" / "Close-Outs").rmdir()
    _run(tmp_path, "detect")
    assert (tmp_path / "Project Documentation" / "2 operational" / "Close-Outs").is_dir()


def test_plugin_only_reuses_existing_project_documentation_folder(tmp_path):
    existing = tmp_path / "2. Project Documentation"
    (existing / "1 governance").mkdir(parents=True)
    _run(tmp_path, "create", "plugin-only")
    assert (existing / "2 operational").is_dir()
    assert not (tmp_path / "Project Documentation").exists()


def test_canonical_layout_builds_tree_inside_virtuoso(tmp_path):
    _run(tmp_path, "create", "canonical")
    for d in CANONICAL_DIRS:
        assert (tmp_path / d).is_dir(), d
    for f in CANONICAL_FILES:
        assert (tmp_path / f).is_file(), f
    assert not (tmp_path / "Project Documentation").exists()


def test_detect_preserves_recorded_canonical_layout(tmp_path):
    _run(tmp_path, "create", "canonical")
    (tmp_path / "Virtuoso" / "Project Documentation" / "2 operational" / "Issues").rmdir()
    _run(tmp_path, "detect")
    assert (tmp_path / "Virtuoso" / "Project Documentation" / "2 operational" / "Issues").is_dir()


def test_canonical_layout_migrates_existing_documentation_without_overwriting(tmp_path):
    _run(tmp_path, "create", "plugin-only")
    root_roadmap = tmp_path / "Project Documentation" / "1 governance" / "Roadmap.md"
    root_roadmap.write_text("ROOT ROADMAP", encoding="utf-8")
    canonical_roadmap = (
        tmp_path / "Virtuoso" / "Project Documentation" / "1 governance" / "Roadmap.md"
    )
    canonical_roadmap.parent.mkdir(parents=True)
    canonical_roadmap.write_text("CANONICAL ROADMAP", encoding="utf-8")

    _run(tmp_path, "create", "canonical")

    assert canonical_roadmap.read_text(encoding="utf-8") == "CANONICAL ROADMAP"
    assert root_roadmap.read_text(encoding="utf-8") == "ROOT ROADMAP"
    assert (tmp_path / "Virtuoso" / "Project Documentation" / "2 operational" / "sprint-queue.xlsx").is_file()
