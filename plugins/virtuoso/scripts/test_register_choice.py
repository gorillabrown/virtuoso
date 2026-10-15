"""`create --register`: where the work register lives (HB-10)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT, snapshot_tree

PREFLIGHT = str(Path(PLUGIN_ROOT) / "scripts" / "virtuoso_preflight.py")


def create(root, *args):
    return subprocess.run(
        [sys.executable, PREFLIGHT, "--root", str(root), "--mode", "create", "--authorize",
         "--json", *args],
        capture_output=True, text=True, encoding="utf-8", env=dict(os.environ))


def manifest(root):
    return json.loads((root / "Virtuoso" / "workspace-layout.json").read_text(encoding="utf-8"))


def test_create_with_a_tool_identifier_registers_it_external(project, tmp_path):
    mappings = tmp_path / "mappings.json"
    mappings.write_text(json.dumps({
        "fieldMappings": {"id": "Item ID", "title": "Name"},
        "statusMappings": {"completed": ["Done"]}}), encoding="utf-8")
    result = create(project, "--register", "notion:database/abc",
                    "--register-mappings", str(mappings))
    assert result.returncode == 0, result.stdout + result.stderr
    data = manifest(project)
    role = data["roles"]["workRegister"]
    assert role["external"] == "notion:database/abc" and role["provider"] == "connector"
    assert role["validation"] == "external" and "path" not in role
    snap = data["roles"]["workRegisterSnapshot"]
    assert snap["path"] == "Virtuoso/work-register.snapshot.json"
    assert snap["provider"] == "snapshot" and snap["generatedFrom"] == "workRegister"
    policy = data["policy"]["workRegister"]
    assert policy["snapshot"] == "workRegisterSnapshot"
    assert policy["fieldMappings"] == {"id": "Item ID", "title": "Name"}
    assert policy["statusMappings"] == {"completed": ["Done"]}
    assert not list(project.rglob("*.csv"))
    again = create(project, "--register", "csv")
    assert again.returncode != 0 and "already-registered" in again.stdout


def test_create_without_a_choice_is_todays_layout(project):
    assert create(project).returncode == 0
    assert (project / "Project Documentation" / "2 operational" / "work-register.csv").is_file()
    assert "workRegisterSnapshot" not in manifest(project)["roles"]


def test_create_with_csv_is_todays_layout(project, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    assert create(project).returncode == 0
    assert create(other, "--register", "csv").returncode == 0
    assert snapshot_tree(project) == snapshot_tree(other)


def test_create_with_markdown_seeds_a_table(project):
    assert create(project, "--register", "markdown").returncode == 0
    role = manifest(project)["roles"]["workRegister"]
    assert role["provider"] == "markdown" and role["path"].endswith("work-register.md")
    text = (project / role["path"]).read_text(encoding="utf-8")
    assert "| id | title | sequence |" in text


def test_a_spreadsheet_without_openpyxl_fails_naming_it(project, monkeypatch):
    sys.path.insert(0, str(Path(PREFLIGHT).parent))
    import virtuoso_preflight
    monkeypatch.setattr(virtuoso_preflight.providers.xlsx_provider, "dependency_available",
                        lambda: (False, "no module"))
    outcome = virtuoso_preflight.run_create(str(project), authorized=True, register="xlsx")
    assert outcome.status == "failed" and "openpyxl" in outcome.message
    assert not list(project.iterdir())


def test_a_malformed_identifier_is_refused(project):
    for bad in ("./board.csv", "board", "C:\\boards\\x.csv"):
        result = create(project, "--register", bad)
        assert result.returncode != 0
        assert not list(project.iterdir())


def test_mappings_without_an_id_column_are_refused(project, tmp_path):
    mappings = tmp_path / "mappings.json"
    mappings.write_text(json.dumps({"fieldMappings": {"title": "Name"}}), encoding="utf-8")
    result = create(project, "--register", "notion:database/abc",
                    "--register-mappings", str(mappings))
    assert result.returncode != 0
    assert not list(project.iterdir())


@pytest.mark.parametrize("content, args", [
    ("[1, 2]", ("--register", "notion:database/abc")),
    ('{"fieldMappings": 5}', ("--register", "notion:database/abc")),
    ('{"fieldMappings": {"id": "ID"}}', ("--register", "csv")),
])
def test_bad_register_mappings_are_refused_before_any_write(project, tmp_path, content, args):
    mappings = tmp_path / "mappings.json"
    mappings.write_text(content, encoding="utf-8")
    result = create(project, *args, "--register-mappings", str(mappings))
    assert result.returncode != 0 and "Traceback" not in result.stderr
    assert not list(project.iterdir())


def test_create_with_a_tool_identifier_works_from_a_subfolder(project):
    """The command the skill prints also works from somewhere other than the root."""
    sub = project / "docs"
    sub.mkdir()
    result = subprocess.run(
        [sys.executable, PREFLIGHT, "--root", "..", "--mode", "create", "--authorize",
         "--register", "linear:team/ENG"],
        capture_output=True, text=True, encoding="utf-8", env=dict(os.environ), cwd=sub)
    assert result.returncode == 0, result.stdout + result.stderr
    assert manifest(project)["roles"]["workRegister"]["external"] == "linear:team/ENG"


def test_the_init_skill_asks_first_and_never_claims_a_connection():
    """Frame 3: the register question comes before create, in three groups, in order."""
    text = (Path(PLUGIN_ROOT) / "skills" / "virtuoso-init" / "SKILL.md").read_text(encoding="utf-8")
    section = text[text.index("## New project? Create"):text.index("### What create lays down")]
    ask = section.index("### First: ask where the work register lives")
    assert ask < section.index("--mode create --authorize --register")
    groups = [section.index(g) for g in ("**A file in the repository**",
                                         "**A task tool this session can reach**",
                                         "**Another tool, by identifier**")]
    assert ask < groups[0] < groups[1] < groups[2]
    flat = " ".join(section.split())
    assert "That tool is not connected in this session" in flat
    assert "Record it only if they ask." in flat
