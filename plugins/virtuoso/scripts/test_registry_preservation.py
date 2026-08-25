"""Registry preservation, round-tripping, authority, and migration.

Covers redesign items 88, 89, 90, 91, 101 — plus the safety rules those tests
exist to protect: no silent rewriting, no authority inferred from a name, no
re-pointing a registered-but-absent role.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT, snapshot_tree
from tools.governance import identifiers, readme as readme_mod, registry as registry_mod
from tools.governance import repair as repair_mod, schema, textio, workspace
from tools.governance.errors import RoleNotRegistered, SchemaVersionError

PREFLIGHT = str(Path(PLUGIN_ROOT) / "scripts" / "virtuoso_preflight.py")


def run(root, *args):
    return subprocess.run([sys.executable, PREFLIGHT, "--root", str(root), *args],
                          capture_output=True, text=True, env=dict(os.environ))


def parse(stdout):
    status = writes = None
    for line in stdout.splitlines():
        if line.startswith("virtuoso-status: "):
            status = line.split(": ", 1)[1].strip()
        elif line.startswith("writes: "):
            writes = int(line.split(": ", 1)[1])
    return status, writes


# --- fixtures ----------------------------------------------------------------

CUSTOM_README = """# Our Governance Registry

We keep our own prose up here, and we mean to keep it.

> A block quote with **formatting**, a `code span`, and a — dash.

| Our own table | That the plugin knows nothing about |
|---------------|-------------------------------------|
| row one       | value                                |

<!-- a comment of ours -->

## Registered roles

<!-- virtuoso:begin-generated -->
| Role | Target | Provider | Authority | Mutability | Writers | State |
|------|--------|----------|-----------|------------|---------|-------|
| Roadmap / specification store | `docs/ROADMAP.md` | markdown | live | read-write | roadmap-review | present |

<!-- virtuoso-governance-registry
# Generated view of Virtuoso/workspace-layout.json — the manifest is the authority.
roadmap: docs/ROADMAP.md
-->
<!-- virtuoso:end-generated -->

## Our extension section

Everything down here is ours too. Ordering, labels, and comments must survive.

- a list item
- another one
"""

CUSTOM_MANIFEST = {
    "schemaVersion": 2,
    "pluginCompatibility": ">=1.4.0 <2.0.0",
    "layout": "plugin-only",
    "adopted": True,
    "documentationRoot": "docs",
    "roles": {
        "roadmap": {
            "path": "docs/ROADMAP.md",
            "provider": "markdown",
            "authority": "live",
            "mutability": "read-write",
            "owner": "roadmap-review",
            "allowedWriters": ["roadmap-review"],
            "validation": "markdown",
            "classification": "active",
            "origin": "authored",
            "label": "Roadmap / specification store",
        },
    },
    "x-our-namespace": {"anything": ["we", "like"], "nested": {"deeply": True}},
}


@pytest.fixture
def customized(project):
    (project / "docs").mkdir()
    (project / "docs" / "ROADMAP.md").write_text("# Roadmap\n", encoding="utf-8")
    (project / "Virtuoso").mkdir()
    (project / "Virtuoso" / ".virtuoso").write_text("virtuoso-workspace\n", encoding="utf-8")
    (project / "Virtuoso" / "workspace-layout.json").write_text(
        json.dumps(CUSTOM_MANIFEST, indent=2) + "\n", encoding="utf-8")
    (project / "Virtuoso.Governance.Readme.md").write_text(CUSTOM_README, encoding="utf-8")
    return project


# --- item 88: byte-for-byte preservation --------------------------------------


@pytest.mark.parametrize("mode", ["check", "detect", "adopt"])
def test_check_and_adopt_write_zero_files_against_a_customized_registry(customized, mode):
    before = snapshot_tree(customized)
    result = run(customized, "--mode", mode)
    _status, writes = parse(result.stdout)
    assert writes == 0
    assert snapshot_tree(customized) == before


def test_adopt_against_a_registered_project_does_not_heal(customized):
    """Item 4: adoption against an existing workspace must not invoke repair."""
    before = snapshot_tree(customized)
    result = run(customized, "--mode", "adopt")
    assert snapshot_tree(customized) == before
    assert "did not heal" in result.stdout or parse(result.stdout)[0] in ("ready", "warning")


def test_repair_preserves_every_byte_outside_the_generated_region(customized):
    original = (customized / "Virtuoso.Governance.Readme.md").read_text(encoding="utf-8")
    run(customized, "--mode", "repair", "--apply")
    after = (customized / "Virtuoso.Governance.Readme.md").read_text(encoding="utf-8")

    head_original = original[:original.index(readme_mod.BEGIN_MARK)]
    head_after = after[:after.index(readme_mod.BEGIN_MARK)]
    assert head_after == head_original

    tail_original = original[original.index(readme_mod.END_MARK):]
    tail_after = after[after.index(readme_mod.END_MARK):]
    assert tail_after == tail_original


def test_a_user_authored_readme_is_never_regenerated(project):
    run(project, "--mode", "create", "--authorize")
    authored = "# Ours alone\n\nNo generated region anywhere in this file.\n"
    (project / "Virtuoso.Governance.Readme.md").write_text(authored, encoding="utf-8")

    before = snapshot_tree(project)
    run(project, "--mode", "check")
    assert snapshot_tree(project) == before

    preview = run(project, "--mode", "repair")
    assert "append" in preview.stdout.lower()
    assert snapshot_tree(project) == before      # preview writes nothing

    run(project, "--mode", "repair", "--apply")
    after = (project / "Virtuoso.Governance.Readme.md").read_text(encoding="utf-8")
    assert after.startswith(authored.rstrip("\n"))   # every prior byte preserved
    assert readme_mod.BEGIN_MARK in after            # the region was appended


# --- item 89: round-trip ------------------------------------------------------


def test_registry_round_trip_preserves_extensions_and_ordering(customized):
    before = json.loads((customized / "Virtuoso" / "workspace-layout.json").read_text(
        encoding="utf-8"))
    run(customized, "--mode", "repair", "--apply")
    after = json.loads((customized / "Virtuoso" / "workspace-layout.json").read_text(
        encoding="utf-8"))
    assert after["x-our-namespace"] == before["x-our-namespace"]
    assert after["documentationRoot"] == "docs"
    assert after["roles"]["roadmap"]["label"] == "Roadmap / specification store"


def test_crlf_line_endings_survive(project):
    run(project, "--mode", "create", "--authorize")
    manifest = project / "Virtuoso" / "workspace-layout.json"
    raw = manifest.read_bytes()
    manifest.write_bytes(raw.replace(b"\n", b"\r\n"))

    before = manifest.read_bytes()
    run(project, "--mode", "check")
    assert manifest.read_bytes() == before, "a settled CRLF file must not be rewritten"

    # A real rewrite keeps the file's own convention rather than imposing LF.
    assert textio.detect_eol(str(manifest)) == "\r\n"
    textio.write_if_changed(str(manifest), json.dumps({"schemaVersion": 2}) + "\n")
    assert b"\r\n" in manifest.read_bytes()


def test_write_if_changed_is_a_no_op_when_content_matches(tmp_path):
    target = tmp_path / "f.txt"
    assert textio.write_if_changed(str(target), "hello\n") is True
    stamp = target.stat().st_mtime_ns
    assert textio.write_if_changed(str(target), "hello\n") is False
    assert target.stat().st_mtime_ns == stamp


# --- item 90: authority precedence -------------------------------------------


def test_external_live_register_local_ledger_and_legacy_catalog_coexist(project):
    """All three roles registered at once; each keeps its declared authority and
    only the live one serves the work register."""
    from tools.governance import providers
    (project / "Virtuoso").mkdir()
    (project / "docs").mkdir()
    (project / "docs" / "catalog.csv").write_text("id,title,status\nA-1,First,Queued\n",
                                                  encoding="utf-8")
    (project / "docs" / "Ledger.md").write_text("# Ledger\n", encoding="utf-8")
    manifest = {
        "schemaVersion": 2,
        "roles": {
            "workRegister": {"external": "monday:board/1234567890", "provider": "connector",
                             "authority": "live", "mutability": "read-write",
                             "allowedWriters": ["roadmap-review"], "validation": "external",
                             "classification": "active", "origin": "authored"},
            "terminalLedger": {"path": "docs/Ledger.md", "provider": "markdown",
                               "authority": "terminal", "mutability": "append-only",
                               "allowedWriters": ["pointer-closeout"],
                               "validation": "markdown", "classification": "active",
                               "origin": "authored"},
            "sprintCatalog": {"path": "docs/catalog.csv", "provider": "csv",
                              "authority": "mirror", "mutability": "generated",
                              "allowedWriters": ["roadmap-review"],
                              "validation": "csv-headers", "classification": "active",
                              "origin": "generated", "generatedFrom": "workRegister"},
        },
    }
    (project / "Virtuoso" / "workspace-layout.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")

    reg = registry_mod.load(str(project), plugin_version="1.4.0")
    assert [f for f in reg.findings if f.severity == "error"] == []

    assert reg.roles["workRegister"].authority == "live"
    assert reg.roles["terminalLedger"].authority == "terminal"
    assert reg.roles["sprintCatalog"].authority == "mirror"

    # The live register is the one the provider layer serves...
    selection = providers.work_register(reg, actor="roadmap-review")
    assert selection.role_name == "workRegister"
    assert selection.compatibility is False

    # ...and the mirror is not writable by anyone, whatever allowedWriters says.
    assert reg.roles["sprintCatalog"].mutability == "generated"
    assert reg.writable("terminalLedger", "roadmap-review") is False
    assert reg.writable("terminalLedger", "pointer-closeout") is True


def test_two_live_registers_is_an_error(project):
    (project / "Virtuoso").mkdir()
    (project / "docs").mkdir()
    for name in ("a.csv", "b.csv"):
        (project / "docs" / name).write_text("id\n", encoding="utf-8")
    manifest = {"schemaVersion": 2, "roles": {
        "workRegister": {"path": "docs/a.csv", "provider": "csv", "authority": "live",
                         "mutability": "read-write", "validation": "csv-headers",
                         "classification": "active", "origin": "authored"},
        "otherRegister": {"path": "docs/b.csv", "provider": "csv", "authority": "live",
                          "mutability": "read-write", "validation": "csv-headers",
                          "classification": "active", "origin": "authored"},
    }}
    (project / "Virtuoso" / "workspace-layout.json").write_text(json.dumps(manifest),
                                                                encoding="utf-8")
    reg = registry_mod.load(str(project))
    assert any(f.code == "ambiguous-authority" for f in reg.findings)


def test_a_name_never_confers_authority():
    """Item 6: `sprintCatalog` is authoritative only if the project says so."""
    spec = schema.RoleSpec.from_manifest("sprintCatalog", "docs/sprint-catalog.csv")
    assert spec.authority == "unknown"
    assert spec.writable_by("roadmap-review") is False


# --- item 91: external identifiers -------------------------------------------


@pytest.mark.parametrize("value", [
    "monday:board/1234567890",
    "jira:project/ABC",
    "github:repo/example-org/example-repo",
    "postgres:table/public.work_items",
    "https://example.invalid/boards/42",
])
def test_external_identifiers_validate_without_touching_the_filesystem(project, value):
    (project / "Virtuoso").mkdir()
    manifest = {"schemaVersion": 2, "roles": {
        "workRegister": {"external": value, "provider": "connector", "authority": "live",
                         "mutability": "read-write", "validation": "external",
                         "classification": "active", "origin": "authored"}}}
    (project / "Virtuoso" / "workspace-layout.json").write_text(json.dumps(manifest),
                                                                encoding="utf-8")
    reg = registry_mod.load(str(project))
    assert [f.message for f in reg.findings if f.severity == "error"] == []
    role = reg.roles["workRegister"]
    assert role.presence == "external"       # never "absent"
    assert role.absolute == ""               # never resolved against the filesystem
    assert reg.resolve("workRegister") == value


@pytest.mark.parametrize("value", ["not-an-identifier", "", "C:\\boards\\42", "file:/tmp/x"])
def test_malformed_external_identifiers_are_reported(value):
    assert identifiers.validate(value)


def test_external_provider_declared_with_a_path_is_a_mismatch(project):
    (project / "Virtuoso").mkdir()
    (project / "docs").mkdir()
    (project / "docs" / "x.csv").write_text("id\n", encoding="utf-8")
    manifest = {"schemaVersion": 2, "roles": {
        "workRegister": {"path": "docs/x.csv", "provider": "connector", "authority": "live",
                         "mutability": "read-write", "validation": "external",
                         "classification": "active", "origin": "authored"}}}
    (project / "Virtuoso" / "workspace-layout.json").write_text(json.dumps(manifest),
                                                                encoding="utf-8")
    reg = registry_mod.load(str(project))
    assert any(f.code == "provider-mismatch" for f in reg.findings)


# --- path validation (item 19) ------------------------------------------------


@pytest.mark.parametrize("path,code", [
    ("../../etc/passwd", "unsafe-path"),
    ("/etc/passwd", "unsafe-path"),
    ("docs/archive/ROADMAP.md", "unsafe-path"),      # archive claiming live authority
])
def test_unsafe_registered_paths_are_rejected(project, path, code):
    (project / "Virtuoso").mkdir()
    manifest = {"schemaVersion": 2, "roles": {
        "roadmap": {"path": path, "provider": "markdown", "authority": "live",
                    "mutability": "read-write", "validation": "markdown",
                    "classification": "active", "origin": "authored"}}}
    (project / "Virtuoso" / "workspace-layout.json").write_text(json.dumps(manifest),
                                                                encoding="utf-8")
    reg = registry_mod.load(str(project))
    assert any(f.code == code for f in reg.findings), [f.as_dict() for f in reg.findings]


def test_a_registered_but_absent_role_is_reported_not_repointed(project):
    """Item 20: never search for a lookalike and silently repoint the role."""
    run(project, "--mode", "create", "--authorize")
    manifest = project / "Virtuoso" / "workspace-layout.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    registered = data["roles"]["roadmap"]["path"]
    os.remove(project / registered)
    # A very plausible lookalike sits right next to it.
    lookalike = project / "Project Documentation" / "1 governance" / "Roadmap.backup.md"
    lookalike.write_text("# Roadmap\n## Completed Work Summary\n", encoding="utf-8")

    reg = registry_mod.load(str(project))
    assert reg.roles["roadmap"].path == registered
    assert reg.roles["roadmap"].presence == "absent"

    run(project, "--mode", "repair", "--apply")
    after = json.loads(manifest.read_text(encoding="utf-8"))
    assert after["roles"]["roadmap"]["path"] == registered


def test_resolving_an_unregistered_role_raises_rather_than_guessing(project):
    run(project, "--mode", "create", "--authorize")
    reg = registry_mod.load(str(project))
    with pytest.raises(RoleNotRegistered):
        reg.resolve("someRoleNobodyRegistered")


# --- item 101: migration fixtures --------------------------------------------

V1_MANIFEST = {
    "layout": "plugin-only",
    "adopted": False,
    "documentationRoot": "Project Documentation",
    "paths": {
        "roadmap": "Project Documentation/1 governance/Roadmap.md",
        "sprintCatalog": "Project Documentation/2 operational/sprint-catalog.csv",
        "sprintQueue": "Project Documentation/2 operational/sprint-queue.xlsx",
        "lessons": "Project Documentation/1 governance/Lessons.md",
        "closeOuts": "Project Documentation/2 operational/Close-Outs",
        "issues": "Project Documentation/2 operational/Issues",
        "roadmapReviews": "Project Documentation/2 operational/roadmap-reviews",
        "governance": "Project Documentation/1 governance",
        "operational": "Project Documentation/2 operational",
        "scripts": "Virtuoso/scripts",
        "governanceReadme": "Virtuoso.Governance.Readme.md",
        "epics": "Project Documentation/1 governance/Epics.md",
    },
}


@pytest.fixture
def v1_project(project):
    (project / "Virtuoso").mkdir()
    (project / "Virtuoso" / ".virtuoso").write_text("virtuoso-workspace\n", encoding="utf-8")
    (project / "Virtuoso" / "workspace-layout.json").write_text(
        json.dumps(V1_MANIFEST, indent=2) + "\n", encoding="utf-8")
    for rel in ("Project Documentation/1 governance", "Project Documentation/2 operational"):
        (project / rel).mkdir(parents=True, exist_ok=True)
    (project / V1_MANIFEST["paths"]["roadmap"]).write_text("# Roadmap\n", encoding="utf-8")
    (project / V1_MANIFEST["paths"]["sprintCatalog"]).write_text("id,title\n", encoding="utf-8")
    (project / V1_MANIFEST["paths"]["epics"]).write_text("# Epics\n", encoding="utf-8")
    return project


def test_v1_migration_does_not_promote_the_compatibility_catalog(v1_project):
    reg = registry_mod.load(str(v1_project))
    assert reg.schema_version == 1
    assert reg.roles["sprintCatalog"].authority == "mirror"
    assert reg.roles["sprintCatalog"].writable_by("roadmap-review") is False
    assert any(f.code == "compatibility-catalog" for f in reg.findings)


def test_v1_migration_leaves_unknown_roles_unclassified(v1_project):
    reg = registry_mod.load(str(v1_project))
    epics = reg.roles["epics"]
    assert epics.authority == "unknown"
    assert epics.mutability == "read-only"
    assert epics.writable_by("roadmap-review") is False
    assert any(f.code == "unclassified-legacy-role" for f in reg.findings)


def test_v1_migration_is_non_destructive(v1_project):
    """The roadmap and the catalog are untouched; only the control files change."""
    before = snapshot_tree(v1_project)
    run(v1_project, "--mode", "repair", "--apply")
    after = snapshot_tree(v1_project)
    for rel, raw in before.items():
        if rel.startswith("Virtuoso/workspace-layout") or rel.endswith("Governance.Readme.md"):
            continue
        assert after[rel] == raw, "migration modified %s" % rel


def test_v1_migration_preserves_plugin_internal_keys(v1_project):
    run(v1_project, "--mode", "repair", "--apply")
    data = json.loads((v1_project / "Virtuoso" / "workspace-layout.json").read_text(
        encoding="utf-8"))
    assert data["schemaVersion"] == schema.SCHEMA_VERSION
    assert data["x-legacy-v1"]["paths"]["scripts"] == "Virtuoso/scripts"
    assert "paths" not in data, "the v1 dual-authority mapping must not survive"


def test_a_future_schema_version_is_refused_loudly(project):
    (project / "Virtuoso").mkdir()
    (project / "Virtuoso" / "workspace-layout.json").write_text(
        json.dumps({"schemaVersion": 99, "roles": {}}), encoding="utf-8")
    with pytest.raises(SchemaVersionError):
        registry_mod.load(str(project))
    result = run(project, "--mode", "check")
    assert parse(result.stdout)[0] == "failed"
    assert parse(result.stdout)[1] == 0
