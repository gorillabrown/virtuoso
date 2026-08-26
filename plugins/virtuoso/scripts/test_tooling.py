"""Tooling corrections (items 82-87).

The cockpit reads the configured authoritative provider; the report generator
writes only roles the project declared generated; the close-out path helper is
read-only and fails loudly; nothing falls back to a conventional path.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT, snapshot_tree
from tools.governance import registry as registry_mod

PREFLIGHT = str(Path(PLUGIN_ROOT) / "scripts" / "virtuoso_preflight.py")
REGISTRY_CLI = str(Path(PLUGIN_ROOT) / "scripts" / "virtuoso_registry.py")
COCKPIT = str(Path(PLUGIN_ROOT) / "scripts" / "generate_cockpit.py")
REPORT = str(Path(PLUGIN_ROOT) / "scripts" / "build_register_report.py")

ROWS = (
    "ITEM-1,First thing,1,Completed,Full Spec,,S,,G1,,,,2026-01-01,,,\n"
    "ITEM-2,Second thing,2,Queued,Full Spec,ITEM-1,M,,G1,,,,,,,\n"
)


def run(script, *args):
    return subprocess.run([sys.executable, script, *args], capture_output=True,
                          text=True, env=dict(os.environ))


@pytest.fixture
def workspace(project):
    run(PREFLIGHT, "--root", str(project), "--mode", "create", "--authorize")
    register = project / "Project Documentation" / "2 operational" / "work-register.csv"
    with open(register, "a", encoding="utf-8") as handle:
        handle.write(ROWS)
    roadmap = project / "Project Documentation" / "1 governance" / "Roadmap.md"
    text = roadmap.read_text(encoding="utf-8")
    text = text.replace("|------|---------|--------|-----------|",
                        "|------|---------|--------|-----------|\n| ITEM-1 | 1 | shipped | — |")
    text = text.replace("## Active & Remaining Work\n",
                        "## Active & Remaining Work\n\n#### ITEM-2 — Second thing\n\n"
                        "Acceptance criteria: mechanical.\n")
    roadmap.write_text(text, encoding="utf-8")
    return project


@pytest.fixture
def external_workspace(project):
    """A connector-backed register with an exact-revision canonical snapshot."""
    (project / "Virtuoso").mkdir()
    snapshot = project / "Virtuoso" / "work-register.snapshot.json"
    snapshot.write_text(json.dumps({
        "snapshotVersion": 1,
        "takenAt": "2099-01-01T00:00:00Z",
        "provider": "connector",
        "source": "monday:board/1234567890",
        "fields": ["id", "status", "revision"],
        "items": [{
            "id": "123", "title": "Example", "status": "queued",
            "raw_status": "Queued", "revision": "rev-1",
        }],
    }, indent=2), encoding="utf-8")
    manifest = {
        "schemaVersion": 2,
        "roles": {
            "workRegister": {
                "external": "monday:board/1234567890", "provider": "connector",
                "authority": "live", "mutability": "read-write",
                "allowedWriters": ["roadmap-review"], "validation": "external",
                "classification": "active", "origin": "authored",
            },
            "workRegisterSnapshot": {
                "path": "Virtuoso/work-register.snapshot.json", "provider": "snapshot",
                "authority": "report", "mutability": "generated",
                "validation": "exists", "classification": "active", "origin": "generated",
            },
        },
        "policy": {"workRegister": {"snapshot": "workRegisterSnapshot"}},
    }
    (project / "Virtuoso" / "workspace-layout.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    return project


def cockpit_model(html: str) -> dict:
    match = re.search(r"const MODEL = (\{.*?\});\n", html, re.S)
    assert match, "the cockpit did not embed its model"
    return json.loads(match.group(1))


# --- item 82/84: the cockpit reads the configured provider ---------------------


def test_the_cockpit_reads_the_configured_work_register(workspace):
    completed = run(COCKPIT, "--root", str(workspace))
    assert completed.returncode == 0, completed.stderr
    model = cockpit_model((workspace / "Virtuoso" / "reports"
                           / "planning-cockpit.html").read_text(encoding="utf-8"))
    assert model["workspace"]["work_register_role"] == "workRegister"
    assert model["workspace"]["work_register_authority"] == "live"
    assert model["provenance"]["provider"] == "csv"
    assert [i["id"] for i in model["items"]] == ["ITEM-1", "ITEM-2"]


def test_the_cockpit_needs_no_spreadsheet(workspace):
    """Item 82: it must not require a generated workbook."""
    for path in workspace.rglob("*.xlsx"):
        path.unlink()
    completed = run(COCKPIT, "--root", str(workspace))
    assert completed.returncode == 0, completed.stderr


def test_the_cockpit_states_its_provenance_and_health(workspace):
    run(COCKPIT, "--root", str(workspace))
    model = cockpit_model((workspace / "Virtuoso" / "reports"
                           / "planning-cockpit.html").read_text(encoding="utf-8"))
    assert model["provenance"]["takenAt"]
    assert model["provenance"]["stale"] is False
    assert model["health"]["head_id"] == "ITEM-2"
    assert model["health"]["drift_findings"] == []


def test_the_cockpit_refuses_a_project_without_a_registry(project):
    completed = run(COCKPIT, "--root", str(project))
    assert completed.returncode != 0
    assert "virtuoso_preflight" in (completed.stderr + completed.stdout)


def test_the_cockpit_never_overwrites_a_registered_document(workspace):
    reg = registry_mod.load(str(workspace))
    roadmap = reg.resolve("roadmap")
    completed = run(COCKPIT, "--root", str(workspace), "--output", roadmap)
    assert completed.returncode != 0
    assert "refusing to overwrite" in (completed.stderr + completed.stdout)


def test_the_cockpit_surfaces_drift_rather_than_fixing_it(workspace):
    register = workspace / "Project Documentation" / "2 operational" / "work-register.csv"
    with open(register, "a", encoding="utf-8") as handle:
        handle.write("ITEM-9,Ghost item,9,Queued,Stub,,S,,G1,,,,,,,\n")
    before = snapshot_tree(workspace / "Project Documentation")
    run(COCKPIT, "--root", str(workspace))
    model = cockpit_model((workspace / "Virtuoso" / "reports"
                           / "planning-cockpit.html").read_text(encoding="utf-8"))
    assert any("ITEM-9" in finding for finding in model["health"]["drift_findings"])
    assert snapshot_tree(workspace / "Project Documentation") == before


# --- item 83: the retired recalculation script --------------------------------


def test_the_retired_recalculation_script_is_gone():
    assert not (Path(PLUGIN_ROOT) / "skills" / "roadmap-review" / "scripts").exists()
    for path in Path(PLUGIN_ROOT).rglob("recalc*.py"):
        raise AssertionError("a retired recalculation script survives at %s" % path)


def test_the_retired_workbook_builder_is_gone():
    assert not (Path(PLUGIN_ROOT) / "scripts" / "build_sprint_queue.py").exists()
    assert not (Path(PLUGIN_ROOT) / "tools" / "roadmap_visualizer" / "workbook.py").exists()


# --- item 58/84: generated artifacts ------------------------------------------


@pytest.mark.skipif(
    __import__("importlib").util.find_spec("openpyxl") is None,
    reason="openpyxl is not installed")
def test_the_report_generator_writes_only_a_declared_generated_role(workspace):
    manifest = workspace / "Virtuoso" / "workspace-layout.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["roles"]["sprintQueue"] = {
        "path": "Project Documentation/2 operational/report.xlsx", "provider": "xlsx",
        "authority": "report", "mutability": "generated", "validation": "xlsx",
        "classification": "active", "origin": "generated",
        "generatedFrom": "workRegister", "generatedBy": "build_register_report"}
    manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")

    completed = run(REPORT, "--root", str(workspace))
    assert completed.returncode == 0, completed.stderr
    assert (workspace / data["roles"]["sprintQueue"]["path"]).exists()

    # Flip it to authored: the generator must refuse.
    data["roles"]["sprintQueue"]["origin"] = "authored"
    data["roles"]["sprintQueue"]["mutability"] = "read-write"
    manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")
    refused = run(REPORT, "--root", str(workspace))
    assert refused.returncode != 0
    assert "declared generated" in refused.stderr


def test_the_report_generator_names_the_fix_when_no_role_exists(workspace):
    completed = run(REPORT, "--root", str(workspace))
    assert completed.returncode != 0
    assert "not registered" in completed.stderr or "openpyxl" in completed.stderr


# --- items 85, 86, 87: the close-out path helper ------------------------------


def test_closeout_paths_are_read_only_by_default(workspace):
    reg = registry_mod.load(str(workspace))
    closeouts = Path(reg.resolve("closeOuts"))
    if closeouts.exists():
        closeouts.rmdir()
    before = snapshot_tree(workspace)

    completed = run(REGISTRY_CLI, "--root", str(workspace), "closeout",
                    "--item", "ITEM-2", "--date", "2026-01-01")
    assert completed.returncode == 0
    assert "prepared=False" in completed.stdout
    assert not closeouts.exists(), "querying a path must not create it"
    assert snapshot_tree(workspace) == before


def test_prepare_is_the_explicit_opt_in(workspace):
    reg = registry_mod.load(str(workspace))
    closeouts = Path(reg.resolve("closeOuts"))
    if closeouts.exists():
        closeouts.rmdir()
    completed = run(REGISTRY_CLI, "--root", str(workspace), "closeout",
                    "--item", "ITEM-2", "--date", "2026-01-01", "--prepare")
    assert completed.returncode == 0
    assert "prepared=True" in completed.stdout
    assert closeouts.is_dir()


def test_closeout_fails_loudly_on_an_invalid_registry(workspace):
    """Item 85: never fall back to a conventional Close-Outs directory."""
    manifest = workspace / "Virtuoso" / "workspace-layout.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["roles"]["roadmap"]["path"] = "../../escape.md"
    manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")

    before = snapshot_tree(workspace)
    completed = run(REGISTRY_CLI, "--root", str(workspace), "closeout",
                    "--item", "ITEM-2", "--date", "2026-01-01")
    assert completed.returncode == 3
    assert "present but invalid" in completed.stderr
    assert "--mode repair" in completed.stderr
    assert snapshot_tree(workspace) == before
    assert not (workspace / "docs" / "Close-Outs").exists()
    assert not (workspace / "Close-Outs").exists()


def test_closeout_fails_loudly_with_no_registry(project):
    completed = run(REGISTRY_CLI, "--root", str(project), "closeout",
                    "--item", "ITEM-2", "--date", "2026-01-01")
    assert completed.returncode == 3
    assert "no governance registry" in completed.stderr
    assert not (project / "docs").exists()


def test_closeout_resolves_the_next_lesson_identifier(workspace):
    reg = registry_mod.load(str(workspace))
    lessons = Path(reg.resolve("lessons"))
    lessons.write_text("# Lessons\n\n## SRL-004 — something\n", encoding="utf-8")  # validate-ok: the default lesson prefix is the subject of this test
    completed = run(REGISTRY_CLI, "--root", str(workspace), "closeout",
                    "--item", "ITEM-2", "--date", "2026-01-01")
    assert "nextLessonId=SRL-005" in completed.stdout  # validate-ok: default prefix under test


def test_the_lesson_prefix_is_configurable(workspace):
    reg = registry_mod.load(str(workspace))
    Path(reg.resolve("lessons")).write_text("# Lessons\n\n## LL-011 — x\n", encoding="utf-8")
    completed = run(REGISTRY_CLI, "--root", str(workspace), "closeout",
                    "--item", "ITEM-2", "--date", "2026-01-01", "--lesson-prefix", "LL")
    assert "nextLessonId=LL-012" in completed.stdout


# --- item 87: no heuristic fallbacks -------------------------------------------


def test_resolving_a_role_never_invents_a_conventional_path(workspace):
    completed = run(REGISTRY_CLI, "--root", str(workspace), "resolve", "sprintQueue")
    assert completed.returncode == 3
    assert "not registered" in completed.stderr
    assert "does not guess conventional paths" in completed.stderr


def test_the_registry_cli_queries_write_nothing(workspace):
    before = snapshot_tree(workspace)
    for args in (["roles"], ["items"], ["next"], ["kpis"], ["provider"], ["recovery"],
                 ["repo"], ["resolve", "roadmap"]):
        run(REGISTRY_CLI, "--root", str(workspace), *args)
    assert snapshot_tree(workspace) == before


def test_external_mutation_cli_plans_and_confirms_with_recovery(external_workspace):
    planned = run(
        REGISTRY_CLI, "--root", str(external_workspace), "--actor", "roadmap-review",
        "mutation-plan", "--operation", "set-status", "--item", "123",
        "--fields-json", json.dumps({"status": "In Flight"}),
        "--revision", "rev-1", "--json")
    assert planned.returncode == 0, planned.stderr
    plan = json.loads(planned.stdout)
    assert plan["expectedRevision"] == "rev-1"
    assert plan["idempotencyKey"]
    assert plan["recoveryId"]

    pending = run(REGISTRY_CLI, "--root", str(external_workspace), "recovery", "--json")
    assert len(json.loads(pending.stdout)["outstanding"]) == 1

    confirmed = run(
        REGISTRY_CLI, "--root", str(external_workspace), "--actor", "roadmap-review",
        "mutation-confirm", "--operation", plan["operation"], "--item", plan["itemId"],
        "--idempotency-key", plan["idempotencyKey"],
        "--recovery-id", plan["recoveryId"], "--actual-revision", "rev-2",
        "--succeeded", "--json")
    assert confirmed.returncode == 0, confirmed.stderr
    outcome = json.loads(confirmed.stdout)
    assert outcome["succeeded"] is True
    assert outcome["actualRevision"] == "rev-2"
    pending = run(REGISTRY_CLI, "--root", str(external_workspace), "recovery", "--json")
    assert json.loads(pending.stdout)["outstanding"] == []


def test_external_mutation_cli_rejects_stale_revision(external_workspace):
    completed = run(
        REGISTRY_CLI, "--root", str(external_workspace), "--actor", "roadmap-review",
        "mutation-plan", "--operation", "set-status", "--item", "123",
        "--fields-json", json.dumps({"status": "In Flight"}),
        "--revision", "stale-revision", "--json")
    assert completed.returncode == 3
    assert "changed since it was read" in completed.stderr
    assert not (external_workspace / "Virtuoso" / ".recovery").exists()


def test_external_mutation_cli_rejects_an_unauthorized_actor(external_workspace):
    completed = run(
        REGISTRY_CLI, "--root", str(external_workspace), "--actor", "next-pointer",
        "mutation-plan", "--operation", "set-status", "--item", "123",
        "--fields-json", json.dumps({"status": "In Flight"}),
        "--revision", "rev-1", "--json")
    assert completed.returncode == 3
    assert "does not support" in completed.stderr
    assert not (external_workspace / "Virtuoso" / ".recovery").exists()


# --- item 62: immutable-hash verification --------------------------------------


def test_protected_files_are_hashed_before_and_after(workspace):
    from tools.governance import integrity
    reg = registry_mod.load(str(workspace))
    before = integrity.snapshot(reg)
    assert before.hashes, "the terminal ledger is protected and should be hashed"
    assert integrity.compare(before, integrity.snapshot(reg)) == []

    ledger = Path(reg.resolve("terminalLedger"))
    ledger.write_text(ledger.read_text(encoding="utf-8") + "tampered\n", encoding="utf-8")
    problems = integrity.compare(before, integrity.snapshot(reg))
    assert len(problems) == 1
    assert "modified during the run" in problems[0]


def test_a_removed_protected_file_is_detected(workspace):
    from tools.governance import integrity
    reg = registry_mod.load(str(workspace))
    before = integrity.snapshot(reg)
    Path(reg.resolve("terminalLedger")).unlink()
    problems = integrity.compare(before, integrity.snapshot(reg))
    assert any("removed during the run" in p for p in problems)


def test_protected_roles_come_from_policy(workspace):
    from tools.governance import integrity
    manifest = workspace / "Virtuoso" / "workspace-layout.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data.setdefault("policy", {})["sweep"] = {"protectedAuthorities": []}
    manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")
    reg = registry_mod.load(str(workspace))
    names = {spec.name for spec in integrity.protected_roles(reg)}
    # With no protected authorities declared, only immutable/read-only roles qualify.
    assert "terminalLedger" not in names


def test_the_protected_command_is_read_only(workspace):
    before = snapshot_tree(workspace)
    completed = run(REGISTRY_CLI, "--root", str(workspace), "protected")
    assert completed.returncode == 0
    assert snapshot_tree(workspace) == before


# --- item 79: declared runtime dependencies ------------------------------------


def test_declared_dependencies_are_checked(workspace):
    completed = run(REGISTRY_CLI, "--root", str(workspace), "deps", "--json")
    payload = json.loads(completed.stdout)
    assert payload["dependencies"], "openpyxl is declared by default"
    assert payload["dependencies"][0]["name"] == "openpyxl"


def test_an_unsatisfiable_dependency_is_reported_not_raised(workspace):
    manifest = workspace / "Virtuoso" / "workspace-layout.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data.setdefault("policy", {})["dependencies"] = {"openpyxl": ">=999"}
    manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")
    completed = run(REGISTRY_CLI, "--root", str(workspace), "deps")
    assert completed.returncode == 3
    assert "does not satisfy" in completed.stdout


def test_a_missing_dependency_is_reported_not_raised(workspace):
    manifest = workspace / "Virtuoso" / "workspace-layout.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data.setdefault("policy", {})["dependencies"] = {"definitely_not_installed_xyz": ">=1"}
    manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")
    completed = run(REGISTRY_CLI, "--root", str(workspace), "deps")
    assert completed.returncode == 3
    assert "not installed" in completed.stdout


@pytest.mark.parametrize("version,spec,expected", [
    ("3.1.5", ">=3.1", True), ("3.0.9", ">=3.1", False),
    ("4.0", "<4", False), ("3.9", "<4", True),
    ("3.1.2", "==3.1.2", True), ("3.1.3", "==3.1.2", False),
    ("3.1.5", "", True), ("3.1.5", "whatever", True),
])
def test_version_specifiers(version, spec, expected):
    from tools.governance import dependencies
    assert dependencies.satisfies(version, spec) is expected


def test_the_spreadsheet_provider_withdraws_capabilities_without_its_dependency(monkeypatch):
    from tools.governance.providers import xlsx_provider
    monkeypatch.setattr(xlsx_provider, "dependency_available", lambda: (False, "no module"))
    provider = xlsx_provider.XlsxWorkRegister(source="/nowhere/register.xlsx")
    assert provider.capabilities == frozenset()
    with pytest.raises(Exception) as excinfo:
        provider.require("list-active")
    assert "openpyxl" in str(excinfo.value)
    assert provider.describe()["dependency"]["available"] is False
