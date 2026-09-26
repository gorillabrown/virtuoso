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

import codecs
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
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
AGENT_FILES = sorted(p.name for p in (ROOT / "agents").glob("*.md"))


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


def _probe_case_sensitivity() -> bool:
    """Whether the temp filesystem distinguishes ``probe`` from ``PROBE``.

    Measured, never inferred from ``sys.platform``: a case-sensitive volume can
    be mounted on Windows or macOS and a case-insensitive one on Linux, and the
    fixtures below create two files whose names differ only in case. pytest's
    tmp_path lives under the same temp root this probes.
    """
    base = tempfile.mkdtemp()
    try:
        with open(os.path.join(base, "probe"), "w", encoding="utf-8") as handle:
            handle.write("lower")
        return not os.path.exists(os.path.join(base, "PROBE"))
    finally:
        shutil.rmtree(base, ignore_errors=True)


#: True where two names differing only in case are two files.
CASE_SENSITIVE_FS = _probe_case_sensitivity()

#: Overlay files `with_overlays` lays down, and findings the audit then reports.
#: Both are two fewer where the case-only pair collapses into one file.
EXPECTED_OVERLAYS = 5 if CASE_SENSITIVE_FS else 4
EXPECTED_FINDINGS = 3 if CASE_SENSITIVE_FS else 2


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
    """Overlays covering every classification the audit makes.

    One applies, one mirrors nothing, one is outside the mirrorable subtrees, and
    one agent overlay applies. The case-only duplicate is laid down ONLY on a
    case-sensitive filesystem: elsewhere it is the same file as its lowercase
    twin, so writing it would overwrite that file's content and quietly change
    what every test built on this fixture is asserting about.
    """
    base = registered / "Virtuoso" / "overlays"
    files = [
        ("skills/epic/SKILL.md", "always name the ticket\n"),
        ("skills/no-such-skill/SKILL.md", "mirrors nothing\n"),
        ("notes/scratch.md", "not addressable\n"),
    ]
    if CASE_SENSITIVE_FS:
        files.append(("skills/EPIC/SKILL.md", "wrong case\n"))
    for relative, body in files:
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
            "---\nname: %s\ndescription: The %s fixture.\n---\n\n%s\n\n# %s\n"
            % (name, name, overlays_mod.OVERLAY_CLAUSE, name), encoding="utf-8")
    (root / "agents").mkdir(parents=True)
    for name in ("Alpha", "Beta"):
        (root / "agents" / ("%s.md" % name)).write_text(
            "---\nname: %s\ndescription: The %s fixture.\n---\n\n%s\n\n"
            "Memory location: `<project-root>/.claude/agent-memory/%s/`\n"
            % (name, name, overlays_mod.OVERLAY_CLAUSE, name.lower()), encoding="utf-8")
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


@pytest.mark.parametrize("bad", [
    "/skills/epic/SKILL.md",
    "\\skills\\epic\\SKILL.md",
    "C:/skills/epic/SKILL.md",
    "C:\\skills\\epic\\SKILL.md",
])
def test_a_rooted_or_drive_qualified_key_is_refused_everywhere(bad):
    """Refused by both resolvers, on every OS and every interpreter.

    `os.path.isabs` is not a portable test for this: it answers differently per
    platform AND per interpreter, because Python 3.13 stopped treating a lone
    leading slash as absolute on Windows. A key one interpreter accepts and
    another drops is the divergence this module exists to prevent, and CI's
    3.12 cannot see it.
    """
    assert overlays_mod.mirror_path(bad) == ""
    assert overlays_mod.case_exact_join(str(ROOT), bad) == ""


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


@pytest.mark.skipif(not CASE_SENSITIVE_FS,
                    reason="two names differing only in case are one file here, so the "
                           "condition under test cannot be created")
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


def test_case_exactness_itself_is_covered_on_every_filesystem(with_overlays):
    """The audit's case-mismatch FINDING needs a case-sensitive volume to exist.
    The module's case-exactness does not, and is what actually protects a project.

    Skipping the finding test where the condition cannot be built is honest.
    Skipping it and testing nothing in its place would mean the property silently
    lost its coverage on the maintainer's own platform.
    """
    reg = registry_mod.load(str(with_overlays))
    exact = overlays_mod.find(reg, PLUGIN_ROOT, "skills/epic/SKILL.md")
    assert exact is not None and exact.mirrors_shipped_file

    # A wrongly-cased request never stands in for the shipped file. On a
    # case-sensitive volume the uppercase directory exists as its own overlay, so
    # find() may return it — but it must never claim to mirror a shipped file,
    # because the plugin ships no `skills/EPIC/`.
    assert overlays_mod.find(reg, PLUGIN_ROOT, "skills/epic/skill.md") is None
    wrong_case = overlays_mod.find(reg, PLUGIN_ROOT, "skills/EPIC/SKILL.md")
    assert wrong_case is None or not wrong_case.mirrors_shipped_file


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
# Pairings — a declared id must have a prose body
# =============================================================================


def _declare(root, ids):
    manifest = root / "Virtuoso" / "workspace-layout.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data.setdefault("policy", {})["rubric"] = {"version": "1.0", "extensions": list(ids)}
    manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _rubric_overlay(root, text):
    base = root / "Virtuoso" / "overlays" / "references"
    base.mkdir(parents=True, exist_ok=True)
    (base / "readiness-rubric.md").write_text(text, encoding="utf-8")


def _codes(root):
    return [f.code for f in overlays_mod.audit(
        registry_mod.load(str(root)), PLUGIN_ROOT).findings]


def test_the_pairing_table_is_declared_not_scattered():
    assert overlays_mod.PAIRINGS
    pairing = overlays_mod.PAIRINGS[0]
    assert pairing.policy_key == "rubric.extensions"
    assert pairing.mirror == "references/readiness-rubric.md"


@pytest.mark.parametrize("heading,defines", [
    ("## db-migration — forward and backward", True),
    ("### db-migration", True),
    ("#### db-migration (both directions)", True),
    ("##\tdb-migration", True),                     # a tab is a valid heading separator
    ("## DB-Migration — capitalized by a human", True),
    ("## Why we dropped db-migration", False),      # discusses it; does not define it
    ("## db-migration-rollback — a different id", False),
    ("## db-migrations", False),
    ("# db-migration", False),                      # depth 1 is the document title
    ("db-migration", False),                        # not a heading at all
    ("##\ndb-migration", False),                    # a bare ## and then a paragraph
])
def test_what_counts_as_a_body(heading, defines):
    assert bool(overlays_mod.body_heading("db-migration").search(heading)) is defines


def test_a_heading_inside_a_code_fence_is_an_example_not_a_definition(registered):
    """This plugin's own rubric shows `## db-migration` inside a fence.

    A project that copies that example into its overlay is showing what a section
    looks like, not writing one, and must not thereby satisfy the check.
    """
    _declare(registered, ["db-migration"])
    _rubric_overlay(registered,
                    "# additions\n\n```markdown\n## db-migration\nexample\n```\n")
    assert "pairing-body-missing" in _codes(registered)


@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_body_detection_is_identical_under_both_line_endings(registered, newline):
    """Written as explicit bytes, so every platform exercises both endings.

    `Path.write_text` translates newlines, so a test that writes "\n" produces CRLF
    on Windows and LF elsewhere -- each platform then tests only its own ending and
    neither tests the other. The fenced-example case failed exactly this way: `$`
    in multiline mode matches before the "\n" with the "\r" still ahead of it, so
    the closing fence never matched, the block was never blanked, and an example
    defined a check on Windows only.
    """
    _declare(registered, ["db-migration"])
    base = registered / "Virtuoso" / "overlays" / "references"
    base.mkdir(parents=True, exist_ok=True)
    body = ("# additions", "", "```markdown", "## db-migration", "example", "```", "")
    (base / "readiness-rubric.md").write_bytes(newline.join(body).encode("utf-8"))
    assert "pairing-body-missing" in _codes(registered), \
        "a fenced example defined the check under %r line endings" % newline


@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_a_real_section_is_found_under_both_line_endings(registered, newline):
    _declare(registered, ["db-migration"])
    base = registered / "Virtuoso" / "overlays" / "references"
    base.mkdir(parents=True, exist_ok=True)
    body = ("## db-migration", "", "both directions named", "")
    (base / "readiness-rubric.md").write_bytes(newline.join(body).encode("utf-8"))
    assert not [c for c in _codes(registered) if c.startswith("pairing-")]


@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_an_empty_section_is_a_stub_under_both_line_endings(registered, newline):
    _declare(registered, ["db-migration"])
    base = registered / "Virtuoso" / "overlays" / "references"
    base.mkdir(parents=True, exist_ok=True)
    body = ("## db-migration", "", "", "## something else", "", "prose", "")
    (base / "readiness-rubric.md").write_bytes(newline.join(body).encode("utf-8"))
    assert "pairing-body-stub" in _codes(registered)


def test_a_real_section_after_a_fenced_example_still_counts(registered):
    _declare(registered, ["db-migration"])
    _rubric_overlay(registered,
                    "# additions\n\n```markdown\n## db-migration\nexample\n```\n\n"
                    "## db-migration\n\nboth directions named\n")
    assert not [c for c in _codes(registered) if c.startswith("pairing-")]


def test_a_heading_with_nothing_under_it_is_a_stub(registered):
    """Deleting the placeholder is the obvious way to 'fix' the stub warning.

    If an empty section passed, the gate's own remedy would satisfy it by a second
    route -- the same failure pairing-body-stub was added to close.
    """
    _declare(registered, ["db-migration"])
    _rubric_overlay(registered, "## db-migration\n\n\n## something else\n\nprose\n")
    codes = _codes(registered)
    assert "pairing-body-stub" in codes
    assert "pairing-body-missing" not in codes


def test_a_capitalized_heading_defines_the_declared_id(registered):
    """An id is an identifier; a heading is prose a person writes.

    Requiring the prose to match the identifier's case reports the natural way to
    write the section as undefined, which is a false report about correct work.
    """
    _declare(registered, ["deployment"])
    _rubric_overlay(registered, "## Deployment — environment and rollback\n\nrehearsed\n")
    assert not [c for c in _codes(registered) if c.startswith("pairing-")]


def test_a_declared_id_with_a_body_is_clean(registered):
    _declare(registered, ["db-migration"])
    _rubric_overlay(registered, "## db-migration — forward and backward migration\n")
    assert "pairing-body-missing" not in _codes(registered)


def test_a_declared_id_with_no_body_is_reported(registered):
    _declare(registered, ["db-migration"])
    _rubric_overlay(registered, "## house style\n\nsome prose\n")
    status = overlays_mod.audit(registry_mod.load(str(registered)), PLUGIN_ROOT)
    hits = [f for f in status.findings if f.code == "pairing-body-missing"]
    assert len(hits) == 1
    assert "db-migration" in hits[0].message
    assert "references/readiness-rubric.md" in hits[0].message   # names the fix
    assert hits[0].severity == "warning"


def test_a_heading_that_merely_mentions_the_id_is_not_a_body(registered):
    _declare(registered, ["db-migration"])
    _rubric_overlay(registered, "## Why we dropped db-migration as a blocker\n")
    assert "pairing-body-missing" in _codes(registered)


def test_each_undefined_id_is_reported_separately(registered):
    _declare(registered, ["db-migration", "deployment", "accessibility"])
    _rubric_overlay(registered, "## deployment — environment and rollback\n")
    hits = [c for c in _codes(registered) if c == "pairing-body-missing"]
    assert len(hits) == 2


def test_declaring_nothing_reports_nothing(registered):
    _declare(registered, [])
    _rubric_overlay(registered, "")
    assert not [c for c in _codes(registered) if c.startswith("pairing-")]


def test_ids_declared_with_no_overlays_role_are_reported(project):
    run(PREFLIGHT, "--root", str(project), "--mode", "create", "--authorize")
    _declare(project, ["deployment"])
    status = overlays_mod.audit(registry_mod.load(str(project)), PLUGIN_ROOT)
    assert [f.code for f in status.findings] == ["pairing-mirror-unregistered"]
    assert status.findings[0].severity == "info"
    assert "deployment" in status.findings[0].message


def test_a_declared_id_with_the_overlay_file_absent_is_reported(registered):
    _declare(registered, ["deployment"])            # role registered, no directory
    assert "pairing-body-missing" in _codes(registered)


def test_a_malformed_policy_value_is_ignored_not_raised(registered):
    manifest = registered / "Virtuoso" / "workspace-layout.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data.setdefault("policy", {})["rubric"] = {"extensions": "db-migration"}   # not a list
    manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")
    assert not [c for c in _codes(registered) if c.startswith("pairing-")]


def test_a_utf16_overlay_is_read_rather_than_called_missing(registered):
    """Windows PowerShell 5.1's `>` writes UTF-16 with a BOM.

    That is the documented way to save a scaffold, so a reader that rejects a BOM
    turns the documented workflow into a file the plugin calls absent -- and the
    operator, who wrote a correct heading, is told nothing defines it.
    """
    _declare(registered, ["db-migration"])
    base = registered / "Virtuoso" / "overlays" / "references"
    base.mkdir(parents=True)
    (base / "readiness-rubric.md").write_bytes(
        "## db-migration\n\nboth directions named\n".encode("utf-16"))
    codes = _codes(registered)
    assert "pairing-body-missing" not in codes
    assert "overlay-unreadable" not in codes


def test_a_utf8_bom_overlay_is_read(registered):
    _declare(registered, ["db-migration"])
    base = registered / "Virtuoso" / "overlays" / "references"
    base.mkdir(parents=True)
    (base / "readiness-rubric.md").write_bytes(
        codecs.BOM_UTF8 + "## db-migration\n\nboth directions named\n".encode("utf-8"))
    assert "pairing-body-missing" not in _codes(registered)


def test_an_undecodable_overlay_says_so_instead_of_saying_missing(registered):
    """pwsh 7 redirects a legacy code page when the console is not UTF-8.

    Those bytes carry no BOM and are not valid UTF-8, so nothing can read them.
    The operator must be told the file is unreadable -- "nothing defines this id"
    sends them to rewrite a section that is already there.
    """
    _declare(registered, ["db-migration"])
    base = registered / "Virtuoso" / "overlays" / "references"
    base.mkdir(parents=True)
    (base / "readiness-rubric.md").write_bytes(
        "## db-migration \u2014 both directions\n".encode("cp1252"))
    codes = _codes(registered)
    assert "overlay-unreadable" in codes
    assert "pairing-body-missing" not in codes


def test_the_scaffold_redirect_round_trips_through_a_byte_stream(registered):
    """`--scaffold --for X > X` must produce a file this plugin can read back.

    The redirect is the whole write, so stdout here is a file the audit will
    later parse. Capturing bytes rather than text is the point: a console
    encoding must not be able to change what lands on disk.
    """
    _declare(registered, ["db-migration"])
    completed = subprocess.run(
        [sys.executable, REGISTRY_CLI, "--root", str(registered), "overlays",
         "--scaffold", "--for", "references/readiness-rubric.md"],
        capture_output=True, env=dict(os.environ))
    assert completed.returncode == 0, completed.stderr
    target = registered / "Virtuoso" / "overlays" / "references" / "readiness-rubric.md"
    target.parent.mkdir(parents=True)
    target.write_bytes(completed.stdout)
    assert "pairing-body-stub" in _codes(registered)


def test_pairing_findings_are_never_errors(registered):
    _declare(registered, ["db-migration"])
    status = overlays_mod.audit(registry_mod.load(str(registered)), PLUGIN_ROOT)
    assert not [f for f in status.findings if f.severity == "error"]


def test_a_missing_body_shows_in_the_session_start_line(registered):
    _declare(registered, ["db-migration"])
    _rubric_overlay(registered, "## unrelated\n")
    completed = run(PREFLIGHT, "--root", str(registered), "--mode", "check", "--quiet")
    assert "virtuoso-status: ready" in completed.stdout
    assert "finding(s)" in completed.stdout


def test_the_pairing_check_creates_nothing(registered):
    _declare(registered, ["db-migration"])
    before = snapshot_tree(str(registered))
    overlays_mod.audit(registry_mod.load(str(registered)), PLUGIN_ROOT)
    assert snapshot_tree(str(registered)) == before


# --- the plugin-side half ------------------------------------------------------


def test_every_shipped_pairing_resolves():
    module = load_validate()
    oks, fails = check_against(module, ROOT, "check_overlay_pairings")
    assert fails == []
    assert "pairing(s) resolve" in oks[0]


def test_ci_rejects_a_pairing_naming_an_unshipped_file(monkeypatch):
    module = load_validate()
    monkeypatch.setattr(module.overlays_mod, "PAIRINGS", (
        overlays_mod.Pairing("rubric.extensions", "references/no-such-file.md", "check"),))
    _oks, fails = check_against(module, ROOT, "check_overlay_pairings")
    assert len(fails) == 1 and "does not ship" in fails[0]


def test_ci_rejects_a_pairing_naming_an_excluded_file(monkeypatch):
    module = load_validate()
    monkeypatch.setattr(module.overlays_mod, "PAIRINGS", (
        overlays_mod.Pairing("rubric.extensions", "references/registry-contract.md", "check"),))
    _oks, fails = check_against(module, ROOT, "check_overlay_pairings")
    assert len(fails) == 1 and "overlays exclude" in fails[0]


def test_ci_rejects_a_pairing_naming_an_undocumented_policy_key(monkeypatch):
    module = load_validate()
    monkeypatch.setattr(module.overlays_mod, "PAIRINGS", (
        overlays_mod.Pairing("rubric.notAKey", "references/readiness-rubric.md", "check"),))
    _oks, fails = check_against(module, ROOT, "check_overlay_pairings")
    assert len(fails) == 1 and "no documented default" in fails[0]


def test_the_body_convention_is_documented_where_projects_read_about_extensions():
    text = (ROOT / "references" / "readiness-rubric.md").read_text(encoding="utf-8")
    assert "starts with" in text
    assert "<overlays>/references/readiness-rubric.md" in text
    assert "pairing-body-missing" in text


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


def test_an_undefined_id_is_named_when_no_overlays_role_exists(project):
    """The state a project is in the moment it declares its first extension.

    Printing only "not registered" here is the loop's second step saying nothing
    at the exact point the operator needs to be told what to do.
    """
    run(PREFLIGHT, "--root", str(project), "--mode", "create", "--authorize")
    _declare(project, ["deployment"])
    line = overlays_mod.audit(registry_mod.load(str(project)), PLUGIN_ROOT).line()
    assert "not registered" in line
    assert "deployment" in line


def test_an_undefined_id_is_named_when_the_directory_is_absent(registered):
    _declare(registered, ["deployment"])
    line = overlays_mod.audit(registry_mod.load(str(registered)), PLUGIN_ROOT).line()
    assert "registered but absent" in line
    assert "deployment" in line


def test_every_undefined_id_is_named(registered):
    _declare(registered, ["deployment", "db-migration"])
    line = overlays_mod.audit(registry_mod.load(str(registered)), PLUGIN_ROOT).line()
    assert "db-migration" in line and "deployment" in line


def test_a_clean_project_says_nothing_extra(registered):
    """The suffix must be absent, not empty-but-present: a line that always ends
    in punctuation trains the reader to stop looking at the end of it."""
    _declare(registered, ["db-migration"])
    _rubric_overlay(registered, "## db-migration\n\nboth directions named\n")
    line = overlays_mod.audit(registry_mod.load(str(registered)), PLUGIN_ROOT).line()
    assert "undefined" not in line and "finding(s)" not in line


def test_the_session_start_line_names_the_undefined_id(registered):
    _declare(registered, ["deployment"])
    completed = run(PREFLIGHT, "--root", str(registered), "--mode", "check", "--quiet")
    assert "virtuoso-status: ready" in completed.stdout
    assert "deployment" in completed.stdout


def test_the_status_line_counts_applied_overlays_and_findings(with_overlays):
    line = overlays_mod.audit(registry_mod.load(str(with_overlays)), PLUGIN_ROOT).line()
    assert line.startswith("overlays: 2 applied")
    assert "%d finding(s)" % EXPECTED_FINDINGS in line


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
    # The JSON follows the machine lines. Read from its first line, never from a
    # fixed line count: the set of machine lines grows (deadlines: joined in 1.8.1).
    lines = completed.stdout.splitlines()
    payload = json.loads("\n".join(lines[next(i for i, line in enumerate(lines)
                                              if line.startswith("{")):]))
    assert payload["overlays"]["registered"] is True
    assert len(payload["overlays"]["overlays"]) == EXPECTED_OVERLAYS
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


@pytest.mark.parametrize("location", [
    "Memory location: `<project-root>/.claude/agent-memory/beta/`\n",   # correctly documented
    "",                                                                 # or not at all
])
def test_the_memory_audit_refuses_a_memory_field(fake_plugin, location):
    """A host honours `memory:` on a project's copy of an agent and names the folder
    from `name:`, a second spelling beside the brief's lowercase one."""
    target = fake_plugin / "agents" / "Beta.md"
    target.write_text("---\nname: Beta\nmemory: project\n---\n\n%s\n\n# Beta\n%s"
                      % (overlays_mod.OVERLAY_CLAUSE, location), encoding="utf-8")
    module = load_validate()
    _oks, fails = check_against(module, fake_plugin, "check_agent_memory_names")
    assert len(fails) == 1 and "declares a memory: field" in fails[0]
    assert "Beta/" in fails[0] and "beta/" in fails[0]


def test_a_memory_word_in_the_body_is_not_the_field(fake_plugin):
    target = fake_plugin / "agents" / "Beta.md"
    target.write_text(target.read_text(encoding="utf-8") + "\nmemory: kept in the brief\n",
                      encoding="utf-8")
    module = load_validate()
    _oks, fails = check_against(module, fake_plugin, "check_agent_memory_names")
    assert fails == []


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


#: The shipped agents that keep a memory, written out rather than found by a search:
#: an agent that loses its location fails here.
MEMORY_AGENTS = ("Archimedes", "Hesiod", "Hippocrates", "Pythagoras", "Socrates")


def test_the_agents_with_memory_document_its_lowercase_location_and_no_field():
    for name in MEMORY_AGENTS:
        text = (ROOT / "agents" / ("%s.md" % name)).read_text(encoding="utf-8")
        assert ("Memory location: `<project-root>/.claude/agent-memory/%s/`" % name.lower()
                in text), name
    for name in AGENT_FILES:
        head = (ROOT / "agents" / name).read_text(encoding="utf-8").split("\n---\n", 1)[0]
        assert "\nmemory:" not in head, name


def test_the_memory_guide_states_the_spelling_the_host_behaviour_and_the_repair():
    guide = (ROOT / "references" / "agent-memory-guide.md").read_text(encoding="utf-8")
    assert "`.claude/agent-memory/socrates/`" in guide and "**lowercase**" in guide
    assert "<name-of-agent>" in guide and "memory:" in guide       # the host behaviour
    assert "## Repairing a memory split by case" in guide
    assert "git ls-files .claude/agent-memory" in guide


def test_the_memory_guide_ships_in_references_and_agents_cite_it_there():
    assert (ROOT / "references" / "agent-memory-guide.md").is_file()
    assert not (ROOT / "agents" / "AGENT_MEMORY_GUIDE.md").exists()
    # Written out, not found by a search: an agent that loses its pointer fails here.
    for name in ("Archimedes", "Hesiod", "Hippocrates", "Plato", "Pythagoras", "Socrates"):
        text = (ROOT / "agents" / ("%s.md" % name)).read_text(encoding="utf-8")
        assert "references/agent-memory-guide.md" in text, name
        assert "AGENT_MEMORY_GUIDE" not in text, name


# =============================================================================
# The frontmatter hosts load
# =============================================================================


def _write_skill(plugin, name, frontmatter):
    folder = plugin / "skills" / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "SKILL.md").write_text(
        "---\n%s---\n\n%s\n" % (frontmatter, overlays_mod.OVERLAY_CLAUSE), encoding="utf-8")


def test_the_host_frontmatter_check_passes_on_a_complete_tree(fake_plugin):
    # The skill bodies carry the overlay clause's placeholders. Only frontmatter is held
    # to the hosts' rules, so a tag in a body is legal.
    assert "<skill>" in (fake_plugin / "skills" / "alpha" / "SKILL.md").read_text(
        encoding="utf-8")
    module = load_validate()
    oks, fails = check_against(module, fake_plugin, "check_host_frontmatter")
    assert fails == []
    assert "2 skill(s) and 2 agent(s)" in oks[0]


def test_the_host_frontmatter_check_catches_a_guide_among_the_agents(fake_plugin):
    # Hosts load every .md under agents/ as an agent; the memory guide was counted as one.
    (fake_plugin / "agents" / "GUIDE.md").write_text("# A guide\n", encoding="utf-8")
    module = load_validate()
    _oks, fails = check_against(module, fake_plugin, "check_host_frontmatter")
    assert len(fails) == 1
    assert "agents/GUIDE.md: no frontmatter" in fails[0]
    assert "Alpha" not in fails[0] and "Beta" not in fails[0]


@pytest.mark.parametrize("description, bracket", [
    ('Use when the user says "start at <time>".', "<"),
    # A validator reads the raw string: a code span does not hide a tag. An upload was
    # refused over a backtick-wrapped `<ViewTransition>`.
    ("Wraps route changes in `<ViewTransition>`.", "<"),
    ("Use when the queue depth > 10.", ">"),
])
def test_the_host_frontmatter_check_refuses_any_angle_bracket_in_a_description(
        fake_plugin, description, bracket):
    _write_skill(fake_plugin, "alpha", "name: alpha\ndescription: %s\n" % description)
    module = load_validate()
    _oks, fails = check_against(module, fake_plugin, "check_host_frontmatter")
    assert len(fails) == 1
    assert "skills/alpha/SKILL.md: description contains %r" % bracket in fails[0]


def test_the_host_frontmatter_check_catches_a_description_over_the_limit(fake_plugin):
    # Folded across two lines, as the shipped skills write it: 500 + 1 + 523 is exactly
    # the documented limit, and one character more is over it.
    module = load_validate()
    _write_skill(fake_plugin, "alpha", "name: alpha\ndescription: >\n  %s\n  %s\n"
                 % ("a" * 500, "b" * 523))
    assert check_against(module, fake_plugin, "check_host_frontmatter")[1] == []
    _write_skill(fake_plugin, "alpha", "name: alpha\ndescription: >\n  %s\n  %s\n"
                 % ("a" * 500, "b" * 524))
    _oks, fails = check_against(module, fake_plugin, "check_host_frontmatter")
    assert len(fails) == 1 and "description is 1025 characters" in fails[0]


def test_the_host_frontmatter_check_catches_a_name_hosts_refuse(fake_plugin):
    module = load_validate()
    _write_skill(fake_plugin, "claude-helper", "name: claude-helper\ndescription: Helps.\n")
    _oks, fails = check_against(module, fake_plugin, "check_host_frontmatter")
    assert len(fails) == 1 and "skills/claude-helper/SKILL.md" in fails[0]
    assert "reserved word 'claude'" in fails[0]
    shutil.rmtree(fake_plugin / "skills" / "claude-helper")
    for name in ("Helper", "alpha--beta", "-alpha", "alpha-", "a" * 65):
        _write_skill(fake_plugin, name, "name: %s\ndescription: Helps.\n" % name)
        _oks, fails = check_against(module, fake_plugin, "check_host_frontmatter")
        assert len(fails) == 1 and "name %r is not 1-64 lowercase" % name in fails[0], name
        shutil.rmtree(fake_plugin / "skills" / name)
    for name in ("a", "3rd-party-audit", "a" * 64):
        _write_skill(fake_plugin, name, "name: %s\ndescription: Helps.\n" % name)
        assert check_against(module, fake_plugin, "check_host_frontmatter")[1] == [], name
        shutil.rmtree(fake_plugin / "skills" / name)


def test_the_frontmatter_reader_agrees_with_a_yaml_parser():
    yaml = pytest.importorskip("yaml")
    module = load_validate()
    files = [ROOT / "skills" / name / "SKILL.md" for name in SKILL_NAMES]
    files += [ROOT / "agents" / name for name in AGENT_FILES]
    for path in files:
        text = path.read_text(encoding="utf-8")
        header = yaml.safe_load(re.match(r"---\s*\n(.*?)\n---\s*\n", text, re.S).group(1))
        fields = module.frontmatter_fields(text)
        for key in ("name", "description"):
            assert fields[key] == str(header[key]).strip(), (path.name, key)


# =============================================================================
# Scaffolding — emitted, never written
# =============================================================================


def test_scaffold_returns_text_for_an_overlayable_file(registered):
    reg = registry_mod.load(str(registered))
    content = overlays_mod.scaffold(reg, "agents/%s" % AGENT_FILES[0])
    assert content.startswith("<!-- Virtuoso project overlay for agents/")
    assert "may not loosen" in content


def test_scaffold_refuses_a_file_that_cannot_be_overlaid(registered):
    reg = registry_mod.load(str(registered))
    assert overlays_mod.scaffold(reg, "references/registry-contract.md") == ""
    assert overlays_mod.scaffold(reg, "notes/scratch.md") == ""
    assert overlays_mod.scaffold(reg, "../escape.md") == ""


def test_scaffold_seeds_a_section_per_undefined_id(registered):
    reg = registry_mod.load(str(registered))
    content = overlays_mod.scaffold(reg, "references/readiness-rubric.md",
                                    missing_ids=["db-migration", "deployment"])
    assert "## db-migration" in content and "## deployment" in content
    # The seeded heading must actually satisfy the check it is seeding.
    assert overlays_mod.body_heading("db-migration").search(content)


def test_scaffold_plan_matches_what_the_audit_is_complaining_about(registered):
    _declare(registered, ["db-migration", "deployment"])
    _rubric_overlay(registered, "## deployment — environment and rollback\n")
    reg = registry_mod.load(str(registered))
    status = overlays_mod.audit(reg, PLUGIN_ROOT)
    plan = overlays_mod.scaffold_plan(reg, status)
    assert [mirror for mirror, _ in plan] == ["references/readiness-rubric.md"]
    content = plan[0][1]
    assert "## db-migration" in content          # the one the audit reports
    assert "## deployment" not in content        # already defined; not re-scaffolded


def test_a_saved_scaffold_does_not_silence_the_warning_that_produced_it(registered):
    """The remedy must not satisfy the gate. A stub heading reads as a definition to
    any 'does a section exist' check, so scaffolding would clear the warning with
    nothing written."""
    _declare(registered, ["db-migration"])
    reg = registry_mod.load(str(registered))
    content = overlays_mod.scaffold(reg, "references/readiness-rubric.md",
                                    missing_ids=["db-migration"])
    _rubric_overlay(registered, content)
    codes = _codes(registered)
    assert "pairing-body-stub" in codes
    assert "pairing-body-missing" not in codes      # the section does exist


def test_replacing_the_placeholder_clears_the_stub_finding(registered):
    _declare(registered, ["db-migration"])
    _rubric_overlay(registered,
                    "## db-migration\n\nboth migrations named; data-loss analysis stated\n")
    assert not [c for c in _codes(registered) if c.startswith("pairing-")]


def test_a_stub_for_one_id_does_not_mask_a_real_body_for_another(registered):
    _declare(registered, ["db-migration", "deployment"])
    _rubric_overlay(registered,
                    "## db-migration\n\n%s\n\n## deployment\n\nrollback command stated\n"
                    % overlays_mod.SCAFFOLD_PLACEHOLDER)
    hits = [f for f in overlays_mod.audit(registry_mod.load(str(registered)), PLUGIN_ROOT).findings
            if f.code == "pairing-body-stub"]
    assert len(hits) == 1 and "db-migration" in hits[0].message


def test_scaffold_plan_is_empty_when_everything_is_defined(registered):
    _declare(registered, ["db-migration"])
    _rubric_overlay(registered, "## db-migration — both directions\n")
    reg = registry_mod.load(str(registered))
    assert overlays_mod.scaffold_plan(reg, overlays_mod.audit(reg, PLUGIN_ROOT)) == []


def test_the_scaffold_verb_writes_nothing(registered):
    """The load-bearing claim: the overlays role is read-only with no writers, and
    scaffolding must not become the exception that qualifies that sentence."""
    _declare(registered, ["db-migration"])
    before = snapshot_tree(str(registered))
    for args in (["overlays", "--scaffold"],
                 ["overlays", "--scaffold", "--for", "agents/%s" % AGENT_FILES[0]],
                 ["overlays", "--scaffold", "--for", "references/readiness-rubric.md"]):
        completed = run(REGISTRY_CLI, "--root", str(registered), *args)
        assert completed.returncode == 0, completed.stderr
    assert snapshot_tree(str(registered)) == before
    assert not (registered / "Virtuoso" / "overlays").exists()


def test_no_ceremony_can_write_the_overlays_role_even_now(registered):
    reg = registry_mod.load(str(registered))
    for actor in ("project-profile", "roadmap-review", "*", ""):
        assert reg.writable("overlays", actor) is False


def test_the_single_file_scaffold_is_exactly_the_files_content(registered, tmp_path):
    """`... --scaffold --for <path> > <file>` must produce a usable overlay with no
    header lines to strip — the operator's redirect is the whole write."""
    completed = run(REGISTRY_CLI, "--root", str(registered), "overlays", "--scaffold",
                    "--for", "references/readiness-rubric.md")
    assert completed.returncode == 0
    assert not completed.stdout.startswith("# ====")
    target = registered / "Virtuoso" / "overlays" / "references" / "readiness-rubric.md"
    target.parent.mkdir(parents=True)
    target.write_text(completed.stdout, encoding="utf-8")
    status = overlays_mod.audit(registry_mod.load(str(registered)), PLUGIN_ROOT)
    assert [o.mirror for o in status.applied] == ["references/readiness-rubric.md"]


def test_the_single_file_scaffold_seeds_declared_ids_too(registered):
    # --for and the full plan must not disagree about the same path.
    _declare(registered, ["db-migration"])
    completed = run(REGISTRY_CLI, "--root", str(registered), "overlays", "--scaffold",
                    "--for", "references/readiness-rubric.md")
    assert completed.returncode == 0
    assert "## db-migration" in completed.stdout
    assert overlays_mod.body_heading("db-migration").search(completed.stdout)


def test_the_multi_file_scaffold_names_every_path(registered):
    _declare(registered, ["db-migration"])
    completed = run(REGISTRY_CLI, "--root", str(registered), "overlays", "--scaffold")
    assert "# ==== " in completed.stdout
    assert "references/readiness-rubric.md" in completed.stdout


def test_scaffolding_an_unscaffoldable_file_is_unanswerable(registered):
    completed = run(REGISTRY_CLI, "--root", str(registered), "overlays", "--scaffold",
                    "--for", "references/registry-contract.md")
    assert completed.returncode == 3
    assert "may carry an overlay" in completed.stderr


def test_nothing_to_scaffold_says_so(registered):
    completed = run(REGISTRY_CLI, "--root", str(registered), "overlays", "--scaffold")
    assert completed.returncode == 0
    assert "nothing to scaffold" in completed.stdout


# =============================================================================
# The project-profile ceremony
# =============================================================================


PROFILE = ROOT / "skills" / "project-profile" / "SKILL.md"


def test_project_profile_ships():
    assert PROFILE.is_file()
    assert "project-profile" in SKILL_NAMES


def test_project_profile_carries_the_shared_contract_and_the_clause():
    text = PROFILE.read_text(encoding="utf-8")
    assert "<!-- virtuoso-shared-contract v2 -->" in text
    assert overlays_mod.OVERLAY_CLAUSE in text


def test_project_profiles_contract_block_is_identical_to_every_other_skill():
    def block(path):
        text = path.read_text(encoding="utf-8")
        start = text.index("<!-- virtuoso-shared-contract v2 -->")
        return text[start:text.index("\n", text.index("- **Effort levels** —"))]
    reference = block(ROOT / "skills" / "virtuoso-init" / "SKILL.md")
    assert block(PROFILE) == reference


def test_project_profile_states_that_it_never_writes_an_overlay():
    said = flat(PROFILE.read_text(encoding="utf-8"))
    assert "never writes a project's overlays" in said
    assert "Never writes an overlay" in said


def test_project_profile_routes_an_unregistered_project_to_init():
    said = flat(PROFILE.read_text(encoding="utf-8"))
    assert "virtuoso-init" in said
    assert "repair-needed" in said


def test_every_catalogue_question_names_a_real_policy_key():
    from tools.governance import policy as policy_mod
    text = PROFILE.read_text(encoding="utf-8")
    declared = set(re.findall(r"`policy\.([A-Za-z][A-Za-z0-9_.]*)`", text))
    assert declared, "the catalogue declares no policy keys at all"
    defaults = policy_mod.load({})
    for key in sorted(declared):
        assert defaults.get(key, None) is not None, \
            "the catalogue names policy.%s, which has no documented default" % key


def test_the_catalogue_covers_every_pairing():
    text = PROFILE.read_text(encoding="utf-8")
    for pairing in overlays_mod.PAIRINGS:
        assert "`policy.%s`" % pairing.policy_key in text, \
            "%s is checkable but the interview never asks about it" % pairing.policy_key


def test_project_profile_documents_the_declaration_and_body_rule():
    said = flat(PROFILE.read_text(encoding="utf-8"))
    assert "Declaration" in said and "Body" in said
    assert "make it one" in said           # the corollary


# =============================================================================
# policy-set — the declaration half, written
# =============================================================================


def _manifest(root):
    return json.loads((root / "Virtuoso" / "workspace-layout.json")
                      .read_text(encoding="utf-8"))


def test_assign_sets_a_dotted_key_without_mutating_its_input():
    from tools.governance import policy as policy_mod
    original = {"rubric": {"version": "1.0"}}
    updated = policy_mod.assign(original, "rubric.extensions", ["db-migration"])
    assert updated["rubric"]["extensions"] == ["db-migration"]
    assert updated["rubric"]["version"] == "1.0"       # siblings survive
    assert "extensions" not in original["rubric"]      # pure


def test_assign_creates_intermediate_levels():
    from tools.governance import policy as policy_mod
    assert policy_mod.assign({}, "a.b.c", 1) == {"a": {"b": {"c": 1}}}


def test_is_documented_distinguishes_a_real_key_from_a_storage_slot():
    from tools.governance import policy as policy_mod
    assert policy_mod.is_documented("rubric.extensions")
    assert not policy_mod.is_documented("rubric.notAKey")


def test_policy_set_previews_without_writing(registered):
    before = snapshot_tree(str(registered))
    completed = run(REGISTRY_CLI, "--root", str(registered), "--actor", "project-profile",
                    "policy-set", "rubric.extensions", "--value-json", '["db-migration"]')
    assert completed.returncode == 0, completed.stderr
    assert "rubric.extensions" in completed.stdout
    assert snapshot_tree(str(registered)) == before


def test_policy_set_writes_the_value_and_backs_the_manifest_up(registered):
    from tools.governance import backup as backup_mod
    completed = run(REGISTRY_CLI, "--root", str(registered), "--actor", "project-profile",
                    "policy-set", "rubric.extensions", "--value-json", '["db-migration"]',
                    "--apply")
    assert completed.returncode == 0, completed.stderr
    assert _manifest(registered)["policy"]["rubric"]["extensions"] == ["db-migration"]
    backups = registered.joinpath(*backup_mod.BACKUP_DIRNAME.split(os.sep))
    assert backups.is_dir() and any(backups.iterdir())


def test_policy_set_feeds_the_pairing_check(registered):
    """The half this writes must be the half the audit reads.

    This is the whole loop in one assertion: the ceremony writes the declaration,
    and session start immediately reports that its body is missing.
    """
    completed = run(REGISTRY_CLI, "--root", str(registered), "--actor", "project-profile",
                    "policy-set", "rubric.extensions", "--value-json", '["db-migration"]',
                    "--apply")
    assert completed.returncode == 0, completed.stderr
    assert "pairing-body-missing" in _codes(registered)


def _roles_meaning(root):
    """Every role's meaning, as the registry reads it back."""
    reg = registry_mod.load(str(root))
    return {name: (spec.target, spec.provider, spec.authority, spec.mutability,
                   sorted(spec.allowed_writers), spec.validation,
                   spec.classification, spec.origin)
            for name, spec in reg.roles.items()}


def test_policy_set_preserves_unrelated_manifest_content(registered):
    """Roles and schema survive a policy write, byte value for byte value.

    Raw-JSON equality, not meaning-for-meaning. It once had to be the weaker form,
    because the serializer dropped an explicitly-empty `allowedWriters` -- which
    the `overlays` role in this fixture carries, straight from the documented
    shape. A project's own key is now preserved, so the strict assertion is the
    true one and the weaker one would hide a regression.
    """
    before_meaning = _roles_meaning(registered)
    before_raw = _manifest(registered)
    run(REGISTRY_CLI, "--root", str(registered), "--actor", "project-profile",
        "policy-set", "rubric.extensions", "--value-json", '["db-migration"]', "--apply")
    after_raw = _manifest(registered)
    assert _roles_meaning(registered) == before_meaning
    assert after_raw["roles"] == before_raw["roles"]
    assert after_raw["schemaVersion"] == before_raw["schemaVersion"]
    assert after_raw["layout"] == before_raw["layout"]
    assert after_raw["documentationRoot"] == before_raw["documentationRoot"]


@pytest.mark.parametrize("writer_path", ["repair", "policy-set"])
def test_an_explicit_empty_allowed_writers_survives_a_manifest_write(registered, writer_path):
    """A project that writes "nobody may write this" keeps saying it.

    The registry contract documents the `overlays` role with `"allowedWriters": []`
    and a project copying that shape had it stripped by the next manifest write --
    the file stopped matching the documentation it came from. textio's opening
    paragraph promises the governance layer does not churn user files; dropping a
    key someone deliberately wrote is that churn, meaning preserved or not.
    """
    assert _manifest(registered)["roles"]["overlays"]["allowedWriters"] == []
    if writer_path == "repair":
        run(PREFLIGHT, "--root", str(registered), "--mode", "repair", "--apply")
    else:
        run(REGISTRY_CLI, "--root", str(registered), "--actor", "project-profile",
            "policy-set", "rubric.extensions", "--value-json", '["x"]', "--apply")
    assert _manifest(registered)["roles"]["overlays"]["allowedWriters"] == []


def test_a_role_that_never_declared_writers_does_not_gain_the_key(registered):
    """Preservation, not invention. The key appears only where it was written."""
    manifest = registered / "Virtuoso" / "workspace-layout.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["roles"]["governance"].pop("allowedWriters", None)
    manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")
    run(PREFLIGHT, "--root", str(registered), "--mode", "repair", "--apply")
    assert "allowedWriters" not in _manifest(registered)["roles"]["governance"]


@pytest.mark.parametrize("entry,writable", [
    ({"path": "x"}, False),
    ({"path": "x", "allowedWriters": []}, False),
    ({"path": "x", "allowedWriters": ["a"]}, True),
])
def test_declaring_the_key_does_not_change_who_may_write(entry, writable):
    """An empty list and an absent key remain the same answer. The distinction is
    about what the file says, never about what a ceremony may do."""
    spec = schema.RoleSpec.from_manifest(
        "r", dict(entry, mutability="read-write", authority="reference"))
    assert spec.writable_by("a") is writable


def test_a_scaffolded_workspace_does_not_gain_an_empty_writers_key(project):
    """`create`'s output bytes are unchanged by the preservation above.

    Preservation is about a project's own file. A fresh scaffold says "no writers"
    by omission, as it does for an empty owner, and the release pipeline compares
    create's bytes across versions -- so a new key here would be a release-gate
    failure bought for nothing.
    """
    run(PREFLIGHT, "--root", str(project), "--mode", "create", "--authorize")
    roles = json.loads((project / "Virtuoso" / "workspace-layout.json")
                       .read_text(encoding="utf-8"))["roles"]
    empty = [name for name, role in roles.items() if role.get("allowedWriters") == []]
    assert empty == [], "create started emitting an empty allowedWriters for %s" % empty


def test_a_policy_write_churns_no_more_than_repair_already_does(project, tmp_path):
    """The new writer must introduce no normalization of its own.

    Two identical workspaces: one written by `repair --apply`, one by `policy-set
    --apply`. Whatever the serializer normalizes, it must normalize the same way
    for both -- a new write path that churned a manifest differently from the
    established one would be a second, quieter definition of "preserved".
    """
    def build(root):
        run(PREFLIGHT, "--root", str(root), "--mode", "create", "--authorize")
        manifest = root / "Virtuoso" / "workspace-layout.json"
        data = json.loads(manifest.read_text(encoding="utf-8"))
        data["roles"]["overlays"] = dict(schema.default_role("overlays"),
                                         path="Virtuoso/overlays")
        manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return manifest

    via_repair = build(project)
    other = tmp_path / "other"
    other.mkdir()
    via_policy = build(other)

    run(PREFLIGHT, "--root", str(project), "--mode", "repair", "--apply")
    run(REGISTRY_CLI, "--root", str(other), "--actor", "project-profile",
        "policy-set", "rubric.extensions", "--value-json", '["db-migration"]', "--apply")

    repaired = json.loads(via_repair.read_text(encoding="utf-8"))
    policied = json.loads(via_policy.read_text(encoding="utf-8"))
    assert policied["roles"] == repaired["roles"]


def test_policy_set_refuses_without_an_actor(registered):
    completed = run(REGISTRY_CLI, "--root", str(registered),
                    "policy-set", "rubric.extensions", "--value-json", "[]", "--apply")
    assert completed.returncode == 3
    assert "actor" in completed.stderr


def test_policy_set_refuses_an_undocumented_key(registered):
    """A key nothing documents is a storage slot: no ceremony reads it, so writing
    it produces configuration that looks live and is inert."""
    before = snapshot_tree(str(registered))
    completed = run(REGISTRY_CLI, "--root", str(registered), "--actor", "project-profile",
                    "policy-set", "rubric.notAKey", "--value-json", '"x"', "--apply")
    assert completed.returncode == 3
    assert "documented" in completed.stderr
    assert snapshot_tree(str(registered)) == before


def test_policy_set_refuses_a_value_that_fails_validation(registered):
    before = snapshot_tree(str(registered))
    completed = run(REGISTRY_CLI, "--root", str(registered), "--actor", "project-profile",
                    "policy-set", "git.policy", "--value-json", '"yolo"', "--apply")
    assert completed.returncode == 3
    assert "not valid" in completed.stderr
    assert snapshot_tree(str(registered)) == before


def test_policy_set_refuses_malformed_json(registered):
    completed = run(REGISTRY_CLI, "--root", str(registered), "--actor", "project-profile",
                    "policy-set", "rubric.extensions", "--value-json", "[not json",
                    "--apply")
    assert completed.returncode == 3
    assert "valid JSON" in completed.stderr


def test_policy_set_never_writes_an_overlay(registered):
    """The role stays read-only with no writers. A ceremony that can write policy
    must not have acquired the ability to write the other half."""
    run(REGISTRY_CLI, "--root", str(registered), "--actor", "project-profile",
        "policy-set", "rubric.extensions", "--value-json", '["db-migration"]', "--apply")
    reg = registry_mod.load(str(registered))
    assert reg.writable("overlays", "project-profile") is False
    assert not (registered / "Virtuoso" / "overlays").exists()


def _backup_dirs(root):
    from tools.governance import backup as backup_mod
    base = root.joinpath(*backup_mod.BACKUP_DIRNAME.split(os.sep))
    return sorted(d for d in base.iterdir() if d.is_dir()) if base.is_dir() else []


def test_two_applies_in_one_second_do_not_share_a_backup(registered):
    """The original must survive two chained writes.

    Backup directories are stamped to the second. Two applies inside one second
    shared a directory, so the second copied the FIRST APPLY'S OUTPUT over the
    pristine original and the state before either write was gone. The skill tells
    a ceremony to set one key per invocation, which makes chaining the normal
    shape rather than an unlucky one; this reproduced in three trials of three.
    """
    manifest = registered / "Virtuoso" / "workspace-layout.json"
    pristine = manifest.read_text(encoding="utf-8")
    for key, value in (("rubric.extensions", '["a"]'),
                       ("roadmap.dispatchBuffer", "3")):
        completed = run(REGISTRY_CLI, "--root", str(registered), "--actor", "project-profile",
                        "policy-set", key, "--value-json", value, "--apply")
        assert completed.returncode == 0, completed.stderr

    dirs = _backup_dirs(registered)
    assert len(dirs) == 2, "two applies produced %d backup set(s)" % len(dirs)
    saved = [copy.read_text(encoding="utf-8")
             for d in dirs for copy in d.rglob("workspace-layout.json")]
    assert pristine in saved, "the state before either write is not recoverable"


def test_a_backup_set_never_reuses_an_existing_directory(project):
    """The guarantee is "this directory is mine", so it is an existence check.

    A finer timestamp would make a collision unlikely rather than impossible, and
    a backup that is merely unlikely to be overwritten is not a backup.
    """
    from tools.governance import backup as backup_mod
    import datetime as dt
    frozen = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    seen = set()
    for _ in range(3):
        opened = backup_mod.open_set(str(project), "policy-set", now=frozen)
        os.makedirs(opened.directory, exist_ok=True)
        assert opened.directory not in seen
        seen.add(opened.directory)


def test_a_backup_records_the_ceremony_that_asked(registered):
    """A label says what happened; the actor says who asked. A restore needs both."""
    run(REGISTRY_CLI, "--root", str(registered), "--actor", "project-profile",
        "policy-set", "rubric.extensions", "--value-json", '["a"]', "--apply")
    manifest = json.loads((_backup_dirs(registered)[0] / "manifest.json")
                          .read_text(encoding="utf-8"))
    assert manifest["label"] == "policy-set"
    assert manifest["actor"] == "project-profile"


@pytest.mark.parametrize("key,value,why", [
    ("rubric.extensions", '"db-migration"', "a string where a list is documented"),
    ("rubric", '"everything"', "a string replacing a whole section"),
    ("roadmap.dispatchBuffer", '"five"', "a string where a number is documented"),
    ("actors", '["planner"]', "a list replacing a mapping"),
    ("roadmap.eagerSpec", "1", "a number where a flag is documented"),
])
def test_a_value_of_the_wrong_shape_is_refused(registered, key, value, why):
    """Stored-and-ignored is the failure this whole architecture is about.

    A string in `rubric.extensions` declared a readiness check that no ceremony
    could read and that session start never mentioned: the project believed it had
    a gate and had an inert string. The documented-KEY check stopped one field
    short of the documented TYPE.
    """
    before = snapshot_tree(str(registered))
    completed = run(REGISTRY_CLI, "--root", str(registered), "--actor", "project-profile",
                    "policy-set", key, "--value-json", value, "--apply")
    assert completed.returncode == 3, why
    assert "documented as" in completed.stderr
    assert snapshot_tree(str(registered)) == before


@pytest.mark.parametrize("value", ['["roadmap-review"]', "null"])
def test_a_documented_key_whose_default_is_none_can_be_set(registered, value):
    """`workRegister.creators` is documented, meaningful, and defaults to None.

    is_documented read the VALUE, so the one key governing who may create work
    items could never be set at all -- a documented setting the writer refused.
    """
    completed = run(REGISTRY_CLI, "--root", str(registered), "--actor", "project-profile",
                    "policy-set", "workRegister.creators", "--value-json", value, "--apply")
    assert completed.returncode == 0, completed.stderr


def test_policy_set_prunes_old_backups_as_repair_does(registered):
    """Retention is policy, and a new writer must not be the one path that ignores it."""
    manifest = registered / "Virtuoso" / "workspace-layout.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data.setdefault("policy", {}).setdefault("sweep", {})["backupRetention"] = 2
    manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")
    for n in range(4):
        run(REGISTRY_CLI, "--root", str(registered), "--actor", "project-profile",
            "policy-set", "roadmap.dispatchBuffer", "--value-json", str(n + 1), "--apply")
    assert len(_backup_dirs(registered)) <= 2


def test_the_body_heading_docstring_keeps_its_escapes():
    """It explains why the pattern uses a tab class instead of a whitespace class.

    Written as a non-raw docstring, the escape for tab became a literal tab
    character and the one for whitespace became an invalid escape -- so the
    explanation of the fix was itself corrupted, and Python 3.12+ warns about it.
    Asserted with chr(92) rather than backslash literals, because a test about
    escaping that is itself hard to escape is a test nobody can read.
    """
    backslash = chr(92)
    text = overlays_mod.body_heading.__doc__
    assert backslash + "t" in text, "the tab escape did not survive as written"
    assert backslash + "s" in text, "the whitespace escape did not survive"
    assert backslash * 2 not in text, "the escapes were doubled instead"
    assert not [c for c in text if ord(c) < 32 and c != chr(10)], \
        "an escape was consumed into a literal control character"


def _catalogue_rows() -> list[str]:
    """The Phase 2 interview table's data rows, header and rule excluded."""
    body = PROFILE.read_text(encoding="utf-8").split("## Phase 2")[1].split("## Phase 3")[0]
    return [line for line in body.splitlines()
            if line.startswith("|") and not line.startswith("|---")
            and not line.startswith("| Ask")]


def test_every_catalogue_row_either_names_a_declaration_or_says_it_has_none():
    """The catalogue's own rule is that each question maps to exactly one
    declaration. One row collects bodies instead, which is legitimate — but it has
    to SAY so, or it quietly contradicts the rule it is printed underneath.
    """
    rows = _catalogue_rows()
    assert rows, "the catalogue has no rows"
    for row in rows:
        assert "`policy." in row or "no declaration" in row, \
            "catalogue row neither names a policy key nor admits it has none: %s" % row


def test_exactly_one_catalogue_row_collects_bodies():
    """If a second row ever stops naming a declaration, that is drift, not design."""
    assert sum(1 for row in _catalogue_rows() if "no declaration" in row) == 1


def test_project_profile_names_the_command_that_writes_policy():
    said = flat(PROFILE.read_text(encoding="utf-8"))
    assert "policy-set" in said


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


def test_the_privacy_policy_link_names_the_policy_this_repository_publishes():
    """The plugin page and the directory listing link a privacy policy. It must be this
    repository's own, and the file must exist to be published; a link to a host's general
    policy, or to a file the release never carries, answers nothing about Virtuoso."""
    codex = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    claude = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert codex["interface"]["privacyPolicyURL"] == claude["repository"] + "/blob/main/PRIVACY.md"
    assert (ROOT.parent.parent / "PRIVACY.md").is_file()


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
    # Compared against the folders on disk, never a literal: a hardcoded count is a
    # second roster that the next skill has to remember to update.
    assert found == SKILL_NAMES
    assert found, "the alternate-host manifest serves no skills at all"


def test_the_alternate_host_manifest_describes_itself_for_the_plugin_page():
    """The host's plugin page is rendered from `interface`, not from `description`.

    Without these keys the page falls back to the bare name and description: no
    tagline, no example prompts, and no information panel. Each key below is one
    row or element of that page, so a missing one is a blank on a published page.
    """
    interface = json.loads(
        (ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))["interface"]
    for key in ("displayName", "shortDescription", "longDescription", "developerName",
                "category", "capabilities", "defaultPrompt", "websiteURL",
                "privacyPolicyURL", "termsOfServiceURL", "brandColor"):
        assert interface.get(key), f"the plugin page has no {key}"
    assert len(interface["shortDescription"]) <= 80, "the tagline is too long to render"
    for key in ("composerIcon", "logo"):
        asset = ROOT / interface[key].lstrip("./")
        assert asset.is_file(), f"{key} points at a file that is not shipped: {interface[key]}"


def test_the_alternate_host_manifest_lists_the_hooks_it_ships():
    """The plugin page lists `interface.capabilities`, a free-text list. The manifest
    ships a session hook, so the page says so, in the words published manifests that
    ship hooks use."""
    manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["hooks"]
    assert "Lifecycle hooks" in manifest["interface"]["capabilities"]


def test_both_hosts_and_the_marketplace_describe_the_plugin_the_same_way():
    """One plugin, three descriptions of it: the Claude manifest, the alternate-host
    manifest, and the marketplace entry that installs it. They drift silently — the
    marketplace kept a "16 skills" description after the manifests moved on — so the
    fields a person reads on either host's plugin page are held equal here."""
    claude = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    codex = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    market = json.loads((ROOT.parent.parent / ".claude-plugin" / "marketplace.json")
                        .read_text(encoding="utf-8"))
    [entry] = [p for p in market["plugins"] if p["name"] == claude["name"]]
    for field in ("name", "version", "description", "author", "homepage", "repository",
                  "license", "keywords"):
        assert claude[field] == codex[field] == entry[field], field
    assert claude["displayName"] == entry["displayName"] == codex["interface"]["displayName"]
    assert entry["category"] == codex["interface"]["category"]
    assert codex["interface"]["developerName"] == claude["author"]["name"]
    assert codex["interface"]["websiteURL"] == claude["homepage"]
    assert entry["tags"], "the marketplace entry carries no tags"


@pytest.mark.skipif(not HAVE_GIT, reason="git is not installed")
def test_the_alternate_host_manifest_is_shipped_not_ignored():
    """Checked with --no-index, i.e. against the ignore PATTERNS themselves.

    Without --no-index, check-ignore skips tracked files entirely, so this test
    passed even under a pattern that ignored the manifest -- it could never have
    caught the regression it is named for.
    """
    completed = git("check-ignore", "--no-index", "-q", ".codex-plugin/plugin.json",
                    cwd=ROOT)
    assert completed.returncode != 0, "the alternate-host manifest is gitignored"


@pytest.mark.skipif(not HAVE_GIT, reason="git is not installed")
def test_the_dev_clones_root_codex_directory_stays_ignored():
    """The June decision holds: a repository-root .codex-plugin/ is local WIP.

    Un-ignoring the plugin's own manifest deleted an unanchored `.codex-plugin/`
    line, which un-ignored the root directory too. A dev clone that had one then
    failed release.py's clean-tree gate -- the release was blocked by a file that
    was never meant to be seen. The anchored pattern keeps the two apart, and the
    test above pins the other half.
    """
    completed = git("check-ignore", "--no-index", "-q", ".codex-plugin/plugin.json",
                    cwd=ROOT.parent.parent)
    assert completed.returncode == 0, "the repository-root .codex-plugin/ is not ignored"


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
