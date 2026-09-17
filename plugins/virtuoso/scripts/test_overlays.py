"""Project overlays: the registry role, mirror-path lookup, the CLI verb, the
SessionStart line, and the CI enforcement that keeps the clause in every shipped
skill and agent.

Four layers, one per way the old whole-file fork failed:

* the **role** says where a project's overlays live, and says it read-only;
* the **module** finds them case-exactly and audits what it finds;
* the **clause** tells every skill and agent to read its own overlay, and CI finds
  the skills and agents by scanning the folders, so a new one cannot ship without it;
* the **status line** always states a result, so no output can never be mistaken
  for an all-clear.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT, snapshot_tree
from tools.governance import overlays as overlays_mod, registry as registry_mod, schema
from tools.governance import result as result_mod

ROOT = Path(PLUGIN_ROOT)
PREFLIGHT = str(ROOT / "scripts" / "virtuoso_preflight.py")
REGISTRY_CLI = str(ROOT / "scripts" / "virtuoso_registry.py")
VALIDATE = str(ROOT / "scripts" / "validate.py")

SKILL_NAMES = sorted(d.name for d in (ROOT / "skills").iterdir() if d.is_dir())
AGENT_FILES = sorted(p.name for p in (ROOT / "agents").glob("*.md")
                     if p.name != "AGENT_MEMORY_GUIDE.md")


def run(script, *args):
    return subprocess.run([sys.executable, script, *args], capture_output=True,
                          text=True, env=dict(os.environ))


def load_validate():
    """validate.py as a module, so a check can be aimed at a fixture tree."""
    spec = importlib.util.spec_from_file_location("virtuoso_validate", VALIDATE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_against(module, root, function_name):
    """Run one validator check against ``root``. Returns ``(oks, fails)``."""
    module.ROOT = str(root)
    module.oks.clear()
    module.fails.clear()
    getattr(module, function_name)()
    return list(module.oks), list(module.fails)


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


def flat(text: str) -> str:
    """Collapse whitespace. A clause is prose and will be rewrapped; a test that
    breaks on a line break is testing the wrapping, not what the clause says."""
    return " ".join(text.split())


HAVE_GIT = shutil.which("git") is not None


# --- fixtures ------------------------------------------------------------------


@pytest.fixture
def registered(project):
    """A created workspace with an `overlays` role registered but no directory yet."""
    run(PREFLIGHT, "--root", str(project), "--mode", "create", "--authorize")
    manifest = project / "Virtuoso" / "workspace-layout.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["roles"]["overlays"] = dict(schema.default_role("overlays"), path="Virtuoso/overlays")
    manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return project


@pytest.fixture
def with_overlays(registered):
    """Four overlays: one that applies, one spelled with the wrong case, one that
    mirrors nothing, and one outside the mirrorable subtrees."""
    base = registered / "Virtuoso" / "overlays"
    for relative, body in (
        ("skills/epic/SKILL.md", "always name the ticket\n"),
        ("skills/EPIC/SKILL.md", "wrong case\n"),
        ("skills/no-such-skill/SKILL.md", "mirrors nothing\n"),
        ("notes/scratch.md", "not addressable\n"),
    ):
        target = base.joinpath(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    (base / "agents").mkdir(parents=True, exist_ok=True)
    (base / "agents" / AGENT_FILES[0]).write_text("agent addition\n", encoding="utf-8")
    return registered


@pytest.fixture
def fake_plugin(tmp_path):
    """A minimal plugin tree — two skills, two agents — for aiming a CI check at."""
    root = tmp_path / "plugin"
    for name in ("alpha", "beta"):
        folder = root / "skills" / name
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text(
            "---\nname: %s\n---\n\n%s\n\n# %s\n" % (name, overlays_mod.OVERLAY_CLAUSE, name),
            encoding="utf-8")
    (root / "agents").mkdir(parents=True)
    for name in ("Alpha", "Beta"):
        (root / "agents" / ("%s.md" % name)).write_text(
            "---\nname: %s\nmemory: project\n---\n\n%s\n\nMemory location: "
            "`<project-root>/.claude/agent-memory/%s/`\n"
            % (name, overlays_mod.OVERLAY_CLAUSE, name.lower()), encoding="utf-8")
    return root


# =============================================================================
# Layer 1 — the registry role
# =============================================================================


def test_overlays_is_a_declared_role_with_defaults():
    assert "overlays" in schema.DEFAULT_ROLES
    meta = schema.default_role("overlays")
    assert meta["provider"] == "directory"
    assert meta["authority"] == "reference"


def test_the_overlays_role_is_declared_read_only():
    assert schema.default_role("overlays")["mutability"] == "read-only"


def test_the_overlays_role_names_no_writers():
    assert schema.default_role("overlays")["allowedWriters"] == []


def test_overlays_is_absent_from_the_create_role_order():
    # A project that never asked for overlays must not be handed an empty folder.
    assert "overlays" not in schema.CREATE_ROLE_ORDER


def test_create_lays_down_no_overlays_directory(project):
    run(PREFLIGHT, "--root", str(project), "--mode", "create", "--authorize")
    assert not (project / "Virtuoso" / "overlays").exists()
    assert "overlays" not in json.loads(
        (project / "Virtuoso" / "workspace-layout.json").read_text(encoding="utf-8"))["roles"]


@pytest.mark.parametrize("actor", ["roadmap-review", "pointer-closeout", "next-pointer", "*"])
def test_no_ceremony_may_write_the_overlays_role(registered, actor):
    # The read-only guard already in the plugin is what enforces this; the role
    # earns that protection by being registered read-only, not by new code.
    reg = registry_mod.load(str(registered))
    assert reg.writable("overlays", actor) is False


def test_a_read_only_role_refuses_a_wildcard_writer_too():
    spec = schema.RoleSpec.from_manifest(
        "overlays", dict(schema.default_role("overlays"), path="x", allowedWriters=["*"]))
    assert spec.writable_by("anyone") is False


def test_an_overlays_path_escaping_the_project_root_is_an_error(registered):
    manifest = registered / "Virtuoso" / "workspace-layout.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["roles"]["overlays"]["path"] = "../elsewhere"
    manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")
    reg = registry_mod.load(str(registered))
    assert any(f.code == "unsafe-path" and f.role == "overlays" for f in reg.findings)


def test_repair_preserves_a_registered_overlays_role(registered):
    # The role is outside CREATE_ROLE_ORDER, which is how repair orders known roles.
    # Being unknown to that ordering must mean "kept as a project role", not "dropped".
    completed = run(PREFLIGHT, "--root", str(registered), "--mode", "repair", "--apply")
    assert completed.returncode == 0
    role = json.loads((registered / "Virtuoso" / "workspace-layout.json")
                      .read_text(encoding="utf-8"))["roles"]["overlays"]
    assert role["mutability"] == "read-only"
    assert role["path"] == "Virtuoso/overlays"


def test_repair_never_introduces_an_overlays_role(project):
    run(PREFLIGHT, "--root", str(project), "--mode", "create", "--authorize")
    run(PREFLIGHT, "--root", str(project), "--mode", "repair", "--apply")
    data = json.loads((project / "Virtuoso" / "workspace-layout.json").read_text(encoding="utf-8"))
    assert "overlays" not in data["roles"]
    assert not (project / "Virtuoso" / "overlays").exists()


def test_the_overlays_role_round_trips_through_the_manifest(registered):
    reg = registry_mod.load(str(registered))
    emitted = reg.to_manifest()["roles"]["overlays"]
    assert emitted["mutability"] == "read-only"
    assert emitted["path"] == "Virtuoso/overlays"


# =============================================================================
# Layer 2 — case-exact mirror lookup
# =============================================================================


def test_case_exact_join_resolves_an_exactly_spelled_path(tmp_path):
    (tmp_path / "skills" / "epic").mkdir(parents=True)
    (tmp_path / "skills" / "epic" / "SKILL.md").write_text("x", encoding="utf-8")
    resolved = overlays_mod.case_exact_join(str(tmp_path), "skills/epic/SKILL.md")
    assert os.path.isfile(resolved)


def test_case_exact_join_refuses_a_wrongly_cased_leaf(tmp_path):
    (tmp_path / "skills" / "epic").mkdir(parents=True)
    (tmp_path / "skills" / "epic" / "SKILL.md").write_text("x", encoding="utf-8")
    # os.path.exists answers yes to this on Windows and on a default macOS volume.
    assert overlays_mod.case_exact_join(str(tmp_path), "skills/epic/skill.md") == ""


def test_case_exact_join_refuses_a_wrongly_cased_directory(tmp_path):
    (tmp_path / "skills" / "epic").mkdir(parents=True)
    (tmp_path / "skills" / "epic" / "SKILL.md").write_text("x", encoding="utf-8")
    assert overlays_mod.case_exact_join(str(tmp_path), "Skills/epic/SKILL.md") == ""


def test_case_exact_join_returns_empty_for_an_absent_path(tmp_path):
    assert overlays_mod.case_exact_join(str(tmp_path), "skills/ghost/SKILL.md") == ""


@pytest.mark.parametrize("bad", ["", "   ", "..", "../outside.md", "skills/../../escape.md",
                                 "./skills/epic/SKILL.md"])
def test_case_exact_join_refuses_traversal_and_empty(tmp_path, bad):
    assert overlays_mod.case_exact_join(str(tmp_path), bad) == ""


def test_case_exact_join_refuses_an_absolute_path(tmp_path):
    target = tmp_path / "file.md"
    target.write_text("x", encoding="utf-8")
    assert overlays_mod.case_exact_join(str(tmp_path), str(target)) == ""


def test_case_exact_join_returns_empty_when_the_root_is_missing(tmp_path):
    assert overlays_mod.case_exact_join(str(tmp_path / "nope"), "a/b.md") == ""


def test_mirror_path_normalizes_separators_and_edges():
    assert overlays_mod.mirror_path("skills\\epic\\SKILL.md") == "skills/epic/SKILL.md"
    assert overlays_mod.mirror_path("skills/epic/SKILL.md/") == "skills/epic/SKILL.md"
    assert overlays_mod.mirror_path("  agents/Plato.md  ") == "agents/Plato.md"


@pytest.mark.parametrize("bad", ["", "  ", "..", "a/../b", "./a", None, 5,
                                 "/skills/epic/SKILL.md"])
def test_mirror_path_rejects_unusable_keys(bad):
    # An absolute key is refused here for the same reason case_exact_join refuses
    # one: the two must agree, or a path one accepts the other silently drops.
    assert overlays_mod.mirror_path(bad) == ""


def test_in_mirror_root_accepts_every_shipped_subtree():
    assert overlays_mod.in_mirror_root("skills/epic/SKILL.md")
    assert overlays_mod.in_mirror_root("agents/Plato.md")
    assert overlays_mod.in_mirror_root("references/git-policy.md")
    assert not overlays_mod.in_mirror_root("notes/scratch.md")


def test_is_overlayable_excludes_the_registry_contract():
    # Structurally in a mirror root, and still not overlayable: overlaying the file
    # that defines what an overlay may do would let a project rewrite its own limits.
    assert overlays_mod.in_mirror_root("references/registry-contract.md")
    assert not overlays_mod.is_overlayable("references/registry-contract.md")


@pytest.mark.parametrize("mirror", ["skills/epic/SKILL.md", "agents/Plato.md",
                                    "references/readiness-rubric.md",
                                    "references/git-policy.md",
                                    "references/actors-and-interaction.md",
                                    "references/WORKFLOW_REFERENCE.md"])
def test_every_other_shipped_reference_is_overlayable(mirror):
    assert overlays_mod.is_overlayable(mirror)


def test_the_exclusion_list_names_only_shipped_files():
    for mirror in overlays_mod.NON_OVERLAYABLE:
        assert (ROOT / mirror).is_file(), "%s is excluded but not shipped" % mirror


def test_discover_ignores_dot_entries_and_caches(tmp_path):
    (tmp_path / "skills" / "epic").mkdir(parents=True)
    (tmp_path / "skills" / "epic" / "SKILL.md").write_text("x", encoding="utf-8")
    (tmp_path / "skills" / "epic" / ".DS_Store").write_text("x", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "junk.pyc").write_text("x", encoding="utf-8")
    (tmp_path / ".hidden").mkdir()
    (tmp_path / ".hidden" / "x.md").write_text("x", encoding="utf-8")
    assert overlays_mod.discover(str(tmp_path)) == ["skills/epic/SKILL.md"]


def test_discover_on_a_missing_root_is_empty(tmp_path):
    assert overlays_mod.discover(str(tmp_path / "nope")) == []


# =============================================================================
# Resolution and audit
# =============================================================================


def test_find_returns_none_when_no_overlays_role_is_registered(project):
    run(PREFLIGHT, "--root", str(project), "--mode", "create", "--authorize")
    reg = registry_mod.load(str(project))
    assert overlays_mod.find(reg, PLUGIN_ROOT, "skills/epic/SKILL.md") is None


def test_find_returns_none_when_the_directory_does_not_exist(registered):
    reg = registry_mod.load(str(registered))
    assert overlays_mod.find(reg, PLUGIN_ROOT, "skills/epic/SKILL.md") is None


def test_find_resolves_a_skill_overlay(with_overlays):
    reg = registry_mod.load(str(with_overlays))
    overlay = overlays_mod.find(reg, PLUGIN_ROOT, "skills/epic/SKILL.md")
    assert overlay is not None and overlay.present
    assert Path(overlay.path).read_text(encoding="utf-8") == "always name the ticket\n"
    assert overlay.mirrors_shipped_file


def test_find_resolves_an_agent_overlay(with_overlays):
    reg = registry_mod.load(str(with_overlays))
    overlay = overlays_mod.find(reg, PLUGIN_ROOT, "agents/%s" % AGENT_FILES[0])
    assert overlay is not None and overlay.mirrors_shipped_file


def test_find_refuses_a_wrongly_cased_request(with_overlays):
    reg = registry_mod.load(str(with_overlays))
    assert overlays_mod.find(reg, PLUGIN_ROOT, "skills/epic/skill.md") is None


def test_find_returns_none_for_a_shipped_file_with_no_overlay(with_overlays):
    reg = registry_mod.load(str(with_overlays))
    assert overlays_mod.find(reg, PLUGIN_ROOT, "skills/git-handoff/SKILL.md") is None


def test_audit_of_an_unregistered_project_reports_nothing_registered(project):
    run(PREFLIGHT, "--root", str(project), "--mode", "create", "--authorize")
    status = overlays_mod.audit(registry_mod.load(str(project)), PLUGIN_ROOT)
    assert status.registered is False
    assert status.overlays == [] and status.findings == []


def test_audit_reports_a_registered_but_absent_directory_as_information(registered):
    status = overlays_mod.audit(registry_mod.load(str(registered)), PLUGIN_ROOT)
    assert status.registered and not status.root_present
    assert [f.code for f in status.findings] == ["overlays-absent"]
    assert status.findings[0].severity == "info"


def test_audit_never_produces_an_error_severity_finding(with_overlays):
    # An overlay problem is the project's to fix; turning a working registry into
    # one that "needs repair" would promise a repair plan that cannot exist.
    status = overlays_mod.audit(registry_mod.load(str(with_overlays)), PLUGIN_ROOT)
    assert status.findings
    assert not [f for f in status.findings if f.severity == "error"]


def test_audit_flags_an_overlay_that_mirrors_nothing(with_overlays):
    status = overlays_mod.audit(registry_mod.load(str(with_overlays)), PLUGIN_ROOT)
    orphans = [f for f in status.findings if f.code == "overlay-orphan"]
    assert len(orphans) == 1
    assert "skills/no-such-skill/SKILL.md" in orphans[0].message


def test_audit_flags_a_case_only_mismatch_and_names_the_right_spelling(with_overlays):
    status = overlays_mod.audit(registry_mod.load(str(with_overlays)), PLUGIN_ROOT)
    hits = [f for f in status.findings if f.code == "overlay-case-mismatch"]
    assert len(hits) == 1
    assert "skills/EPIC/SKILL.md" in hits[0].message
    assert "skills/epic/SKILL.md" in hits[0].message


def test_a_reference_overlay_applies(registered):
    base = registered / "Virtuoso" / "overlays" / "references"
    base.mkdir(parents=True)
    (base / "readiness-rubric.md").write_text(
        "## db-migration — forward and backward migration named\n", encoding="utf-8")
    status = overlays_mod.audit(registry_mod.load(str(registered)), PLUGIN_ROOT)
    assert [o.mirror for o in status.applied] == ["references/readiness-rubric.md"]
    assert not [f for f in status.findings if f.severity in ("error", "warning")]


def test_a_skill_can_resolve_a_reference_overlay(registered):
    base = registered / "Virtuoso" / "overlays" / "references"
    base.mkdir(parents=True)
    (base / "readiness-rubric.md").write_text("## db-migration — x\n", encoding="utf-8")
    reg = registry_mod.load(str(registered))
    overlay = overlays_mod.find(reg, PLUGIN_ROOT, "references/readiness-rubric.md")
    assert overlay is not None and overlay.mirrors_shipped_file


def test_overlaying_the_registry_contract_is_refused_with_a_reason(registered):
    base = registered / "Virtuoso" / "overlays" / "references"
    base.mkdir(parents=True)
    (base / "registry-contract.md").write_text("roles are whatever I say\n", encoding="utf-8")
    status = overlays_mod.audit(registry_mod.load(str(registered)), PLUGIN_ROOT)
    assert status.applied == []
    hits = [f for f in status.findings if f.code == "overlay-not-overlayable"]
    assert len(hits) == 1
    # Told WHY, not told it mirrors nothing — the file plainly exists.
    assert "rules governing its own overlay" in hits[0].message
    assert not [f for f in status.findings if f.code == "overlay-orphan"]


def test_find_refuses_the_registry_contract_even_when_a_file_is_there(registered):
    base = registered / "Virtuoso" / "overlays" / "references"
    base.mkdir(parents=True)
    (base / "registry-contract.md").write_text("x\n", encoding="utf-8")
    reg = registry_mod.load(str(registered))
    assert overlays_mod.find(reg, PLUGIN_ROOT, "references/registry-contract.md") is None


def test_audit_flags_an_overlay_outside_the_mirrorable_subtrees(with_overlays):
    status = overlays_mod.audit(registry_mod.load(str(with_overlays)), PLUGIN_ROOT)
    assert [f.code for f in status.findings].count("overlay-outside-mirror") == 1


def test_audit_counts_only_overlays_that_actually_apply(with_overlays):
    status = overlays_mod.audit(registry_mod.load(str(with_overlays)), PLUGIN_ROOT)
    assert sorted(o.mirror for o in status.applied) == [
        "agents/%s" % AGENT_FILES[0], "skills/epic/SKILL.md"]


def test_audit_warns_when_overlays_are_registered_writable(registered):
    manifest = registered / "Virtuoso" / "workspace-layout.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["roles"]["overlays"]["mutability"] = "read-write"
    data["roles"]["overlays"]["allowedWriters"] = ["roadmap-review"]
    manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")
    codes = [f.code for f in overlays_mod.audit(
        registry_mod.load(str(registered)), PLUGIN_ROOT).findings]
    assert "overlays-writable" in codes and "overlays-has-writers" in codes


def test_audit_warns_when_overlays_are_registered_as_an_external_identifier(registered):
    manifest = registered / "Virtuoso" / "workspace-layout.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["roles"]["overlays"] = {"external": "connector:store/42", "provider": "connector",
                                 "authority": "reference", "mutability": "read-only"}
    manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")
    status = overlays_mod.audit(registry_mod.load(str(registered)), PLUGIN_ROOT)
    assert [f.code for f in status.findings] == ["overlays-external"]
    assert status.applied == []


def test_audit_creates_nothing(registered):
    before = snapshot_tree(str(registered))
    overlays_mod.audit(registry_mod.load(str(registered)), PLUGIN_ROOT)
    assert snapshot_tree(str(registered)) == before
    assert not (registered / "Virtuoso" / "overlays").exists()


def test_the_safety_floor_is_published_and_non_empty():
    assert overlays_mod.SAFETY_FLOOR
    assert "git-safety" in overlays_mod.SAFETY_FLOOR
    assert "write-permission" in overlays_mod.SAFETY_FLOOR


def test_the_safety_floor_is_carried_in_the_audit_payload(with_overlays):
    payload = overlays_mod.audit(registry_mod.load(str(with_overlays)), PLUGIN_ROOT).as_dict()
    assert payload["safetyFloor"] == list(overlays_mod.SAFETY_FLOOR)


# =============================================================================
# The status line
# =============================================================================


def test_an_unregistered_project_says_so_rather_than_saying_nothing():
    assert overlays_mod.OverlayStatus().line() == "overlays: not registered"


def test_a_default_result_reports_the_honest_line():
    outcome = result_mod.Result(status=result_mod.READY, mode="check", root=".")
    assert outcome.overlay_line() == "overlays: not registered"


def test_the_status_line_is_never_empty(registered, with_overlays):
    for root in (registered, with_overlays):
        status = overlays_mod.audit(registry_mod.load(str(root)), PLUGIN_ROOT)
        assert status.line().startswith("overlays: ") and len(status.line()) > len("overlays: ")


def test_the_status_line_distinguishes_absent_from_empty(registered):
    absent = overlays_mod.audit(registry_mod.load(str(registered)), PLUGIN_ROOT).line()
    (registered / "Virtuoso" / "overlays").mkdir(parents=True)
    empty = overlays_mod.audit(registry_mod.load(str(registered)), PLUGIN_ROOT).line()
    assert "registered but absent" in absent
    assert "none present" in empty
    assert absent != empty


def test_the_status_line_counts_applied_overlays_and_findings(with_overlays):
    line = overlays_mod.audit(registry_mod.load(str(with_overlays)), PLUGIN_ROOT).line()
    assert line.startswith("overlays: 2 applied")
    assert "3 finding(s)" in line


def test_preflight_prints_the_overlay_line_on_an_unregistered_project(project):
    completed = run(PREFLIGHT, "--root", str(project), "--mode", "check")
    assert "overlays: not registered" in completed.stdout


@pytest.mark.parametrize("mode", ["check", "detect", "adopt", "repair"])
def test_every_mode_prints_an_overlay_line(with_overlays, mode):
    completed = run(PREFLIGHT, "--root", str(with_overlays), "--mode", mode)
    assert "\noverlays: " in "\n" + completed.stdout


def test_the_overlay_line_survives_quiet(with_overlays):
    completed = run(PREFLIGHT, "--root", str(with_overlays), "--mode", "check", "--quiet")
    assert "overlays: 2 applied" in completed.stdout


def test_a_failed_run_still_reports_an_overlay_line(project):
    completed = run(PREFLIGHT, "--root", str(project), "--mode", "create")   # no --authorize
    assert "virtuoso-status: failed" in completed.stdout
    assert "overlays: " in completed.stdout


def test_the_two_line_contract_is_unchanged():
    # Callers parsing the published two-line contract keep working; the overlay
    # line is printed beside it, not spliced into it.
    outcome = result_mod.Result(status=result_mod.READY, mode="check", root=".")
    assert outcome.contract_lines() == ["virtuoso-status: ready", "writes: 0"]


def test_the_json_result_carries_the_overlay_detail(with_overlays):
    completed = run(PREFLIGHT, "--root", str(with_overlays), "--mode", "check", "--json")
    payload = json.loads(completed.stdout.split("\n", 3)[3])
    assert payload["overlays"]["registered"] is True
    assert len(payload["overlays"]["overlays"]) == 5
    assert payload["overlays"]["line"].startswith("overlays: 2 applied")


def test_preflight_reporting_overlays_writes_nothing(with_overlays):
    before = snapshot_tree(str(with_overlays))
    completed = run(PREFLIGHT, "--root", str(with_overlays), "--mode", "check")
    assert "writes: 0" in completed.stdout
    assert snapshot_tree(str(with_overlays)) == before


# =============================================================================
# Layer 3 — the CLI verb
# =============================================================================


def test_the_overlays_verb_answers_on_an_unregistered_project(project):
    completed = run(REGISTRY_CLI, "--root", str(project), "overlays")
    assert completed.returncode == 0
    assert completed.stdout.strip() == "overlays: not registered"


def test_the_overlays_verb_lists_what_applies_and_what_does_not(with_overlays):
    completed = run(REGISTRY_CLI, "--root", str(with_overlays), "overlays")
    assert completed.returncode == 0
    assert "applies    skills/epic/SKILL.md" in completed.stdout
    assert "inert      notes/scratch.md" in completed.stdout
    assert "[warning]" in completed.stdout


def test_the_overlays_verb_prints_the_safety_floor_when_overlays_apply(with_overlays):
    completed = run(REGISTRY_CLI, "--root", str(with_overlays), "overlays")
    assert "may not loosen" in completed.stdout
    for rule in overlays_mod.SAFETY_FLOOR:
        assert rule in completed.stdout


def test_the_overlays_verb_resolves_one_file_to_a_path(with_overlays):
    completed = run(REGISTRY_CLI, "--root", str(with_overlays), "overlays",
                    "--for", "skills/epic/SKILL.md")
    assert completed.returncode == 0
    assert Path(completed.stdout.strip()).read_text(encoding="utf-8") == "always name the ticket\n"


def test_no_overlay_for_a_file_is_an_answer_not_an_error(with_overlays):
    completed = run(REGISTRY_CLI, "--root", str(with_overlays), "overlays",
                    "--for", "skills/git-handoff/SKILL.md")
    assert completed.returncode == 0
    assert "no overlay for skills/git-handoff/SKILL.md" in completed.stdout


def test_an_unusable_mirror_path_is_unanswerable(with_overlays):
    completed = run(REGISTRY_CLI, "--root", str(with_overlays), "overlays",
                    "--for", "../escape.md")
    assert completed.returncode == 3
    assert "not a usable mirror path" in completed.stderr


def test_the_overlays_verb_emits_structured_output(with_overlays):
    completed = run(REGISTRY_CLI, "--root", str(with_overlays), "overlays", "--json")
    payload = json.loads(completed.stdout)
    assert payload["registered"] and payload["rootPresent"]
    assert {o["mirror"] for o in payload["overlays"]} >= {"skills/epic/SKILL.md"}
    assert payload["safetyFloor"] == list(overlays_mod.SAFETY_FLOOR)


def test_the_overlays_verb_for_one_file_emits_structured_output(with_overlays):
    completed = run(REGISTRY_CLI, "--root", str(with_overlays), "overlays", "--json",
                    "--for", "skills/no-such-skill/SKILL.md")
    payload = json.loads(completed.stdout)
    assert payload["mirror"] == "skills/no-such-skill/SKILL.md"
    assert payload["overlay"]["mirrorsShippedFile"] is False


def test_the_overlays_verb_writes_nothing(with_overlays):
    before = snapshot_tree(str(with_overlays))
    run(REGISTRY_CLI, "--root", str(with_overlays), "overlays")
    run(REGISTRY_CLI, "--root", str(with_overlays), "overlays", "--for", "agents/Plato.md")
    assert snapshot_tree(str(with_overlays)) == before


# =============================================================================
# Layer 4 — the clause, and the CI that keeps it there
# =============================================================================


@pytest.mark.parametrize("name", SKILL_NAMES)
def test_every_shipped_skill_carries_the_clause_verbatim(name):
    text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    assert overlays_mod.OVERLAY_CLAUSE in text


@pytest.mark.parametrize("name", AGENT_FILES)
def test_every_shipped_agent_carries_the_clause_verbatim(name):
    text = (ROOT / "agents" / name).read_text(encoding="utf-8")
    assert overlays_mod.OVERLAY_CLAUSE in text


def test_the_clause_names_the_safety_narrowing():
    said = flat(overlays_mod.OVERLAY_CLAUSE)
    assert "may not loosen" in said
    assert "wins on conflict" in said


def test_the_clause_sends_the_reader_to_reference_overlays_too():
    # The v1 clause covered only "this file". A reference is read by a skill that
    # follows a pointer to it, so v1 left reference overlays with nobody to read them.
    said = flat(overlays_mod.OVERLAY_CLAUSE)
    assert "v2" in overlays_mod.CLAUSE_MARKER
    assert "every shipped file you read" in said
    assert "references/<file>.md" in said


def test_the_clause_names_the_one_file_that_cannot_be_overlaid():
    said = flat(overlays_mod.OVERLAY_CLAUSE)
    for mirror in overlays_mod.NON_OVERLAYABLE:
        assert mirror in said, "%s is excluded but the clause never says so" % mirror


def test_the_clause_has_exactly_one_home_in_python():
    # Two copies is how the words drift apart. Only the module may carry them.
    here = Path(__file__).resolve()          # this file names the probe; it is the searcher
    holders = []
    for path in ROOT.rglob("*.py"):
        if "__pycache__" in path.parts or path.resolve() == here:
            continue
        if "never fork or edit a shipped file" in path.read_text(encoding="utf-8"):
            holders.append(path.relative_to(ROOT).as_posix())
    assert holders == ["tools/governance/overlays.py"]


def test_the_ci_check_passes_on_a_complete_tree(fake_plugin):
    module = load_validate()
    oks, fails = check_against(module, fake_plugin, "check_overlay_clause")
    assert fails == []
    assert "2 skill(s) and 2 agent(s)" in oks[0]


def test_the_ci_check_catches_a_skill_that_lost_the_clause(fake_plugin):
    target = fake_plugin / "skills" / "alpha" / "SKILL.md"
    target.write_text(target.read_text(encoding="utf-8").replace(
        overlays_mod.OVERLAY_CLAUSE, ""), encoding="utf-8")
    module = load_validate()
    _oks, fails = check_against(module, fake_plugin, "check_overlay_clause")
    assert len(fails) == 1 and "skills/alpha/SKILL.md" in fails[0]


def test_the_ci_check_catches_an_agent_that_lost_the_clause(fake_plugin):
    target = fake_plugin / "agents" / "Beta.md"
    target.write_text(target.read_text(encoding="utf-8").replace(
        overlays_mod.OVERLAY_CLAUSE, ""), encoding="utf-8")
    module = load_validate()
    _oks, fails = check_against(module, fake_plugin, "check_overlay_clause")
    assert len(fails) == 1 and "agents/Beta.md" in fails[0]


def test_a_brand_new_skill_cannot_ship_without_the_clause(fake_plugin):
    # The roster is read off disk, so the sixteenth skill is checked the moment it
    # exists — nobody has to remember to add it to a list.
    folder = fake_plugin / "skills" / "gamma"
    folder.mkdir(parents=True)
    (folder / "SKILL.md").write_text("---\nname: gamma\n---\n\n# gamma\n", encoding="utf-8")
    module = load_validate()
    _oks, fails = check_against(module, fake_plugin, "check_overlay_clause")
    assert len(fails) == 1 and "skills/gamma/SKILL.md" in fails[0]


def test_the_ci_check_catches_a_reworded_clause(fake_plugin):
    target = fake_plugin / "skills" / "beta" / "SKILL.md"
    assert "may not loosen" in target.read_text(encoding="utf-8")   # probe is contiguous
    target.write_text(target.read_text(encoding="utf-8").replace(
        "may not loosen", "may freely loosen"), encoding="utf-8")
    module = load_validate()
    _oks, fails = check_against(module, fake_plugin, "check_overlay_clause")
    assert len(fails) == 1 and "drifted" in fails[0]


# =============================================================================
# The agent-memory audit
# =============================================================================


def test_the_memory_audit_passes_on_a_consistent_tree(fake_plugin):
    module = load_validate()
    oks, fails = check_against(module, fake_plugin, "check_agent_memory_names")
    assert fails == []
    assert "git index unavailable" in oks[0]       # the fixture is not a repository


def test_the_memory_audit_catches_a_wrongly_cased_directory(fake_plugin):
    target = fake_plugin / "agents" / "Alpha.md"
    target.write_text(target.read_text(encoding="utf-8").replace(
        "agent-memory/alpha/", "agent-memory/Alpha/"), encoding="utf-8")
    module = load_validate()
    _oks, fails = check_against(module, fake_plugin, "check_agent_memory_names")
    assert len(fails) == 1 and "should be 'alpha'" in fails[0]


def test_the_memory_audit_catches_a_directory_named_for_another_agent(fake_plugin):
    target = fake_plugin / "agents" / "Alpha.md"
    target.write_text(target.read_text(encoding="utf-8").replace(
        "agent-memory/alpha/", "agent-memory/beta/"), encoding="utf-8")
    module = load_validate()
    _oks, fails = check_against(module, fake_plugin, "check_agent_memory_names")
    assert len(fails) == 1 and "agents/Alpha.md" in fails[0]


def test_the_memory_audit_catches_memory_declared_with_nowhere_to_put_it(fake_plugin):
    target = fake_plugin / "agents" / "Beta.md"
    target.write_text(
        "---\nname: Beta\nmemory: project\n---\n\n%s\n\n# Beta\n" % overlays_mod.OVERLAY_CLAUSE,
        encoding="utf-8")
    module = load_validate()
    _oks, fails = check_against(module, fake_plugin, "check_agent_memory_names")
    assert len(fails) == 1 and "documents no memory location" in fails[0]


def test_the_memory_audit_catches_a_name_that_disagrees_with_its_filename(fake_plugin):
    target = fake_plugin / "agents" / "Beta.md"
    target.write_text(target.read_text(encoding="utf-8").replace(
        "name: Beta", "name: Betta"), encoding="utf-8")
    module = load_validate()
    _oks, fails = check_against(module, fake_plugin, "check_agent_memory_names")
    assert len(fails) == 1 and "!= filename" in fails[0]


@pytest.mark.skipif(not HAVE_GIT, reason="git is not installed")
def test_the_memory_audit_consults_gits_index_when_there_is_one(fake_plugin):
    assert git("init", cwd=fake_plugin).returncode == 0
    assert git("add", "agents", cwd=fake_plugin).returncode == 0
    module = load_validate()
    oks, fails = check_against(module, fake_plugin, "check_agent_memory_names")
    assert fails == []
    assert "disk and git index agree" in oks[0]


@pytest.mark.skipif(not HAVE_GIT, reason="git is not installed")
def test_the_memory_audit_catches_a_case_only_rename_the_filesystem_hides(fake_plugin):
    # A rename git's index never saw. On a case-insensitive filesystem every
    # `os.path.exists` still answers yes; the index is what tells the truth.
    git("init", cwd=fake_plugin)
    git("add", "agents", cwd=fake_plugin)
    (fake_plugin / "agents" / "Alpha.md").rename(fake_plugin / "agents" / "alpha.md")
    module = load_validate()
    _oks, fails = check_against(module, fake_plugin, "check_agent_memory_names")
    assert len(fails) == 1
    assert "not in git's index" in fails[0] and "not on disk under that exact name" in fails[0]


@pytest.mark.skipif(not HAVE_GIT, reason="git is not installed")
def test_the_memory_audit_catches_an_agent_that_was_never_added(fake_plugin):
    git("init", cwd=fake_plugin)
    git("add", "agents/Alpha.md", cwd=fake_plugin)
    module = load_validate()
    _oks, fails = check_against(module, fake_plugin, "check_agent_memory_names")
    assert len(fails) == 1 and "Beta.md is on disk but not in git's index" in fails[0]


def test_every_shipped_agent_that_declares_memory_documents_where_it_lives():
    for name in AGENT_FILES:
        text = (ROOT / "agents" / name).read_text(encoding="utf-8")
        if "\nmemory:" in text:
            assert "agent-memory/%s/" % name[:-3].lower() in text, name


# =============================================================================
# Install surfaces
# =============================================================================


def test_every_install_manifest_advertises_the_same_version():
    versions = {
        ".claude-plugin/plugin.json":
            json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"],
        ".codex-plugin/plugin.json":
            json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"],
        "marketplace.json":
            json.loads((ROOT.parent.parent / ".claude-plugin" / "marketplace.json")
                       .read_text(encoding="utf-8"))["plugins"][0]["version"],
    }
    assert len(set(versions.values())) == 1, versions


def test_the_release_bumper_tracks_every_install_manifest():
    tracked = {f["path"] for f in
               json.loads((ROOT / ".version-bump.json").read_text(encoding="utf-8"))["files"]}
    assert ".claude-plugin/plugin.json" in tracked
    assert ".codex-plugin/plugin.json" in tracked
    assert "../../.claude-plugin/marketplace.json" in tracked


def test_the_version_check_reports_all_manifests_in_sync():
    completed = run(str(ROOT / "scripts" / "bump_version.py"), "--check")
    assert completed.returncode == 0
    assert "All declared files in sync" in completed.stdout
    assert ".codex-plugin/plugin.json" in completed.stdout


def test_the_alternate_host_manifest_points_at_a_hook_file_that_exists():
    manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    target = ROOT / manifest["hooks"].lstrip("./")
    assert target.is_file(), manifest["hooks"]


def test_the_alternate_host_manifest_serves_every_shipped_skill():
    manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    skills_dir = ROOT / manifest["skills"].lstrip("./")
    found = sorted(p.parent.name for p in skills_dir.glob("*/SKILL.md"))
    assert found == SKILL_NAMES
    assert len(found) == 15


@pytest.mark.skipif(not HAVE_GIT, reason="git is not installed")
def test_the_alternate_host_manifest_is_shipped_not_ignored():
    completed = git("check-ignore", "-q", ".codex-plugin/plugin.json", cwd=ROOT)
    assert completed.returncode != 0, "the alternate-host manifest is gitignored"


def test_every_shipped_hook_file_runs_a_read_only_session_start():
    for path in sorted((ROOT / "hooks").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        commands = [h["command"] for entry in data["hooks"]["SessionStart"]
                    for h in entry["hooks"]]
        assert commands, path.name
        for command in commands:
            assert "--mode check" in command or "--mode detect" in command, path.name
            assert "--mode create" not in command, path.name


# =============================================================================
# The whole validator, on the real tree
# =============================================================================


def test_the_shipped_tree_passes_validation():
    completed = run(VALIDATE)
    assert completed.returncode == 0, completed.stdout
    assert "All checks passed." in completed.stdout
