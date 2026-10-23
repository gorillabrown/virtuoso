"""The interactive roadmap board (design: docs/superpowers/specs/2026-09-24-...).

One generated page with Dashboard, Roadmap and Completed tabs, registered as the
``board`` role. These tests read the model the generator embeds, and the page itself.
"""
from __future__ import annotations

import csv
import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT
from test_tooling import (  # noqa: F401 - fixtures are used by name
    COCKPIT, PREFLIGHT, REGISTRY_CLI, external_workspace, run, workspace)
from tools.governance import registry as registry_mod, schema
from tools.governance.policy import Policy
from tools.governance.providers import base, kpi, mapping
from tools.governance.providers.csv_provider import CsvWorkRegister
from tools.governance.providers.ledger import LedgerRecord
from tools.roadmap_visualizer import board, comments, completed, dashboard, generate
from tools.roadmap_visualizer.board_render import render_board

STATUSES = mapping.StatusMapping()
SKILLS = Path(PLUGIN_ROOT) / "skills"

BOARD_CLI = str(Path(PLUGIN_ROOT) / "scripts" / "generate_board.py")
REGISTER = Path("Project Documentation") / "2 operational" / "work-register.csv"

#: A register laid out like the design's reference board, with generic data.
REFERENCE_HEADERS = ["Item", "Seq", "Lane", "Impl Status", "Written", "Description",
                     "Depends On", "Sprint Code", "Branch", "Repo Spec", "Notes", "LOE",
                     "Points", "Phase", "Stage"]
REFERENCE_ROWS = [
    ["ENG-1 — Build the engine", "20", "ENGINE", "Queued", "Full Spec", "First part", "",
     "ENG-1", "eng-1", "docs/eng-1.md", "", "M", "3", "Phase 1", "Build"],
    ["GOV-2 — Write the rules", "1,000", "GOV", "In Flight", "Stub", "Second part", "ENG-1",
     "GOV-2", "", "", "a note", "S", "1", "Phase 1", "Plan"],
    ["ENG-3 — Ship it", "25", "ENGINE", "Blocked", "Stub", "", "ENG-1, GOV-2",
     "ENG-3", "", "", "", "L", "5", "Phase 2", "Build"],
    ["ENG-0 — Old work", "10", "ENGINE", "Done", "Full Spec", "", "", "ENG-0", "", "", "",
     "S", "2", "Phase 1", "Build"],
]


def write_csv(path: Path, headers, rows) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def reference_snapshot(tmp_path) -> base.Snapshot:
    path = tmp_path / "reference.csv"
    write_csv(path, REFERENCE_HEADERS, REFERENCE_ROWS)
    return CsvWorkRegister(source=str(path), mapping=mapping.Mapping()).snapshot()


def item(id_, status=base.QUEUED, sequence=None, **fields) -> base.WorkItem:
    return base.WorkItem(id=id_, status=status, sequence=sequence, **fields)


def embedded(html: str) -> dict:
    match = re.search(r'<script id="board-data" type="application/json">(.*?)</script>',
                      html, re.S)
    assert match, "the board did not embed its model"
    return json.loads(match.group(1))


@pytest.fixture
def reference_workspace(workspace):  # noqa: F811
    """The tooling workspace, its register replaced by the reference layout."""
    write_csv(workspace / REGISTER, REFERENCE_HEADERS, REFERENCE_ROWS)
    return workspace


def git_init(root: Path) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True)


# --- D1: the role, creation, the ignore line, the protected guard ------------------


def test_the_board_role_and_its_comments_role_are_declared():
    for name, path in ((board.BOARD_ROLE, board.DEFAULT_PATH),
                       (board.COMMENTS_ROLE, board.COMMENTS_PATH)):
        spec = schema.RoleSpec.from_manifest(name, dict(schema.default_role(name), path=path))
        assert spec.authority in schema.AUTHORITIES and spec.provider in schema.PROVIDERS
        assert name not in schema.CREATE_ROLE_ORDER     # opt-in: the first review adds it
    assert schema.default_role(board.BOARD_ROLE)["mutability"] == "generated"
    assert board.DEFAULT_PATH == "roadmap-board.html"


def test_the_review_creates_the_board(workspace):  # noqa: F811
    assert board.BOARD_ROLE not in registry_mod.load(str(workspace)).roles
    completed = run(BOARD_CLI, "--root", str(workspace), "--create")
    assert completed.returncode == 0, completed.stderr
    assert "board roles registered: board, boardComments" in completed.stdout
    assert "board created: " in completed.stdout

    reg = registry_mod.load(str(workspace))
    assert reg.roles[board.BOARD_ROLE].path == board.DEFAULT_PATH
    assert reg.roles[board.COMMENTS_ROLE].path == board.COMMENTS_PATH
    assert not [f for f in reg.findings if f.severity == "error"]
    assert (workspace / board.DEFAULT_PATH).is_file()
    readme = (workspace / schema.README_RELPATH).read_text(encoding="utf-8")
    board_line = next(line for line in readme.splitlines()
                      if line.startswith("| Roadmap board (generated page)"))
    assert board_line.rstrip().endswith("| present |")              # the readme sees the page

    again = run(BOARD_CLI, "--root", str(workspace), "--create")
    assert again.returncode == 0, again.stderr
    assert "registered" not in again.stdout and "board regenerated: " in again.stdout


def test_the_board_page_is_ignored_once(workspace):  # noqa: F811
    git_init(workspace)
    lines = generate.ensure_board(workspace)
    assert "gitignore: added /roadmap-board.html" in lines
    gitignore = (workspace / ".gitignore").read_text(encoding="utf-8")
    assert gitignore.splitlines().count("/roadmap-board.html") == 1
    check = subprocess.run(["git", "-C", str(workspace), "check-ignore", "-q",
                            board.DEFAULT_PATH])
    assert check.returncode == 0

    (workspace / board.DEFAULT_PATH).unlink()              # created again: already ignored
    lines = generate.ensure_board(workspace)
    assert any(line.startswith("gitignore: skipped") for line in lines)
    assert (workspace / ".gitignore").read_text(encoding="utf-8") == gitignore


def test_the_board_page_is_ignored_only_in_a_git_repository(workspace):  # noqa: F811
    if subprocess.run(["git", "-C", str(workspace), "rev-parse"],
                      capture_output=True).returncode == 0:
        pytest.skip("the temporary directory sits inside a git repository")
    gitignore = workspace / ".gitignore"
    before = gitignore.read_bytes() if gitignore.exists() else None
    lines = generate.ensure_board(workspace)
    assert "gitignore: skipped (not a git repository)" in lines
    assert (gitignore.read_bytes() if gitignore.exists() else None) == before


def test_the_board_refuses_a_protected_path(workspace):  # noqa: F811
    generate.ensure_board(workspace)
    for target in (schema.MANIFEST_RELPATH, str(REGISTER), board.COMMENTS_PATH):
        before = (workspace / target).read_bytes() if (workspace / target).exists() else None
        with pytest.raises(ValueError, match="refusing to overwrite"):
            generate.generate_board(workspace, target)
        after = (workspace / target).read_bytes() if (workspace / target).exists() else None
        assert after == before


# --- D2: the Roadmap tab -----------------------------------------------------------


def test_the_roadmap_tab_groups_live_work_by_pipeline_state():
    items = [item("A-3", base.QUEUED, 30), item("A-1", base.QUEUED, 10),
             item("A-9", base.UNKNOWN, None, raw_status="Parked"),
             item("A-2", base.IN_FLIGHT, 20), item("A-5", base.COMPLETED, 5),
             item("A-6", base.SUPERSEDED, 6), item("A-0", base.QUEUED, 10)]
    groups = board.roadmap_groups(items)
    assert [(g["key"], g["title"]) for g in groups] == [("in-flight", "In Flight"),
                                                        ("conveyor", "Conveyor")]
    assert groups[1]["ids"] == ["A-0", "A-1", "A-3", "A-9"]      # Seq, then id; unsequenced last
    assert "A-5" not in sum((g["ids"] for g in groups), [])      # terminal items leave the tab
    assert board.row(items[2])["warn"] and not board.row(items[0])["warn"]
    blocked = board.roadmap_groups(items + [item("A-7", base.BLOCKED, 7)])
    assert [g["title"] for g in blocked] == ["In Flight", "Conveyor", "Blocked / Gated"]


def test_the_roadmap_tab_columns_follow_the_register(tmp_path):
    snap = reference_snapshot(tmp_path)
    name_key = board.name_column(snap.items)
    columns = board.roadmap_columns(snap.fields, snap.headers, snap.items, name_key)
    assert [c["header"] for c in columns] == [
        "Seq", "Lane", "Impl Status", "Written", "Description", "Depends On", "Sprint Code",
        "Branch", "Repo Spec", "Notes", "LOE", "Phase", "Points", "Stage"]

    tiers = {i.id: i.sequence for i in snap.items}
    assert tiers["GOV-2"] == 1000 and tiers["ENG-1"] == 20    # "1,000" is a backlog tier
    assert board.roadmap_groups(snap.items)[0]["ids"] == ["GOV-2"]

    lean = [item("A-1", title="One"), item("A-2", title="Two")]
    columns = board.roadmap_columns(["id", "title", "status"], {}, lean)
    assert [c["key"] for c in columns] == ["status"]       # only what the register carries


def test_unmapped_columns_are_kept(tmp_path):
    snap = reference_snapshot(tmp_path)
    name_key = board.name_column(snap.items)
    columns = board.roadmap_columns(snap.fields, snap.headers, snap.items, name_key)
    keys = [c["key"] for c in columns]
    assert keys[-2:] == ["extra:Points", "extra:Stage"]   # after the mapped ones
    every_header = set(REFERENCE_HEADERS) - {"Item"}       # Item is the frozen name column
    assert every_header == {c["header"] for c in columns}
    assert {c["key"]: c["kind"] for c in columns}["extra:Points"] == "number"


# --- D3: the reference board's four mapping cases ----------------------------------


@pytest.mark.parametrize("case", ["item-holds-id-and-title", "lane-vs-stage",
                                  "loe-vs-points", "impl-status-and-written"])
def test_reference_mapping(case, tmp_path):
    snap = reference_snapshot(tmp_path)
    first = next(i for i in snap.items if i.id == "ENG-1")
    if case == "item-holds-id-and-title":
        assert snap.headers["id"] == "Sprint Code" and first.title == ""
        assert first.extra["Item"] == "ENG-1 — Build the engine"
        assert board.name_column(snap.items) == "Item"
        assert board.display_name(first, "Item") == "ENG-1 — Build the engine"
    elif case == "lane-vs-stage":
        assert snap.headers["workstream"] == "Lane" and first.workstream == "ENGINE"
        assert first.extra["Stage"] == "Build"
    elif case == "loe-vs-points":
        assert snap.headers["effort"] == "LOE" and first.effort == "M"
        assert first.extra["Points"] == "3"
    else:
        assert "impl status" in mapping.DEFAULT_ALIASES["status"]
        assert "written" in mapping.DEFAULT_ALIASES["written_status"]
        assert snap.headers["status"] == "Impl Status" and first.status == base.QUEUED
        assert snap.headers["written_status"] == "Written"
        assert first.written_status == base.FULL_SPEC


def test_a_mapped_column_shows_the_projects_own_header(external_workspace):
    """A snapshot import records no headers; the project's fieldMappings name them."""
    manifest = external_workspace / schema.MANIFEST_RELPATH
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["policy"]["workRegister"]["fieldMappings"] = {"status": "Impl Status"}
    manifest.write_text(json.dumps(data), encoding="utf-8")
    model = generate.build_board(generate.read(external_workspace))
    assert {c["key"]: c["header"] for c in model["columns"]}["status"] == "Impl Status"


def test_register_headers_survive_a_snapshot_file(tmp_path):
    from tools.governance.providers import snapshot_provider
    snap = reference_snapshot(tmp_path)
    path = tmp_path / "snap.json"
    snapshot_provider.write_snapshot(str(path), snap)
    again = snapshot_provider.SnapshotWorkRegister(source=str(path)).snapshot()
    assert again.headers == snap.headers


# --- D9: copy text -----------------------------------------------------------------


def test_copy_text():
    plain = item("SK-01", title="Deadline support", spec_link="docs/sk-01.md", branch="sk-01")
    assert board.copy_text(plain) == "SK-01 — Deadline support"
    assert board.copy_text(plain, dispatch=True) == ("SK-01 — Deadline support\n"
                                                     "Spec: docs/sk-01.md\nBranch: sk-01")
    named = item("SK-02", title="SK-02 — Already named")
    assert board.copy_text(named) == "SK-02 — Already named"
    item_only = item("SK-03", extra={"Item": "SK-03 — From the item column"})
    assert board.copy_text(item_only, "Item") == "SK-03 — From the item column"
    assert board.copy_text(item_only, "Item", dispatch=True) == "SK-03 — From the item column"
    bare = item("SK-04")
    assert board.copy_text(bare) == "SK-04"
    model_row = board.row(plain)
    assert model_row["copy"] == board.copy_text(plain)
    assert model_row["copyDispatch"] == board.copy_text(plain, dispatch=True)


# --- D10: rendering and safety -----------------------------------------------------


def test_the_board_is_self_contained(reference_workspace):
    generate.ensure_board(reference_workspace)
    page = (reference_workspace / board.DEFAULT_PATH).read_text(encoding="utf-8")
    remote = re.findall(r'<(?:script|link|img|style|source)\b[^>]*\b(?:src|href)\s*=\s*'
                        r'["\']?\s*(?:https?:|//)', page, re.I)
    assert remote == []
    style = page.split("<style>", 1)[1].split("</style>", 1)[0]
    assert "@import" not in style and "url(" not in style.lower()   # no remote font or image
    assert "<script src" not in page and "<link" not in page
    model = embedded(page)
    assert {r["id"] for r in model["rows"]} == {"ENG-0", "ENG-1", "ENG-3", "GOV-2"}


def test_embedded_json_is_escaped():
    hostile = item("X-1", title="</script><script>alert(1)</script>",
                   notes="<!--<script> &   -->", description="<!--<script>")
    model = {"project": "</title>p", "rows": [board.row(hostile)], "columns": [],
             "roadmap": {"groups": board.roadmap_groups([hostile])}}
    page = render_board(model)
    payload = page.split('<script id="board-data" type="application/json">', 1)[1]
    payload = payload.split("</script>", 1)[0]
    assert "<" not in payload and ">" not in payload    # not even "<!--<script>"
    assert embedded(page)["rows"][0]["values"]["notes"] == "<!--<script> &   -->"
    assert embedded(page)["rows"][0]["name"] == "X-1 — </script><script>alert(1)</script>"
    assert "<title>&lt;/title&gt;p" in page
    assert ".innerHTML" not in page


def test_the_board_has_dark_mode():
    page = render_board({"project": "p", "rows": [], "columns": [], "roadmap": {"groups": []}})
    style = page.split("<style>", 1)[1].split("</style>", 1)[0]
    assert "@media (prefers-color-scheme: dark)" in style
    assert ':root[data-theme="dark"]' in style
    rules = re.sub(r"--[\w-]+\s*:\s*[^;]+;", "", style)        # drop the declarations
    hard = re.findall(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|(?<![-\w])(?:white|black)(?![-\w])",
                      rules)
    assert hard == [], "colours outside custom properties: %s" % hard


# --- D4: the Completed tab ---------------------------------------------------------


def rec(record_id, item_id, day, result="completed", **fields) -> LedgerRecord:
    return LedgerRecord(record_id=record_id, item_id=item_id, completed=day, result=result,
                        **fields)


def by_id(rows) -> dict:
    return {r["id"]: r for r in rows}


def test_the_completed_tab_joins_the_register_with_the_ledger():
    items = [item("C-1", base.COMPLETED, 1, title="One", raw_status="Done", effort="S"),
             item("C-2", base.DISSOLVED, 2, title="Two", notes="superseded by C-9"),
             item("L-1", base.QUEUED, 3, title="Live")]
    records = [rec("TR-1", "C-1", "2026-01-02", evidence="docs/c1.md", effort="m"),
               rec("TR-2", "C-2", "2026-01-05", "dissolved")]
    rows, problems = completed.completed_rows(items, records, STATUSES)
    assert problems == []
    assert [r["id"] for r in rows] == ["C-2", "C-1"]               # newest completion first
    one = by_id(rows)["C-1"]
    assert one["values"]["closeout"] == "docs/c1.md" and one["values"]["completedOn"] == "2026-01-02"
    assert one["values"]["loe"] == "m"                             # the ledger's Effort first
    assert one["unreconciled"] == "" and one["name"] == "C-1 — One"
    assert by_id(rows)["C-2"]["values"]["supersededBy"] == "C-9"
    groups = completed.completed_groups(rows)
    assert [(g["title"], g["ids"]) for g in groups] == [("Completed", ["C-1"]),
                                                        ("Retired", ["C-2"])]


def test_unreconciled_rows_are_marked_on_both_sides():
    items = [item("C-1", base.COMPLETED, 1), item("L-2", base.QUEUED, 2),
             item("C-3", base.COMPLETED, 3)]
    records = [rec("TR-1", "L-2", "2026-01-02"), rec("TR-2", "X-9", "2026-01-03"),
               rec("TR-3", "C-3", "2026-01-04")]
    rows = by_id(completed.completed_rows(items, records, STATUSES)[0])
    assert rows["C-1"]["unreconciled"] == "no ledger record for this item"
    assert rows["L-2"]["unreconciled"] == "the register shows L-2 as queued"
    assert rows["X-9"]["unreconciled"] == "the register has no item X-9"
    assert rows["C-3"]["unreconciled"] == ""
    without = by_id(completed.completed_rows(items, records, STATUSES, ledger=False)[0])
    assert set(without) == {"C-1", "C-3"} and not any(r["unreconciled"] for r in without.values())


def test_a_corrected_record_replaces_the_one_it_corrects():
    items = [item("C-1", base.COMPLETED, 1)]
    records = [rec("TR-1", "C-1", "2026-01-02", effort_estimate="2h", effort_actual="1h"),
               rec("TR-2", "", "2026-01-03", "", corrects="TR-1", effort_actual="3h10m"),
               rec("TR-3", "", "", "", corrects="TR-99"),
               rec("TR-4", "", "2026-01-05")]
    rows, problems = completed.completed_rows(items, records, STATUSES)
    assert [r["id"] for r in rows] == ["C-1"]
    row = rows[0]
    assert row["record"] == "TR-1" and row["corrected"] is True
    assert row["values"]["completedOn"] == "2026-01-03"
    assert row["values"]["estimateActual"] == "2h → 3h10m" and row["over"] is True
    assert [v["record"] for v in row["history"]] == ["TR-1", "TR-2"]
    assert problems == ["ledger record TR-3 corrects TR-99, which is not in the ledger; skipped",
                        "ledger record TR-4 has no item; skipped"]


def test_a_corrected_record_chain_and_earlier_records_stay_visible():
    items = [item("C-1", base.COMPLETED, 1), item("C-2", base.DISSOLVED, 2)]
    records = [rec("TR-1", "C-1", "2026-01-02"),
               rec("TR-2", "", "", "", corrects="TR-1", effort_actual="2h"),
               rec("TR-3", "", "", "", corrects="TR-2", effort_actual="3h"),   # corrects a correction
               rec("TR-4", "C-1", "2026-03-01"),                             # completed again
               rec("TR-5", "C-2", "2026-01-04", "won't fix")]               # a word no vocabulary maps
    rows, problems = completed.completed_rows(items, records, STATUSES)
    assert problems == []
    one, two = by_id(rows)["C-1"], by_id(rows)["C-2"]
    assert one["record"] == "TR-4" and one["earlier"] == 1
    assert [v["record"] for v in one["history"]] == ["TR-1", "TR-2", "TR-3", "TR-4"]
    first = completed.effective_records(records)[0][0]
    assert first["actual"] == "3h" and first["corrected"] is True
    assert two["result"] == base.DISSOLVED and two["retired"] is True


def test_ledger_only_rows_are_sliced_by_the_ledger_result(workspace):  # noqa: F811
    ledger = registry_mod.load(str(workspace)).resolve("terminalLedger")
    with open(ledger, "a", encoding="utf-8") as handle:
        handle.write("| TR-001 | GONE-1 | 2026-01-05 | completed | x.md |  |  |  |  |\n")
    model = generate.build_board(generate.read(workspace))
    row = by_id(model["completed"]["rows"])["GONE-1"]
    assert row["unreconciled"] == "the register has no item GONE-1"
    assert row["facets"]["complete"] == "complete"


def test_estimate_to_actual_uses_durations_and_effort():
    assert completed.over_estimate("2h", "3h10m") is True
    assert completed.over_estimate("90m", "1.5h") is False
    assert completed.over_estimate("S", "M") is False             # sizes are not durations
    assert completed.over_estimate("", "2h") is False
    items = [item("C-1", base.COMPLETED, 1, effort="L"), item("C-2", base.COMPLETED, 2)]
    records = [rec("TR-1", "C-1", "2026-01-02", effort_estimate="2h"),
               rec("TR-2", "C-2", "2026-01-03", effort="xs", effort_actual="1h")]
    rows = by_id(completed.completed_rows(items, records, STATUSES)[0])
    assert rows["C-1"]["values"]["loe"] == "L"                    # register effort, as fallback
    assert rows["C-1"]["values"]["estimateActual"] == "2h → ?"
    assert rows["C-2"]["values"]["loe"] == "xs"


# --- D5: the Dashboard -------------------------------------------------------------


def test_dashboard_tiles_restate_kpi_and_health(workspace):  # noqa: F811
    reading = generate.read(workspace)
    model = generate.build_board(reading)
    tiles = {t["key"]: t for t in model["dashboard"]["tiles"]}
    metrics = {m["name"]: m for m in reading.metrics.as_dict()["metrics"]}
    assert tiles["total"]["value"] == metrics["total-items"]["value"] == 2
    assert tiles["complete"]["value"] == 1 and tiles["incomplete"]["value"] == 1
    assert tiles["percent"]["value"] == metrics["percent-complete-by-count"]["value"]
    assert tiles["blocked"]["value"] == metrics["count-blocked"]["value"]
    assert tiles["buffer"]["value"] == "%d / %d" % (reading.health.buffer_filled,
                                                    reading.health.buffer_target)
    assert tiles["pace"]["value"] == "no deadline"
    provenance = reading.snapshot.provenance()
    for tile in tiles.values():
        assert provenance["provider"] in tile["source"] and provenance["takenAt"] in tile["source"]


def test_slicers_are_built_from_the_data():
    items = [item("A-1", base.QUEUED, 1, workstream="UI", group="G1",
                  extra={"Stage": "Build", "Desc": "a"}),
             item("A-2", base.QUEUED, 2, workstream="ENGINE", group="G1",
                  extra={"Stage": "Plan", "Desc": "b"}),
             item("A-3", base.QUEUED, 3, workstream="UI", group="G1",
                  extra={"Stage": "Build", "Desc": "c"})]
    columns = board.roadmap_columns(["id", "workstream", "group", "status"], {}, items)
    found = {s["key"]: s for s in dashboard.slicers(items, columns, {})}
    assert found["complete"]["values"] == ["complete", "incomplete"]   # always offered
    assert "workstream" in found and found["workstream"]["values"] == ["UI", "ENGINE"]
    assert "group" not in found and "status" not in found        # one value: no slicer
    assert "extra:Stage" in found and "extra:Desc" not in found  # unique per row: no slicer
    blank = items + [item("A-4", base.QUEUED, 4, workstream="")]
    streams = {s["key"]: s for s in dashboard.slicers(blank, columns, {})}["workstream"]
    assert streams["values"] == ["UI", "ENGINE", ""] and streams["labels"][""] == "(none)"
    some = [item("B-1", group="G1"), item("B-2", group="")]
    groups = {s["key"]: s for s in dashboard.slicers(some, [], {})}["group"]
    assert groups["values"] == ["G1", ""]                        # one value and blanks


def test_slicer_order_follows_policy():
    items = [item("A-1", base.BLOCKED, 1, workstream="OPS", effort="L"),
             item("A-2", base.QUEUED, 2, workstream="ENGINE", effort="xs"),
             item("A-3", base.IN_FLIGHT, 3, workstream="UI", effort="M")]
    orders = {"workstream": ["UI", "ENGINE"], "effort": list(kpi.DEFAULT_EFFORT_SCALE),
              "status": list(base.CANONICAL_STATUSES)}
    found = {s["key"]: s["values"] for s in dashboard.slicers(items, [], orders)}
    assert found["workstream"] == ["UI", "ENGINE", "OPS"]         # policy, then first seen
    assert found["effort"] == ["xs", "M", "L"]
    assert found["status"] == ["queued", "in-flight", "blocked"]


# --- workstreams and deliverables ----------------------------------------------------

STRUCTURE = [{"id": "W1", "name": "Engine", "deliverables": [
                 {"id": "D1", "name": "Core"},
                 {"id": "D2", "name": "A very long deliverable name"}]},
             {"id": "W2", "name": "Docs", "deliverables": [{"id": "D3", "name": "Guide"}]}]
WITHOUT_STRUCTURE = Path(__file__).parent / "fixtures" / "board.without-structure.expected.json"
TIME_KEYS = ("generatedAt", "takenAt", "asOf", "mtime")
_STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?")


def comparable(model, root):
    """The model without its date- and time-valued fields; the workspace path reads
    ``<root>``, the register's ``<register>``, and every separator ``/``, so the comparison
    holds on any machine and the stored copy names no project's directory."""
    forms = (Path(root).as_uri(), str(root).replace("\\", "/"))
    register = REGISTER.as_posix()

    def strip(value):
        if isinstance(value, dict):
            return {k: strip(v) for k, v in value.items() if k not in TIME_KEYS}
        if isinstance(value, list):
            return [strip(v) for v in value]
        if isinstance(value, str):
            value = value.replace("\\", "/")
            for form in forms:
                value = value.replace(form, "<root>")
            value = value.replace(register, "<register>")
            return _STAMP.sub("<time>", value)
        return value
    return strip(model)


def approve(root: Path, workstreams) -> None:
    layout = root / "Virtuoso" / "workspace-layout.json"
    data = json.loads(layout.read_text(encoding="utf-8"))
    data.setdefault("policy", {}).setdefault("roadmap", {})["workstreams"] = workstreams
    layout.write_text(json.dumps(data, indent=2), encoding="utf-8")


def test_the_board_filters_by_workstream_and_deliverable():
    policy = Policy(data={"roadmap": {"workstreams": STRUCTURE}})
    assert board.approved_structure(policy) == STRUCTURE
    assert board.approved_structure(Policy(data={"roadmap": {"lanes": ["UI"]}})) == []
    items = [item("A-1", base.QUEUED, 1, workstream="Docs", deliverable="Guide"),
             item("A-2", base.QUEUED, 2, workstream="W1",            # an id reads as assigned
                  deliverable="A very long deliverable name"),
             item("A-3", base.IN_FLIGHT, 3, workstream="Engine", deliverable="Core"),
             item("A-4", base.QUEUED, 4, workstream="Engine"),
             item("A-5", base.QUEUED, 5),
             item("A-6", base.COMPLETED, 6, workstream="Engine", deliverable="Core")]
    groups = board.structure_groups(items, STRUCTURE)
    assert [(g["title"], g["ids"]) for g in groups] == [
        ("Engine › Core", ["A-3"]), ("Engine › A very long deliverable name", ["A-2"]),
        ("Engine", ["A-4"]), ("Docs › Guide", ["A-1"]), ("Unassigned", ["A-5"])]
    found = {s["key"]: s for s in dashboard.slicers(items, [], dashboard.policy_orders(policy),
                                                    structured=True)}
    deliverables = found["deliverable"]
    assert deliverables["values"] == ["D1", "D2", "D3", ""]       # a stored name reads as its id
    assert deliverables["labels"] == {"D1": "Core", "D2": "A very long d…", "D3": "Guide",
                                      "": "Unassigned"}
    assert len(deliverables["labels"]["D2"]) == dashboard.FACET_WIDTH
    assert found["workstream"]["values"] == ["W1", "W2", ""]
    assert found["workstream"]["labels"]["W1"] == "Engine"
    assert found["workstream"]["labels"]["W2"] == "Docs"
    assert found["workstream"]["labels"][""] == "Unassigned"
    plain = {s["key"]: s for s in dashboard.slicers(items, [], {})}
    assert plain["workstream"]["labels"][""] == "(none)"         # no structure: as before
    assert "deliverable" not in plain                            # even with deliverable data
    assert "deliverable" not in dashboard.facets(items[0])
    for broken in ([{"id": "W", "deliverables": 5}], [{"id": "W", "deliverables": ["D"]}],
                   ["W"]):                                       # refused, never a crash
        policy = Policy(data={"roadmap": {"workstreams": broken}})
        assert board.approved_structure(policy) == []
        assert dashboard.policy_orders(policy)["deliverable"] == []


def test_a_workstream_stored_by_id_and_by_name_is_one_slicer_value():
    policy = Policy(data={"roadmap": {"workstreams": STRUCTURE}})
    items = [item("B-1", base.QUEUED, 1, workstream="W1"),
             item("B-2", base.QUEUED, 2, workstream="Engine"),
             item("B-3", base.QUEUED, 3, workstream="Elsewhere")]      # unknown: as stored
    found = {s["key"]: s for s in dashboard.slicers(items, [], dashboard.policy_orders(policy),
                                                    structured=True)}
    values = found["workstream"]["values"]
    assert values.count("W1") == 1 and "Engine" not in values
    assert values == ["W1", "Elsewhere"]
    assert found["workstream"]["labels"] == {"W1": "Engine"}
    index = dashboard.structure_index(STRUCTURE)
    assert [dashboard.facets(i, True, index)["workstream"] for i in items[:2]] == ["W1", "W1"]
    assert dashboard.facets(items[1])["workstream"] == "Engine"     # no structure: as stored


def done_page(tmp_path, structure: bool) -> list[str]:
    """The Completed tab's group titles, grouped by workstream, in the page's own script."""
    sync_playwright = page_runner()
    done = []
    for id_, stream in (("C-1", "Engine"), ("C-2", "")):
        finished = item(id_, base.COMPLETED, 1, workstream=stream)
        done.append(dict(board.row(finished), facets=dashboard.facets(finished),
                         result="completed", retired=False))
    roadmap = {"groups": [], "live": []}
    if structure:
        roadmap["structure"] = []
    model = {"project": "p", "rows": done, "columns": [], "roadmap": roadmap,
             "completed": {"rows": done, "problems": [],
                           "columns": [{"key": "workstream", "header": "Workstream",
                                        "kind": "label"}],
                           "groups": [{"key": "completed", "title": "Completed",
                                       "rail": "green", "ids": ["C-1", "C-2"]}]},
             "dashboard": {"tiles": [], "slicers": []}}
    page_file = tmp_path / ("structured.html" if structure else "plain.html")
    page_file.write_text(render_board(model), encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(page_file.as_uri())
        page.evaluate("selectTab('completed')")
        page.select_option("#done-toolbar select[aria-label='Group by']", "workstream")
        titles = page.locator("#done-groups .group-title > span:not(.count)").all_inner_texts()
        browser.close()
    assert errors == []
    return titles


def test_unassigned_finished_items_group_as_unassigned(workspace, tmp_path):  # noqa: F811
    approve(workspace, STRUCTURE)
    model = generate.build_board(generate.read(workspace))
    live = model["roadmap"]["structure"]
    assert live and live[-1]["title"] == "Unassigned" and live[-1]["ids"] == model["roadmap"]["live"]
    finished = model["completed"]["rows"]
    assert finished and all(not r["facets"]["workstream"] for r in finished)
    assert done_page(tmp_path, structure=True) == ["Engine", "Unassigned"]
    assert done_page(tmp_path, structure=False) == ["Engine", "(none)"]


def test_a_board_without_structure_renders_as_before(reference_workspace):
    page = render_board(generate.build_board(generate.read(reference_workspace)))
    expected = json.loads(WITHOUT_STRUCTURE.read_text(encoding="utf-8"))
    assert comparable(embedded(page), reference_workspace) == expected


# --- D6: comments ------------------------------------------------------------------


def note(text, at="2026-10-01T10:00:00Z", resolved=False):
    return {"at": at, "text": text, "resolved": resolved}


def test_the_comments_sidecar_is_written_sorted_one_entry_per_item(tmp_path):
    path = tmp_path / "c.json"
    found = {"Z-1": {"updated": "2026-10-02T00:00:00Z", "notes": [note("last")]},
             "A-1": {"updated": "2026-10-01T00:00:00Z", "notes": [note("first")]}}
    comments.write_comments(str(path), found)
    text = path.read_text(encoding="utf-8")
    assert text.index('"A-1"') < text.index('"Z-1"')
    assert text == json.dumps({"comments": found, "version": 1}, sort_keys=True, indent=2,
                              ensure_ascii=False) + "\n"
    assert comments.read_comments(str(path)) == (found, [])
    with pytest.raises(comments.CommentsError):
        comments.dumps({"A-1": {"updated": "x", "notes": [{"text": ""}]}})


def test_the_comments_sidecar_reader_skips_damage(tmp_path):
    path = tmp_path / "c.json"
    path.write_text(json.dumps({"version": 1, "comments": {
        "A-1": {"updated": "t", "notes": [note("fine")]},
        "B-2": {"notes": "not a list"}}}), encoding="utf-8")
    found, problems = comments.read_comments(str(path))
    assert list(found) == ["A-1"] and problems == ["skipped B-2: the entry has no updated time"]
    path.write_text("{not json", encoding="utf-8")
    assert comments.read_comments(str(path))[0] == {}


#: Two copies of the comments, as the page and the file can hold them.
MERGE_DURABLE = {
    "A-1": {"updated": "2026-10-01T00:00:00Z", "notes": [note("file", "2026-10-01T00:00:00Z")]},
    "B-2": {"updated": "2026-10-05T00:00:00Z", "notes": [
        note("asked", "2026-10-01T00:00:00Z", resolved=True)]},
    "10": {"updated": "2026-10-01T00:00:00Z", "notes": [note("ten ☃", "2026-10-01T00:00:00Z")]},
}
MERGE_LOCAL = {
    "A-1": {"updated": "2026-10-03T00:00:00Z", "notes": [
        note("file", "2026-10-01T00:00:00Z"), note("browser", "2026-10-03T00:00:00Z")]},
    "B-2": {"updated": "2026-10-02T00:00:00Z", "notes": [
        note("asked", "2026-10-01T00:00:00Z"), note("unsaved", "2026-10-02T00:00:00Z")]},
    "9": {"updated": "2026-10-02T00:00:00Z", "notes": [note("nine \U0001F600", "2026-10-02T00:00:00Z")]},
    # the browser is newer, but the review resolved the first note in the file meanwhile
    "D-4": {"updated": "2026-10-03T00:00:00Z", "notes": [
        note("asked", "2026-10-01T00:00:00Z"), note("follow-up", "2026-10-03T00:00:00Z")]},
}
MERGE_DURABLE["D-4"] = {"updated": "2026-10-02T00:00:00Z", "notes": [
    dict(note("asked", "2026-10-01T00:00:00Z", resolved=True), answer="done")]}


def test_the_comments_sidecar_merge_keeps_every_note_and_the_newest_resolution():
    merged = comments.merge(MERGE_DURABLE, MERGE_LOCAL)
    assert [n["text"] for n in merged["A-1"]["notes"]] == ["file", "browser"]
    assert merged["A-1"]["updated"] == "2026-10-03T00:00:00Z"
    # the file is newer (a review resolved B-2); the browser's unsaved note survives it
    assert [(n["text"], n["resolved"]) for n in merged["B-2"]["notes"]] == [
        ("asked", True), ("unsaved", False)]
    assert merged["B-2"]["updated"] == "2026-10-05T00:00:00Z"
    # a resolution in either copy stands, even when the other copy is newer
    assert [(n["text"], n["resolved"], n.get("answer")) for n in merged["D-4"]["notes"]] == [
        ("asked", True, "done"), ("follow-up", False, None)]
    tie = comments.merge({"C-3": {"updated": "t", "notes": [note("x", resolved=True)]}},
                         {"C-3": {"updated": "t", "notes": [note("x")]}})
    assert tie["C-3"]["notes"][0]["resolved"] is True              # a tie keeps the file
    assert set(merged) == {"A-1", "B-2", "9", "10", "D-4"}


def page_runner():
    """Run the page's own JavaScript in Chromium, or skip where it is not installed."""
    sync_api = pytest.importorskip("playwright.sync_api")
    return sync_api.sync_playwright


def test_the_page_merges_and_writes_comments_exactly_as_the_generator(tmp_path):
    sync_playwright = page_runner()
    page_file = tmp_path / "board.html"
    page_file.write_text(render_board({"project": "p", "rows": [], "columns": [],
                                       "roadmap": {"groups": [], "live": []}}), encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(page_file.as_uri())
        merged_in_page = page.evaluate("([a, b]) => mergeComments(a, b)",
                                       [MERGE_DURABLE, MERGE_LOCAL])
        text_in_page = page.evaluate("(c) => sidecarText(c)", merged_in_page)
        browser.close()
    merged = comments.merge(MERGE_DURABLE, MERGE_LOCAL)
    assert merged_in_page == merged
    assert text_in_page == comments.dumps(merged)                  # "10" before "9", emoji too


def test_the_page_survives_a_hand_typed_completion_date(tmp_path):
    sync_playwright = page_runner()
    rows = [dict(board.row(item("C-1", base.COMPLETED, 1)), facets={"complete": "complete"})]
    rows[0]["values"].update(completedOn="Oct 9, 2026")
    done = [dict(rows[0], result="completed", retired=False)]
    model = {"project": "p", "rows": rows, "columns": [],
             "roadmap": {"groups": [], "live": []},
             "completed": {"rows": done, "columns": [], "problems": [],
                           "groups": [{"key": "completed", "title": "Completed", "rail": "green",
                                       "ids": ["C-1"]}]},
             "dashboard": {"tiles": [{"key": "total", "label": "Total", "value": 1,
                                      "detail": "", "source": "s"}], "slicers": []}}
    page_file = tmp_path / "board.html"
    page_file.write_text(render_board(model), encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(page_file.as_uri())
        tiles = page.locator("[data-tile]").count()
        done_rows = page.locator("#done-groups tbody tr").count()
        browser.close()
    assert errors == [] and tiles == 1 and done_rows == 1


def test_comments_survive_regeneration(workspace):  # noqa: F811
    generate.ensure_board(workspace)
    sidecar = workspace / board.COMMENTS_PATH
    comments.write_comments(str(sidecar), {
        "ITEM-2": {"updated": "2026-10-01T10:00:00Z", "notes": [note("needs a spec")]}})
    for _ in range(2):
        generate.generate_board(workspace)
        model = embedded((workspace / board.DEFAULT_PATH).read_text(encoding="utf-8"))
        assert model["comments"]["ITEM-2"]["notes"][0]["text"] == "needs a spec"
    assert sidecar.read_text(encoding="utf-8").startswith('{\n  "comments"')


def test_the_review_reads_and_resolves_board_comments(workspace):  # noqa: F811
    tool = str(Path(PLUGIN_ROOT) / "scripts" / "board_comments.py")
    generate.ensure_board(workspace)
    sidecar = workspace / board.COMMENTS_PATH
    comments.write_comments(str(sidecar), {
        "ITEM-2": {"updated": "2026-10-01T10:00:00Z", "notes": [note("needs a spec")]}})
    listed = run(tool, "--root", str(workspace), "--json")
    assert json.loads(listed.stdout)["open"] == [
        {"item": "ITEM-2", "at": "2026-10-01T10:00:00Z", "text": "needs a spec"}]
    refused = run(tool, "--root", str(workspace), "--actor", "next-dispatch", "--resolve",
                  "ITEM-2", "--answer", "specified", "--apply")
    assert refused.returncode == 2 and "may not write" in refused.stderr
    done = run(tool, "--root", str(workspace), "--actor", "roadmap-review", "--resolve",
               "ITEM-2", "--answer", "specified in the review", "--apply")
    assert done.returncode == 0, done.stderr
    entry = comments.read_comments(str(sidecar))[0]["ITEM-2"]
    assert entry["notes"][0]["resolved"] is True
    assert entry["notes"][0]["answer"] == "specified in the review"
    assert entry["updated"] > "2026-10-01T10:00:00Z"
    assert json.loads(run(tool, "--root", str(workspace), "--json").stdout)["open"] == []
    again = run(tool, "--root", str(workspace), "--actor", "roadmap-review", "--resolve",
                "ITEM-2", "--answer", "twice", "--apply")
    assert again.returncode == 2 and "no open comment" in again.stderr


def test_the_review_reads_board_comments_in_b3():
    text = (SKILLS / "roadmap-review" / "SKILL.md").read_text(encoding="utf-8")
    b3 = text.split("### B.3", 1)[1].split("\n### ", 1)[0]
    assert b3.count("comments") >= 2 and "board_comments" in b3


# --- D7: freshness -----------------------------------------------------------------


def preflight_lines(root) -> dict:
    out = run(PREFLIGHT, "--root", str(root), "--mode", "check")
    return dict(line.split(": ", 1) for line in out.stdout.splitlines() if ": " in line)


def test_the_board_regenerates_after_record_completion(workspace):  # noqa: F811
    generate.ensure_board(workspace)
    before = embedded((workspace / board.DEFAULT_PATH).read_text(encoding="utf-8"))
    assert "ITEM-2" not in by_id(before["completed"]["rows"])
    done = subprocess.run(
        [os.sys.executable, REGISTRY_CLI, "--root", str(workspace), "--actor",
         "dispatch-closeout", "record-completion", "--item", "ITEM-2", "--date", "2026-02-01",
         "--result", "completed", "--evidence", "CloseOut.ITEM-2.md", "--apply"],
        capture_output=True, text=True, encoding="utf-8",
        env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    assert done.returncode == 0, done.stderr
    assert "board regenerated: " in done.stdout
    after = embedded((workspace / board.DEFAULT_PATH).read_text(encoding="utf-8"))
    assert by_id(after["completed"]["rows"])["ITEM-2"]["unreconciled"] == ""


def test_the_board_stale_advisory(workspace):  # noqa: F811
    generate.ensure_board(workspace)
    lines = preflight_lines(workspace)
    assert lines["board"].startswith("current")          # the check can say "not stale"
    register = workspace / REGISTER
    later = os.stat(register).st_mtime + 60
    os.utime(register, (later, later))
    stale = preflight_lines(workspace)
    assert stale["board"].startswith("stale (workRegister changed since ")
    assert stale["virtuoso-status"] == lines["virtuoso-status"]   # advice, never a block
    generate.generate_board(workspace)
    assert preflight_lines(workspace)["board"].startswith("current")


def test_a_source_written_during_generation_reads_stale(workspace, monkeypatch):  # noqa: F811
    from tools.roadmap_visualizer import freshness
    generate.ensure_board(workspace)
    original = generate.read

    def read_then_write(root):
        reading = original(root)
        register = workspace / REGISTER
        later = os.stat(register).st_mtime + 30
        os.utime(register, (later, later))                       # an edit lands mid-generation
        return reading

    monkeypatch.setattr(generate, "read", read_then_write)
    generate.generate_board(workspace)
    assert freshness.board_status(str(workspace)).startswith("stale (workRegister")


def test_the_board_missing_advisory(workspace):  # noqa: F811
    assert preflight_lines(workspace)["board"] == "not registered"
    generate.ensure_board(workspace)
    (workspace / board.DEFAULT_PATH).unlink()
    lines = preflight_lines(workspace)
    assert lines["board"].startswith("missing (roadmap-board.html")
    assert lines["writes"] == "0"


def test_every_ceremony_that_changes_the_register_names_the_board():
    for skill in ("dispatch-closeout", "next-dispatch", "roadmap-review"):
        text = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
        assert "generate_board" in text, skill


# --- the cockpit retired (VIR-029) -------------------------------------------------

LEGACY_COCKPIT = Path("Virtuoso") / "reports" / "planning-cockpit.html"


def test_the_dashboard_shows_drift_findings(workspace):  # noqa: F811
    with open(workspace / REGISTER, "a", encoding="utf-8") as handle:
        handle.write("ITEM-9,Ghost item,9,Queued,Stub,,S,,G1,,,,,,,\n")
    generate.ensure_board(workspace)
    html = (workspace / board.DEFAULT_PATH).read_text(encoding="utf-8")
    assert 'id="drift-list"' in html and "BOARD.health" in html
    health = embedded(html)["health"]
    assert any("ITEM-9" in f for f in health["drift_findings"])
    assert isinstance(health["recommendation"], str) and health["recommendation"]


def test_the_header_names_the_register_role(workspace):  # noqa: F811
    generate.ensure_board(workspace)
    html = (workspace / board.DEFAULT_PATH).read_text(encoding="utf-8")
    assert embedded(html)["register"] == {"role": "workRegister", "authority": "live",
                                          "compatibilityAdapter": False}
    assert "BOARD.register" in html


def test_generate_cockpit_is_an_alias_for_the_board(workspace):  # noqa: F811
    out = run(COCKPIT, "--root", str(workspace))
    assert out.returncode == 2 and "generate_board --create" in out.stderr
    assert out.stderr.index("generate_board --create") < out.stderr.index(
        "generate_cockpit is retired")                     # the notice follows the error
    generate.ensure_board(workspace)
    out = run(COCKPIT, "--root", str(workspace))
    assert out.returncode == 0, out.stderr
    assert "board written: " in out.stdout
    assert "generate_cockpit is retired" in out.stderr
    assert not (workspace / LEGACY_COCKPIT).exists()


def test_an_existing_cockpit_page_is_left_alone(workspace):  # noqa: F811
    page = workspace / LEGACY_COCKPIT
    page.parent.mkdir(parents=True, exist_ok=True)
    page.write_bytes(b"<html>an old cockpit</html>")
    generate.ensure_board(workspace)
    assert run(COCKPIT, "--root", str(workspace)).returncode == 0
    assert run(BOARD_CLI, "--root", str(workspace)).returncode == 0
    assert page.read_bytes() == b"<html>an old cockpit</html>"


def test_the_cockpit_renderer_is_gone():
    assert not (Path(PLUGIN_ROOT) / "tools" / "roadmap_visualizer" / "render.py").exists()
    assert not hasattr(generate, "generate") and not hasattr(generate, "main")
