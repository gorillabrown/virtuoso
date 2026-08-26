import importlib.util, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "sprint_guards.py")
_spec = importlib.util.spec_from_file_location("sprint_guards", SCRIPT)
sg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sg)


def _run(*args):
    proc = subprocess.run([sys.executable, SCRIPT, *args],
                          capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def _seed_registry(root, close_outs="closeouts", in_readme=False):
    """Lay down a minimal registry. `in_readme=True` puts closeOuts ONLY in the
    readme machine block, exercising the manifest-missing fallback."""
    (root / close_outs).mkdir(parents=True, exist_ok=True)
    (root / "Virtuoso").mkdir(exist_ok=True)
    paths = {"roadmap": "Roadmap.md"}
    if not in_readme:
        paths["closeOuts"] = close_outs
    (root / "Virtuoso" / "workspace-layout.json").write_text(
        json.dumps({"layout": "plugin-only", "paths": paths}, indent=2),
        encoding="utf-8")
    machine = "roadmap: Roadmap.md"
    if in_readme:
        machine += "\ncloseOuts: %s" % close_outs
    (root / "Virtuoso.Governance.Readme.md").write_text(
        "# Registry\n\n<!-- virtuoso-governance-registry\n%s\n-->\n" % machine,
        encoding="utf-8")


def test_resolve_registry_path_prefers_the_manifest(tmp_path):
    _seed_registry(tmp_path)
    assert sg.resolve_registry_path(str(tmp_path), "closeOuts") == \
        os.path.join(str(tmp_path), "closeouts")


def test_resolve_registry_path_falls_back_to_the_readme_machine_block(tmp_path):
    _seed_registry(tmp_path, in_readme=True)
    assert sg.resolve_registry_path(str(tmp_path), "closeOuts") == \
        os.path.join(str(tmp_path), "closeouts")


def test_resolve_registry_path_returns_none_for_an_unregistered_key(tmp_path):
    _seed_registry(tmp_path)
    assert sg.resolve_registry_path(str(tmp_path), "nosuchrole") is None


def test_staging_sweep_is_clean_when_no_memos_are_resident(tmp_path):
    _seed_registry(tmp_path)
    rc, out = _run("staging-sweep", "--root", str(tmp_path))
    assert rc == 0, out
    assert "staging-sweep: clean" in out


def test_staging_sweep_reports_each_resident_memo(tmp_path):
    _seed_registry(tmp_path)
    for name in ("Memo.SK-1.GovernanceStaging.2026-08-01.md",
                 "Memo.SK-2.GovernanceStaging.2026-08-02.md"):
        (tmp_path / "closeouts" / name).write_text("staged\n", encoding="utf-8")
    rc, out = _run("staging-sweep", "--root", str(tmp_path))
    assert rc == 1, out
    assert "staging-sweep: 2 resident memo(s)" in out
    assert "Memo.SK-1.GovernanceStaging.2026-08-01.md" in out
    assert "Memo.SK-2.GovernanceStaging.2026-08-02.md" in out


def test_staging_sweep_ignores_a_processed_subdirectory(tmp_path):
    """A memo already moved aside is closed, not open. Only the top level counts."""
    _seed_registry(tmp_path)
    done = tmp_path / "closeouts" / ".processed"
    done.mkdir()
    (done / "Memo.SK-3.GovernanceStaging.2026-08-03.md").write_text("x", encoding="utf-8")
    rc, out = _run("staging-sweep", "--root", str(tmp_path))
    assert rc == 0, out


def test_staging_sweep_exits_2_when_closeouts_is_unregistered(tmp_path):
    (tmp_path / "Virtuoso").mkdir()
    (tmp_path / "Virtuoso" / "workspace-layout.json").write_text(
        json.dumps({"paths": {"roadmap": "Roadmap.md"}}), encoding="utf-8")
    rc, out = _run("staging-sweep", "--root", str(tmp_path))
    assert rc == 2, out
    assert "closeOuts" in out
