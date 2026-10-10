"""The time log: each task row's working time, measured by the machine clock.

A dispatch's rows are listed once, into ``Timing.<sprint>.jsonl`` in the closeOuts
role; each row's start, waits and end are stamped by the clock, never typed. A row's
working time is end − start − waits, and a row the log cannot measure says so.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import PLUGIN_ROOT
from tools.governance import timing
from tools.governance.errors import GovernanceError

ROOT = Path(PLUGIN_ROOT)
PREFLIGHT = str(ROOT / "scripts" / "virtuoso_preflight.py")
REGISTRY_CLI = str(ROOT / "scripts" / "virtuoso_registry.py")

T = dt.datetime(2026, 9, 30, 14, 0, tzinfo=dt.timezone.utc)


def at(minutes: float) -> str:
    return timing.stamp(T + dt.timedelta(minutes=minutes))


def plan(*ids, **fields):
    return {"event": "open", "at": at(0),
            "rows": [dict({"id": i, "title": "row %d" % i}, **fields) for i in ids]}


def ev(event, row, minutes, **extra):
    return dict({"event": event, "row": row, "at": at(minutes)}, **extra)


def run(*args):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True,
                          encoding="utf-8", env=dict(os.environ))


# --- measuring ---------------------------------------------------------------------------

def test_working_minutes_are_end_minus_start():
    found = timing.rows([plan(1), ev("start", 1, 0), ev("end", 1, 12)], T)
    assert found[0].working == 12 and found[0].measured


def test_a_wait_is_shown_and_left_out_of_working_time():
    events = [plan(1), ev("start", 1, 0), ev("wait", 1, 5), ev("resume", 1, 185),
              ev("end", 1, 192)]
    row = timing.rows(events, T)[0]
    assert row.working == 12
    assert row.waited == 180
    assert "12 min worked · waited 3h 00m" in timing.render_status([row], T)


def test_a_row_missing_its_start_or_end_is_not_measured():
    events = [plan(1, 2, 3), ev("end", 1, 10), ev("start", 2, 0),
              ev("start", 3, 30), ev("end", 3, 20)]
    found = {row.id: row for row in timing.rows(events, T + dt.timedelta(hours=1))}
    for row_id in (1, 2, 3):
        assert found[row_id].measured is False and found[row_id].working is None, row_id
    status = timing.render_status(list(found.values()), T)
    assert "1. row 1 — not measured" in status
    assert "3. row 3 — not measured" in status


def test_status_is_the_same_after_a_reread(tmp_path):
    path = str(tmp_path / "Timing.X-1.jsonl")
    timing.append(path, {"event": "open", "rows": [{"id": 1, "title": "a"},
                                                  {"id": 2, "title": "b"}]}, T)
    timing.append(path, {"event": "start", "row": 1}, T)
    timing.append(path, {"event": "wait", "row": 1}, T + dt.timedelta(minutes=3))
    moment = T + dt.timedelta(minutes=40)
    first = timing.render_status(timing.rows(timing.load(path), moment), moment)
    second = timing.render_status(timing.rows(timing.load(path), moment), moment)
    assert first == second
    assert "waiting on the owner" in first


def test_stamps_are_utc(tmp_path):
    path = str(tmp_path / "Timing.X-1.jsonl")
    local = dt.datetime(2026, 3, 8, 1, 30, tzinfo=dt.timezone(dt.timedelta(hours=-6)))
    written = timing.append(path, {"event": "open", "rows": []}, local)
    assert written["at"] == "2026-03-08T07:30:00Z"
    timing.append(path, {"event": "start", "row": 1})
    assert all(event["at"].endswith("Z") for event in timing.load(path))


def test_a_second_start_on_a_running_row_is_refused():
    events = [plan(1), ev("start", 1, 0)]
    with pytest.raises(GovernanceError, match="row 1 is already"):
        timing.check(events, "start", 1)


def test_an_unknown_row_is_refused():
    with pytest.raises(GovernanceError, match="row 9 is not in this sprint's plan"):
        timing.check([plan(1, 2)], "start", 9)


def test_a_missing_close_outs_directory_is_refused_not_created(tmp_path):
    path = str(tmp_path / "absent" / "Timing.X-1.jsonl")
    with pytest.raises(GovernanceError, match="closeout --item"):
        timing.append(path, {"event": "open", "rows": []}, T)
    assert not (tmp_path / "absent").exists()


@pytest.mark.parametrize("bad", [{"estimate": "abc"}, {"estimate": -5}, {"estimate": True},
                                 {"id": True}, {"id": "1"}, {"parallel": "false"},
                                 {"owner": 7}, {"class": "big"}, {"model": 7},
                                 {"specRevision": 3}, {"group": ["g"]},
                                 {"class": "repeat", "timebox": 30, "onTimebox": "stop"},
                                 {"class": "frontier", "timebox": 30},
                                 {"class": "frontier", "onTimebox": "stop"},
                                 {"class": "frontier", "timebox": 0, "onTimebox": "stop"},
                                 {"class": "frontier", "timebox": 0.4, "onTimebox": "stop"},
                                 {"class": "frontier", "timebox": "2h", "onTimebox": "stop"},
                                 {"class": "frontier", "timebox": 30, "onTimebox": "stop",
                                  "estimate": 30},
                                 {"splitFrom": 1}])
def test_a_row_value_the_log_cannot_read_back_is_refused(bad):
    with pytest.raises(GovernanceError, match="row 'a'"):
        timing.plan_rows([dict({"id": 1, "title": "a"}, **bad)])


def test_a_malformed_row_in_the_log_is_skipped_not_fatal():
    events = [{"event": "open", "at": at(0), "rows": [
        {"id": 1, "title": "a", "estimate": "abc"}, {"id": 2, "title": "b"}]},
        {"event": "add", "at": at(1), "rows": None}, ev("start", 2, 0)]
    assert [row.id for row in timing.rows(events, T)] == [2]


def test_an_append_after_a_cut_off_line_starts_a_new_line(tmp_path):
    path = tmp_path / "Timing.X-1.jsonl"
    timing.append(str(path), {"event": "open", "rows": [{"id": 1, "title": "a"}]}, T)
    with open(path, "ab") as handle:
        handle.write(b'{"event": "sta')                   # a write cut off mid-line
    timing.append(str(path), {"event": "start", "row": 1}, T)
    lines = path.read_bytes().split(b"\n")
    assert lines[1] == b'{"event": "sta' and lines[2].startswith(b'{"event": "start"')
    with pytest.raises(GovernanceError, match="line 2 is not a JSON event"):
        timing.load(str(path))


def test_a_line_that_is_not_an_object_is_named(tmp_path):
    path = tmp_path / "Timing.X-1.jsonl"
    path.write_text('{"event": "open", "rows": []}\n[1, 2]\n', encoding="utf-8")
    with pytest.raises(GovernanceError, match="line 2 is not a JSON event \\(not an object\\)"):
        timing.load(str(path))


def test_a_log_opens_once_and_every_row_is_numbered():
    with pytest.raises(GovernanceError, match="already open"):
        timing.check([plan(1)], "open")
    with pytest.raises(GovernanceError, match="has no id"):
        timing.plan_rows([{"title": "unnumbered"}])
    with pytest.raises(GovernanceError, match="never carries a time"):
        timing.plan_rows([{"id": 1, "title": "a", "minutes": 12}])


# --- the CLI -----------------------------------------------------------------------------

@pytest.fixture
def workspace(project):
    assert run(PREFLIGHT, "--root", str(project), "--mode", "create",
               "--authorize").returncode == 0
    return project


def timing_cli(root, *args, actor="virtuoso"):
    return run(REGISTRY_CLI, "--root", str(root), "--actor", actor, "timing",
               "--sprint", "HB-9", *args)


def rows_file(root, rows) -> str:
    path = root / "rows.json"
    path.write_text(json.dumps(rows), encoding="utf-8")
    return str(path)


def log_path(root) -> Path:
    found = list(root.rglob("Timing.HB-9.jsonl"))
    assert len(found) == 1, found
    return found[0]


def test_the_cli_appends_events_with_the_real_clock(workspace):
    listing = rows_file(workspace, [{"id": 1, "title": "Load spec", "estimate": 10},
                                    {"id": 2, "title": "Edit", "tier": "bounded",
                                     "estimate": 30}])
    for args in (("--open", "--rows-file", listing), ("--start", "2"), ("--end", "2")):
        completed = timing_cli(workspace, *args)
        assert completed.returncode == 0, completed.stderr
    lines = log_path(workspace).read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["event"] for line in lines] == ["open", "start", "end"]
    clock = dt.datetime.now(dt.timezone.utc)
    for line in lines:
        stamped = timing.parse_stamp(json.loads(line)["at"])
        assert abs((clock - stamped).total_seconds()) < 60
    status = timing_cli(workspace, "--status")
    assert status.returncode == 0 and "✓ 2. Edit [bounded]" in status.stdout


def test_the_cli_accepts_no_time(workspace):
    completed = run(REGISTRY_CLI, "timing", "--help")
    assert completed.returncode == 0
    for flag in ("--at", "--time", "--minutes", "--duration"):
        assert flag not in completed.stdout.split(), flag
        assert flag + " " not in completed.stdout, flag


def test_the_cli_refuses_an_actor_that_may_not_write_close_outs(workspace):
    listing = rows_file(workspace, [{"id": 1, "title": "Load spec", "estimate": 10}])
    assert timing_cli(workspace, "--open", "--rows-file", listing).returncode == 0
    before = log_path(workspace).read_bytes()
    refused = timing_cli(workspace, "--start", "1", actor="roadmap-status")
    assert refused.returncode == 3
    assert "may not write the closeOuts role" in refused.stderr
    assert log_path(workspace).read_bytes() == before


def test_the_cli_refuses_a_second_start_and_an_unknown_row(workspace):
    listing = rows_file(workspace, [{"id": 1, "title": "Load spec", "estimate": 10}])
    assert timing_cli(workspace, "--open", "--rows-file", listing).returncode == 0
    assert timing_cli(workspace, "--start", "1").returncode == 0
    again = timing_cli(workspace, "--start", "1")
    assert again.returncode == 3 and "row 1 is already" in again.stderr
    unknown = timing_cli(workspace, "--end", "7")
    assert unknown.returncode == 3 and "row 7 is not in this sprint's plan" in unknown.stderr


# =============================================================================
# HB-2 — each row is priced when it is listed
# =============================================================================

UTC = dt.timezone.utc


def past(*workings, kind="", tier="", effort=""):
    return [timing.Row(id=i + 1, kind=kind, tier=tier, effort=effort, working=w)
            for i, w in enumerate(workings)]


def priced_plan(*rows):
    """An open event whose rows carry ``(predicted, parallel)``."""
    return {"event": "open", "at": at(0), "rows": [
        {"id": i + 1, "title": "row %d" % (i + 1), "predicted": minutes, "basis": "estimated",
         "parallel": parallel} for i, (minutes, parallel) in enumerate(rows)]}


def test_a_kind_with_three_runs_is_priced_by_its_median():
    history = past(30, 35, 38, 40, 41, 45, kind="merge-slot")
    row = timing.Row(id=1, kind="merge-slot", estimate=90)
    assert timing.price(row, history) == (39, "median of 6 runs")


def test_fewer_than_three_falls_back_to_tier_and_effort():
    history = (past(100, 110, kind="merge-slot", tier="bounded")
               + past(10, 12, 20, tier="mechanical", effort="low"))
    row = timing.Row(id=1, kind="merge-slot", tier="mechanical")   # effort from the tier
    assert timing.price(row, history) == (12, "median of 3 runs")


def test_with_no_history_every_row_reads_estimated():
    assert timing.price(timing.Row(id=1, estimate=90), []) == (90, "estimated")
    specs = timing.price_rows([{"id": 1, "title": "Implement", "estimate": 90},
                               {"id": 2, "title": "Merge", "kind": "merge-slot",
                                "estimate": 40}], [])
    found = timing.rows([{"event": "open", "at": at(0), "rows": specs}], T)
    status = timing.render_status(found, T, UTC)
    assert status.splitlines()[1].endswith("90 min (estimated)")
    assert status.splitlines()[2].endswith("40 min (estimated)")
    assert "median" not in status


def test_open_refuses_a_row_it_cannot_price():
    with pytest.raises(GovernanceError, match=r"rows 1, 3 have no history"):
        timing.price_rows([{"id": 1, "title": "a"}, {"id": 2, "title": "b", "estimate": 5},
                           {"id": 3, "title": "c"}], [])


def test_remaining_sums_unfinished_sequential_rows():
    events = [priced_plan((10, False), (20, False), (15, False), (35, True)),
              ev("start", 1, 0), ev("end", 1, 10), ev("start", 2, 10)]
    moment = T + dt.timedelta(minutes=18)          # row 2: 8 of 20 worked
    found = timing.rows(events, moment)
    assert timing.remaining(found, moment) == (27, [2, 3], [4])
    head = timing.header(found, moment, UTC)
    assert "Remaining 27 min (sequential rows 2, 3; row 4 parallel, excluded)" in head
    assert "Now: row 2 running." in head
    # A running row past its prediction contributes nothing, never a negative figure.
    late = T + dt.timedelta(minutes=40)
    assert timing.remaining(timing.rows(events, late), late)[0] == 15


def test_an_added_row_takes_the_next_number_and_counts():
    events = [priced_plan(*[(10, False)] * 14)]
    before = timing.remaining(timing.rows(events, T), T)[0]
    added = timing.plan_rows([{"title": "Root-cause the review finding"}],
                             timing.rows(events), added=True)
    assert added[0]["id"] == 15
    events.append({"event": "add", "at": at(5),
                   "rows": [dict(added[0], predicted=25, basis="estimated")]})
    found = timing.rows(events, T)
    assert found[-1].added
    assert "□ +15. Root-cause the review finding" in timing.render_status(found, T, UTC)
    assert timing.remaining(found, T)[0] == before + 25


def test_a_waiting_row_holds_its_remainder_and_the_finish_moves():
    events = [priced_plan((30, False)), ev("start", 1, 0), ev("wait", 1, 10)]
    early, later = T + dt.timedelta(minutes=20), T + dt.timedelta(minutes=80)
    assert timing.remaining(timing.rows(events, early), early)[0] == 20
    assert timing.remaining(timing.rows(events, later), later)[0] == 20
    first = timing.header(timing.rows(events, early), early, UTC)
    second = timing.header(timing.rows(events, later), later, UTC)
    assert "est. finish 14:40 local (+00:00) · 14:40 UTC" in first
    assert "est. finish 15:40 local (+00:00) · 15:40 UTC" in second
    assert "Now: row 1 waiting on the owner." in second


def test_the_finish_is_shown_in_the_local_zone_and_utc():
    events = [priced_plan((30, False))]
    chicago = dt.timezone(dt.timedelta(hours=-5))
    assert "est. finish 09:30 local (-05:00) · 14:30 UTC" in timing.header(
        timing.rows(events, T), T, chicago)


def test_kinds_are_normalized():
    assert timing.normal_kind("Merge slot") == "merge-slot"
    assert timing.normal_kind("  merge_SLOT ") == "merge-slot"
    events = [{"event": "open", "at": at(0), "rows": [
        {"id": 1, "title": "a", "kind": "Merge slot"},
        {"id": 2, "title": "b", "kind": "merge-slot"},
        {"id": 3, "title": "c", "kind": "MERGE_SLOT"}]}]
    for row_id in (1, 2, 3):
        events += [ev("start", row_id, 10 * row_id), ev("end", row_id, 10 * row_id + 5)]
    history = [row for row in timing.rows(events) if row.measured]
    assert timing.kinds(history) == {"merge-slot": 3}
    row = timing._row({"id": 9, "title": "x", "kind": "Merge Slot"})
    assert timing.price(row, history) == (5, "median of 3 runs")


def test_all_parallel_rows_leave_no_sequential_remainder():
    found = timing.rows([priced_plan((20, True), (30, True))], T)
    assert timing.remaining(found, T) == (0, [], [1, 2])
    head = timing.header(found, T, UTC)
    assert "Remaining 0 min (no sequential rows remain; rows 1, 2 parallel, excluded)" in head


def test_the_current_run_prices_its_later_rows(tmp_path):
    path = str(tmp_path / "Timing.RUN-1.jsonl")
    timing.append(path, {"event": "open", "rows": timing.price_rows(
        [{"id": i, "title": "review %d" % i, "kind": "review", "estimate": 30}
         for i in (1, 2, 3)], [])}, T)
    for row_id, (begin, end) in zip((1, 2, 3), ((0, 12), (12, 26), (26, 36))):
        timing.append(path, {"event": "start", "row": row_id}, T + dt.timedelta(minutes=begin))
        timing.append(path, {"event": "end", "row": row_id, "result": "done"},
                      T + dt.timedelta(minutes=end))
    later = timing.price_rows([{"id": 4, "title": "review 4", "kind": "review"}],
                              timing.history(str(tmp_path)))
    assert (later[0]["predicted"], later[0]["basis"]) == (12, "median of 3 runs")


def test_the_kinds_command_lists_names_in_use(workspace):
    listing = rows_file(workspace, [
        {"id": i, "title": "merge %d" % i, "kind": "merge-slot", "estimate": 20}
        for i in (1, 2, 3)] + [{"id": 4, "title": "gate", "kind": "gate-3", "estimate": 20}])
    opened = timing_cli(workspace, "--open", "--rows-file", listing)
    assert opened.returncode == 0, opened.stderr
    assert "kinds in use: none yet" in opened.stdout
    for row_id in ("1", "2", "3", "4"):
        assert timing_cli(workspace, "--start", row_id).returncode == 0
        assert timing_cli(workspace, "--end", row_id).returncode == 0
    listed = run(REGISTRY_CLI, "--root", str(workspace), "timing", "--kinds", "--json")
    assert listed.returncode == 0, listed.stderr
    assert json.loads(listed.stdout)["kinds"] == {"merge-slot": 3, "gate-3": 1}
    shown = run(REGISTRY_CLI, "--root", str(workspace), "timing", "--kinds")
    assert "merge-slot" in shown.stdout and "3 measured run(s)" in shown.stdout


def test_the_header_counts_in_minutes_past_an_hour():
    found = timing.rows([priced_plan((60, False), (65, False))], T)
    assert "Remaining 125 min (sequential rows 1, 2)" in timing.header(found, T, UTC)


def test_only_rows_that_ran_to_done_price_later_rows(tmp_path):
    events = [{"event": "open", "at": at(0), "rows": [
        {"id": i, "title": "m%d" % i, "kind": "merge-slot"} for i in (1, 2, 3)]}]
    events += [ev("start", 1, 0), ev("end", 1, 30, result="done"),
               ev("start", 2, 30), ev("end", 2, 31, result="cancelled"),
               ev("start", 3, 31), ev("end", 3, 32, result="blocked")]
    write_log = tmp_path / "Timing.R-1.jsonl"
    write_log.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    assert [row.id for row in timing.history(str(tmp_path))] == [1]


def test_a_damaged_old_log_is_named_and_left_out_not_fatal(tmp_path):
    good = [{"event": "open", "at": at(0), "rows": [{"id": 1, "title": "a"}]},
            ev("start", 1, 0), ev("end", 1, 9)]
    (tmp_path / "Timing.GOOD.jsonl").write_text(
        "".join(json.dumps(e) + "\n" for e in good), encoding="utf-8")
    (tmp_path / "Timing.CUT.jsonl").write_text('{"event": "op', encoding="utf-8")
    (tmp_path / "Timing.BYTES.jsonl").write_bytes(b"\xff\xfe\x00")
    skipped = []
    assert [row.working for row in timing.history(str(tmp_path), skipped)] == [9]
    assert len(skipped) == 2 and any("Timing.CUT" in s for s in skipped)
    assert any("not UTF-8" in s for s in skipped)


def test_halves_round_up_to_whole_minutes():
    assert timing.price(timing.Row(id=1, estimate=12.5), []) == (13, "estimated")
    assert timing.price(timing.Row(id=1, kind="k"), past(12, 13, 14, 15, kind="k")) == \
        (14, "median of 4 runs")


def test_a_row_with_no_prediction_is_named_unpriced():
    found = timing.rows([plan(1, 2)], T)       # a log written before rows were priced
    head = timing.header(found, T, UTC)
    assert "rows 1, 2 unpriced, counted as 0" in head
    assert timing.render_status(found, T, UTC).splitlines()[1].endswith("unpriced")


# =============================================================================
# HB-3 — the close-out, the ledger and kpis read the time log
# =============================================================================

from tools.governance import learning  # noqa: E402


def worked(rows, item=""):
    """An open event, then a start and an end per row: ``(predicted, minutes, parallel)``."""
    events = [{"event": "open", "at": at(0), "rows": [
        {"id": i + 1, "title": "row %d" % (i + 1), "predicted": p, "basis": "estimated",
         "parallel": par, "item": item} for i, (p, _, par) in enumerate(rows)]}]
    clock = 0
    for i, (_, minutes, _) in enumerate(rows):
        events += [ev("start", i + 1, clock), ev("end", i + 1, clock + minutes, result="done")]
        clock += minutes
    return events


def write_log(directory, name, events):
    path = Path(directory) / ("Timing.%s.jsonl" % name)
    path.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
    return path


def test_the_summary_estimate_is_the_first_listing_total():
    events = worked([(60, 70, False), (90, 95, False), (100, 107, False), (35, 40, True)])
    result = timing.summary(events)
    assert (result["estimate"], result["actual"]) == ("4h10m", "4h32m")
    assert round(learning.hours(result["estimate"]), 4) == 4.1667
    assert round(learning.hours(result["actual"]), 4) == 4.5333
    table = timing.summary_markdown(result)
    assert "## Time" not in table and "| 4 | row 4 |" in table
    assert "Estimate 4h10m" in table and "Actual 4h32m" in table


def test_an_added_row_counts_in_the_actual_but_not_the_estimate():
    events = worked([(60, 60, False)])
    events.append({"event": "add", "at": at(70), "rows": [
        {"id": 2, "title": "fix", "predicted": 20, "basis": "estimated"}]})
    events += [ev("start", 2, 70), ev("end", 2, 95)]
    result = timing.summary(events)
    assert (result["estimate"], result["actual"]) == ("1h00m", "1h25m")


def test_the_summary_splits_by_item():
    events = worked([(30, 40, False), (50, 45, False)])
    events[0]["rows"][0]["item"], events[0]["rows"][1]["item"] = "HB-1", "HB-2"
    assert (timing.summary(events, "HB-2")["estimate"],
            timing.summary(events, "HB-2")["actual"]) == ("50m", "45m")
    assert timing.summary(events)["estimate"] == "1h20m"
    with pytest.raises(GovernanceError, match="no rows for item HB-9"):
        timing.summary(events, "HB-9")


def test_a_row_over_three_times_its_prediction_is_flagged_as_an_unseen_wait(tmp_path):
    events = worked([(10, 31, False), (10, 30, False)])
    found = timing.rows(events)
    assert found[0].flagged and not found[1].flagged      # 31 > 3 × 10; 30 is not
    write_log(tmp_path, "RUN-1", events)
    assert [row.working for row in timing.history(str(tmp_path))] == [30]
    result = timing.summary(events)
    assert result["flagged"] == [1]
    assert "possible unseen wait" in timing.summary_markdown(result)
    with pytest.raises(GovernanceError, match="row 2 is not flagged"):
        timing.check(events, "confirm", 2)
    timing.check(events, "confirm", 1)
    write_log(tmp_path, "RUN-1", events + [ev("confirm", 1, 99)])
    assert sorted(row.working for row in timing.history(str(tmp_path))) == [30, 31]


def test_kpis_reports_the_timing_figures(workspace):
    closeouts = workspace.joinpath(*json.loads(
        (workspace / "Virtuoso" / "workspace-layout.json").read_text(encoding="utf-8")
    )["roles"]["closeOuts"]["path"].split("/"))

    def figures():
        completed = run(REGISTRY_CLI, "--root", str(workspace), "kpis", "--json")
        assert completed.returncode == 0, completed.stderr
        learning_group = json.loads(completed.stdout)["learning"]
        return ({m["name"]: m for m in learning_group["metrics"]},
                learning_group["provenance"])

    found, _ = figures()
    for name in timing.TIMING_METRICS:
        assert found[name]["computable"] is False
        assert "3 closed time logs" in found[name]["missingInputs"][0]
    write_log(closeouts, "R-1", worked([(10, 12, False)]))
    write_log(closeouts, "R-2", worked([(10, 12, False)]))
    write_log(closeouts, "R-OPEN", worked([(10, 12, False)])[:2])     # still running
    found, _ = figures()
    assert "(2 found)" in found["row-error"]["missingInputs"][0]
    write_log(closeouts, "R-3", worked([(10, 12, False)]))
    (closeouts / "Timing.R-CUT.jsonl").write_text('{"event": "op', encoding="utf-8")
    found, provenance = figures()
    assert found["row-error"]["value"] == 0.2 and found["total-error"]["value"] == 0.2
    assert found["added-share"]["value"] == 0.0
    assert provenance["timeLogsClosed"] == 3 and provenance["timeLogs"]


def test_the_ledger_takes_the_summary_values(workspace):
    layout = json.loads((workspace / "Virtuoso" / "workspace-layout.json")
                        .read_text(encoding="utf-8"))["roles"]
    closeouts = workspace.joinpath(*layout["closeOuts"]["path"].split("/"))
    register = workspace.joinpath(*layout["workRegister"]["path"].split("/"))
    for item, predicted, minutes in (("A", 60, 90), ("B", 120, 180), ("C", 60, 60)):
        write_log(closeouts, item, worked([(predicted, minutes, False)], item=item))
        summary = run(REGISTRY_CLI, "--root", str(workspace), "timing", "--sprint", item,
                      "--summary", "--json")
        assert summary.returncode == 0, summary.stderr
        values = json.loads(summary.stdout)
        with open(register, "a", encoding="utf-8", newline="") as handle:
            handle.write("%s,%s,1,Queued,Full Spec,,S,,,,,,,,,\n" % (item, item))
        completed = run(REGISTRY_CLI, "--root", str(workspace), "--actor", "pointer-closeout",
                        "record-completion", "--item", item, "--date", "2026-09-30",
                        "--result", "shipped", "--estimate", values["estimate"],
                        "--actual", values["actual"], "--apply")
        assert completed.returncode == 0, completed.stdout + completed.stderr
    ledger = workspace.joinpath(*layout["terminalLedger"]["path"].split("/"))
    text = ledger.read_text(encoding="utf-8")
    for estimate, actual in (("1h00m", "1h30m"), ("2h00m", "3h00m"), ("1h00m", "1h00m")):
        assert estimate in text and actual in text
    learning_group = json.loads(run(REGISTRY_CLI, "--root", str(workspace), "kpis",
                                    "--json").stdout)["learning"]
    figure = {m["name"]: m for m in learning_group["metrics"]}["effort-calibration"]
    assert figure["value"] == 1.5


def test_the_cli_confirms_a_flagged_row(workspace):
    listing = rows_file(workspace, [{"id": 1, "title": "Load spec", "estimate": 10}])
    assert timing_cli(workspace, "--open", "--rows-file", listing).returncode == 0
    refused = timing_cli(workspace, "--confirm", "1")
    assert refused.returncode == 3 and "not flagged" in refused.stderr
    shown = run(REGISTRY_CLI, "--root", str(workspace), "timing", "--sprint", "HB-9",
                "--summary")
    assert shown.returncode == 0 and "| Row | Task |" in shown.stdout


def test_the_timing_figures_are_documented():
    contract = (ROOT / "references" / "registry-contract.md").read_text(encoding="utf-8")
    for name in timing.TIMING_METRICS:
        assert "| `%s` |" % name in contract, name
    assert "### The time log" in contract


def section(text, start, end):
    begin = text.index(start)
    return text[begin:text.index(end, begin + len(start))]


def test_the_close_out_takes_time_from_the_log_documented():
    template = (ROOT / "skills" / "pointer-closeout" / "assets" / "CloseOut.template.md"
                ).read_text(encoding="utf-8")
    assert "## Time" in template
    assert "timing --summary" in [line for line in template.splitlines()
                                  if line.startswith("runtime:")][0]
    closeout = (ROOT / "skills" / "pointer-closeout" / "SKILL.md").read_text(encoding="utf-8")
    assert "timing --summary --json" in section(closeout, "--state executed", "Step 6 verifies")
    assert "timing --summary --json" in section(closeout, "### Step 3", "### Step 4")
    assert "timing --summary --json" in section(closeout, "### Step 6", "### On partial failure")
    assert "the spec's effort, as a duration" not in closeout
    virtuoso = (ROOT / "skills" / "virtuoso" / "SKILL.md").read_text(encoding="utf-8")
    assert "Timing.<SPRINT-ID>.jsonl" in section(virtuoso, "sprint_guards artifacts-exist",
                                                 "For a held plan")
    effort = (ROOT / "skills" / "effort-levels" / "SKILL.md").read_text(encoding="utf-8")
    assert "timing" in effort and "effort-calibration" in effort


def test_a_log_without_items_is_one_items_run():
    events = worked([(30, 40, False)])
    result = timing.summary(events, "HB-1")
    assert (result["estimate"], result["actual"], result["complete"]) == ("30m", "40m", True)


def test_a_partial_log_says_so_and_a_cancelled_unrun_row_does_not():
    events = worked([(30, 40, False)])
    events[0]["rows"] += [{"id": 2, "title": "lost start", "predicted": 20},
                          {"id": 3, "title": "never run", "predicted": 10}]
    events += [ev("end", 2, 60), ev("end", 3, 61, result="cancelled")]
    result = timing.summary(events)
    assert result["complete"] is False and result["notMeasured"] == [2]
    assert "Partial: rows 2" in timing.summary_markdown(result)
    whole = timing.summary(events[:1] + events[1:3] + [ev("end", 3, 61, result="cancelled")])
    assert whole["complete"] is False            # row 2 never ended: still partial
    done = worked([(30, 40, False)])
    done[0]["rows"].append({"id": 2, "title": "never run", "predicted": 10})
    done.append(ev("end", 2, 50, result="cancelled"))
    assert timing.summary(done)["complete"] is True


# =============================================================================
# VIR-020 — the fields an append-only log can never backfill
# =============================================================================

FIXTURES = ROOT / "scripts" / "fixtures"
FRONTIER = {"class": "frontier", "timebox": 120, "onTimebox": "stop and file an issue"}


def test_new_fields_round_trip(workspace):
    listing = rows_file(workspace, [
        dict({"id": 1, "title": "Spike the parser", "tier": "cross-cutting",
              "model": "claude-opus-5-5", "host": "claude-code", "specRevision": "8ac443f",
              "group": "g1"}, **FRONTIER),
        {"id": 2, "title": "Wire the flag", "tier": "bounded", "class": "repeat",
         "estimate": 30, "specRevision": "8ac443f", "group": "g1"}])
    parts = workspace / "parts.json"
    parts.write_text(json.dumps([{"title": "Wire the flag, part 2", "class": "calculable",
                                  "estimate": 15}]), encoding="utf-8")
    parts = str(parts)
    for args in (("--open", "--rows-file", listing),
                 ("--start", "1", "--model", "claude-opus-5-5", "--host", "claude-code"),
                 ("--wait", "1", "--reason", "approval"), ("--resume", "1"),
                 ("--end", "1", "--tokens", "1200"), ("--start", "2"),
                 ("--split", "2", "--rows-file", parts)):
        completed = timing_cli(workspace, *args)
        assert completed.returncode == 0, (args, completed.stderr)
    status = json.loads(timing_cli(workspace, "--status", "--json").stdout)["rows"]
    summary = json.loads(run(REGISTRY_CLI, "--root", str(workspace), "timing", "--sprint",
                             "HB-9", "--summary", "--json").stdout)["rows"]
    for found in (status, summary):
        one, two, three = found
        assert {k: one[k] for k in timing.NEW_FIELDS if k != "splitFrom"} == {
            "class": "frontier", "model": "claude-opus-5-5", "host": "claude-code",
            "specRevision": "8ac443f", "group": "g1", "timebox": 120,
            "onTimebox": "stop and file an issue"}
        assert (one["predicted"], one["basis"]) == (120, "timeboxed")
        assert (one["tokens"], one["waitReasons"], one["splitFrom"]) == (
            1200, ["approval"], "not recorded")
        assert (two["class"], two["state"], two["result"]) == ("repeat", "split", "split")
        assert (three["id"], three["splitFrom"], three["class"], three["added"]) == (
            3, 2, "calculable", True)


def test_a_log_from_9071713_reads_unchanged(tmp_path):
    """Frame 6: a log the shipped `timing` wrote reads, prices and summarizes as it did."""
    expected = json.loads((FIXTURES / "Timing.pre-hb4.expected.json").read_text(encoding="utf-8"))
    (tmp_path / "Timing.pre-hb4.jsonl").write_bytes(
        (FIXTURES / "Timing.pre-hb4.jsonl").read_bytes())
    events = timing.load(str(tmp_path / "Timing.pre-hb4.jsonl"))
    shown = [row.as_dict() for row in timing.rows(events, timing.now())]
    result = timing.summary(events)
    for old_rows, new_rows in ((expected["status"], shown),
                               (expected["summary"]["rows"], result["rows"])):
        assert len(old_rows) == len(new_rows) == 8
        for old, new in zip(old_rows, new_rows):
            assert {key: new[key] for key in old} == old
            assert all(new[key] == "not recorded" for key in timing.NEW_FIELDS + ("tokens",))
            assert (new["waitReasons"], new["timeboxReached"]) == (
                ["not recorded"] if new["waited"] else [], False)
    assert {k: v for k, v in result.items() if k != "rows"} == {
        k: v for k, v in expected["summary"].items() if k != "rows"}
    specs = [{key: value for key, value in spec.items() if key not in timing.PRICE_FIELDS}
             for spec in expected["price"]]
    assert timing.price_rows(specs, timing.history(str(tmp_path))) == expected["price"]


def test_a_wait_needs_a_reason(workspace):
    listing = rows_file(workspace, [{"id": 1, "title": "Ask", "estimate": 10}])
    assert timing_cli(workspace, "--open", "--rows-file", listing).returncode == 0
    assert timing_cli(workspace, "--start", "1").returncode == 0
    before = log_path(workspace).read_bytes()
    for args in (("--wait", "1"), ("--wait", "1", "--reason", "lunch"),
                 ("--start", "1", "--reason", "owner")):
        refused = timing_cli(workspace, *args)
        assert refused.returncode == 3, args
        assert log_path(workspace).read_bytes() == before
    assert "--reason owner | approval | blocked | session-ended" in \
        timing_cli(workspace, "--wait", "1").stderr
    assert timing_cli(workspace, "--wait", "1", "--reason", "owner").returncode == 0
    last = json.loads(log_path(workspace).read_text(encoding="utf-8").splitlines()[-1])
    assert (last["event"], last["reason"]) == ("wait", "owner")


def test_a_frontier_row_is_priced_at_its_timebox():
    history = past(30, 35, 40, kind="spike")
    priced = timing.price_rows([dict({"id": 1, "title": "Spike", "kind": "spike"},
                                     **FRONTIER)], history)
    assert (priced[0]["predicted"], priced[0]["basis"]) == (120, "timeboxed")
    assert "estimate" not in priced[0]


def test_timebox_reached_needs_the_clock():
    events = [{"event": "open", "at": at(0), "rows": timing.price_rows(
        [dict({"id": 1, "title": "Spike"}, **FRONTIER)], [])}, ev("start", 1, 0)]
    early, late = T + dt.timedelta(minutes=30), T + dt.timedelta(minutes=121)
    with pytest.raises(GovernanceError, match="worked 30 min of its 2h 00m timebox"):
        timing.check(events, "timebox-reached", 1, early)
    assert "timebox reached" not in timing.render_status(timing.rows(events, early), early)
    timing.check(events, "timebox-reached", 1, late)
    events.append(ev("timebox-reached", 1, 121))
    found = timing.rows(events, late)
    assert "timebox reached — stop and file an issue" in timing.render_status(found, late)
    assert found[0].as_dict()["timeboxReached"] is True
    with pytest.raises(GovernanceError, match="already reached"):
        timing.check(events, "timebox-reached", 1, late)
    plain = [plan(1), ev("start", 1, 0)]
    with pytest.raises(GovernanceError, match="has no timebox"):
        timing.check(plain, "timebox-reached", 1, late)


def test_the_cli_refuses_a_timebox_not_yet_reached(workspace):
    listing = rows_file(workspace, [dict({"id": 1, "title": "Spike"}, **FRONTIER)])
    assert timing_cli(workspace, "--open", "--rows-file", listing).returncode == 0
    assert timing_cli(workspace, "--start", "1").returncode == 0
    before = log_path(workspace).read_bytes()
    refused = timing_cli(workspace, "--timebox-reached", "1")
    assert refused.returncode == 3 and "of its 2h 00m timebox" in refused.stderr
    assert log_path(workspace).read_bytes() == before


def test_a_lost_stamp_never_reaches_a_total(tmp_path):
    """Frame 4: the session dies after row 2 starts; row 3 lost its start."""
    events = worked([(10, 12, False)])
    events[0]["rows"] += [{"id": 2, "title": "died", "predicted": 20, "basis": "estimated"},
                          {"id": 3, "title": "no start", "predicted": 5, "basis": "estimated"}]
    events += [ev("start", 2, 12), ev("end", 3, 40)]
    write_log(tmp_path, "LOST", events)
    assert [row.id for row in timing.history(str(tmp_path))] == [1]
    result = timing.summary(events)
    assert (result["notMeasured"], result["actual"], result["complete"]) == ([2, 3], "12m", False)


def test_tokens_are_a_count(workspace):
    listing = rows_file(workspace, [{"id": 1, "title": "a", "estimate": 10},
                                    {"id": 2, "title": "b", "estimate": 10}])
    assert timing_cli(workspace, "--open", "--rows-file", listing).returncode == 0
    for row in ("1", "2"):
        assert timing_cli(workspace, "--start", row).returncode == 0
    assert timing_cli(workspace, "--end", "1", "--tokens", "1200").returncode == 0
    ended = json.loads(log_path(workspace).read_text(encoding="utf-8").splitlines()[-1])
    assert ended["tokens"] == 1200 and isinstance(ended["tokens"], int)
    before = log_path(workspace).read_bytes()
    for bad in ("4h", "12.5", "-3", "", "²"):
        refused = timing_cli(workspace, "--end", "2", "--tokens", bad)
        assert refused.returncode == 3, bad
        assert log_path(workspace).read_bytes() == before
    assert timing_cli(workspace, "--start", "2", "--tokens", "5").returncode == 3


def test_a_model_change_mid_row_is_kept_on_the_event():
    """Frame 5: the row keeps the model named at its start; the switch is on the event."""
    events = [plan(1),
              dict(ev("start", 1, 0), **timing.event_fields("start", model="model-a")),
              dict(ev("wait", 1, 5), **timing.event_fields("wait", reason="session-ended")),
              dict(ev("resume", 1, 50), **timing.event_fields("resume", model="model-b")),
              ev("end", 1, 60)]
    row = timing.rows(events, T)[0]
    assert (row.as_dict()["model"], row.working, row.wait_reasons) == (
        "model-a", 15, ["session-ended"])
    assert [e.get("model") for e in events if e.get("event") == "resume"] == ["model-b"]


def test_a_split_row_never_double_counts(tmp_path):
    events = [priced_plan((60, False), (30, False)), ev("start", 1, 0),
              ev("end", 1, 25, result="split", rows=[
                  {"id": 3, "title": "part a", "predicted": 20, "basis": "estimated",
                   "splitFrom": 1},
                  {"id": 4, "title": "part b", "predicted": 30, "basis": "estimated",
                   "splitFrom": 1}])]
    moment = T + dt.timedelta(minutes=25)
    assert timing.remaining(timing.rows(events, moment), moment) == (80, [2, 3, 4], [])
    with pytest.raises(GovernanceError, match=r"row 1 has already ended \(split\)"):
        timing.check(events, "split", 1)
    events += [ev("start", 3, 25), ev("end", 3, 45), ev("start", 4, 45), ev("end", 4, 75),
               ev("start", 2, 75), ev("end", 2, 105)]
    found = {row.id: row for row in timing.rows(events)}
    assert (found[1].state, found[1].working) == ("split", 25)
    assert found[3].added and found[3].fields["splitFrom"] == 1
    result = timing.summary(events)
    assert (result["estimateMinutes"], result["actualMinutes"], result["complete"]) == (
        90, 105, True)
    write_log(tmp_path, "SPLIT", events)
    assert sorted(row.id for row in timing.history(str(tmp_path))) == [2, 3, 4]
    unstarted = [priced_plan((60, False)), ev("end", 1, 0, result="split", rows=[
        {"id": 2, "title": "part", "predicted": 10, "basis": "estimated", "splitFrom": 1}]),
        ev("start", 2, 0), ev("end", 2, 10)]
    assert timing.summary(unstarted)["complete"] is True
    # The parent's 25 of 60 minutes is not a miss: row-error reads the parts alone.
    closed = events[:3] + [ev("start", 3, 25), ev("end", 3, 45), ev("end", 4, 45,
                                                                    result="cancelled"),
                           ev("end", 2, 45, result="cancelled")]
    directory = tmp_path / "figures"
    directory.mkdir()
    for name in ("S-1", "S-2", "S-3"):
        write_log(directory, name, closed)
    found = {m.name: m for m in timing.figures(str(directory))}
    assert found["row-error"].value == 0.0


def test_a_hand_edited_timebox_below_a_minute_is_not_a_timebox():
    events = [{"event": "open", "at": at(0), "rows": [
        {"id": 1, "title": "x", "class": "frontier", "timebox": 0, "onTimebox": "stop"}]}]
    row = timing.rows(events, T)[0]
    assert row.timebox is None and "timebox reached" not in timing.render_status([row], T)


# =============================================================================
# VIR-021 — an estimated task list in every spec
# =============================================================================

#: Frame 1 of docs/virtuoso/holding/2026-10-03-measured-per-task-estimation.md: the kind
#: "registry subcommand + tests" has 9 measured runs; the spec lists 7 estimated tasks and
#: 1 frontier task timeboxed to 2h. Rows 3 and 4 share a parallel group, so the chain and
#: the sum differ.
FRAME_1 = """# Roadmap

### VIR-X — Frame one

- **What:** something

##### Task list

| # | Task | Class | Kind | Tier | Effort | Estimate | Timebox | Group |
|---|---|---|---|---|---|---|---|---|
| 1 | The rows-from-spec subcommand | repeat | registry subcommand + tests | bounded | medium | 35m (median of 9 runs) | — | — |
| 2 | The open-from-spec subcommand | repeat | registry subcommand + tests | bounded | medium | 35m (median of 9 runs) | — | — |
| 3 | The total line | repeat | registry subcommand + tests | bounded | | 35m (median of 9 runs) | — | a |
| 4 | The written price | repeat | registry subcommand + tests | bounded | | 35m (median of 9 runs) | — | a |
| 5 | The buffer guard | repeat | registry subcommand + tests | bounded | medium | 35m (median of 9 runs) | — | — |
| 6 | The effort guard | repeat | registry subcommand + tests | bounded | medium | 35m (median of 9 runs) | — | — |
| 7 | The task-rows reference | calculable | reference page | bounded | low | 40m | — | — |
| 8 | Class-aware pricing spike | frontier | | cross-cutting | high | — | ≤2h — stop and file an issue | — |

**Total:** chain 3h35m · sum 4h10m + 1 timeboxed ≤2h; 6 of 7 estimated tasks calibrated

##### Lessons applied
- No live lesson applies — 0 read
"""
NINE_RUNS = (30, 31, 33, 34, 35, 36, 38, 40, 42)        # median 35


def close_outs(root) -> Path:
    path = root.joinpath(*json.loads(
        (root / "Virtuoso" / "workspace-layout.json").read_text(encoding="utf-8")
    )["roles"]["closeOuts"]["path"].split("/"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def nine_runs(root) -> None:
    events = [{"event": "open", "at": at(0), "rows": [
        {"id": i + 1, "title": "past %d" % (i + 1), "kind": "registry-subcommand-tests",
         "predicted": 35, "basis": "estimated"} for i in range(len(NINE_RUNS))]}]
    clock = 0
    for i, minutes in enumerate(NINE_RUNS):
        events += [ev("start", i + 1, clock), ev("end", i + 1, clock + minutes, result="done")]
        clock += minutes
    write_log(close_outs(root), "PAST-1", events)


def spec_file(root, text=FRAME_1) -> str:
    path = root / "spec.md"
    path.write_text(text, encoding="utf-8")
    return str(path)


def from_spec(root, text=FRAME_1, *args):
    return run(REGISTRY_CLI, "--root", str(root), "timing", "--rows-from-spec",
               spec_file(root, text), "--item", "VIR-X", *args)


def test_a_task_list_from_a_spec_parses(workspace):
    nine_runs(workspace)
    completed = from_spec(workspace, FRAME_1, "--json")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout)
    found = result["rows"]
    assert [row["id"] for row in found] == list(range(1, 9))
    assert [row["class"] for row in found] == ["repeat"] * 6 + ["calculable", "frontier"]
    assert {row["kind"] for row in found[:6]} == {"registry-subcommand-tests"}
    assert [(row["predicted"], row["basis"]) for row in found] == (
        [(35, "median of 9 runs")] * 6 + [(40, "estimated"), (120, "timeboxed")])
    assert all(row["item"] == "VIR-X" for row in found)
    assert result["total"].startswith(
        "chain 3h35m · sum 4h10m + 1 timeboxed ≤2h; 6 of 7 estimated tasks calibrated")
    assert "Total: chain 3h35m · sum 4h10m" in from_spec(workspace).stdout


def test_open_from_spec_keeps_ids_and_both_prices(workspace):
    # Written when the kind had 4 runs at a median of 30; launched with 9 at 35.
    nine_runs(workspace)
    spec = spec_file(workspace, FRAME_1.replace("| 7 | The task-rows", "| 17 | The task-rows")
                     .replace("35m (median of 9 runs)", "30m (median of 4 runs)"))
    completed = timing_cli(workspace, "--open", "--from-spec", spec, "--item", "VIR-X")
    assert completed.returncode == 0, completed.stderr
    found = json.loads(timing_cli(workspace, "--status", "--json").stdout)["rows"]
    assert [row["id"] for row in found] == [1, 2, 3, 4, 5, 6, 8, 17]
    by_id = {row["id"]: row for row in found}
    assert (by_id[1]["writtenPredicted"], by_id[1]["writtenBasis"]) == (30, "median of 4 runs")
    assert (by_id[1]["predicted"], by_id[1]["basis"]) == (35, "median of 9 runs")
    assert (by_id[17]["writtenPredicted"], by_id[17]["writtenBasis"]) == (40, "estimated")
    assert (by_id[8]["predicted"], by_id[8]["basis"]) == (120, "timeboxed")
    assert by_id[8]["writtenPredicted"] == "not recorded"
    assert by_id[3]["group"] == "a" and by_id[1]["item"] == "VIR-X"


def test_from_spec_goes_only_with_open_and_in_place_of_rows(workspace):
    spec = spec_file(workspace)
    assert timing_cli(workspace, "--open", "--from-spec", spec, "--rows-file",
                      spec).returncode == 3
    assert not list(workspace.rglob("Timing.HB-9.jsonl"))


def test_a_frontier_row_with_an_estimate_is_refused(workspace):
    refused = from_spec(workspace, FRAME_1.replace("| high | — | ≤2h", "| high | 30m | ≤2h"))
    assert refused.returncode == 1
    assert "task 8: a frontier task receives no single-number estimate" in refused.stdout
    with pytest.raises(GovernanceError, match="a frontier task carries a Timebox"):
        timing.spec_rows(FRAME_1.replace("≤2h — stop and file an issue", "—"), "VIR-X")
    missing = from_spec(workspace, FRAME_1.replace("##### Task list", "##### Tasks"))
    assert missing.returncode == 1 and "no \"Task list\" section for VIR-X" in missing.stdout


def test_a_duration_in_a_task_lists_effort_is_refused():
    with pytest.raises(GovernanceError, match="Effort is a level, never a duration"):
        timing.spec_rows(FRAME_1.replace("| bounded | low | 40m", "| bounded | 40m | 40m"),
                         "VIR-X")


def test_chain_and_sum_are_labelled_apart():
    priced = [{"id": 1, "class": "repeat", "predicted": 30, "basis": "median of 3 runs"},
              {"id": 2, "class": "repeat", "predicted": 50, "basis": "estimated", "group": "g"},
              {"id": 3, "class": "repeat", "predicted": 20, "basis": "estimated", "group": "g"}]
    line = timing.total_line(priced)
    assert line.startswith("chain 1h20m · sum 1h40m; 1 of 3 estimated tasks calibrated")
    assert "timeboxed" not in line
    ungrouped = [dict(row, group="") for row in priced]
    assert timing.total_line(ungrouped).startswith("chain 1h40m · sum 1h40m")


def test_the_buffer_ready_is_unchanged(workspace):
    layout = workspace / "Virtuoso" / "workspace-layout.json"
    data = json.loads(layout.read_text(encoding="utf-8"))
    data.setdefault("policy", {})["lessons"] = {"idPrefix": "LSN"}
    layout.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def role(name):
        return workspace.joinpath(*data["roles"][name]["path"].split("/"))

    role("lessons").write_text("### LSN-001 — Reader first (A-0, 2026-09-01)\n"
                               "**Applies to:** row shapes\n**Status:** Observation\n",
                               encoding="utf-8")
    without = ("# Roadmap\n\n#### R-1 — Written under v1.1\n\n- **What:** something\n\n"
               "##### Lessons applied\n- LSN-001 applied\n")
    role("roadmap").write_text(without, encoding="utf-8")
    with open(role("workRegister"), "a", encoding="utf-8", newline="") as handle:
        handle.write("R-1,Written under v1.1,1,Queued,Full Spec,,S,,,,,,,,,\n")

    def ready():
        completed = run(REGISTRY_CLI, "--root", str(workspace), "kpis", "--json")
        assert completed.returncode == 0, completed.stderr
        return {m["name"]: m for m in json.loads(completed.stdout)["metrics"]}[
            "dispatch-buffer-ready"]["value"]

    def u10():
        return run(REGISTRY_CLI, "--root", str(workspace), "timing", "--rows-from-spec",
                   str(role("roadmap")), "--item", "R-1").returncode

    assert (ready(), u10()) == (1, 1)            # U10 is a gap, and the buffer ignores it
    task_list = FRAME_1[FRAME_1.index("##### Task list"):FRAME_1.index("**Total:**")]
    role("roadmap").write_text(without.replace("##### Lessons", task_list + "##### Lessons"),
                               encoding="utf-8")
    assert (ready(), u10()) == (1, 0)            # closing the gap leaves it unchanged


def test_every_estimated_task_carries_its_estimate():
    with pytest.raises(GovernanceError, match="task 7: an estimated task carries its Estimate"):
        timing.spec_rows(FRAME_1.replace("| low | 40m |", "| low | — |"), "VIR-X")


def test_task_numbers_are_positive_and_used_once(workspace):
    for bad in (FRAME_1.replace("| 2 | The open", "| 1 | The open"),
                FRAME_1.replace("| 1 | The rows", "| 0 | The rows")):
        refused = from_spec(workspace, bad)
        assert refused.returncode == 1
        assert "# is a new positive number, once per task" in refused.stdout


def test_the_table_is_read_as_markdown_draws_it():
    no_separator = FRAME_1.replace("|---|---|---|---|---|---|---|---|---|\n", "")
    assert [row["id"] for row in timing.spec_rows(no_separator, "VIR-X")] == list(range(1, 9))
    second = FRAME_1.replace("**Total:**", "| # | Note |\n|---|---|\n| 99 | not a task |\n\n"
                             "**Total:**")
    assert [row["id"] for row in timing.spec_rows(second, "VIR-X")] == list(range(1, 9))
    fenced = FRAME_1.replace("##### Task list",
                             "```\n##### Task list\n| # | x |\n```\n\n##### Task list", 1)
    whole = fenced[fenced.index("```"):]
    assert len(timing.spec_rows(whole)) == 8          # no --item: fences are still examples


def test_rows_from_spec_needs_no_close_outs_role(workspace):
    layout = workspace / "Virtuoso" / "workspace-layout.json"
    data = json.loads(layout.read_text(encoding="utf-8"))
    del data["roles"]["closeOuts"]
    layout.write_text(json.dumps(data, indent=2), encoding="utf-8")
    completed = from_spec(workspace)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "0 of 7 estimated tasks calibrated" in completed.stdout


def test_from_spec_goes_only_with_open(workspace):
    stray = timing_cli(workspace, "--status", "--from-spec", spec_file(workspace))
    assert stray.returncode == 3 and "--from-spec goes with --open" in stray.stderr
