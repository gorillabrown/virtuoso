import json, os, subprocess, sys

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


def _run_capture(*args, root=None):
    """Run the script capturing stdout+stderr and the exit code (no check)."""
    env = dict(os.environ)
    if root is not None:
        env["VIRTUOSO_HOME"] = str(root)
    proc = subprocess.run(
        [sys.executable, SCRIPT, *args], capture_output=True, text=True, env=env
    )
    return proc.returncode, proc.stdout + proc.stderr


def _manifest(root):
    return json.loads(
        (root / "Virtuoso" / "workspace-layout.json").read_text(encoding="utf-8")
    )


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


# ---------------------------------------------------------------------------
# Adopt: bring an established, un-markered project under management in place.
# ---------------------------------------------------------------------------

def _seed_established_tree(tmp_path, doc_root="2. Project Documentation", roadmap_name="GoG_Roadmap.md"):
    op = tmp_path / doc_root / "2 operational"
    op.mkdir(parents=True)
    (op / roadmap_name).write_text(
        "# GoG Roadmap\n## Completed Work Summary\n## Active & Remaining Sprint Skeletons\n",
        encoding="utf-8",
    )
    (op / "sprint-queue.xlsx").write_bytes(b"PK\x03\x04 stub workbook")
    return op


def test_adopt_recognizes_established_tree_and_points_at_existing_roadmap(tmp_path):
    _seed_established_tree(tmp_path)
    rc, out = _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    assert rc == 0
    assert "virtuoso-status: adopted" in out
    assert (tmp_path / "Virtuoso" / ".virtuoso").is_file()
    m = _manifest(tmp_path)
    assert m["adopted"] is True
    assert m["paths"]["roadmap"] == "2. Project Documentation/2 operational/GoG_Roadmap.md"
    assert m["paths"]["sprintQueue"] == "2. Project Documentation/2 operational/sprint-queue.xlsx"


def test_adopt_never_seeds_a_parallel_roadmap_or_scaffolds_the_tree(tmp_path):
    _seed_established_tree(tmp_path)
    _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    # The only roadmap on disk is the project's own — no default Roadmap.md anywhere.
    roadmaps = sorted(p.name for p in tmp_path.rglob("*.md") if "roadmap" in p.name.lower())
    assert roadmaps == ["GoG_Roadmap.md"], roadmaps
    # Adopt writes ONLY the thin control dir; it does not scaffold the rest of the tree.
    assert not (tmp_path / "2. Project Documentation" / "1 governance").exists()
    assert not (tmp_path / "2. Project Documentation" / "3 temp").exists()


def test_adopt_is_noop_on_bare_project(tmp_path):
    rc, out = _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    assert rc == 0
    assert "virtuoso-status: none" in out
    assert not (tmp_path / "Virtuoso").exists()
    # ...but the plugin-root bridge is still recorded.
    assert (tmp_path / ".virtuoso" / "plugin-root").is_file()


def test_adopt_is_idempotent_and_heal_stays_thin(tmp_path):
    op = _seed_established_tree(tmp_path, doc_root="Project Documentation", roadmap_name="Custom_Roadmap.md")
    roadmap = op / "Custom_Roadmap.md"
    original = roadmap.read_text(encoding="utf-8")
    _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    rc, out = _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    assert rc == 0
    assert "virtuoso-status: ready" in out  # marker now present -> heal path
    assert roadmap.read_text(encoding="utf-8") == original  # never rewritten
    m = _manifest(tmp_path)
    assert m["adopted"] is True
    assert m["paths"]["roadmap"] == "Project Documentation/2 operational/Custom_Roadmap.md"
    # Healing an adopted workspace must not scaffold the doc tree.
    assert not (tmp_path / "Project Documentation" / "1 governance").exists()


def test_detect_reports_adoptable_without_writing(tmp_path):
    _seed_established_tree(tmp_path)
    rc, out = _run_capture("--root", str(tmp_path), "--mode", "detect", root=tmp_path)
    assert rc == 0
    assert "virtuoso-status: adoptable" in out
    assert not (tmp_path / "Virtuoso").exists()  # detect never writes a marker


def test_create_discovers_existing_nonstandard_roadmap(tmp_path):
    gov = tmp_path / "Project Documentation" / "1 governance"
    gov.mkdir(parents=True)
    (gov / "MyProject_Roadmap.md").write_text(
        "# MyProject\n## Completed Work Summary\n## Active & Remaining Sprint Skeletons\n",
        encoding="utf-8",
    )
    _run(tmp_path, "create", "plugin-only")
    m = _manifest(tmp_path)
    assert m["paths"]["roadmap"] == "Project Documentation/1 governance/MyProject_Roadmap.md"
    # No parallel default Roadmap.md seeded beside it.
    assert not (gov / "Roadmap.md").exists()


# ---------------------------------------------------------------------------
# Integrity guard: protect a roadmap from a destructive rewrite when corrupt.
# ---------------------------------------------------------------------------

def test_check_roadmap_ok(tmp_path):
    p = tmp_path / "Roadmap.md"
    p.write_text("# Roadmap\nContent here.\n", encoding="utf-8")
    rc, out = _run_capture("--check-roadmap", str(p))
    assert rc == 0
    assert "roadmap-integrity: ok" in out


def test_check_roadmap_fails_on_null_bytes(tmp_path):
    p = tmp_path / "Roadmap.md"
    p.write_bytes(b"# Roadmap\n\x00\x00 corrupted payload\n")
    rc, out = _run_capture("--check-roadmap", str(p))
    assert rc == 3
    assert "roadmap-integrity: fail" in out
    assert "null-bytes" in out


def test_check_roadmap_warns_on_oversize(tmp_path):
    p = tmp_path / "Roadmap.md"
    p.write_text("# Roadmap\n" + ("x" * (520 * 1024)), encoding="utf-8")
    rc, out = _run_capture("--check-roadmap", str(p))
    assert rc == 2
    assert "roadmap-integrity: warn" in out
    assert "oversize" in out


def test_check_roadmap_fails_when_missing(tmp_path):
    rc, out = _run_capture("--check-roadmap", str(tmp_path / "nope.md"))
    assert rc == 3
    assert "roadmap-integrity: fail" in out
    assert "missing" in out


def test_check_roadmap_warns_on_empty(tmp_path):
    p = tmp_path / "Roadmap.md"
    p.write_text("   \n\n\t\n", encoding="utf-8")
    rc, out = _run_capture("--check-roadmap", str(p))
    assert rc == 2
    assert "roadmap-integrity: warn" in out
    assert "empty" in out


def test_check_roadmap_fails_on_non_utf8(tmp_path):
    p = tmp_path / "Roadmap.md"
    p.write_bytes(b"\xff\xfe not valid utf8 \xff")
    rc, out = _run_capture("--check-roadmap", str(p))
    assert rc == 3
    assert "roadmap-integrity: fail" in out
    assert "not-utf-8" in out


# ---------------------------------------------------------------------------
# Discovery hardening: the live roadmap must beat a stale seed / backup / archive.
# ---------------------------------------------------------------------------

def test_discovery_prefers_real_roadmap_over_stale_seed(tmp_path):
    # A prior /virtuoso-init left an untouched seed at the conventional location...
    gov = tmp_path / "2. Project Documentation" / "1 governance"
    gov.mkdir(parents=True)
    (gov / "Roadmap.md").write_text(
        "# Project Roadmap\n\n**Last updated:** (initialized by virtuoso-init)\n"
        "## Completed Work Summary\n## Active & Remaining Sprint Skeletons\nFinish Line\n"
        "roadmap_doc: Roadmap.md\nfinish_line: \"\"\n",
        encoding="utf-8",
    )
    # ...while the project's real roadmap lives in 2 operational under its own (smaller) file.
    op = tmp_path / "2. Project Documentation" / "2 operational"
    op.mkdir(parents=True)
    (op / "GoG_Roadmap.md").write_text("# GoG\n## Completed Work Summary\n", encoding="utf-8")

    _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    m = _manifest(tmp_path)
    assert m["paths"]["roadmap"] == "2. Project Documentation/2 operational/GoG_Roadmap.md", m["paths"]["roadmap"]


def test_discovery_prefers_live_roadmap_over_backup_copy(tmp_path):
    op = tmp_path / "Project Documentation" / "2 operational"
    op.mkdir(parents=True)
    (op / "GoG_Roadmap.md").write_text(
        "# Live\n## Completed Work Summary\n## Active & Remaining Sprint Skeletons\n", encoding="utf-8"
    )
    # A fat stale snapshot kept beside the live file must not win on size.
    (op / "GoG_Roadmap_OLD_2024.md").write_text(
        "# Old\n## Completed Work Summary\n## Active & Remaining Sprint Skeletons\n" + ("x" * 5000),
        encoding="utf-8",
    )
    _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    m = _manifest(tmp_path)
    assert m["paths"]["roadmap"] == "Project Documentation/2 operational/GoG_Roadmap.md", m["paths"]["roadmap"]


def test_discovery_prefers_live_roadmap_over_archived(tmp_path):
    op = tmp_path / "Project Documentation" / "2 operational"
    (op / "roadmap-reviews" / "archive").mkdir(parents=True)
    (op / "roadmap-reviews" / "archive" / "Old_Roadmap.md").write_text(
        "# Old\n## Completed Work Summary\n## Active & Remaining Sprint Skeletons\nFinish Line\n" + ("x" * 5000),
        encoding="utf-8",
    )
    (op / "Live_Roadmap.md").write_text("# Live\n## Completed Work Summary\n", encoding="utf-8")
    _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    m = _manifest(tmp_path)
    assert m["paths"]["roadmap"] == "Project Documentation/2 operational/Live_Roadmap.md", m["paths"]["roadmap"]


def test_discovery_not_fooled_by_codename_containing_backup_substring(tmp_path):
    # "Gold" must NOT be read as an "old" backup; the real marker-rich roadmap still wins
    # over a markerless decoy even though backup-rank sits above structural markers.
    gov = tmp_path / "Project Documentation" / "1 governance"
    gov.mkdir(parents=True)
    (gov / "Gold_Roadmap.md").write_text(
        "# Gold\n## Completed Work Summary\n## Active & Remaining Sprint Skeletons\nFinish Line\n",
        encoding="utf-8",
    )
    (gov / "draft-roadmap.md").write_text("just notes, no markers\n", encoding="utf-8")
    _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    m = _manifest(tmp_path)
    assert m["paths"]["roadmap"] == "Project Documentation/1 governance/Gold_Roadmap.md", m["paths"]["roadmap"]


def test_discovery_not_fooled_by_roadmap_quoting_the_seed_sentinel(tmp_path):
    # A real roadmap that merely MENTIONS the seed phrase in prose must not be demoted as a seed.
    op = tmp_path / "Project Documentation" / "2 operational"
    op.mkdir(parents=True)
    (op / "Main_Roadmap.md").write_text(
        "# Main\n> Originally (initialized by virtuoso-init) long ago, since fleshed out.\n"
        "## Completed Work Summary\n## Active & Remaining Sprint Skeletons\n",
        encoding="utf-8",
    )
    (op / "Roadmap.md").write_text("# thin placeholder\n", encoding="utf-8")
    _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    m = _manifest(tmp_path)
    assert m["paths"]["roadmap"] == "Project Documentation/2 operational/Main_Roadmap.md", m["paths"]["roadmap"]


def test_adopt_routes_to_none_when_only_archived_roadmap_exists(tmp_path):
    rev = tmp_path / "2. Project Documentation" / "2 operational" / "roadmap-reviews"
    rev.mkdir(parents=True)
    (rev / "2024-01-01-Roadmap.md").write_text("# Snapshot\n## Completed Work Summary\n", encoding="utf-8")
    rc, out = _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    assert rc == 0
    assert "virtuoso-status: none" in out
    assert not (tmp_path / "Virtuoso").exists()


def test_adopt_routes_to_none_when_tree_has_no_roadmap(tmp_path):
    # An established doc subtree but no roadmap is NOT adopted (no phantom manifest path) —
    # it routes to /virtuoso-init, which seeds a roadmap.
    (tmp_path / "2. Project Documentation" / "2 operational").mkdir(parents=True)
    rc, out = _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    assert rc == 0
    assert "virtuoso-status: none" in out
    assert not (tmp_path / "Virtuoso").exists()


def test_detect_quiet_never_adopts_established_tree(tmp_path):
    # The SessionStart hook runs `--mode detect --quiet`; it must never write a marker.
    _seed_established_tree(tmp_path)
    rc, out = _run_capture("--root", str(tmp_path), "--mode", "detect", "--quiet", root=tmp_path)
    assert rc == 0
    assert not (tmp_path / "Virtuoso").exists()


def test_governance_readme_written_on_create_and_registers_roadmap(tmp_path):
    _run(tmp_path, "create")
    readme = tmp_path / "Virtuoso.Governance.Readme.md"
    assert readme.is_file()
    text = readme.read_text(encoding="utf-8")
    # It is the authority and states the no-parallel rule.
    assert "governance registry" in text.lower()
    assert "never create" in text.lower()
    # It registers the seeded roadmap as present.
    assert "Project Documentation/1 governance/Roadmap.md" in text
    assert "✅ registered" in text
    # Manifest mirrors the same path.
    m = _manifest(tmp_path)
    assert m["paths"]["governanceReadme"] == "Virtuoso.Governance.Readme.md"


def test_governance_readme_is_idempotent(tmp_path):
    _run(tmp_path, "create")
    readme = tmp_path / "Virtuoso.Governance.Readme.md"
    first = readme.read_text(encoding="utf-8")
    _run(tmp_path, "create")
    assert readme.read_text(encoding="utf-8") == first  # deterministic; no churn on re-run


def test_adopts_project_with_docs_governance_layout_in_place(tmp_path):
    # A Blurby-shaped project: a live roadmap under docs/governance and NO Project
    # Documentation tree. Adoption must register the real roadmap and never seed a rival.
    gov = tmp_path / "docs" / "governance"
    gov.mkdir(parents=True)
    (gov / "ROADMAP.md").write_text(
        "# Blurby Roadmap\n## Completed Work Summary\n## Active & Remaining Sprint Skeletons\n"
        "Finish Line\n",
        encoding="utf-8",
    )
    rc, out = _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    assert rc == 0
    assert "virtuoso-status: adopted" in out
    m = _manifest(tmp_path)
    assert m["paths"]["roadmap"] == "docs/governance/ROADMAP.md", m["paths"]["roadmap"]
    # No parallel default Roadmap.md anywhere, and no scaffolded Project Documentation tree.
    assert not (tmp_path / "Project Documentation").exists()
    roadmaps = sorted(p.name for p in tmp_path.rglob("*.md") if "roadmap" in p.name.lower())
    assert roadmaps == ["ROADMAP.md"], roadmaps
    # The registry points at the real file.
    readme = (tmp_path / "Virtuoso.Governance.Readme.md").read_text(encoding="utf-8")
    assert "docs/governance/ROADMAP.md" in readme


def test_adopts_project_with_root_roadmap_in_place(tmp_path):
    # A live roadmap at the project root, no documentation tree at all.
    (tmp_path / "ROADMAP.md").write_text(
        "# Root Roadmap\n## Completed Work Summary\n## Active & Remaining Sprint Skeletons\n",
        encoding="utf-8",
    )
    rc, out = _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    assert rc == 0
    assert "virtuoso-status: adopted" in out
    m = _manifest(tmp_path)
    assert m["paths"]["roadmap"] == "ROADMAP.md", m["paths"]["roadmap"]


def test_heal_with_missing_manifest_discovers_roadmap_and_seeds_no_parallel(tmp_path):
    # Marker dir present but no manifest: heal must still discover the real roadmap and not
    # seed a parallel one.
    (tmp_path / "Virtuoso").mkdir()
    op = _seed_established_tree(tmp_path, doc_root="Project Documentation", roadmap_name="Custom_Roadmap.md")
    rc, out = _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    assert rc == 0
    assert "virtuoso-status: ready" in out
    m = _manifest(tmp_path)
    assert m["paths"]["roadmap"] == "Project Documentation/2 operational/Custom_Roadmap.md", m["paths"]["roadmap"]
    assert not (op / "Roadmap.md").exists()
