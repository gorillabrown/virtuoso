"""One vocabulary: workstream and deliverable (1.15.0).

"lane" became "workstream", and an item may name its deliverable. The old names are
project data and keep working for one release: a register column named Lane, a
fieldMappings key lane, roadmap.lanes and combine --lane. Nothing in a project's own
files is rewritten.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT, snapshot_tree
from tools.governance import move as move_mod, policy as policy_mod, registry as registry_mod
from tools.governance.errors import ProviderError
from tools.governance.providers import mapping as mapping_mod, snapshot_provider
from tools.governance.providers.csv_provider import CsvWorkRegister
from tools.governance.providers.markdown_provider import MarkdownWorkRegister
from tools.governance.providers.xlsx_provider import XlsxWorkRegister, dependency_available

ROOT = Path(PLUGIN_ROOT)
PREFLIGHT = str(ROOT / "scripts" / "virtuoso_preflight.py")
REGISTRY_CLI = str(ROOT / "scripts" / "virtuoso_registry.py")
#: items --all --json and kpis --json for REGISTER, read by the plugin before the rename
#: (910b3a3), with the VOLATILE keys removed.
PRE_RENAME = ROOT / "scripts" / "fixtures" / "workstreams.pre-rename.json"

# The project's own column is "Lane": persisted data the rename never touches.
REGISTER = (
    "Id,Title,Seq,Status,Written,Prerequisites,Effort,Lane,Group\n"
    "A-1,Engine core,1,Done,Full Spec,,M,ENGINE,G1\n"
    "A-2,Engine tick,2,In Progress,Full Spec,A-1,S,ENGINE,G1\n"
    "A-3,Menu,3,Queued,Full Spec,,L,UI,G2\n"
    "A-4,Unplaced,4,Queued,Stub,,,,G2\n"
)

ROADMAP = """# Shop — Roadmap

## Active & Remaining Work

#### A-3 — Menu
##### Implementation detail
- **Edit sites:** `src/menu.py`

#### A-4 — Unplaced
##### Implementation detail
- **Edit sites:** `src/other.py`
"""


def run(*args, cli=REGISTRY_CLI):
    return subprocess.run([sys.executable, cli, *args], capture_output=True, text=True,
                          encoding="utf-8", env=dict(os.environ))


def layout_path(root):
    return root / "Virtuoso" / "workspace-layout.json"


def role_path(root, role):
    layout = json.loads(layout_path(root).read_text(encoding="utf-8"))
    return root.joinpath(*layout["roles"][role]["path"].split("/"))


def set_policy(root, **sections):
    path = layout_path(root)
    layout = json.loads(path.read_text(encoding="utf-8"))
    policy = layout.setdefault("policy", {})
    for name, value in sections.items():
        policy.setdefault(name, {}).update(value)
    path.write_text(json.dumps(layout, indent=2), encoding="utf-8")


@pytest.fixture
def shop(project):
    created = run("--root", str(project), "--mode", "create", "--authorize", cli=PREFLIGHT)
    assert created.returncode == 0, created.stdout + created.stderr
    role_path(project, "workRegister").write_text(REGISTER, encoding="utf-8", newline="\n")
    return project


def items_json(root):
    completed = run("--root", str(root), "items", "--all", "--json")
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


#: Keys that vary by run or name the project's own paths; the rename touches none of them.
VOLATILE = ("source", "takenAt", "asOf", "closeOuts", "ledger", "lessons", "timeLogs")


def without(node, keys=VOLATILE):
    if isinstance(node, dict):
        return {k: without(v, keys) for k, v in node.items() if k not in keys}
    if isinstance(node, list):
        return [without(v, keys) for v in node]
    return node


def renamed(node):
    """The pre-rename output with exactly the rename applied: the key ``lane`` and the
    field name ``lane`` become ``workstream``, and each item gains an empty deliverable."""
    if isinstance(node, dict):
        out = {("workstream" if k == "lane" else k): renamed(v) for k, v in node.items()}
        if "workstream" in out and "written_status" in out:      # a work item
            out.setdefault("deliverable", "")
        return out
    if isinstance(node, list):
        out = [renamed("workstream" if v == "lane" else v) for v in node]
        # provenance.fields is a sorted list: the new name sorts into its own place.
        return sorted(out) if "lane" in node and node == sorted(node) else out
    return node


# --- Done-when 1: the old names still work, and warn ----------------------------------


def test_a_lane_column_reads_as_workstream(shop):
    register = role_path(shop, "workRegister")
    before = register.read_bytes()
    by_id = {i["id"]: i for i in items_json(shop)["items"]}
    assert by_id["A-1"]["workstream"] == "ENGINE" and by_id["A-3"]["workstream"] == "UI"
    assert "lane" not in by_id["A-1"]
    assert register.read_bytes() == before                  # the project's header stays

    # A fieldMappings key spelled the old way maps the project's column to workstream.
    register.write_text(REGISTER.replace(",Lane,", ",Swim Group,"), encoding="utf-8",
                        newline="\n")
    set_policy(shop, workRegister={"fieldMappings": {"lane": "Swim Group"}})
    by_id = {i["id"]: i for i in items_json(shop)["items"]}
    assert by_id["A-2"]["workstream"] == "ENGINE"


def test_lane_and_workstream_mappings_together_are_refused():
    with pytest.raises(ProviderError) as refused:
        mapping_mod.Mapping.from_policy({"fieldMappings": {"lane": "Lane", "workstream": "WS"}})
    assert "'lane'" in str(refused.value) and "'workstream'" in str(refused.value)


def test_a_snapshot_written_before_the_rename_reads_lane_as_workstream(tmp_path):
    cache = tmp_path / "snapshot.json"
    old = {"provider": "connector", "source": "notion:database/x",
           "takenAt": "2026-10-13T00:00:00Z", "fields": ["id", "lane", "status"], "headers": {"lane": "Lane"},
           "items": [{"id": "A-1", "status": "queued", "lane": "ENGINE"}]}
    cache.write_text(json.dumps(old), encoding="utf-8")
    before = cache.read_bytes()
    snap = snapshot_provider.SnapshotWorkRegister(source=str(cache)).snapshot()
    assert snap.items[0].workstream == "ENGINE"
    assert snap.fields == ["id", "workstream", "status"]
    assert snap.headers == {"workstream": "Lane"}
    assert cache.read_bytes() == before


def test_a_move_reads_an_old_mappings_file(tmp_path):
    (tmp_path / "mappings.json").write_text(
        json.dumps({"fieldMappings": {"id": "Id", "lane": "Lane"}}), encoding="utf-8")
    read = move_mod.read_mappings(str(tmp_path), "mappings.json")
    assert read["fieldMappings"] == {"id": "Id", "workstream": "Lane"}


def test_roadmap_lanes_reads_as_workstreams_with_a_warning(shop):
    old = {"roadmap": {"lanes": ["ENGINE", {"id": "UI", "name": "Interface"}]}}
    assert policy_mod.load(old).workstreams == [{"id": "ENGINE", "name": "ENGINE"},
                                                {"id": "UI", "name": "Interface"}]
    warned = [f for f in registry_mod.policy_findings(old) if f.code == "policy-renamed"]
    assert len(warned) == 1 and "roadmap.workstreams" in warned[0].message
    assert not [f for f in registry_mod.policy_findings({"roadmap": {"workstreams": []}})
                if f.code == "policy-renamed"]

    # Preflight's read-only check shows the warning to the project.
    set_policy(shop, roadmap={"lanes": ["ENGINE"]})
    checked = run("--root", str(shop), "--mode", "check", cli=PREFLIGHT)
    assert "policy.roadmap.lanes is the old name of policy.roadmap.workstreams" in \
        checked.stdout + checked.stderr


def test_combine_lane_is_a_hidden_alias(shop):
    role_path(shop, "roadmap").write_text(ROADMAP, encoding="utf-8", newline="\n")
    before = snapshot_tree(str(shop))
    new = run("--root", str(shop), "combine", "--workstream", "UI", "--json")
    old = run("--root", str(shop), "combine", "--lane", "UI", "--json")
    assert new.returncode == old.returncode and new.returncode in (0, 1), new.stderr + old.stderr
    assert without(json.loads(old.stdout)) == without(json.loads(new.stdout))
    assert json.loads(new.stdout)["order"] == ["A-3"]
    assert new.stderr == ""
    assert old.stderr.strip().splitlines() == [
        "virtuoso: --lane is the old name of --workstream; it works until the next release"]
    shown = run("combine", "--help").stdout
    assert "--workstream" in shown and "--lane" not in shown
    assert snapshot_tree(str(shop)) == before


# --- Done-when 2: a project with no structure reads as before -------------------------


def test_a_project_without_workstreams_reads_unchanged(shop):
    expected = renamed(json.loads(PRE_RENAME.read_text(encoding="utf-8")))
    completed = run("--root", str(shop), "kpis", "--json")
    assert completed.returncode == 0, completed.stderr
    actual = {"items": items_json(shop), "kpis": json.loads(completed.stdout)}
    assert without(actual) == without(expected)


# --- Done-when 3: the policy shape and the new field ----------------------------------


def test_a_deliverable_in_two_workstreams_is_refused(shop):
    structure = [
        {"id": "engine", "name": "Engine", "purpose": "the tick",
         "deliverables": [{"id": "core", "name": "Core", "purpose": "runs"}]},
        {"id": "ui", "name": "Interface", "purpose": "menus",
         "deliverables": [{"id": "core", "name": "Core again", "purpose": "twice"}]},
    ]
    problems = policy_mod.load({"roadmap": {"workstreams": structure}}).validate()
    assert any("'core' is under two workstreams, 'engine' and 'ui'" in p for p in problems)
    structure[1]["deliverables"][0]["id"] = "menus"
    assert policy_mod.load({"roadmap": {"workstreams": structure}}).validate() == []
    twice = [structure[0], dict(structure[1], id="engine")]
    assert any("'engine' is used twice" in p
               for p in policy_mod.load({"roadmap": {"workstreams": twice}}).validate())

    structure[1]["deliverables"][0]["id"] = "core"
    before = layout_path(shop).read_bytes()
    refused = run("--root", str(shop), "--actor", "roadmap-review", "policy-set",
                  "roadmap.workstreams", "--value-json", json.dumps(structure), "--apply")
    assert refused.returncode != 0 and "under two workstreams" in refused.stderr
    assert layout_path(shop).read_bytes() == before


def test_a_workstream_named_like_another_ones_id_is_refused(shop):
    structure = [{"id": "a", "name": "Alpha"}, {"id": "b", "name": "a"}]
    problems = policy_mod.load({"roadmap": {"workstreams": structure}}).validate()
    assert ("policy.roadmap.workstreams: workstream 'b' is named 'a', which is workstream "
            "'a''s id; rename one") in problems
    before = layout_path(shop).read_bytes()
    refused = run("--root", str(shop), "--actor", "roadmap-review", "policy-set",
                  "roadmap.workstreams", "--value-json", json.dumps(structure), "--apply")
    assert refused.returncode != 0 and "workstream 'b' is named 'a'" in refused.stderr
    assert layout_path(shop).read_bytes() == before                # nothing re-written


def test_a_deliverable_named_like_another_ones_id_is_refused():
    structure = [{"id": "w", "name": "W", "deliverables": [{"id": "d1", "name": "One"}]},
                 {"id": "v", "name": "V", "deliverables": [{"id": "d2", "name": "D1"}]}]
    problems = policy_mod.load({"roadmap": {"workstreams": structure}}).validate()
    assert ("policy.roadmap.workstreams: deliverable 'd2' is named 'D1', which is deliverable "
            "'d1''s id; rename one") in problems


def test_a_name_equal_to_its_own_id_is_allowed():
    structure = [{"id": "docs", "name": "Docs",
                  "deliverables": [{"id": "guide", "name": "GUIDE"}]}]
    assert policy_mod.load({"roadmap": {"workstreams": structure}}).validate() == []
    assert policy_mod.load({"roadmap": {"lanes": ["Core", "core"]}}).validate() == []


CSV_TEXT = ("id,title,status,workstream,deliverable\n"
            "D-1,First,Queued,engine,core\n")
MARKDOWN_TEXT = """# Work
## Active & Remaining Work
| id | title | status | workstream | deliverable |
|----|-------|--------|------------|-------------|
| D-1 | First | Queued | engine | core |
"""


@pytest.mark.parametrize("kind", ["csv", "markdown", "xlsx", "snapshot"])
def test_deliverable_is_a_canonical_field_in_every_provider(kind, tmp_path):
    if kind == "markdown":
        target = tmp_path / "register.md"
        target.write_text(MARKDOWN_TEXT, encoding="utf-8")
        provider = MarkdownWorkRegister(source=str(target))
    elif kind == "xlsx":
        if not dependency_available()[0]:
            pytest.skip("openpyxl is not installed")
        from openpyxl import Workbook
        workbook = Workbook()
        workbook.active.append(["id", "title", "status", "workstream", "deliverable"])
        workbook.active.append(["D-1", "First", "Queued", "engine", "core"])
        target = tmp_path / "register.xlsx"
        workbook.save(target)
        provider = XlsxWorkRegister(source=str(target))
    else:
        target = tmp_path / "register.csv"
        target.write_text(CSV_TEXT, encoding="utf-8")
        provider = CsvWorkRegister(source=str(target))
        if kind == "snapshot":
            cache = tmp_path / "snapshot.json"
            snapshot_provider.write_snapshot(str(cache), provider.snapshot())
            provider = snapshot_provider.SnapshotWorkRegister(source=str(cache))
    snap = provider.snapshot()
    item = snap.items[0]
    assert (item.workstream, item.deliverable) == ("engine", "core")
    assert {"workstream", "deliverable"} <= set(snap.fields)
