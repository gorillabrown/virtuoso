"""Workstreams and deliverables: the review proposes, the owner approves (1.15.0).

``structure --propose`` reads the active items and proposes; it writes nothing.
``structure --apply`` writes an approved structure: policy, then the register, and it
stops before any write when the register has no column to hold the fields.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT, snapshot_tree
from test_workstreams import PREFLIGHT, layout_path, role_path, run, set_policy

SKILL = Path(PLUGIN_ROOT) / "skills" / "roadmap-review" / "SKILL.md"

HEADER = "Id,Title,Seq,Status,Written,Prerequisites,Effort,Workstream,Deliverable,Group\n"
# Seven active items in two clusters, joined only by the weak share of src/engine/tick.py.
ROWS = (
    "A-1,Core,1,Queued,Full Spec,,M,,,\n"
    "A-2,Tick,2,Queued,Full Spec,,S,,,\n"
    "A-3,Saves,3,Queued,Full Spec,A-2,S,,,\n"
    "A-4,Save slots,4,Queued,Full Spec,A-3,S,,,\n"
    "B-1,Menu,5,Queued,Full Spec,,M,,,\n"
    "B-2,Theme,6,Queued,Full Spec,,S,,,\n"
    "B-3,Hud,7,Queued,Full Spec,B-2,S,,,\n"
    "D-1,Old engine,0,Done,Full Spec,,S,,,\n"
)
FILES = {
    "A-1": ["src/engine/core.py", "src/engine/tick.py"],
    "A-2": ["src/engine/core.py", "src/engine/tick.py"],
    "A-3": ["src/engine/save.py"],
    "A-4": ["src/engine/save.py"],
    "B-1": ["src/ui/menu.py", "src/ui/theme.py", "src/ui/config.py"],
    "B-2": ["src/ui/menu.py", "src/ui/theme.py"],
    "B-3": ["src/ui/hud.py", "src/engine/tick.py"],
    "D-1": ["src/engine/core.py"],
}


def roadmap(files: dict) -> str:
    out = ["# Game — Roadmap", "", "## Active & Remaining Work", ""]
    for item_id, paths in files.items():
        out += ["#### %s — %s" % (item_id, item_id), "##### Implementation detail"]
        if paths:
            out.append("- **Edit sites:** " + ", ".join("`%s`" % p for p in paths))
        out.append("")
    return "\n".join(out)


def make(root, rows=ROWS, header=HEADER, files=FILES):
    created = run("--root", str(root), "--mode", "create", "--authorize", cli=PREFLIGHT)
    assert created.returncode == 0, created.stdout + created.stderr
    role_path(root, "workRegister").write_text(header + rows, encoding="utf-8", newline="\n")
    role_path(root, "roadmap").write_text(roadmap(files), encoding="utf-8", newline="\n")
    return root


@pytest.fixture
def game(project):
    return make(project)


def propose(root) -> dict:
    completed = run("--root", str(root), "structure", "--propose", "--json")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return json.loads(completed.stdout)


def apply(root, approved, actor="roadmap-review"):
    path = Path(str(root) + "-approved.json")
    path.write_text(approved if isinstance(approved, str) else json.dumps(approved),
                    encoding="utf-8")
    return run("--root", str(root), "--actor", actor, "structure", "--apply", "--file",
               str(path), "--json")


def register_rows(root) -> dict:
    with open(role_path(root, "workRegister"), encoding="utf-8", newline="") as handle:
        return {row["Id"]: row for row in csv.DictReader(handle)}


def policy_of(root) -> dict:
    return json.loads(layout_path(root).read_text(encoding="utf-8")).get("policy", {})


def clusters(result) -> list:
    return [w["items"] for w in result["workstreams"]]


APPROVED = {"workstreams": [
    {"id": "eng", "name": "Engine", "purpose": "the simulation",
     "deliverables": [{"id": "core", "name": "Core loop", "purpose": "tick and core"},
                      {"id": "saves", "name": "Saves", "purpose": "save files"}]},
    {"id": "ui", "name": "Interface", "purpose": "what the player sees",
     "deliverables": [{"id": "menus", "name": "Menus", "purpose": "menus and HUD"}]}]}


# --- Frame 1: a first proposal ----------------------------------------------------------

def test_a_first_proposal_clusters_by_shared_files_and_prerequisites(game):
    result = propose(game)
    assert result["mode"] == "first"
    assert clusters(result) == [["A-1", "A-2", "A-3", "A-4"], ["B-1", "B-2", "B-3"]]
    engine, ui = result["workstreams"]
    # Deliverables inside a workstream: joined by prerequisite chains.
    assert [d["items"] for d in engine["deliverables"]] == [["A-1"], ["A-2", "A-3", "A-4"]]
    assert [d["items"] for d in ui["deliverables"]] == [["B-1"], ["B-2", "B-3"]]
    assert "prerequisite: A-2 before A-3" in engine["signals"]
    assert any("src/ui/menu.py" in s for s in ui["signals"])
    assert result["provenance"]["source"].endswith(".csv")


def test_the_proposal_names_crossings_as_hints(game):
    assert propose(game)["crossings"] == [
        {"between": ["W1", "W2"], "files": ["src/engine/tick.py"], "prerequisites": []}]


def test_propose_writes_nothing(game):
    before = snapshot_tree(str(game))
    propose(game)
    assert snapshot_tree(str(game)) == before


def test_a_proposal_is_reproducible(game):
    first, second = propose(game), propose(game)
    for result in (first, second):
        result["provenance"].pop("takenAt")             # the read time, not the proposal
    assert first == second


def test_items_without_signals_are_named(project):
    files = dict(FILES, **{"C-1": [], "C-2": []})
    root = make(project, rows=ROWS + "C-1,Loose,8,Queued,Full Spec,,S,,,\n"
                                     "C-2,Looser,9,Queued,Full Spec,,S,,,\n", files=files)
    result = propose(root)
    loose = [w for w in result["workstreams"] if w["noSignal"]]
    assert [w["items"] for w in loose] == [["C-1"], ["C-2"]]      # never merged together
    assert not any(w["noSignal"] for w in result["workstreams"] if w not in loose)


def test_an_unreadable_specification_is_named_not_fatal(project):
    files = {k: v for k, v in FILES.items() if k != "B-2"}         # no heading for B-2
    result = propose(make(project, files=files))
    assert result["unread"] == [{"item": "B-2", "why": result["unread"][0]["why"]}]
    assert "B-2" in result["unread"][0]["why"]


def test_a_chunk_row_in_the_roadmap_is_a_grouping(project):
    root = make(project)
    path = role_path(root, "roadmap")
    path.write_text(path.read_text(encoding="utf-8")
                    + "\n| Chunk | Items |\n|---|---|\n| E1 — Engine | A-1, A-2 |\n",
                    encoding="utf-8")
    engine = propose(root)["workstreams"][0]
    assert [d["items"] for d in engine["deliverables"]] == [["A-1", "A-2", "A-3", "A-4"]]
    assert "grouping: E1 — Engine" in engine["signals"]


# --- Frame 2: a later proposal ----------------------------------------------------------

def assigned_rows(extra=""):
    rows = ROWS
    for item_id, w, d in (("A-1", "eng", "core"), ("A-2", "eng", "core"),
                          ("A-3", "eng", "saves"), ("B-1", "ui", "menus"),
                          ("B-2", "ui", "menus"), ("B-3", "ui", "menus")):
        rows = re.sub(r"^(%s,[^\n]*?),,,$" % item_id, r"\1,%s,%s," % (w, d), rows,
                      flags=re.M)
    return rows + extra


def test_a_later_proposal_places_only_new_items(project):
    root = make(project, rows=assigned_rows())
    set_policy(root, roadmap={"workstreams": APPROVED["workstreams"]})
    result = propose(root)
    assert result["mode"] == "later"
    assert [p["item"] for p in result["placements"]] == ["A-4"]       # only the new one
    placement = result["placements"][0]
    assert (placement["workstream"], placement["deliverable"]) == ("eng", "saves")
    assert any("src/engine/save.py" in why for why in placement["why"])
    assert "prerequisite: A-3 before A-4" in placement["why"]
    assert result["splits"] == [] and result["stale"] == []


def menus(count: int, tmp_path, name: str):
    """A project whose ``menus`` deliverable holds B-1..B-3 and ``count - 3`` more."""
    extra = "".join("M-%d,Menu %d,%d,Queued,Full Spec,,S,ui,menus,\n" % (n, n, 20 + n)
                    for n in range(count - 3))
    files = dict(FILES, **{"M-%d" % n: ["src/ui/m%d.py" % n] for n in range(count - 3)})
    root = tmp_path / name
    root.mkdir()
    make(root, rows=assigned_rows(extra), files=files)
    set_policy(root, roadmap={"workstreams": APPROVED["workstreams"]})
    return root


def test_a_large_deliverable_is_proposed_for_a_split(tmp_path):
    assert propose(menus(8, tmp_path, "eight"))["splits"] == []        # 8: not over 8
    splits = propose(menus(9, tmp_path, "nine"))["splits"]
    assert [s["deliverable"] for s in splits] == ["menus"]
    assert len(splits[0]["items"]) == 9
    assert ["B-2", "B-3"] in splits[0]["parts"]                     # the prerequisite chain


def test_two_deliverables_sharing_most_files_are_proposed_for_a_merge(project):
    files = dict(FILES, **{"A-3": ["src/engine/core.py", "src/engine/tick.py"]})
    root = make(project, rows=assigned_rows(), files=files)
    set_policy(root, roadmap={"workstreams": APPROVED["workstreams"]})
    assert propose(root)["merges"] == [
        {"deliverables": ["core", "saves"],
         "files": ["src/engine/core.py", "src/engine/tick.py"]}]


# --- Frame 3: the register has no column for the fields ---------------------------------

NO_COLUMNS = "Id,Title,Seq,Status,Written,Prerequisites,Effort,Group\n"


def test_apply_stops_naming_missing_register_columns(project):
    rows = "".join(",".join(r.split(",")[:7] + [""]) + "\n"
                   for r in ROWS.strip().split("\n"))
    root = make(project, rows=rows, header=NO_COLUMNS)
    before = snapshot_tree(str(root))
    completed = apply(root, dict(APPROVED, assignments={
        "A-1": {"workstream": "eng", "deliverable": "core"}}))
    assert completed.returncode == 1, completed.stdout + completed.stderr
    result = json.loads(completed.stdout)
    assert result["applied"] is False
    assert result["missing"] == ["workstream", "deliverable"]
    assert snapshot_tree(str(root)) == before                # no policy, no register write


def test_propose_reports_the_register_can_hold_a_structure(game):
    assert propose(game)["registerColumns"] == {"ready": True, "missing": []}


def test_propose_reports_missing_register_columns_and_writes_nothing(project):
    rows = "".join(",".join(r.split(",")[:7] + [""]) + "\n"
                   for r in ROWS.strip().split("\n"))
    root = make(project, rows=rows, header=NO_COLUMNS)
    before = snapshot_tree(str(root))
    columns = propose(root)["registerColumns"]
    assert columns["ready"] is False
    assert columns["missing"] == ["workstream", "deliverable"]
    assert "workstream" in columns["fix"]
    assert snapshot_tree(str(root)) == before


def test_the_review_checks_the_register_columns_before_asking():
    text = SKILL.read_text(encoding="utf-8")
    c2 = " ".join(text[text.index("### C.2"):text.index("### C.3")].split())
    assert "registerColumns" in c2
    assert c2.index("registerColumns") < c2.index("approve, rename or reject")
    assert "Adding the workstream and deliverable columns" in c2
    contract = (Path(PLUGIN_ROOT) / "references" / "registry-contract.md").read_text(
        encoding="utf-8")
    assert "**Adding the workstream and deliverable columns.**" in contract


# --- Frame 4: apply, after approval -----------------------------------------------------

def test_apply_writes_policy_then_the_register(game):
    completed = apply(game, dict(APPROVED, assignments={
        "A-1": {"workstream": "eng", "deliverable": "core"},
        "B-3": {"workstream": "ui", "deliverable": "menus"}}))
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout)
    assert result["written"] == ["A-1", "B-3"] and result["plans"] == []
    assert policy_of(game)["roadmap"]["workstreams"] == APPROVED["workstreams"]
    assert policy_of(game)["roadmap"]["hierarchy"] == ["workstream", "deliverable"]
    assert all(p["backup"] for p in result["policy"])
    rows = register_rows(game)
    assert (rows["A-1"]["Workstream"], rows["A-1"]["Deliverable"]) == ("eng", "core")
    assert (rows["B-3"]["Workstream"], rows["B-3"]["Deliverable"]) == ("ui", "menus")
    assert rows["A-2"]["Workstream"] == ""                     # not in the approved file
    # Applying the same file again writes no register row: an item already holding the
    # approved values is not written.
    register = role_path(game, "workRegister").read_bytes()
    again = json.loads(apply(game, dict(APPROVED, assignments={
        "A-1": {"workstream": "eng", "deliverable": "core"}})).stdout)
    assert again["written"] == [] and role_path(game, "workRegister").read_bytes() == register


def test_a_rejected_proposal_writes_nothing(game):
    before = snapshot_tree(str(game))
    completed = apply(game, "")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(completed.stdout)["applied"] is False
    assert snapshot_tree(str(game)) == before


def test_only_active_items_are_assigned(game):
    completed = apply(game, dict(APPROVED, assignments={
        "D-1": {"workstream": "eng", "deliverable": "core"},
        "A-2": {"workstream": "eng", "deliverable": "core"}}))
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout)
    assert result["written"] == ["A-2"]
    assert [u["item"] for u in result["untouched"]] == ["D-1"]
    assert register_rows(game)["D-1"]["Workstream"] == ""


def test_an_assignment_outside_the_approved_structure_is_refused(game):
    before = snapshot_tree(str(game))
    completed = apply(game, dict(APPROVED, assignments={
        "A-1": {"workstream": "ui", "deliverable": "core"}}))
    assert completed.returncode == 1
    assert "not under workstream" in json.loads(completed.stdout)["problems"][0]
    assert snapshot_tree(str(game)) == before


@pytest.fixture
def notion(project):
    """An external register served by a snapshot that carries both columns."""
    (project / "Virtuoso").mkdir()
    (project / "Virtuoso" / "snap.json").write_text(json.dumps({
        "snapshotVersion": 1, "takenAt": "2099-01-01T00:00:00Z", "provider": "connector",
        "source": "notion:database/1", "fields": ["id", "status", "workstream",
                                                 "deliverable", "revision"],
        "items": [{"id": "N-1", "title": "One", "status": "queued", "raw_status": "Queued",
                   "revision": "rev-1"},
                  {"id": "N-2", "title": "Two", "status": "completed",
                   "raw_status": "Done", "revision": "rev-2"}]}), encoding="utf-8")
    manifest = {
        "schemaVersion": 2,
        "roles": {
            "workRegister": {"external": "notion:database/1", "provider": "connector",
                             "authority": "live", "mutability": "read-write",
                             "allowedWriters": ["roadmap-review"],
                             "validation": "external", "classification": "active",
                             "origin": "authored"},
            "workRegisterSnapshot": {"path": "Virtuoso/snap.json", "provider": "snapshot",
                                     "authority": "report", "mutability": "generated",
                                     "validation": "exists", "classification": "active",
                                     "origin": "generated"},
        },
        "policy": {"workRegister": {"snapshot": "workRegisterSnapshot"}},
    }
    layout_path(project).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return project


def test_apply_plans_set_status_for_an_external_register(notion):
    completed = apply(notion, dict(APPROVED, assignments={
        "N-1": {"workstream": "eng", "deliverable": "core"},
        "N-2": {"workstream": "eng", "deliverable": "core"}}))
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout)
    assert result["written"] == []
    assert [(p["operation"], p["itemId"], p["fields"]) for p in result["plans"]] == [
        ("set-status", "N-1", {"workstream": "eng", "deliverable": "core"})]
    assert [u["item"] for u in result["untouched"]] == ["N-2"]
    assert policy_of(notion)["roadmap"]["workstreams"] == APPROVED["workstreams"]


def test_an_external_mapping_without_the_fields_stops_before_policy(notion):
    set_policy(notion, workRegister={"fieldMappings": {"id": "ID", "status": "Status"}})
    before = snapshot_tree(str(notion))
    completed = apply(notion, dict(APPROVED, assignments={
        "N-1": {"workstream": "eng", "deliverable": "core"}}))
    assert completed.returncode == 1, completed.stdout + completed.stderr
    assert json.loads(completed.stdout)["missing"] == ["workstream", "deliverable"]
    assert snapshot_tree(str(notion)) == before


def test_assignments_to_finished_items_still_need_the_columns(project):
    rows = "".join(",".join(r.split(",")[:7] + [""]) + "\n"
                   for r in ROWS.strip().split("\n"))
    root = make(project, rows=rows, header=NO_COLUMNS)
    before = snapshot_tree(str(root))
    completed = apply(root, dict(APPROVED, assignments={
        "D-1": {"workstream": "eng", "deliverable": "core"}}))
    assert completed.returncode == 1
    assert snapshot_tree(str(root)) == before


@pytest.mark.parametrize("kind", ["csv", "markdown", "xlsx"])
def test_assign_on_each_local_provider(kind, tmp_path):
    from test_workstreams import CSV_TEXT, MARKDOWN_TEXT
    from tools.governance.errors import CapabilityError, ConcurrencyError
    from tools.governance.providers.csv_provider import CsvWorkRegister
    from tools.governance.providers.markdown_provider import MarkdownWorkRegister
    from tools.governance.providers.xlsx_provider import XlsxWorkRegister, dependency_available

    def build(name, with_columns=True):
        if kind == "markdown":
            text = MARKDOWN_TEXT if with_columns else (
                "# Work\n## Active & Remaining Work\n| id | title | status |\n"
                "|----|-------|--------|\n| D-1 | First | Queued |\n")
            target = tmp_path / (name + ".md")
            target.write_text(text, encoding="utf-8")
            return MarkdownWorkRegister(source=str(target)), target
        if kind == "xlsx":
            if not dependency_available()[0]:
                pytest.skip("openpyxl is not installed")
            from openpyxl import Workbook
            workbook = Workbook()
            head = ["id", "title", "status"] + (["workstream", "deliverable"]
                                                if with_columns else [])
            workbook.active.append(head)
            workbook.active.append(["D-1", "First", "Queued"]
                                   + (["engine", "core"] if with_columns else []))
            target = tmp_path / (name + ".xlsx")
            workbook.save(target)
            return XlsxWorkRegister(source=str(target)), target
        lines = CSV_TEXT.splitlines(keepends=True)
        if not with_columns:
            lines = [",".join(c for c in l.rstrip("\n").split(",")[:3]) + "\n" for l in lines]
        target = tmp_path / (name + ".csv")
        target.write_text("".join(lines), encoding="utf-8")
        return CsvWorkRegister(source=str(target)), target

    provider, target = build("with")
    item = provider.get("D-1")
    after = provider.assign("D-1", "ui", "menus", revision=item.revision)
    assert (after.workstream, after.deliverable) == ("ui", "menus")
    written = target.read_bytes()
    provider.assign("D-1", "ui", "menus", revision=after.revision)       # idempotent
    assert target.read_bytes() == written
    with pytest.raises(ConcurrencyError):
        provider.assign("D-1", "eng", "core", revision=item.revision)    # a stale read
    bare, bare_target = build("without", with_columns=False)
    untouched = bare_target.read_bytes()
    with pytest.raises(CapabilityError):
        bare.assign("D-1", "ui", "menus")
    assert bare_target.read_bytes() == untouched


# --- The review asks before writing -----------------------------------------------------

def test_the_review_asks_before_writing_structure():
    text = SKILL.read_text(encoding="utf-8")
    c2 = text[text.index("### C.2"):text.index("### C.3")]
    assert "structure --propose" in c2 and "structure --apply" in c2
    assert "approve, rename or reject" in c2
    assert "Nothing is written before the owner approves." in " ".join(c2.split())
