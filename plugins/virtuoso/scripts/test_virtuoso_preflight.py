import hashlib, importlib.util, json, os, subprocess, sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "virtuoso_preflight.py")

# Imported directly (not just invoked via subprocess) so the SK-01 mirror-invariant tests can
# reuse the production readme-parsing logic and role-key schema instead of re-deriving them.
_vp_spec = importlib.util.spec_from_file_location("virtuoso_preflight", SCRIPT)
vp = importlib.util.module_from_spec(_vp_spec)
_vp_spec.loader.exec_module(vp)

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
PLUGIN_ONLY_FILES = [
    "Virtuoso/.virtuoso", "Virtuoso/workspace-layout.json",
    "Project Documentation/1 governance/Roadmap.md",
    "Project Documentation/1 governance/SpecRetro.Lessons_Learned.md",
    "Project Documentation/5 Reference/WORKFLOW_REFERENCE.md",
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


def test_detect_scaffolds_empty_new_project(tmp_path):
    """New behavior: a genuinely empty directory can only ever be a brand-new project (there's
    nothing there for detect to clobber), so detect -- the SessionStart hook path most
    projects first meet Virtuoso through -- auto-scaffolds the standard plugin-only workspace
    instead of silently doing nothing and leaving the user to run /virtuoso-init by hand."""
    assert list(tmp_path.iterdir()) == []  # sanity: genuinely empty
    rc, _out = _run_capture("--root", str(tmp_path), "--mode", "detect", "--quiet", root=tmp_path)
    assert rc == 0
    for d in PLUGIN_ONLY_DIRS:
        assert (tmp_path / d).is_dir(), d
    for f in PLUGIN_ONLY_FILES:
        assert (tmp_path / f).is_file(), f
    m = _manifest(tmp_path)
    assert m["layout"] == "plugin-only"
    # ...and the bridge is still recorded, as on every invocation
    assert (tmp_path / ".virtuoso" / "plugin-root").is_file()


def test_detect_scaffolds_git_only_new_project(tmp_path):
    """A directory containing only a freshly-initialized `.git/` (no other content yet) is
    still a brand-new project for this purpose -- detect auto-scaffolds it exactly like a
    genuinely empty directory."""
    (tmp_path / ".git").mkdir()
    rc, _out = _run_capture("--root", str(tmp_path), "--mode", "detect", "--quiet", root=tmp_path)
    assert rc == 0
    assert (tmp_path / "Virtuoso" / ".virtuoso").is_file()
    assert (tmp_path / "Virtuoso" / "workspace-layout.json").is_file()
    m = _manifest(tmp_path)
    assert m["layout"] == "plugin-only"


def test_detect_stays_inert_on_nonempty_unmarkered_dir(tmp_path):
    """A non-empty, unmarkered, non-adoptable directory (some unrelated content, no Virtuoso/
    marker, no discoverable roadmap) must stay fully inert under detect -- this preserves the
    R1 "detect never writes" spirit for real, existing projects that simply haven't been
    brought under Virtuoso management yet. Only a directory with NOTHING (or only `.git`) in
    it is treated as new."""
    (tmp_path / "README.md").write_text("just a project, not Virtuoso-managed\n", encoding="utf-8")
    before_files, before_dirs = _hash_walk(tmp_path)
    rc, _out = _run_capture("--root", str(tmp_path), "--mode", "detect", "--quiet", root=tmp_path)
    assert rc == 0
    after_files, after_dirs = _hash_walk(tmp_path)
    assert after_dirs == before_dirs, "detect created or removed a directory"
    assert after_files == before_files, "detect mutated a non-empty unmarkered project"
    assert not (tmp_path / "Virtuoso").exists()


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


def test_archive_plural_segments_excluded_from_discovery(tmp_path):
    # GoG uses "archives/" (plural). A structurally-richer decoy roadmap sitting there must NOT
    # outrank the live roadmap in 2 operational -- the PRD R9 discovery hazard for an
    # unregistered project (no Virtuoso/ marker, no registry overlay yet). The decoy filename
    # deliberately avoids any _BACKUP_NAME_TOKENS ("archive" is not one) so the only thing that
    # can save the live roadmap is _ARCHIVE_SEGMENTS excluding the "archives" directory segment.
    op = tmp_path / "Project Documentation" / "2 operational"
    op.mkdir(parents=True)
    (op / "Live_Roadmap.md").write_text(
        "# Live Roadmap\n## Completed Work Summary\n## Active & Remaining Sprint Skeletons\n",
        encoding="utf-8",
    )
    (op / "archives").mkdir()
    (op / "archives" / "GoG_Roadmap_Archive_2026-07-10.md").write_text(
        "# Archived Snapshot\n## Finish Line\n## Completed Work Summary\n"
        "## Active & Remaining Sprint Skeletons\n",
        encoding="utf-8",
    )
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


# ---------------------------------------------------------------------------
# Registry-authoritative preflight (fix/registry-authoritative-preflight): behavioral
# regression tests for the registry-clobber remediation. See
# docs/superpowers/specs/2026-07-18-preflight-registry-clobber-remediation-design.md (R1-R6).
#
# build_curated_fixture() ports the session's repro fixture: a markered, HEALTHY, hand-curated
# Virtuoso project whose registry (workspace-layout.json + the governance readme's machine
# block) is the single source of truth. It carries two project-custom roles ("epics",
# "roadmapArchives") the plugin has never heard of, a live roadmap that a structurally-richer
# archive would outrank under pure discovery scoring, a real (non-stub) lessons catalog
# registered under a non-default name, and a vendored script that differs from the plugin's
# own bundled copy by line-ending convention only. A correct preflight run must leave all of
# this untouched; the current implementation does not.
# ---------------------------------------------------------------------------

_PLUGIN_ROOT_FOR_FIXTURES = os.path.dirname(HERE)
_CLOSEOUT_SCRIPT_SRC = os.path.join(
    _PLUGIN_ROOT_FOR_FIXTURES, "skills", "pointer-closeout", "scripts", "prepare_closeout_files.py"
)
_RECALC_SCRIPT_SRC = os.path.join(
    _PLUGIN_ROOT_FOR_FIXTURES, "skills", "roadmap-review", "scripts", "recalc.py"
)

CURATED_DOC_ROOT = "2. Project Documentation"
CURATED_ROADMAP_REL = CURATED_DOC_ROOT + "/2 operational/GoG_Roadmap.md"
CURATED_ARCHIVE_REL = CURATED_DOC_ROOT + "/archives/GoG_Roadmap_Archive_2026-07-10.md"
CURATED_LESSONS_REL = CURATED_DOC_ROOT + "/1 governance/GoG_Lessons_Catalog.md"
CURATED_EPICS_REL = CURATED_DOC_ROOT + "/1 governance/Epics.md"
CURATED_ROADMAP_ARCHIVES_REL = CURATED_DOC_ROOT + "/archives"
CURATED_SPRINT_QUEUE_REL = CURATED_DOC_ROOT + "/2 operational/sprint-queue.xlsx"
CURATED_SPRINT_CATALOG_REL = CURATED_DOC_ROOT + "/2 operational/sprint-catalog.csv"
CURATED_WORKFLOW_REF_REL = CURATED_DOC_ROOT + "/5 Reference/WORKFLOW_REFERENCE.md"
CURATED_CLOSE_OUTS_REL = CURATED_DOC_ROOT + "/2 operational/Close-Outs"
CURATED_ISSUES_REL = CURATED_DOC_ROOT + "/2 operational/Issues"
CURATED_ROADMAP_REVIEWS_REL = CURATED_DOC_ROOT + "/2 operational/roadmap-reviews"
CURATED_OUTSIDE_AUDITS_REL = CURATED_DOC_ROOT + "/4 Outside Audits"
CURATED_REFERENCE_REL = CURATED_DOC_ROOT + "/5 Reference"

# Live roadmap: exactly 2 of the 5 _ROADMAP_MARKERS substrings ("Completed Work Summary",
# "Active & Remaining Sprint").
_LIVE_ROADMAP_TEXT = """# GoG Roadmap

**Last updated:** 2026-07-15

## Completed Work Summary
| Sprint | Session | Result | Close-Out |
|--------|---------|--------|-----------|
| GOG-01 | S1 | shipped | CO-01 |

## Active & Remaining Sprint Skeletons

### GOG-02 - Next sprint
(dispatch-ready spec lives here)
"""

# Archive snapshot: exactly 3 of the 5 _ROADMAP_MARKERS substrings ("Finish Line",
# "Completed Work Summary", "Active & Remaining Sprint") -- one more than the live roadmap
# above, so naive structural discovery outranks the registered live roadmap. The directory
# segment is "archives" (plural); _ARCHIVE_SEGMENTS only lists "archive" (singular), so
# current code does NOT exclude this as an archived copy -- it competes as a live candidate
# and wins on marker count. This is the exact clobber scenario from the PRD evidence base.
_ARCHIVED_ROADMAP_TEXT = """# GoG Roadmap - Archived Snapshot (2026-07-10)

## Finish Line - Target
Ship v1.0 (archived target; see the live roadmap for the current one)

## Completed Work Summary
| Sprint | Session | Result | Close-Out |
|--------|---------|--------|-----------|
| GOG-01 | S1 | shipped | CO-01 |

## Active & Remaining Sprint Skeletons
(this snapshot is frozen; the live roadmap supersedes it)
"""

_LESSONS_CATALOG_TEXT = """# GoG Spec Retrospective - Lessons Learned

## SRL-001 - Discovery scoring favors marker count over registration
An archived snapshot with more structural section headers can outrank the registered live
roadmap under pure discovery scoring. Registry authority must short-circuit discovery for any
role the registry already has.

## SRL-002 - Registry regeneration must round-trip unknown keys
Project-custom registry roles (epics, roadmapArchives) are not part of the plugin's fixed role
list and must survive every regeneration cycle unchanged.
"""

_EPICS_TEXT = """# GoG Epics

## EPIC-01 - Combat Engine Calibration
## EPIC-02 - Archetype Behavioral Rollout
"""

_WORKFLOW_REFERENCE_TEXT = """# Workflow Reference

GoG's project-specific workflow notes (curated; not the plugin's default template).
"""

_SPRINT_CATALOG_CSV = "Sprint,Status,Result\nGOG-01,shipped,done\n"

# (label, relative path, status) for the curated readme's human-readable table -- the 9
# standard roles (labels copied verbatim from GOVERNANCE_ROLES) plus the 2 project-custom
# ones. Ordering and label text here are the fixture's own curated ground truth; the tests
# only ever compare curated bytes against post-run bytes, never re-derive an "expected"
# render from the production template.
_CURATED_ROLE_ROWS = [
    ("Roadmap", CURATED_ROADMAP_REL, "✅ registered"),
    ("Sprint catalog (CSV — source of truth)", CURATED_SPRINT_CATALOG_REL, "✅ registered"),
    ("Sprint queue (xlsx — optional generated report)", CURATED_SPRINT_QUEUE_REL, "✅ registered"),
    ("Lessons / retrospective", CURATED_LESSONS_REL, "✅ registered"),
    ("Close-outs (directory)", CURATED_CLOSE_OUTS_REL, "✅ registered"),
    ("Issues (directory)", CURATED_ISSUES_REL, "✅ registered"),
    ("Roadmap reviews (directory)", CURATED_ROADMAP_REVIEWS_REL, "✅ registered"),
    ("Outside audits (directory)", CURATED_OUTSIDE_AUDITS_REL, "✅ registered"),
    ("Reference (directory)", CURATED_REFERENCE_REL, "✅ registered"),
    ("Epics", CURATED_EPICS_REL, "✅ registered"),
    ("Roadmap archives (directory)", CURATED_ROADMAP_ARCHIVES_REL, "✅ registered"),
]

# (machine key, relative path) mirroring the table above -- known roles first, then the 2
# custom keys, matching R2's required ordering for the machine-readable block.
_CURATED_MACHINE_PAIRS = [
    ("roadmap", CURATED_ROADMAP_REL),
    ("sprintCatalog", CURATED_SPRINT_CATALOG_REL),
    ("sprintQueue", CURATED_SPRINT_QUEUE_REL),
    ("lessons", CURATED_LESSONS_REL),
    ("closeOuts", CURATED_CLOSE_OUTS_REL),
    ("issues", CURATED_ISSUES_REL),
    ("roadmapReviews", CURATED_ROADMAP_REVIEWS_REL),
    ("outsideAudits", CURATED_OUTSIDE_AUDITS_REL),
    ("reference", CURATED_REFERENCE_REL),
    ("epics", CURATED_EPICS_REL),
    ("roadmapArchives", CURATED_ROADMAP_ARCHIVES_REL),
]

# Verbatim copy of production's GOVERNANCE_README_TEMPLATE (I5a review, FIX 2): GoG's live
# readme was verified byte-identical to this exact text, so it -- not an invented
# simplification -- is the ground truth the "byte-identical convergence" assertions below are
# checked against. Keep this in sync with GOVERNANCE_README_TEMPLATE in virtuoso_preflight.py.
_CURATED_README_TEMPLATE = """# Virtuoso Governance Registry

**This file is the authority.** It is the single source of truth for where this project's
governance documents live. Every Virtuoso skill (`/roadmap-review`, `/roadmap-status`,
`/next-pointer`, `/pointer-closeout`, `/mid-dispatch-decision`, `/3rd-party-audit`) resolves
the roadmap, sprint catalog, lessons log, close-outs, issues, and review artifacts through the
registry below — and **never creates a parallel or competing document for a role already
registered here.**

Register the project's real files wherever they actually live (e.g. `docs/governance/ROADMAP.md`).
When a document already exists, this registry points at it; nothing is copied, moved, or seeded
beside it. `Virtuoso/workspace-layout.json` is the machine-readable mirror of the same paths.

## Required documents

| Role | Path | Status |
|------|------|--------|
{table}

## Rules for skills

1. **Resolve every governance document through this registry** before reading or writing.
2. **Never create a new document for a role already registered** — open and edit the
   registered file in place.
3. If a required role is `⬜ not present` and the work needs it, **register the project's
   existing file** (preferred) or create one **and register it here** — never leave a rival
   unregistered or seed an empty template beside a real document.
4. If the registry and the files on disk diverge, **fix the registry** (repoint the path to
   the existing document) — do not fork a rival.

<!-- virtuoso-governance-registry
{machine}
-->
"""


def _eol_toggled(data):
    """Flip `data`'s line-ending convention (CRLF<->LF): the result normalizes identically to
    the input (both collapse to the same bytes under \\r\\n -> \\n) but differs from the input
    byte-for-byte otherwise. Direction-agnostic so the fixture is reproducible regardless of
    which EOL style this checkout's core.autocrlf setting gave the plugin's own source file."""
    normalized = data.replace(b"\r\n", b"\n")
    if b"\r\n" in data:
        return normalized  # input had CRLF -> vendored copy uses bare LF
    return normalized.replace(b"\n", b"\r\n")  # input was bare LF -> vendored copy uses CRLF


def build_curated_fixture(root):
    """Build the R6 repro fixture: a markered, hand-curated, HEALTHY Virtuoso project whose
    registry (workspace-layout.json + Virtuoso.Governance.Readme.md's machine block) is
    self-consistent and authoritative. A correct preflight run (detect or heal/adopt) must
    leave every byte of it alone.

    Reused by test_detect_mode_mutates_nothing_on_markered_project,
    test_heal_preserves_curated_registry_and_custom_roles, and
    test_vendor_refresh_skips_eol_only_differences; kept import/call-able standalone (only
    needs a root path) for reuse by deployment verification.

    Returns a dict of the fixture's interesting paths and curated relative-path constants:
    root, doc_root, roadmap_rel, archive_rel, lessons_rel, epics_rel, roadmap_archives_rel,
    manifest_path, readme_path, vendored_script_path.
    """
    root = Path(root)
    docs = root / CURATED_DOC_ROOT

    for rel in (
        "1 governance",
        "2 operational",
        "3 temp",
        "4 Outside Audits",
        "5 Reference",
        "2 operational/roadmap-reviews",
        "2 operational/roadmap-reviews/checkins",
        "2 operational/Close-Outs",
        "2 operational/Issues",
        "archives",
    ):
        (docs / rel).mkdir(parents=True, exist_ok=True)

    (docs / "2 operational" / "GoG_Roadmap.md").write_text(_LIVE_ROADMAP_TEXT, encoding="utf-8")
    (docs / "archives" / "GoG_Roadmap_Archive_2026-07-10.md").write_text(
        _ARCHIVED_ROADMAP_TEXT, encoding="utf-8"
    )
    (docs / "1 governance" / "GoG_Lessons_Catalog.md").write_text(
        _LESSONS_CATALOG_TEXT, encoding="utf-8"
    )
    (docs / "1 governance" / "Epics.md").write_text(_EPICS_TEXT, encoding="utf-8")
    (docs / "5 Reference" / "WORKFLOW_REFERENCE.md").write_text(
        _WORKFLOW_REFERENCE_TEXT, encoding="utf-8"
    )
    (docs / "2 operational" / "sprint-catalog.csv").write_text(_SPRINT_CATALOG_CSV, encoding="utf-8")
    (docs / "2 operational" / "sprint-queue.xlsx").write_bytes(b"PK\x03\x04 curated workbook stub")

    virtuoso = root / "Virtuoso"
    scripts = virtuoso / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    (virtuoso / ".virtuoso").write_text("virtuoso-workspace\n", encoding="utf-8")

    recalc_bytes = Path(_RECALC_SCRIPT_SRC).read_bytes()
    (scripts / "recalc.py").write_bytes(recalc_bytes)  # byte-identical to the plugin's own copy

    closeout_src_bytes = Path(_CLOSEOUT_SCRIPT_SRC).read_bytes()
    vendored_closeout_bytes = _eol_toggled(closeout_src_bytes)
    assert vendored_closeout_bytes != closeout_src_bytes, (
        "fixture bug: EOL toggle produced no difference from the plugin's source"
    )
    assert (
        vendored_closeout_bytes.replace(b"\r\n", b"\n") == closeout_src_bytes.replace(b"\r\n", b"\n")
    ), "fixture bug: EOL toggle changed more than line endings"
    vendored_script_path = scripts / "prepare_closeout_files.py"
    vendored_script_path.write_bytes(vendored_closeout_bytes)

    manifest_data = {
        "layout": "plugin-only",
        "adopted": False,
        "documentationRoot": CURATED_DOC_ROOT,
        "paths": {
            "governance": CURATED_DOC_ROOT + "/1 governance",
            "operational": CURATED_DOC_ROOT + "/2 operational",
            "temp": CURATED_DOC_ROOT + "/3 temp",
            "outsideAudits": CURATED_OUTSIDE_AUDITS_REL,
            "reference": CURATED_REFERENCE_REL,
            "roadmap": CURATED_ROADMAP_REL,
            "sprintQueue": CURATED_SPRINT_QUEUE_REL,
            "sprintCatalog": CURATED_SPRINT_CATALOG_REL,
            "lessons": CURATED_LESSONS_REL,
            "workflowReference": CURATED_WORKFLOW_REF_REL,
            "closeOuts": CURATED_CLOSE_OUTS_REL,
            "issues": CURATED_ISSUES_REL,
            "roadmapReviews": CURATED_ROADMAP_REVIEWS_REL,
            "scripts": "Virtuoso/scripts",
            "governanceReadme": "Virtuoso.Governance.Readme.md",
            "epics": CURATED_EPICS_REL,
            "roadmapArchives": CURATED_ROADMAP_ARCHIVES_REL,
        },
    }
    manifest_path = virtuoso / "workspace-layout.json"
    manifest_path.write_text(json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8")

    readme_text = _CURATED_README_TEMPLATE.format(
        table="\n".join("| %s | `%s` | %s |" % row for row in _CURATED_ROLE_ROWS),
        machine="\n".join("%s: %s" % pair for pair in _CURATED_MACHINE_PAIRS),
    )
    readme_path = root / "Virtuoso.Governance.Readme.md"
    readme_path.write_text(readme_text, encoding="utf-8")

    return {
        "root": root,
        "doc_root": CURATED_DOC_ROOT,
        "roadmap_rel": CURATED_ROADMAP_REL,
        "archive_rel": CURATED_ARCHIVE_REL,
        "lessons_rel": CURATED_LESSONS_REL,
        "epics_rel": CURATED_EPICS_REL,
        "roadmap_archives_rel": CURATED_ROADMAP_ARCHIVES_REL,
        "manifest_path": manifest_path,
        "readme_path": readme_path,
        "vendored_script_path": vendored_script_path,
    }


# ---------------------------------------------------------------------------
# SK-01: registry mirror invariant + GoG-facsimile fixture. The readme is hand-damaged to the
# v1.3.0 signature while the manifest stays correct/curated -- proving a single heal converges
# the readme to the manifest exactly, without touching real user content (SR-3: a real-sized
# lessons file at the curated path the damaged readme fails to name).
# ---------------------------------------------------------------------------

# The plugin's default lessons stub path -- the exact "1 governance/" location a v1.3.0-era
# readme pointed the lessons role at, before GoG's own curated Lessons Catalog was registered.
_V1_3_0_LESSONS_STUB_REL = CURATED_DOC_ROOT + "/1 governance/SpecRetro.Lessons_Learned.md"

# The v1.3.0-signature machine block: the 9 known roles only (the epics/roadmapArchives
# project-custom-role feature postdates this signature -- R2), with roadmap repointed at the
# archive snapshot and lessons repointed at the plugin's default stub instead of the curated
# catalog. Every other role matches the correct/curated ground truth verbatim.
_V1_3_0_ROLE_ROWS = [
    ("Roadmap", CURATED_ARCHIVE_REL, "✅ registered"),
    ("Sprint catalog (CSV — source of truth)", CURATED_SPRINT_CATALOG_REL, "✅ registered"),
    ("Sprint queue (xlsx — optional generated report)", CURATED_SPRINT_QUEUE_REL, "✅ registered"),
    ("Lessons / retrospective", _V1_3_0_LESSONS_STUB_REL, "⬜ not present"),
    ("Close-outs (directory)", CURATED_CLOSE_OUTS_REL, "✅ registered"),
    ("Issues (directory)", CURATED_ISSUES_REL, "✅ registered"),
    ("Roadmap reviews (directory)", CURATED_ROADMAP_REVIEWS_REL, "✅ registered"),
    ("Outside audits (directory)", CURATED_OUTSIDE_AUDITS_REL, "✅ registered"),
    ("Reference (directory)", CURATED_REFERENCE_REL, "✅ registered"),
]
_V1_3_0_MACHINE_PAIRS = [
    ("roadmap", CURATED_ARCHIVE_REL),
    ("sprintCatalog", CURATED_SPRINT_CATALOG_REL),
    ("sprintQueue", CURATED_SPRINT_QUEUE_REL),
    ("lessons", _V1_3_0_LESSONS_STUB_REL),
    ("closeOuts", CURATED_CLOSE_OUTS_REL),
    ("issues", CURATED_ISSUES_REL),
    ("roadmapReviews", CURATED_ROADMAP_REVIEWS_REL),
    ("outsideAudits", CURATED_OUTSIDE_AUDITS_REL),
    ("reference", CURATED_REFERENCE_REL),
    # no "epics" / "roadmapArchives" -- absent in the v1.3.0 signature (predates R2).
]

_GOG_FACSIMILE_LESSONS_MIN_BYTES = 1024 * 1024  # SR-3: a real-sized (>=1 MB) lessons file


def build_gog_facsimile(root):
    """GoG-facsimile fixture (SK-01): reuses build_curated_fixture's CORRECT, complete manifest
    (curated custom paths incl. epics/roadmapArchives) but hand-damages the governance readme
    to the v1.3.0 signature that predates it: roadmap repointed at the archive snapshot,
    lessons repointed at the plugin's default stub path, and both project-custom keys entirely
    absent. Also inflates the real lessons file (at the CURATED path the damaged readme fails
    to name) past 1 MB per SR-3, so a heal that repairs the registry without touching real user
    content is provably distinguishable from one that doesn't.

    Returns build_curated_fixture's dict plus: 'lessons_path' (absolute), 'default_lessons_
    stub_path' (absolute; expected to stay absent), 'correct_readme_bytes' and
    'correct_manifest_bytes' (the pre-damage, manifest-matching ground truth a single heal is
    expected to reconstruct byte-for-byte).
    """
    fx = build_curated_fixture(root)
    root = Path(root)

    correct_readme_bytes = fx["readme_path"].read_bytes()
    correct_manifest_bytes = fx["manifest_path"].read_bytes()

    # Inflate the real lessons file at its curated (correct) path past 1 MB (SR-3) -- content
    # is asserted preserved after heal, not just size, so pad rather than truncate/replace.
    lessons_path = root / fx["lessons_rel"]
    lessons_text = _LESSONS_CATALOG_TEXT
    pad_needed = _GOG_FACSIMILE_LESSONS_MIN_BYTES - len(lessons_text.encode("utf-8"))
    if pad_needed > 0:
        lessons_text += "\n<!-- SR-3 padding -->\n" + ("x" * pad_needed)
    lessons_path.write_text(lessons_text, encoding="utf-8")
    assert lessons_path.stat().st_size >= _GOG_FACSIMILE_LESSONS_MIN_BYTES

    # Hand-damage the readme to the v1.3.0 signature -- same template, different table/machine.
    damaged_readme = _CURATED_README_TEMPLATE.format(
        table="\n".join("| %s | `%s` | %s |" % row for row in _V1_3_0_ROLE_ROWS),
        machine="\n".join("%s: %s" % pair for pair in _V1_3_0_MACHINE_PAIRS),
    )
    fx["readme_path"].write_text(damaged_readme, encoding="utf-8")

    fx["lessons_path"] = lessons_path
    fx["default_lessons_stub_path"] = root / _V1_3_0_LESSONS_STUB_REL
    fx["correct_readme_bytes"] = correct_readme_bytes
    fx["correct_manifest_bytes"] = correct_manifest_bytes
    return fx


def _hash_walk(root, exclude_top=(".virtuoso",)):
    """Recursive content+structure snapshot of a directory tree: {relative file path -> sha256
    of its bytes}, plus the set of every relative directory path -- so both content drift and
    new/removed files-or-dirs are caught. Excludes top-level entries named in `exclude_top`:
    the cross-project ~/.virtuoso plugin-root bridge (record_root() in virtuoso_preflight.py)
    is written unconditionally on every invocation by design (see test_detect_noop_on_plain_
    folder above, which already treats it as an always-expected side effect) and is out of
    scope for the "detect writes nothing" contract, which is about the PROJECT tree."""
    root = Path(root)
    files = {}
    dirs = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirpath = Path(dirpath)
        rel_dir = dirpath.relative_to(root)
        if rel_dir == Path("."):
            dirnames[:] = [d for d in dirnames if d not in exclude_top]
        else:
            dirs.add(rel_dir.as_posix())
        for fn in filenames:
            fp = dirpath / fn
            rel = fp.relative_to(root).as_posix()
            files[rel] = hashlib.sha256(fp.read_bytes()).hexdigest()
    return files, dirs


def test_detect_mode_mutates_nothing_on_markered_project(tmp_path):
    """R1: the SessionStart hook's exact invocation (--mode detect --quiet) must mutate ZERO
    bytes of a markered, curated project. Current code's detect branch unconditionally calls
    _heal(), which regenerates the registry from discovery/defaults instead of treating the
    curated registry as authoritative -- expected to fail on a hash-walk mismatch, not on a
    fixture or harness bug."""
    build_curated_fixture(tmp_path)
    before_files, before_dirs = _hash_walk(tmp_path)

    rc, _out = _run_capture("--root", str(tmp_path), "--mode", "detect", "--quiet", root=tmp_path)

    after_files, after_dirs = _hash_walk(tmp_path)
    assert rc == 0
    assert after_dirs == before_dirs, "detect mode created or removed a directory"
    assert after_files == before_files, "detect mode mutated file content on a curated project"


def test_heal_preserves_curated_registry_and_custom_roles(tmp_path):
    """R2: heal/adopt on an already-curated project must treat the registry as authoritative --
    converging byte-identical, round-tripping project-custom roles (epics, roadmapArchives) in
    both registry files, keeping the registered live roadmap even though the archive outscores
    it structurally (3 markers vs 2), and reconstructing a deleted manifest from the readme's
    machine block with curated paths rather than re-derived defaults. Current code regenerates
    both files purely from discovery/defaults every run, dropping unknown keys and re-pointing
    the roadmap at whichever candidate scores highest."""
    fx = build_curated_fixture(tmp_path)
    manifest_before = fx["manifest_path"].read_bytes()
    readme_before = fx["readme_path"].read_bytes()

    rc, _out = _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    assert rc == 0

    manifest_after = fx["manifest_path"].read_bytes()
    readme_after = fx["readme_path"].read_bytes()

    assert manifest_after == manifest_before, "heal rewrote the curated manifest"
    assert readme_after == readme_before, "heal rewrote the curated governance readme"

    m = json.loads(manifest_after.decode("utf-8"))
    assert m["paths"].get("epics") == fx["epics_rel"], "epics role dropped from the manifest"
    assert m["paths"].get("roadmapArchives") == fx["roadmap_archives_rel"], (
        "roadmapArchives role dropped from the manifest"
    )

    readme_text = readme_after.decode("utf-8")
    assert ("epics: " + fx["epics_rel"]) in readme_text, "epics role dropped from the readme"
    assert ("roadmapArchives: " + fx["roadmap_archives_rel"]) in readme_text, (
        "roadmapArchives role dropped from the readme"
    )

    assert m["paths"]["roadmap"] != fx["archive_rel"], (
        "roadmap pointer was repointed to the archive (structural-marker discovery beat the "
        "registered path)"
    )
    assert m["paths"]["roadmap"] == fx["roadmap_rel"], (
        "roadmap pointer was repointed away from the registered live roadmap: "
        + m["paths"]["roadmap"]
    )

    # R3 acceptance criterion: lessons is registered under a non-default (real, curated) name,
    # so heal must never seed the default stub path beside it.
    default_lessons_stub = fx["root"] / CURATED_DOC_ROOT / "1 governance" / "SpecRetro.Lessons_Learned.md"
    assert not default_lessons_stub.exists(), (
        "heal seeded a lessons stub at the default path even though lessons is registered "
        "at a real, curated path: " + str(default_lessons_stub)
    )

    # R2 last criterion: manifest deleted, readme intact -> heal must reconstruct the manifest
    # from the machine block with curated paths, not re-derived defaults. Uses a fresh fixture
    # instance so this sub-scenario isn't muddied by the (already-clobbered, under RED) state
    # left behind by the assertions above.
    recon_root = tmp_path / "manifest_reconstruction"
    recon_root.mkdir()
    fx2 = build_curated_fixture(recon_root)
    fx2["manifest_path"].unlink()

    rc2, _out2 = _run_capture("--root", str(recon_root), "--mode", "adopt", root=recon_root)
    assert rc2 == 0
    assert fx2["manifest_path"].exists(), "heal did not reconstruct a missing manifest at all"

    m2 = json.loads(fx2["manifest_path"].read_text(encoding="utf-8"))
    assert m2["paths"].get("roadmap") == fx2["roadmap_rel"], (
        "reconstructed manifest did not recover the curated roadmap pointer from the readme's "
        "machine block: " + str(m2["paths"].get("roadmap"))
    )
    assert m2["paths"].get("lessons") == fx2["lessons_rel"], (
        "reconstructed manifest did not recover the curated lessons pointer"
    )
    assert m2["paths"].get("epics") == fx2["epics_rel"], (
        "reconstructed manifest did not recover the epics custom role"
    )
    assert m2["paths"].get("roadmapArchives") == fx2["roadmap_archives_rel"], (
        "reconstructed manifest did not recover the roadmapArchives custom role"
    )


def test_vendor_refresh_skips_eol_only_differences(tmp_path):
    """R5: _refresh_copy must normalize CRLF<->LF before comparing, so a vendored script that
    differs from the plugin's bundled copy ONLY by line-ending convention is left alone.
    Current code does a raw byte comparison and rewrites (reporting "refreshed") on every run
    purely because of EOL convention, even though the content is identical."""
    fx = build_curated_fixture(tmp_path)
    vendored_before = fx["vendored_script_path"].read_bytes()

    rc, _out = _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    assert rc == 0

    vendored_after = fx["vendored_script_path"].read_bytes()
    assert vendored_after == vendored_before, (
        "vendor refresh rewrote a script that differed from the plugin's copy only by EOL "
        "convention"
    )


def test_create_mode_still_scaffolds_bare_tree(tmp_path):
    """R3 regression pin: --mode create on a bare (unmarkered, empty) tree must still scaffold
    the full workspace exactly as before -- registry-authority changes must not regress the
    create-mode bootstrap path. Expected to PASS against current code."""
    _run(tmp_path, "create")
    for d in PLUGIN_ONLY_DIRS:
        assert (tmp_path / d).is_dir(), d
    for f in PLUGIN_ONLY_FILES:
        assert (tmp_path / f).is_file(), f
    assert (tmp_path / "Virtuoso.Governance.Readme.md").is_file()
    m = _manifest(tmp_path)
    assert m["paths"]["roadmap"] == "Project Documentation/1 governance/Roadmap.md"


# ---------------------------------------------------------------------------
# I5a spec-compliance review fixes.
# ---------------------------------------------------------------------------

def _build_nondefault_close_outs_fixture(root):
    """A markered, curated, non-adopted (layout:plugin-only, adopted:false -- i.e. the
    _build_full route) project that registers the "closeOuts" directory role at a
    project-specific, NON-default path ("2 operational/sprints") while the computed-default
    location ("2 operational/Close-Outs") is absent from disk -- empirically live for GoG.
    Regression fixture for FIX 1 (I5a review): _build_full's directory-scaffolding loop ran
    on paths computed BEFORE the registry overlay was applied, so it could conjure a phantom
    empty directory at the unused default location even though the role is registered
    elsewhere. Returns {root, close_outs_rel, default_close_outs_path}."""
    root = Path(root)
    docs = root / "2. Project Documentation"
    close_outs_rel = "2. Project Documentation/2 operational/sprints"
    (docs / "2 operational" / "sprints").mkdir(parents=True, exist_ok=True)

    virtuoso = root / "Virtuoso"
    (virtuoso / "scripts").mkdir(parents=True, exist_ok=True)
    (virtuoso / ".virtuoso").write_text("virtuoso-workspace\n", encoding="utf-8")

    manifest_data = {
        "layout": "plugin-only",
        "adopted": False,
        "documentationRoot": "2. Project Documentation",
        "paths": {
            "governance": "2. Project Documentation/1 governance",
            "operational": "2. Project Documentation/2 operational",
            "temp": "2. Project Documentation/3 temp",
            "outsideAudits": "2. Project Documentation/4 Outside Audits",
            "reference": "2. Project Documentation/5 Reference",
            "roadmap": "2. Project Documentation/1 governance/Roadmap.md",
            "sprintQueue": "2. Project Documentation/2 operational/sprint-queue.xlsx",
            "sprintCatalog": "2. Project Documentation/2 operational/sprint-catalog.csv",
            "lessons": "2. Project Documentation/1 governance/SpecRetro.Lessons_Learned.md",
            "workflowReference": "2. Project Documentation/5 Reference/WORKFLOW_REFERENCE.md",
            "closeOuts": close_outs_rel,
            "issues": "2. Project Documentation/2 operational/Issues",
            "scripts": "Virtuoso/scripts",
            "governanceReadme": "Virtuoso.Governance.Readme.md",
        },
    }
    (virtuoso / "workspace-layout.json").write_text(
        json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "root": root,
        "close_outs_rel": close_outs_rel,
        "default_close_outs_path": docs / "2 operational" / "Close-Outs",
    }


def test_registry_overlay_applied_before_directory_scaffolding(tmp_path):
    """Regression (I5a review, FIX 1): _build_full must read and apply the registry overlay
    BEFORE its _ensure_dir scaffolding loop runs, not after -- otherwise a directory role
    registered at a non-default path (closeOuts -> "sprints" here) still gets a phantom empty
    directory conjured at the unused computed-default location ("Close-Outs"). Empirically
    live for GoG (adopted:false / layout:plugin-only is the _build_full route). Checked via
    filesystem, not git status: an empty directory is invisible to git."""
    fx = _build_nondefault_close_outs_fixture(tmp_path)
    default_close_outs = fx["default_close_outs_path"]
    assert not default_close_outs.exists()  # sanity: fixture starts without the phantom dir

    rc, _out = _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    assert rc == 0
    assert not default_close_outs.exists(), (
        "heal (_build_full) created a phantom directory at the default closeOuts location "
        "even though closeOuts is registered elsewhere: " + str(default_close_outs)
    )

    rc2, _out2 = _run_capture(
        "--root", str(tmp_path), "--mode", "detect", "--quiet", root=tmp_path
    )
    assert rc2 == 0
    assert not default_close_outs.exists(), (
        "detect created a phantom directory at the default closeOuts location even though "
        "closeOuts is registered elsewhere: " + str(default_close_outs)
    )


def _build_registered_missing_roadmap_fixture(root):
    """An ADOPTED (thin) markered project where "roadmap" is registered at a path that does
    NOT exist on disk, while a real, structurally-rich roadmap sits elsewhere in the docs tree
    -- discoverable, and would win both _discover_roadmap and _discover_roadmap_anywhere if
    the registry didn't short-circuit them first. Fixture for R4 ("a registered path absent on
    disk stays registered ... never re-guessed or re-anchored"). Returns {root,
    registered_roadmap_rel, discoverable_roadmap_rel}."""
    root = Path(root)
    docs = root / "2. Project Documentation"
    op = docs / "2 operational"
    op.mkdir(parents=True, exist_ok=True)
    (docs / "1 governance").mkdir(parents=True, exist_ok=True)

    # A real, discoverable roadmap that would win on structural markers if discovery ran.
    discoverable_roadmap_rel = "2. Project Documentation/2 operational/Discoverable_Roadmap.md"
    (op / "Discoverable_Roadmap.md").write_text(
        "# Discoverable\n## Completed Work Summary\n## Active & Remaining Sprint Skeletons\n"
        "Finish Line\n",
        encoding="utf-8",
    )
    # The registered roadmap path -- deliberately never created on disk.
    registered_roadmap_rel = "2. Project Documentation/1 governance/Registered_Roadmap.md"

    virtuoso = root / "Virtuoso"
    (virtuoso / "scripts").mkdir(parents=True, exist_ok=True)
    (virtuoso / ".virtuoso").write_text("virtuoso-workspace\n", encoding="utf-8")

    manifest_data = {
        "layout": "plugin-only",
        "adopted": True,
        "documentationRoot": "2. Project Documentation",
        "paths": {
            "governance": "2. Project Documentation/1 governance",
            "operational": "2. Project Documentation/2 operational",
            "temp": "2. Project Documentation/3 temp",
            "outsideAudits": "2. Project Documentation/4 Outside Audits",
            "reference": "2. Project Documentation/5 Reference",
            "roadmap": registered_roadmap_rel,
            "sprintQueue": "2. Project Documentation/2 operational/sprint-queue.xlsx",
            "sprintCatalog": "2. Project Documentation/2 operational/sprint-catalog.csv",
            "lessons": "2. Project Documentation/1 governance/SpecRetro.Lessons_Learned.md",
            "workflowReference": "2. Project Documentation/5 Reference/WORKFLOW_REFERENCE.md",
            "closeOuts": "2. Project Documentation/2 operational/Close-Outs",
            "issues": "2. Project Documentation/2 operational/Issues",
            "scripts": "Virtuoso/scripts",
            "governanceReadme": "Virtuoso.Governance.Readme.md",
        },
    }
    (virtuoso / "workspace-layout.json").write_text(
        json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "root": root,
        "registered_roadmap_rel": registered_roadmap_rel,
        "discoverable_roadmap_rel": discoverable_roadmap_rel,
    }


def test_registered_but_missing_path_kept_and_marked_not_present(tmp_path):
    """R4: a registered path absent on disk stays registered (with the CURATED path, in both
    regenerated outputs), renders "not present" in the readme, and is never re-guessed or
    re-anchored by discovery -- even when a real, structurally-rich alternative sits right
    there in the docs tree and would otherwise win. Uses an adopted (thin) project so BOTH
    _apply_discovery's short-circuit and _build_thin's _anchor_adopted_paths fallback are
    exercised (both are gated by the same "already registered" check)."""
    fx = _build_registered_missing_roadmap_fixture(tmp_path)
    assert not (tmp_path / fx["registered_roadmap_rel"]).exists()  # sanity: genuinely missing

    rc, _out = _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    assert rc == 0

    m = _manifest(tmp_path)
    assert m["paths"]["roadmap"] == fx["registered_roadmap_rel"], (
        "registered-but-missing roadmap was re-guessed/re-anchored to a discoverable "
        "alternative: " + m["paths"]["roadmap"]
    )

    readme = (tmp_path / "Virtuoso.Governance.Readme.md").read_text(encoding="utf-8")
    assert ("`" + fx["registered_roadmap_rel"] + "` | ⬜ not present") in readme, readme
    assert fx["discoverable_roadmap_rel"] not in readme, (
        "the discoverable alternative leaked into the registry despite roadmap being "
        "registered elsewhere"
    )

    # Still never seeded/created -- heal only registers, it does not conjure content (R3).
    assert not (tmp_path / fx["registered_roadmap_rel"]).exists()


# ---------------------------------------------------------------------------
# SK-01: registry mirror invariant -- the readme's machine block must parse to exactly the
# manifest's path mapping after every regenerating run; a GoG-facsimile fixture proves a
# single heal converges a damaged readme to the manifest without touching real user content.
# ---------------------------------------------------------------------------

def test_readme_machine_block_mirrors_manifest_after_every_write(tmp_path):
    """SK-01: after every regenerating run (create, adopt-triggered heal, detect-triggered
    heal), the readme's machine block must parse to exactly the manifest's path mapping for
    every role _ROLE_PATHKEY knows about -- the invariant _assert_registry_mirror enforces
    internally right after each writer pair in _build_full/_build_thin."""
    build_curated_fixture(tmp_path)

    for mode_args in (
        ("--mode", "create"),
        ("--mode", "adopt"),
        ("--mode", "detect", "--quiet"),
    ):
        rc, out = _run_capture("--root", str(tmp_path), *mode_args, root=tmp_path)
        assert rc == 0, out

        overlay = vp._read_registry_from_readme(str(tmp_path)) or {}
        manifest_paths = json.loads(
            (tmp_path / "Virtuoso" / "workspace-layout.json").read_text(encoding="utf-8")
        )["paths"]
        expected = {k: v for k, v in manifest_paths.items() if k in vp._ROLE_PATHKEY}
        assert expected, "sanity: manifest carried no known governance roles to compare"
        for key, rel in expected.items():
            assert overlay.get(key) == rel, (
                "mode=%s role=%s readme=%r manifest=%r"
                % (mode_args, key, overlay.get(key), rel)
            )


def test_gog_facsimile_damaged_readme_heals_from_manifest(tmp_path):
    """SK-01 Done-when 3: a GoG-facsimile fixture -- correct/curated manifest, readme hand-
    damaged to the v1.3.0 signature (roadmap -> archive, lessons -> default stub, custom keys
    absent) -- must converge to the manifest in a SINGLE heal, and the real (>=1 MB per SR-3)
    lessons file living at the curated path the damaged readme fails to name must be left
    completely untouched (size and content)."""
    fx = build_gog_facsimile(tmp_path)

    lessons_before = fx["lessons_path"].read_bytes()
    assert len(lessons_before) >= _GOG_FACSIMILE_LESSONS_MIN_BYTES  # sanity: fixture as specced
    damaged_readme_before = fx["readme_path"].read_bytes()
    assert damaged_readme_before != fx["correct_readme_bytes"], (
        "fixture bug: hand-damaged readme is not actually different from the correct one"
    )

    rc, out = _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    assert rc == 0, out

    assert fx["readme_path"].read_bytes() == fx["correct_readme_bytes"], (
        "one heal did not converge the damaged readme to exactly the manifest's registry"
    )
    assert fx["manifest_path"].read_bytes() == fx["correct_manifest_bytes"], (
        "heal rewrote the already-correct manifest"
    )
    assert fx["lessons_path"].read_bytes() == lessons_before, (
        "heal touched the real lessons file's content"
    )
    assert not fx["default_lessons_stub_path"].exists(), (
        "heal seeded/created a lessons stub at the plugin's default path even though lessons "
        "is registered at the real curated path"
    )


# ---------------------------------------------------------------------------
# SK-02 / R10: readme-only roles (roadmapReviews, documentationRoot) must round-trip through
# the manifest instead of being re-defaulted by the next regeneration. Live repro (twice on
# 2026-07-18): the manifest schema could not carry roadmapReviews at all, so the manifest-first
# overlay fallback silently dropped a curated readme-only value on every subsequent heal.
# ---------------------------------------------------------------------------

def test_roadmap_reviews_registration_round_trips_through_manifest(tmp_path):
    """RED-first (the live regression): simulate a pre-migration project -- an existing manifest
    whose schema pre-dates roadmapReviews entirely (the key is simply absent from its "paths"
    dict, exactly like every manifest written by the unfixed code), while the governance readme
    carries a curated, non-default roadmapReviews repoint in its machine block (the readme is
    the only carrier before migration). Two further regenerations must (1) migrate the curated
    readme-only value into the manifest the first time it's observed, and (2) never re-default
    it afterward once the manifest carries it."""
    _run(tmp_path, "create")

    default_rel = "Project Documentation/2 operational/roadmap-reviews"
    curated_rel = "roadmap-reviews"  # curated repoint: project root, not the computed default
    (tmp_path / curated_rel).mkdir()

    # Pre-migration manifest: ensure roadmapReviews is absent entirely, exactly as every
    # manifest written by the unfixed code would have it (the schema simply never emitted the
    # key) -- unconditional so this fixture setup is valid whether or not the manifest writer
    # has already been fixed to emit it.
    manifest_path = tmp_path / "Virtuoso" / "workspace-layout.json"
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_data["paths"].pop("roadmapReviews", None)
    manifest_path.write_text(json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8")

    # The readme is the only carrier of the curated repoint before migration.
    readme_path = tmp_path / "Virtuoso.Governance.Readme.md"
    text = readme_path.read_text(encoding="utf-8")
    assert ("roadmapReviews: " + default_rel) in text  # sanity: default value present pre-edit
    assert ("| Roadmap reviews (directory) | `" + default_rel + "` | ✅ registered |") in text
    text = text.replace("roadmapReviews: " + default_rel, "roadmapReviews: " + curated_rel)
    text = text.replace(
        "| Roadmap reviews (directory) | `" + default_rel + "` | ✅ registered |",
        "| Roadmap reviews (directory) | `" + curated_rel + "` | ✅ registered |",
    )
    readme_path.write_text(text, encoding="utf-8")

    # First regeneration: the curated readme-only value must be migrated into the manifest.
    _run(tmp_path, "detect")
    m = _manifest(tmp_path)
    assert m["paths"].get("roadmapReviews") == curated_rel, (
        "curated roadmapReviews value from the readme was not carried into the manifest: "
        + str(m["paths"].get("roadmapReviews"))
    )

    # Second regeneration: now that the manifest carries it, it must not be re-defaulted.
    _run(tmp_path, "detect")
    m2 = _manifest(tmp_path)
    assert m2["paths"].get("roadmapReviews") == curated_rel, (
        "roadmapReviews value was re-defaulted by a subsequent regeneration: "
        + str(m2["paths"].get("roadmapReviews"))
    )
    readme_after = readme_path.read_text(encoding="utf-8")
    assert ("roadmapReviews: " + curated_rel) in readme_after, (
        "readme machine block was re-defaulted by a subsequent regeneration"
    )


def _build_custom_documentation_root_fixture(root):
    """A markered, ADOPTED (thin) project whose manifest curates "documentationRoot" as a
    folder name that is NOT one of DOC_ROOT_CANDIDATES ("Project Documentation" /
    "2. Project Documentation") -- so _project_doc_root's discovery pass finds no established
    candidate on disk and falls back to the plugin's own default ("Project Documentation",
    which does not even exist here). Every known role is registered under the custom root so
    _apply_registry_overlay/_apply_discovery short-circuit and never touch paths["docs"]
    itself -- isolating documentationRoot preservation as the only thing under test. Returns
    {root, custom_doc_root_rel}."""
    root = Path(root)
    custom_doc_root_rel = "GoG Docs"
    docs = root / custom_doc_root_rel
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "GoG_Roadmap.md").write_text(
        "# GoG Roadmap\n## Completed Work Summary\n## Active & Remaining Sprint Skeletons\n",
        encoding="utf-8",
    )
    (docs / "sprint-queue.xlsx").write_bytes(b"PK\x03\x04 stub workbook")

    virtuoso = root / "Virtuoso"
    (virtuoso / "scripts").mkdir(parents=True, exist_ok=True)
    (virtuoso / ".virtuoso").write_text("virtuoso-workspace\n", encoding="utf-8")

    manifest_data = {
        "layout": "plugin-only",
        "adopted": True,
        "documentationRoot": custom_doc_root_rel,
        "paths": {
            "roadmap": custom_doc_root_rel + "/GoG_Roadmap.md",
            "sprintQueue": custom_doc_root_rel + "/sprint-queue.xlsx",
            "sprintCatalog": custom_doc_root_rel + "/sprint-catalog.csv",
            "lessons": custom_doc_root_rel + "/SpecRetro.Lessons_Learned.md",
            "closeOuts": custom_doc_root_rel + "/Close-Outs",
            "issues": custom_doc_root_rel + "/Issues",
            "roadmapReviews": custom_doc_root_rel + "/roadmap-reviews",
            "outsideAudits": custom_doc_root_rel + "/Outside Audits",
            "reference": custom_doc_root_rel + "/Reference",
            "scripts": "Virtuoso/scripts",
            "governanceReadme": "Virtuoso.Governance.Readme.md",
        },
    }
    (virtuoso / "workspace-layout.json").write_text(
        json.dumps(manifest_data, indent=2) + "\n", encoding="utf-8"
    )
    return {"root": root, "custom_doc_root_rel": custom_doc_root_rel}


def test_documentation_root_preserved_on_regeneration(tmp_path):
    """SK-02 / R10: an existing manifest's curated documentationRoot must be preserved verbatim
    across regeneration, not recomputed from _project_doc_root's discovery pass -- which would
    silently fall back to the plugin's own default candidate name ("Project Documentation")
    instead of the project's real, custom-named documentation root, even though nothing on
    disk actually changed. Two further regenerations must leave it untouched."""
    fx = _build_custom_documentation_root_fixture(tmp_path)

    rc, out = _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    assert rc == 0, out
    m = _manifest(tmp_path)
    assert m["documentationRoot"] == fx["custom_doc_root_rel"], (
        "documentationRoot was recomputed instead of preserved: " + m["documentationRoot"]
    )
    # sanity: the plugin's own default candidate was never discovered/created here
    assert not (tmp_path / "Project Documentation").exists()

    # A second regeneration (detect-triggered heal) must not drift it either.
    rc2, out2 = _run_capture(
        "--root", str(tmp_path), "--mode", "detect", "--quiet", root=tmp_path
    )
    assert rc2 == 0, out2
    m2 = _manifest(tmp_path)
    assert m2["documentationRoot"] == fx["custom_doc_root_rel"], (
        "documentationRoot drifted on a second regeneration: " + m2["documentationRoot"]
    )


# ---------------------------------------------------------------------------
# PF-01: line-ending preservation (C2) + semantic-difference manifest writes (C1 residual).
# See Roadmap.md "#### PF-01" (Phase 4 -- Preflight Write Discipline) and the worked reference
# soak-check.py::check_line_ending_preservation, which this section's tests mirror.
# ---------------------------------------------------------------------------

def _force_eol(data, eol):
    """Normalize `data`'s line endings to exactly `eol` (b"\\n" or b"\\r\\n") throughout."""
    normalized = data.replace(b"\r\n", b"\n")
    if eol == b"\n":
        return normalized
    return normalized.replace(b"\n", b"\r\n")


def test_refresh_text_preserves_lf_line_endings(tmp_path):
    """PF-01 / C2: a registry file that is pure LF, given a GENUINE content change (not just a
    settled no-op), comes back with CRLF=0 -- _refresh_text must preserve the file's own line
    ending on write instead of letting Python's text-mode write impose the platform default.
    The writer early-outs on a settled tree and never opens the files at all, so this forces a
    real rewrite first by dropping a known role key from the manifest (mirrors
    soak-check.py::check_line_ending_preservation, the worked reference for this exact check) --
    a test that never triggers a write would prove only that an untouched file keeps its bytes."""
    build_curated_fixture(tmp_path)
    rc, out = _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    assert rc == 0, out  # settle first

    readme = tmp_path / "Virtuoso.Governance.Readme.md"
    manifest = tmp_path / "Virtuoso" / "workspace-layout.json"

    # Force pure LF -- the condition that exposes the defect.
    for p in (readme, manifest):
        p.write_bytes(_force_eol(p.read_bytes(), b"\n"))

    # Force a genuine rewrite: drop a known role key from the manifest. `pre_heal` snapshots
    # the state right before healing -- for the manifest that's the DROPPED-key text, which is
    # guaranteed to differ from whatever the writer regenerates (restoring the key), so
    # "rewritten" is detected by construction rather than by luck of whether the final bytes
    # happen to match some earlier snapshot (on a platform whose default already matches the
    # target convention, comparing against the ORIGINAL settled snapshot would risk a false
    # "no rewrite happened" here even though a write syscall did occur).
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert "sprintCatalog" in data["paths"], "sanity: fixture carries the role we plan to drop"
    data["paths"].pop("sprintCatalog")
    manifest.write_bytes(_force_eol(json.dumps(data, indent=2).encode("utf-8") + b"\n", b"\n"))
    pre_heal = {p: p.read_bytes() for p in (readme, manifest)}

    rc2, out2 = _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    assert rc2 == 0, out2

    post_heal = {p: p.read_bytes() for p in (readme, manifest)}
    assert post_heal[manifest] != pre_heal[manifest], (
        "heal did not rewrite the manifest even though a role key was dropped -- this test "
        "proves nothing"
    )

    rewritten = [p for p in (readme, manifest) if post_heal[p] != pre_heal[p]]
    for p in rewritten:
        crlf = post_heal[p].count(b"\r\n")
        assert crlf == 0, "%s came back with CRLF=%d after an LF-in rewrite" % (p.name, crlf)


def test_refresh_text_preserves_crlf_line_endings(tmp_path):
    """PF-01 / C2: a registry file that is pure CRLF, given a genuine content change, stays
    CRLF -- the mirror-image of test_refresh_text_preserves_lf_line_endings, forcing the
    opposite starting convention so the fix is proven direction-agnostic rather than
    coincidentally matching whatever the test-running platform's default happens to be."""
    build_curated_fixture(tmp_path)
    rc, out = _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    assert rc == 0, out

    readme = tmp_path / "Virtuoso.Governance.Readme.md"
    manifest = tmp_path / "Virtuoso" / "workspace-layout.json"

    for p in (readme, manifest):
        p.write_bytes(_force_eol(p.read_bytes(), b"\r\n"))

    # See test_refresh_text_preserves_lf_line_endings for why "rewritten" is detected against
    # the pre-heal (dropped-key) snapshot rather than the original settled one.
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert "sprintCatalog" in data["paths"], "sanity: fixture carries the role we plan to drop"
    data["paths"].pop("sprintCatalog")
    manifest.write_bytes(_force_eol(json.dumps(data, indent=2).encode("utf-8") + b"\n", b"\r\n"))
    pre_heal = {p: p.read_bytes() for p in (readme, manifest)}

    rc2, out2 = _run_capture("--root", str(tmp_path), "--mode", "adopt", root=tmp_path)
    assert rc2 == 0, out2

    post_heal = {p: p.read_bytes() for p in (readme, manifest)}
    assert post_heal[manifest] != pre_heal[manifest], (
        "heal did not rewrite the manifest even though a role key was dropped -- this test "
        "proves nothing"
    )

    rewritten = [p for p in (readme, manifest) if post_heal[p] != pre_heal[p]]
    for p in rewritten:
        body = post_heal[p]
        crlf = body.count(b"\r\n")
        bare = body.count(b"\n") - crlf
        assert bare == 0, "%s came back with bare LF=%d after a CRLF-in rewrite" % (p.name, bare)


def test_settled_crlf_tree_is_not_rewritten(tmp_path):
    """Anti-regression guard for the PF-01 trap: making _refresh_text's COMPARISON line-ending-
    aware (instead of only the write) would make every settled CRLF tree compare unequal
    against the plain-\\n `content` string and rewrite on EVERY invocation -- the exact opposite
    of this sprint's goal. A settled CRLF workspace, run twice, must have IDENTICAL mtimes and
    raw bytes. This must PASS before AND after the PF-01 change; if it ever fails, the churn
    regression described in the PF-01 spec has been introduced."""
    _run_capture("--root", str(tmp_path), "--mode", "create", root=tmp_path)
    readme = tmp_path / "Virtuoso.Governance.Readme.md"
    manifest = tmp_path / "Virtuoso" / "workspace-layout.json"

    for p in (readme, manifest):
        p.write_bytes(_force_eol(p.read_bytes(), b"\r\n"))
    stat_before = {p: p.stat().st_mtime_ns for p in (readme, manifest)}
    bytes_before = {p: p.read_bytes() for p in (readme, manifest)}

    rc, out = _run_capture("--root", str(tmp_path), "--mode", "create", root=tmp_path)
    assert rc == 0, out

    for p in (readme, manifest):
        assert p.stat().st_mtime_ns == stat_before[p], (
            "%s was rewritten (mtime changed) on a settled CRLF tree" % p.name
        )
        assert p.read_bytes() == bytes_before[p], (
            "%s was rewritten (bytes changed) on a settled CRLF tree" % p.name
        )


def test_reordered_manifest_produces_no_write(tmp_path):
    """PF-01 / C1 residual: a manifest whose keys are merely in a DIFFERENT ORDER from what the
    writer would generate -- same role->path mapping -- must produce ZERO writes. Intended
    consequence (do not "fix" it): the reordered manifest STAYS reordered on disk; not churning
    is worth more than canonical key order. SK-01's _assert_registry_mirror compares dicts and
    is order-insensitive, so it must still pass."""
    _run_capture("--root", str(tmp_path), "--mode", "create", root=tmp_path)
    manifest = tmp_path / "Virtuoso" / "workspace-layout.json"

    data = json.loads(manifest.read_text(encoding="utf-8"))
    reordered = dict(reversed(list(data.items())))
    reordered["paths"] = dict(reversed(list(data["paths"].items())))
    assert reordered == data  # sanity: semantically identical, order differs
    reordered_text = json.dumps(reordered, indent=2) + "\n"
    assert reordered_text != json.dumps(data, indent=2) + "\n"  # sanity: text actually differs
    manifest.write_text(reordered_text, encoding="utf-8")

    stat_before = manifest.stat().st_mtime_ns
    bytes_before = manifest.read_bytes()

    rc, out = _run_capture("--root", str(tmp_path), "--mode", "create", root=tmp_path)
    assert rc == 0, out

    assert manifest.stat().st_mtime_ns == stat_before, (
        "reordered manifest was rewritten (mtime changed) though semantically identical"
    )
    assert manifest.read_bytes() == bytes_before, (
        "reordered manifest was rewritten (bytes changed) though semantically identical"
    )

    # SK-01's mirror invariant must still hold despite the on-disk key reordering.
    vp._assert_registry_mirror(str(tmp_path))


def test_detect_line_ending_edge_cases(tmp_path):
    """PF-01: lock in _detect_line_ending's edge-case contract directly.

    SR-1 review (Plato, 2026-07-19) found these behaviours correct but covered only
    indirectly, via pure-LF/pure-CRLF fixtures -- so a future refactor could silently flip
    the tie-break or break mixed-ending detection with the suite still green. On a
    persistence surface that is not good enough: the whole point of PF-01 is that this
    function decides how users' governance files get rewritten.
    """
    cases = [
        (b"", None, "empty file: nothing to infer"),
        (b"no newline at all", None, "single line, no terminator"),
        (b"a\nb\nc\n", "\n", "pure LF"),
        (b"a\r\nb\r\nc\r\n", "\r\n", "pure CRLF"),
        (b"a\r\nb\n", "\n", "exact tie resolves to LF (documented, arbitrary)"),
        (b"a\r\nb\r\nc\n", "\r\n", "mixed, CRLF majority"),
        (b"a\nb\nc\r\n", "\n", "mixed, LF majority"),
        (b"a\rb\rc\r", None, "CR-only (classic Mac): invisible to the vote, falls back"),
    ]
    for i, (body, expected, why) in enumerate(cases):
        p = tmp_path / ("case_%d.txt" % i)
        p.write_bytes(body)
        assert vp._detect_line_ending(str(p)) == expected, (
            "%s -- %r should detect %r" % (why, body, expected)
        )

    missing = tmp_path / "does_not_exist.txt"
    assert vp._detect_line_ending(str(missing)) is None, "nonexistent file must not raise"
