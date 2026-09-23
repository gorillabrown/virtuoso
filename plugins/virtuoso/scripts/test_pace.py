"""Pace against a dated deadline (v1.8.1): the engine, ``kpis``, and the cockpit.

The acceptance fixture is the Gloves of Glory roadmap review of 2026-09-22, whose
figures an operator derived by hand because the plugin could not: 60 items and
235.5 points remaining, 201.0 of them blocked, twelve completions in the trailing
four weeks, and a deadline of 2027-01-01 for "the overall game build".
"""
from __future__ import annotations

import datetime as _dt

import pytest

from tools.governance.deadlines import Deadline
from tools.governance.providers import base, pace
from tools.governance.providers.ledger import LedgerRecord
from tools.governance.providers.mapping import Mapping

STATUSES = Mapping().statuses
AS_OF = "2026-09-22T12:00:00Z"
GAME_BUILD = Deadline(id="game-build", date=_dt.date(2027, 1, 1), owner="Evan",
                      label="Overall game build", recorded="2026-09-22")


def item(item_id, effort="m", status=base.QUEUED, **fields):
    return base.WorkItem(id=item_id, status=status, raw_status=status, effort=effort, **fields)


def gog_items():
    """40 unblocked items (34.5 points) and 20 blocked (201.0 points)."""
    sizes = ["xs"] * 30 + ["s-m"] * 6 + ["m"] * 2 + ["xs-s"] * 2
    blocked = ["xl"] * 5 + ["l"] * 11 + ["m-l"] * 2 + ["s"] + ["s-m"]
    out = [item("Q-%02d" % n, size) for n, size in enumerate(sizes, 1)]
    out += [item("H-%02d" % n, size, base.BLOCKED) for n, size in enumerate(blocked, 1)]
    return out


def snapshot(items, *, taken_at=AS_OF, fields=("status", "effort", "completed"), stale=False):
    return base.Snapshot(items=list(items), provider="test", source="memory",
                         taken_at=taken_at, fields=list(fields), stale=stale,
                         stale_reason="older than 24h" if stale else "")


def record(n, day, result="completed", item_id=None, corrects=""):
    return LedgerRecord(record_id="TR-%03d" % n, item_id=item_id or "DONE-%03d" % n,
                        completed=day, result=result, corrects=corrects)


def gog_ledger():
    days = ["2026-08-26", "2026-08-28", "2026-09-01", "2026-09-03", "2026-09-08",
            "2026-09-10", "2026-09-15", "2026-09-17", "2026-09-21", "2026-09-22"]
    records = [record(1, "2026-08-25")]                           # the day before the window
    records += [record(n, day) for n, day in enumerate(days, 2)]
    records += [record(12, "2026-09-11", "completed (qualified)"),
                record(13, "2026-09-18", "completed (qualified)"),
                record(14, "2026-09-21", "dissolved")]
    return records


def source(records, label="terminalLedger: CompletedWork.Ledger.md"):
    return pace.CompletionSource(pace.from_ledger(records, STATUSES), label)


def compute(deadline=GAME_BUILD, items=None, records=None, **kwargs):
    snap = kwargs.pop("snap", None) or snapshot(gog_items() if items is None else items)
    src = kwargs.pop("src", None) or source(gog_ledger() if records is None else records)
    return pace.compute(deadline, snap, src, **kwargs)


# --- the acceptance fixture ---------------------------------------------------


def test_gog_figures():
    report = compute().as_dict()
    assert report["asOf"] == "2026-09-22"
    assert report["daysRemaining"] == 101
    assert report["weeksRemaining"] == 14.43
    assert report["remaining"] == {"items": 60, "points": 235.5}
    assert report["required"] == {"items": 4.16, "points": 16.32}
    assert report["blocked"]["items"] == 20
    assert report["blocked"]["points"] == 201.0
    assert report["blocked"]["shareOfPoints"] == 85.4
    trailing = report["trailing"]
    assert trailing["window"] == {"from": "2026-08-26", "to": "2026-09-22", "weeks": 4}
    assert trailing["items"] == 3.0
    assert trailing["completions"] == 12
    assert trailing["byResult"] == {"completed": 10, "completed (qualified)": 2}
    assert trailing["excluded"] == {"dissolved": 1}
    assert trailing["projectWide"] is True
    assert report["verdict"] == "behind"
    assert report["basis"] == ["items"]
    assert report["reason"] == "trailing 3.00 items/week is 72% of the 4.16 required"
    assert report["projectedFinish"]["items"] == "2027-02-09"


def test_gog_trailing_points_are_not_computable_when_finished_items_left_the_register():
    report = compute()
    assert report.trailing["points"] is None
    assert "absent from the register" in report.missing["trailing.points"][0]
    assert report.verdict == "behind"                   # items still carry the verdict


def test_gog_renders_the_verdict_projection_and_blocked_share():
    text = compute().render()
    assert "game-build  Overall game build: due 2027-01-01, owner Evan" in text
    assert "101 days, 14.43 weeks remain" in text
    assert "60 items, 235.5 points remain" in text
    assert "201.0 points (85.4% of remaining points)" in text
    assert "4.16 items/week, 16.32 points/week" in text
    assert "12 completions: completed ×10, completed (qualified) ×2; excluded: dissolved ×1" \
        in text
    assert "BEHIND on items" in text
    assert "2027-02-09, 39 days after the deadline" in text


def test_trailing_points_when_the_register_keeps_finished_items():
    done = [item("DONE-%03d" % n, "l", base.COMPLETED) for n in range(2, 14)]
    report = compute(items=gog_items() + done)
    assert report.trailing["points"] == 12 * 8 / 4                 # 24.0 points a week
    assert report.unit_verdicts == {"items": "behind", "points": "ahead"}
    assert report.verdict == "behind" and report.basis == ["items"]  # the worse unit


# --- the window and the record ------------------------------------------------


def test_the_window_is_half_open():
    edges = [record(1, "2026-08-25"), record(2, "2026-08-26"), record(3, "2026-09-22"),
             record(4, "2026-09-23")]
    assert compute(records=edges).trailing["completions"] == 2


def test_an_undatable_completion_makes_trailing_not_computable():
    report = compute(records=gog_ledger() + [record(20, "last Tuesday")])
    assert report.trailing["items"] is None
    assert "TR-020" in report.missing["trailing"][0]
    assert report.verdict == pace.NOT_COMPUTABLE


def test_an_undatable_record_that_is_not_a_completion_does_not_block():
    report = compute(records=gog_ledger() + [record(20, "n/a", "dissolved")])
    assert report.trailing["items"] == 3.0


def test_a_correction_replaces_what_it_corrects():
    records = gog_ledger() + [LedgerRecord(record_id="TR-015", item_id="", completed="",
                                           result="dissolved", corrects="TR-002")]
    report = compute(records=records)
    assert report.trailing["completions"] == 11
    assert report.trailing["excluded"] == {"dissolved": 2}


def test_a_correction_can_date_an_undatable_record():
    records = [record(1, "sometime"),
               LedgerRecord(record_id="TR-002", item_id="", completed="2026-09-20",
                            result="", corrects="TR-001")]
    assert compute(records=records).trailing["completions"] == 1


def test_one_item_completed_twice_counts_once():
    records = [record(1, "2026-09-01", item_id="X-1"), record(2, "2026-09-10", item_id="X-1")]
    assert compute(records=records).trailing["completions"] == 1


def test_register_completion_dates_when_no_ledger_is_registered():
    done = [item("D-1", "m", base.COMPLETED, completed="2026-09-01"),
            item("D-2", "m", base.COMPLETED, completed="2026-09-20T09:00:00Z"),
            item("D-3", "m", base.DISSOLVED, completed="2026-09-02")]
    snap = snapshot(gog_items() + done)
    src = pace.CompletionSource(pace.from_register(snap.items), "workRegister")
    report = pace.compute(GAME_BUILD, snap, src)
    assert report.trailing["completions"] == 2
    assert report.trailing["points"] == 6 / 4
    assert report.trailing["excluded"] == {"dissolved": 1}


def test_no_completion_source_is_not_computable_and_says_why():
    src = pace.CompletionSource([], "", missing=["completion dates: none registered"])
    report = compute(src=src)
    assert report.verdict == pace.NOT_COMPUTABLE
    assert report.missing["trailing"] == ["completion dates: none registered"]
    assert report.required["items"] is not None          # what can be computed still is


def test_ledger_history_shorter_than_the_window_is_noted():
    report = compute(records=[record(1, "2026-09-15")])
    assert any("the completion record begins 2026-09-15" in n for n in report.notes)


# --- scope ---------------------------------------------------------------------


def _scoped(field, *values):
    return Deadline(id="b3", date=_dt.date(2027, 1, 1), owner="Evan",
                    scope_field=field, scope_values=tuple(values))


def test_scope_by_group():
    items = [item("A", group="B3"), item("B", group="b3"), item("C", group="C")]
    report = compute(_scoped("group", "B3"), items=items)
    assert report.remaining["items"] == 2                 # case-insensitive


def test_scope_by_register_column():
    items = [item("A", extra={"Finish Line": "B3"}), item("B", extra={"Finish Line": "C"})]
    assert compute(_scoped("finish line", "B3"), items=items).remaining["items"] == 1


def test_scope_by_id():
    assert compute(_scoped("id", "Q-01", "Q-02")).remaining["items"] == 2


def test_a_scope_matching_nothing_is_not_computable_never_met():
    report = compute(_scoped("group", "B9"), items=[item("A", group="B3")])
    assert report.verdict == pace.NOT_COMPUTABLE
    assert "no work item carries group in {B9}" in report.missing["scope"][0]


def test_an_unknown_scope_field_is_named():
    report = compute(_scoped("milestone", "M1"), items=[item("A")])
    assert "'milestone'" in report.missing["scope"][0]


def test_an_empty_register_is_not_computable_never_met():
    report = compute(items=[])
    assert report.verdict == pace.NOT_COMPUTABLE
    assert report.missing["scope"] == ["the register has no work items"]


def test_every_scoped_item_terminal_is_met():
    items = [item("A", status=base.COMPLETED), item("B", status=base.DISSOLVED)]
    report = compute(items=items)
    assert report.verdict == "met"
    assert report.remaining["items"] == 0


# --- dates and verdicts --------------------------------------------------------


@pytest.mark.parametrize("due, days", [("2026-09-22", 0), ("2026-09-01", -21)])
def test_a_date_that_has_arrived_with_work_remaining_is_overdue(due, days):
    deadline = Deadline(id="x", date=_dt.date.fromisoformat(due), owner="Evan")
    report = compute(deadline)
    assert report.verdict == "overdue"
    assert report.days_remaining == days
    assert report.required["items"] is None
    assert report.projected["items"] == "2027-02-09"     # the projection still shows


def test_no_completions_in_the_window_is_behind_with_no_projection():
    report = compute(records=[record(1, "2026-06-01")])
    assert report.trailing["items"] == 0
    assert report.verdict == "behind"
    assert report.projected["items"] is None
    assert "no completions in the trailing window; no projection" in report.notes


@pytest.mark.parametrize("trailing, verdict", [
    (3.5, "behind"), (3.6, "on track"), (4.0, "on track"), (4.4, "on track"), (4.41, "ahead"),
])
def test_tolerance_bands(trailing, verdict):
    assert pace.unit_verdict(4.0, trailing, 0.1) == verdict


def test_zero_tolerance_is_exact():
    assert pace.unit_verdict(4.0, 4.0, 0) == "on track"
    assert pace.unit_verdict(4.0, 3.99, 0) == "behind"
    assert pace.unit_verdict(4.0, 4.01, 0) == "ahead"


def test_ties_name_both_units():
    done = [item("DONE-%03d" % n, "xs", base.COMPLETED) for n in range(2, 14)]
    report = compute(items=gog_items() + done)            # 1.5 points a week: behind too
    assert report.unit_verdicts == {"items": "behind", "points": "behind"}
    assert report.basis == ["items", "points"]


def test_a_stale_snapshot_is_flagged_and_measured_as_of_its_own_date():
    report = compute(snap=snapshot(gog_items(), taken_at="2026-09-01T00:00:00Z", stale=True))
    assert report.stale is True
    assert report.days_remaining == 122
    assert any("stale" in n for n in report.notes)


def test_an_unreadable_snapshot_time_is_named():
    report = compute(snap=snapshot(gog_items(), taken_at="yesterday"))
    assert report.verdict == pace.NOT_COMPUTABLE
    assert "snapshot time" in report.missing["asOf"][0]


def test_unsized_remaining_work_makes_points_not_computable_but_not_items():
    report = compute(items=gog_items() + [item("U-1", effort="")])
    assert report.remaining["points"] is None
    assert "U-1" in report.missing["remaining.points"][0]
    assert report.verdict == "behind" and report.basis == ["items"]


def test_deadlines_are_reported_in_date_order_and_share_capacity():
    later = Deadline(id="c", date=_dt.date(2027, 6, 1), owner="Evan")
    reports = pace.compute_all([later, GAME_BUILD], snapshot(gog_items()), source(gog_ledger()))
    assert [r.deadline.id for r in reports] == ["game-build", "c"]
    assert all(any("shared capacity" in n for n in r.notes) for r in reports)


def test_record_date_accepts_a_date_or_a_timestamp_and_nothing_else():
    assert pace.record_date("2026-09-22") == _dt.date(2026, 9, 22)
    assert pace.record_date("2026-09-22T10:00:00Z") == _dt.date(2026, 9, 22)
    assert pace.record_date("2026-09-22 10:00") == _dt.date(2026, 9, 22)
    for text in ("22/09/2026", "20260922", "Sep 22, 2026", "", None, "2026-09-31"):
        assert pace.record_date(text) is None, text


# =============================================================================
# Real workspaces: where completions come from
# =============================================================================

import csv  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

from conftest import PLUGIN_ROOT  # noqa: E402
from tools.governance import registry as registry_mod  # noqa: E402
from tools.governance import providers  # noqa: E402

ROOT = Path(PLUGIN_ROOT)
PREFLIGHT = str(ROOT / "scripts" / "virtuoso_preflight.py")
REGISTRY_CLI = str(ROOT / "scripts" / "virtuoso_registry.py")
REGISTER_COLUMNS = ["id", "title", "sequence", "status", "written_status", "prerequisites",
                    "effort", "lane", "group", "spec_link", "branch", "started", "completed",
                    "evidence", "description", "notes"]


def run(script, *args):
    return subprocess.run([sys.executable, script, *args], capture_output=True,
                          text=True, env=dict(os.environ))


def days_ago(n):
    return (_dt.date.today() - _dt.timedelta(days=n)).isoformat()


def role_path(root, role):
    data = json.loads((root / "Virtuoso" / "workspace-layout.json").read_text(encoding="utf-8"))
    return root.joinpath(*data["roles"][role]["path"].split("/"))


def write_register(root, rows):
    with open(role_path(root, "workRegister"), "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REGISTER_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def append_ledger(root, rows):
    path = role_path(root, "terminalLedger")
    text = path.read_text(encoding="utf-8")
    lines = ["| %s | %s | %s | %s | %s | %s |" % row for row in rows]
    path.write_text(text.rstrip("\n") + "\n" + "\n".join(lines) + "\n", encoding="utf-8",
                    newline="\n")


def edit_manifest(root, change):
    path = root / "Virtuoso" / "workspace-layout.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8", newline="\n")


@pytest.fixture
def paced(project):
    """A created workspace with six live items, two completions in the ledger, one
    completed item still in the register, and one far-future deadline."""
    assert run(PREFLIGHT, "--root", str(project), "--mode", "create",
               "--authorize").returncode == 0
    rows = [dict(id="W-%d" % n, title="Item %d" % n, sequence=str(n), status=status,
                 written_status="Stub", effort=effort, group=group)
            for n, (status, effort, group) in enumerate([
                ("Queued", "m", "B1"), ("Queued", "s", "B1"), ("In Progress", "l", "B2"),
                ("Blocked", "xl", "B2"), ("Blocked", "m", "C"), ("Queued", "s", "C")], 1)]
    rows.append(dict(id="W-7", title="Item 7", sequence="7", status="Completed",
                     written_status="Full Spec", effort="m", completed=days_ago(3)))
    write_register(project, rows)
    append_ledger(project, [("TR-001", "W-7", days_ago(3), "completed", "", ""),
                            ("TR-002", "W-0", days_ago(9), "Completed", "", "")])
    edit_manifest(project, lambda d: d.setdefault("policy", {}).setdefault("roadmap", {})
                  .setdefault("deadlines", {}).update(
                      {"ship": {"date": "2099-01-01", "owner": "Owner",
                                "finishLine": "Finish line"}}))
    return project


def _source(root):
    reg = registry_mod.load(str(root))
    snap = providers.work_register(reg).provider.snapshot()
    return providers.completion_source(reg, snap), snap


def test_the_registered_ledger_is_the_completion_source(paced):
    src, _ = _source(paced)
    assert src.label == "terminalLedger: Project Documentation/1 governance/CompletedWork.Ledger.md"
    assert src.missing == []
    assert [(c.record, c.item_id, c.canonical) for c in src.completions] == [
        ("TR-001", "W-7", base.COMPLETED), ("TR-002", "W-0", base.COMPLETED)]


def test_the_register_is_the_source_only_when_no_ledger_is_registered(paced):
    edit_manifest(paced, lambda d: d["roles"].pop("terminalLedger"))
    src, _ = _source(paced)
    assert src.label.startswith("workRegister completion dates")
    assert [c.item_id for c in src.completions] == ["W-7"]


def test_a_registered_ledger_whose_file_is_missing_is_named(paced):
    role_path(paced, "terminalLedger").unlink()
    src, _ = _source(paced)
    assert src.completions == []
    assert "does not exist" in src.missing[0]


def test_no_ledger_and_no_completion_column_is_named(paced):
    edit_manifest(paced, lambda d: d["roles"].pop("terminalLedger"))
    reg = registry_mod.load(str(paced))
    snap = base.Snapshot(items=[], provider="test", source="memory", taken_at=AS_OF,
                         fields=["status"])
    src = providers.completion_source(reg, snap)
    assert src.missing == ["completion dates: no terminal ledger is registered and the "
                           "register carries no completion date"]


def test_the_project_status_vocabulary_reads_the_ledger(paced):
    edit_manifest(paced, lambda d: d["policy"].setdefault("workRegister", {}).update(
        {"statusMappings": {"completed": ["Shipped"]}}))
    append_ledger(paced, [("TR-003", "W-8", days_ago(1), "Shipped", "", "")])
    src, _ = _source(paced)
    assert [c.canonical for c in src.completions][-1] == base.COMPLETED


# =============================================================================
# kpis carries pace
# =============================================================================


def kpis(root, *extra):
    return run(REGISTRY_CLI, "--root", str(root), "kpis", *extra)


def test_kpis_json_carries_a_pace_block(paced):
    completed = kpis(paced, "--json")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(completed.stdout)
    assert {"metrics", "provenance", "pace", "invalidDeadlines"} <= set(payload)
    assert payload["invalidDeadlines"] == []
    [report] = payload["pace"]
    assert report["deadline"]["id"] == "ship"
    assert report["deadline"]["scope"] == "every item in the register"
    assert report["remaining"] == {"items": 6, "points": 36.0}      # 3+1+8+20+3+1
    assert report["blocked"]["items"] == 2
    trailing = report["trailing"]
    assert trailing["completions"] == 2 and trailing["items"] == 0.5
    assert trailing["source"].startswith("terminalLedger: ")
    assert "W-0" in report["missingInputs"]["trailing.points"][0]   # left the register
    assert report["verdict"] == "ahead" and report["basis"] == ["items"]
    assert report["findings"] == []                  # "Finish line" anchors to the seed


def test_kpis_json_pace_is_empty_without_deadlines(paced):
    edit_manifest(paced, lambda d: d["policy"]["roadmap"].pop("deadlines"))
    payload = json.loads(kpis(paced, "--json").stdout)
    assert payload["pace"] == [] and payload["invalidDeadlines"] == []


def test_kpis_text_renders_pace(paced):
    text = kpis(paced).stdout
    assert "\npace\n" in text
    assert "ship  ship: due 2099-01-01, owner Owner" in text
    assert "verdict:  AHEAD on items" in text
    assert "not computable: trailing points/week" in text


def test_kpis_text_says_when_no_deadline_is_declared(paced):
    edit_manifest(paced, lambda d: d["policy"]["roadmap"].pop("deadlines"))
    assert "no deadline is declared (policy.roadmap.deadlines)" in kpis(paced).stdout


def test_kpis_reports_a_hand_edited_invalid_deadline(paced):
    edit_manifest(paced, lambda d: d["policy"]["roadmap"]["deadlines"].update(
        {"broken": {"date": "soon", "owner": "Owner"}}))
    completed = kpis(paced, "--json")
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert [r["deadline"]["id"] for r in payload["pace"]] == ["ship"]
    [finding] = payload["invalidDeadlines"]
    assert finding["code"] == "deadline-invalid" and "broken.date" in finding["message"]
    assert "invalid deadline: policy.roadmap.deadlines.broken.date" in kpis(paced).stdout


def test_kpis_uses_the_project_pace_policy(paced):
    edit_manifest(paced, lambda d: d["policy"]["roadmap"].update(
        {"pace": {"trailingWeeks": 1, "tolerance": 0}}))
    [report] = json.loads(kpis(paced, "--json").stdout)["pace"]
    assert report["trailing"]["window"]["weeks"] == 1
    assert report["trailing"]["completions"] == 1                 # only the 3-days-ago record


def test_an_invalid_pace_policy_falls_back_to_the_defaults_and_says_so(paced):
    edit_manifest(paced, lambda d: d["policy"]["roadmap"].update({"pace": {"tolerance": 5}}))
    [report] = json.loads(kpis(paced, "--json").stdout)["pace"]
    assert report["trailing"]["window"]["weeks"] == 4
    assert any("policy.roadmap.pace is invalid" in n for n in report["notes"])


# =============================================================================
# The cockpit
# =============================================================================

import re  # noqa: E402

from tools.roadmap_visualizer import generate as cockpit  # noqa: E402
from tools.roadmap_visualizer import health as health_mod  # noqa: E402


def cockpit_html(root):
    return Path(cockpit.generate(str(root))).read_text(encoding="utf-8")


def embedded_model(html):
    match = re.search(r"const MODEL = (\{.*?\});\n", html, re.DOTALL)
    assert match, "the cockpit did not embed its model"
    return json.loads(match.group(1).replace("<\\/", "</"))


def test_the_cockpit_model_carries_pace(paced):
    model = embedded_model(cockpit_html(paced))
    [report] = model["metrics"]["pace"]
    assert report["deadline"]["id"] == "ship" and report["verdict"] == "ahead"
    assert model["metrics"]["invalidDeadlines"] == []


def test_the_cockpit_renders_deadline_and_pace_tiles(paced):
    html = cockpit_html(paced)
    assert '["Deadline", deadlineValue(nextPace()), deadlineDetail(nextPace()), "compact"]' \
        in html
    assert '["Pace", paceValue(nextPace()), paceDetail(nextPace()), "compact"]' in html
    assert "none declared" in html and "no deadline" in html


def _concern(verdict):
    return {"verdict": verdict, "reason": "trailing 3.00 items/week is 72% of the 4.16 required",
            "deadline": {"label": "Overall game build", "date": "2027-01-01"}}


def test_behind_or_overdue_replaces_proceed_only():
    concern = health_mod._pace_concern([_concern("ahead"), _concern("behind")])
    assert concern["verdict"] == "behind"
    said = health_mod._recommendation(0, 5, 5, {}, False, concern)
    assert said.startswith("Run the roadmap-review ceremony: pace is behind against "
                           "Overall game build (due 2027-01-01)")
    assert health_mod._recommendation(0, 5, 5, {}, False, None).startswith("Proceed")
    # stale, drift, and a short buffer keep their priority
    assert "stale" in health_mod._recommendation(0, 5, 5, {}, True, concern)
    assert "disagree" in health_mod._recommendation(2, 5, 5, {}, False, concern)
    assert "dispatch buffer" in health_mod._recommendation(0, 3, 5, {}, False, concern)


def test_on_track_ahead_and_met_raise_no_concern():
    assert health_mod._pace_concern([_concern("on track"), _concern("ahead"),
                                     _concern("met"), _concern("not computable")]) is None
