"""Effort in hours beside the size word (v1.17.3).

A register may carry both a size word (``effort``, e.g. an ``LOE`` column) and an hours
estimate (``effort_hours``). ``policy.roadmap.effortBasis`` says which governs; ``auto``
picks hours whenever the register serves an hours field. An item without hours falls
back to its size word through the scale, read as hours, and the figure says so.
"""
from __future__ import annotations

import datetime as _dt

import pytest

from tools.governance import policy as policy_mod
from tools.governance.deadlines import Deadline
from tools.governance.providers import base, effort, kpi, pace
from tools.governance.providers.csv_provider import CsvWorkRegister
from tools.governance.providers.ledger import LedgerRecord, TerminalLedger
from tools.governance.providers.mapping import Mapping

STATUSES = Mapping().statuses
AS_OF = "2026-11-18T12:00:00Z"
SHIP = Deadline(id="ship", date=_dt.date(2026, 12, 30), owner="Evan", recorded="2026-11-18")
BOTH = ("status", "effort", "effort_hours", "completed")


def item(item_id, size="m", hours="", status=base.QUEUED, **fields):
    return base.WorkItem(id=item_id, status=status, raw_status=status, effort=size,
                         effort_hours=hours, **fields)


def snap(items, fields=BOTH):
    return base.Snapshot(items=list(items), provider="test", source="memory", taken_at=AS_OF,
                         fields=list(fields))


# --- parsing and the basis ------------------------------------------------------


@pytest.mark.parametrize("text, hours", [("1.5", 1.5), ("40", 40.0), ("2h", 2.0),
                                         ("0.5 hours", 0.5), (3, 3.0), (".5", 0.5)])
def test_hours_parse(text, hours):
    assert effort.parse_hours(text) == hours


@pytest.mark.parametrize("text", ["", "M", "about 3", "-1", None, True])
def test_not_hours(text):
    assert effort.parse_hours(text) is None


def test_auto_picks_hours_only_when_the_register_serves_them():
    assert effort.resolve("auto", BOTH) == "hours"
    assert effort.resolve("auto", ("status", "effort")) == "size"
    assert effort.resolve("size", BOTH) == "size"
    assert effort.resolve("hours", ("status", "effort")) == "hours"
    assert effort.resolve(None, BOTH) == "hours"


# --- kpis ---------------------------------------------------------------------


def test_kpis_compute_from_hours_with_provenance():
    items = [item("A", "m", "4"), item("B", "s", "1.5", base.COMPLETED), item("C", "l", "12")]
    metrics = kpi.compute(snap(items))
    assert metrics.get("effort-basis").value == "hours"
    total = metrics.get("total-effort")
    assert (total.value, total.unit, total.kind) == (17.5, "hours", "measured")
    assert "3 from the register's hours" in total.basis
    assert metrics.get("completed-effort").value == 1.5
    assert metrics.get("percent-complete-by-effort").value == round(100 * 1.5 / 17.5, 1)


def test_a_row_with_only_a_size_word_falls_back_through_the_scale_and_is_inferred():
    items = [item("A", "m", "4"), item("B", "s", "")]       # s = 1 on the default scale
    total = kpi.compute(snap(items)).get("total-effort")
    assert total.value == 5.0 and total.kind == "inferred"
    assert "1 size word(s) through policy.roadmap.effortScale, read as hours" in total.basis


def test_a_row_with_neither_is_named_and_not_computable():
    items = [item("A", "m", "4"), item("NONE", "", "")]
    total = kpi.compute(snap(items)).get("total-effort")
    assert not total.computable
    assert "hours or a size word for 1 item(s): NONE" in total.missing_inputs[0]


def test_an_unreadable_hours_value_is_named():
    total = kpi.compute(snap([item("A", "m", "lots")])).get("total-effort")
    assert not total.computable and "A ('lots')" in total.missing_inputs[0]


def test_size_basis_keeps_points():
    items = [item("A", "m", "4"), item("B", "s", "1.5")]
    metrics = kpi.compute(snap(items), effort_basis="size")
    assert metrics.get("effort-basis").value == "size"
    total = metrics.get("total-effort")
    assert (total.value, total.unit) == (4.0, "points")


def test_a_register_without_hours_reads_exactly_as_before():
    metrics = kpi.compute(snap([item("A", "m"), item("B", "s")],
                               fields=("status", "effort")))
    assert metrics.get("total-effort").as_dict()["unit"] == "points"
    assert metrics.get("total-effort").value == 4.0


def test_items_over_max_hours_are_flagged_to_split():
    items = [item("A", "xl", "48"), item("B", "m", "40"), item("C", "xl", "60", base.COMPLETED)]
    metric = kpi.compute(snap(items), max_item_hours=40).get("items-over-max-hours")
    assert metric.value == 1 and "A (48 h)" in metric.basis
    assert kpi.compute(snap(items)).get("items-over-max-hours") is None


# --- pace -----------------------------------------------------------------------


def done(n, day, item_id, **effort_fields):
    return LedgerRecord(record_id="TR-%03d" % n, item_id=item_id, completed=day,
                        result="completed", **effort_fields)


def source(records):
    return pace.CompletionSource(pace.from_ledger(records, STATUSES), "ledger")


def test_pace_runs_in_hours_from_the_ledger_hours():
    live = [item("A", "m", "10"), item("B", "s", "6", base.BLOCKED)]
    records = [done(1, "2026-11-02", "OLD-1", effort_hours="8", effort_actual="10h"),
               done(2, "2026-11-10", "OLD-2", effort_hours="4", effort_actual="3h30m")]
    report = pace.compute(SHIP, snap(live), source(records), trailing_weeks=4)
    data = report.as_dict()
    assert data["effortBasis"] == "hours" and data["effortUnit"] == "hours"
    assert data["remaining"] == {"items": 2, "hours": 16.0}
    assert data["blocked"]["hours"] == 6.0 and data["blocked"]["shareOfHours"] == 37.5
    assert report.trailing["hours"] == 12 / 4
    assert report.trailing["actualHours"] == round(13.5 / 4, 2)
    assert data["effort"]["trailing"]["sources"] == {"ledger": 2}
    assert data["effort"]["remaining"]["kind"] == "measured"
    assert set(report.unit_verdicts) == {"items", "hours"}
    text = report.render()
    assert "16.0 hours remain" in text and "hours/week" in text


def test_trailing_hours_fall_back_to_the_register_then_the_size_word():
    live = [item("A", "m", "10"), item("OLD-1", "m", "5", base.COMPLETED),
            item("OLD-2", "s", "", base.COMPLETED)]
    records = [done(1, "2026-11-02", "OLD-1"), done(2, "2026-11-10", "OLD-2")]
    report = pace.compute(SHIP, snap(live), source(records), trailing_weeks=4)
    assert report.trailing["hours"] == (5 + 1) / 4
    assert report.effort["trailing"]["kind"] == "inferred"
    assert "actualHours" not in report.trailing


def test_a_completion_sized_nowhere_names_both_ledger_columns():
    records = [done(1, "2026-11-02", "GONE")]
    report = pace.compute(SHIP, snap([item("A", "m", "10")]), source(records))
    assert report.trailing["hours"] is None
    assert "Hours and Effort column" in report.missing["trailing.hours"][0]


def test_size_basis_pace_is_unchanged():
    report = pace.compute(SHIP, snap([item("A", "m", "10")]), source([]), effort_basis="size")
    assert report.as_dict()["remaining"] == {"items": 1, "points": 3.0}


# --- the register and the ledger carry hours --------------------------------------


def test_a_csv_register_reads_loe_and_hours(tmp_path):
    path = tmp_path / "register.csv"
    path.write_text("Code,Title,Status,LOE,Hours\nA,First,Queued,M,4\nB,Second,Done,S,1.5\n",
                    encoding="utf-8")
    register = CsvWorkRegister(source=str(path), mapping=Mapping.from_policy(
        {"fieldMappings": {"effort": "LOE", "effort_hours": "Hours"}}))
    snapshot = register.snapshot()
    assert {"effort", "effort_hours"} <= set(snapshot.fields)
    assert [(i.effort, i.effort_hours) for i in snapshot.items] == [("M", "4"), ("S", "1.5")]
    assert kpi.compute(snapshot).get("total-effort").value == 5.5


def test_create_item_sizes_in_hours(tmp_path):
    path = tmp_path / "register.csv"
    path.write_text("id,title,status,written_status,effort,hours\n", encoding="utf-8")
    register = CsvWorkRegister(source=str(path))
    created = register.create_item({"id": "N-1", "title": "New", "effort": "S",
                                    "effort_hours": "2.5"})
    assert (created.effort, created.effort_hours) == ("S", "2.5")


@pytest.mark.parametrize("fmt", ["markdown", "csv", "jsonl"])
def test_the_ledger_round_trips_hours(tmp_path, fmt):
    path = tmp_path / ("ledger." + {"markdown": "md"}.get(fmt, fmt))
    if fmt == "markdown":
        path.write_text("| Record | Item | Completed | Result | Evidence | Corrects | Effort "
                        "| Hours |\n|---|---|---|---|---|---|---|---|\n", encoding="utf-8")
    elif fmt == "csv":
        path.write_text("recordId,itemId,completed,result,evidence,corrects,effort,"
                        "effortHours\n", encoding="utf-8")
    book = TerminalLedger(str(path), fmt=fmt, writers=["dispatch-closeout"])
    book.append(LedgerRecord(record_id="TR-001", item_id="A", completed="2026-11-18",
                             result="completed", effort="M", effort_hours="4"),
                actor="dispatch-closeout")
    [read] = book.records()
    assert (read.effort, read.effort_hours) == ("M", "4")


# --- policy -------------------------------------------------------------------------


def test_policy_accepts_the_bases_and_a_limit():
    assert policy_mod.effort_problems("hours", 40) == []
    assert policy_mod.effort_problems("auto", 0) == []
    assert policy_mod.effort_problems("size", 37.5) == []


@pytest.mark.parametrize("basis, limit", [("points", 0), ("auto", -1), ("auto", True),
                                          ("auto", "40")])
def test_policy_refuses_bad_values(basis, limit):
    assert policy_mod.effort_problems(basis, limit)


def test_policy_accessors_fall_back_when_unusable():
    loaded = policy_mod.load({"roadmap": {"effortBasis": "weeks", "maxItemHours": "x"}})
    assert loaded.effort_basis == "auto" and loaded.max_item_hours == 0
    loaded = policy_mod.load({"roadmap": {"effortBasis": "hours", "maxItemHours": 40}})
    assert loaded.effort_basis == "hours" and loaded.max_item_hours == 40
