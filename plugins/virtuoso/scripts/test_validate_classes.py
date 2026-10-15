"""VIR-022: the class-design validation — its verdicts, the leave-one-log-out rule, the
fixed thresholds and the review-focus cases, each on a fixture directory of time logs."""
from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

from conftest import PLUGIN_ROOT

import validate_classes as vc
from tools.governance import timing

SCRIPT = str(Path(PLUGIN_ROOT) / "scripts" / "validate_classes.py")
T = dt.datetime(2026, 10, 1, 9, 0, tzinfo=dt.timezone.utc)


def at(minutes: float) -> str:
    return timing.stamp(T + dt.timedelta(minutes=minutes))


def write_log(directory: Path, name: str, rows, *, closed=True, confirm=()):
    """A time log of ``rows``: ``(class, kind, working minutes)`` or a dict of extra row
    fields with ``working``. Every row starts at 0; a closed log ends every row."""
    specs, events = [], []
    for number, row in enumerate(rows, 1):
        row = dict(row) if isinstance(row, dict) else dict(zip(("class", "kind", "working"), row))
        working = row.pop("working")
        spec = {"id": number, "title": "row %d" % number}
        spec.update({k: v for k, v in row.items() if v is not None})
        specs.append(spec)
        events.append({"event": "start", "row": number, "at": at(0)})
        if closed or number > 1:
            events.append({"event": "end", "row": number, "at": at(working)})
    for number in confirm:
        events.append({"event": "confirm", "row": number, "at": at(500)})
    directory.mkdir(parents=True, exist_ok=True)
    lines = [{"event": "open", "at": at(0), "rows": specs}] + events
    (directory / ("Timing.%s.jsonl" % name)).write_text(
        "".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")


def repeat_logs(directory: Path, count: int, workings=(10, 10, 10)):
    for n in range(count):
        write_log(directory, "L%d" % n, [("repeat", "k", w) for w in workings])


def run(directory: Path, *extra):
    return subprocess.run([sys.executable, SCRIPT, "--dir", str(directory), *extra],
                          capture_output=True, text=True, encoding="utf-8")


def last_lines(completed) -> list[str]:
    return completed.stdout.rstrip("\n").split("\n")[-2:]


# --- the verdicts (Done-when 1) ------------------------------------------------------------

def test_a_directory_built_to_pass_is_go(tmp_path):
    for n in range(6):
        write_log(tmp_path, "L%d" % n, [("repeat", "k", 10), ("repeat", "k", 10),
                                        ("frontier", "f", 5), ("frontier", "f", 50)])
    completed = run(tmp_path)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert last_lines(completed) == ["verdict: go", "frontier: separates (G3 holds)"]


def test_a_directory_with_no_frontier_rows_is_go_and_says_so(tmp_path):
    repeat_logs(tmp_path, 6)
    completed = run(tmp_path)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert last_lines(completed) == ["verdict: go",
                                     "frontier: not computable — 0 of 6 frontier rows"]


def test_a_directory_built_to_fail_g2_is_no_go(tmp_path):
    # Each row prices at 10 (the others' median): r is 0.6, 0.6, 1, 1.8, 1.8 — Q3/Q1 = 3,
    # while every r stays inside 0.5–2.0, so G4 holds and only G2 fails.
    repeat_logs(tmp_path, 6, workings=(6, 6, 10, 18, 18))
    completed = run(tmp_path)
    assert completed.returncode == 2, completed.stdout + completed.stderr
    assert last_lines(completed)[0] == "verdict: no-go — G2"


def test_frontier_rows_as_steady_as_repeat_rows_do_not_separate(tmp_path):
    for n in range(6):
        write_log(tmp_path, "L%d" % n, [("repeat", "k", 10), ("repeat", "k", 10),
                                        ("frontier", "f", 20)])
    completed = run(tmp_path)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert last_lines(completed) == ["verdict: go", "frontier: does not separate (G3 fails)"]


def test_a_root_without_a_close_outs_role_is_not_computable(tmp_path):
    completed = subprocess.run([sys.executable, SCRIPT, "--root", str(tmp_path)],
                               capture_output=True, text=True, encoding="utf-8")
    assert completed.returncode == 3
    assert "validate_classes:" in completed.stderr


def test_five_logs_are_not_computable(tmp_path):
    repeat_logs(tmp_path, 5)
    completed = run(tmp_path)
    assert completed.returncode == 3, completed.stdout + completed.stderr
    assert last_lines(completed)[0] == "verdict: not computable — 5 of 6 closed logs"


def test_g4_fails_when_too_many_repeat_rows_leave_the_band(tmp_path):
    # r is 0.4, 1, 1, 1, 2.5: 40% outside the band, yet Q1 and Q3 both land on 1, so G2 holds.
    repeat_logs(tmp_path, 6, workings=(4, 10, 10, 10, 25))
    completed = run(tmp_path)
    assert completed.returncode == 2
    assert last_lines(completed)[0] == "verdict: no-go — G4"


# --- the leave-one-log-out rule (Done-when 2) ----------------------------------------------

def test_leave_one_log_out(tmp_path):
    """Priced with its own log, a 100-minute row of kind x would see [10, 10, 10, 100, 100,
    100] and price at 55; left out, it sees only the others' three 10s."""
    write_log(tmp_path, "own", [("repeat", "x", 100)] * 3)
    write_log(tmp_path, "other1", [("repeat", "x", 10)] * 2)
    write_log(tmp_path, "other2", [("repeat", "x", 10)])
    logs, _ = vc.read_logs(str(tmp_path))
    priced, _ = vc.price_counted(logs)
    own = [p for p in priced["repeat"] if p.log.endswith("Timing.own.jsonl")]
    assert [p.price for p in own] == [10, 10, 10]
    assert [p.ratio for p in own] == [10.0, 10.0, 10.0]


# --- the thresholds (Done-when 3) ----------------------------------------------------------

def test_thresholds_match_the_plan():
    assert (vc.MIN_LOGS, vc.MIN_REPEAT, vc.MIN_FRONTIER) == (6, 12, 6)
    assert vc.MAX_REPEAT_SPREAD == 2.0
    assert vc.SEPARATION == 1.5
    assert vc.MISCLASS_BAND == (0.5, 2.0)
    assert vc.MAX_MISCLASS == 0.25


# --- the review focus ----------------------------------------------------------------------

def test_an_open_log_is_not_counted(tmp_path):
    repeat_logs(tmp_path, 5)
    write_log(tmp_path, "inflight", [("repeat", "k", 10)] * 3, closed=False)
    completed = run(tmp_path)
    assert completed.returncode == 3
    assert last_lines(completed)[0] == "verdict: not computable — 5 of 6 closed logs"
    assert "open: a run in flight" in completed.stdout


def test_a_flagged_row_is_left_out(tmp_path):
    repeat_logs(tmp_path, 6)
    flagged = {"class": "repeat", "kind": "k", "predicted": 1, "working": 10}   # > 3 x 1
    write_log(tmp_path, "flagged", [flagged])
    logs, _ = vc.read_logs(str(tmp_path))
    priced, _ = vc.price_counted(logs)
    assert not [p for p in priced["repeat"] if p.log.endswith("Timing.flagged.jsonl")]
    write_log(tmp_path, "flagged", [dict(flagged)], confirm=(1,))      # the owner confirms it
    logs, _ = vc.read_logs(str(tmp_path))
    priced, _ = vc.price_counted(logs)
    assert len([p for p in priced["repeat"] if p.log.endswith("Timing.flagged.jsonl")]) == 1


def test_a_log_without_class_is_named(tmp_path):
    repeat_logs(tmp_path, 5)
    write_log(tmp_path, "old", [(None, "k", 10)] * 3)
    completed = run(tmp_path)
    assert completed.returncode == 3
    assert last_lines(completed)[0] == "verdict: not computable — 5 of 6 closed logs"
    old = [line for line in completed.stdout.split("\n") if "Timing.old.jsonl" in line]
    assert old and "no class on every row" in old[0]


def test_a_zero_quartile_is_not_computable(tmp_path):
    assert vc.spread([0.0, 0.0, 0.0, 1.0]) == (None, "Q1 is 0")
    repeat_logs(tmp_path, 6, workings=(10, 10, 10, 10, 0, 0))     # prices at 10; a third take 0
    completed = run(tmp_path)
    assert completed.returncode == 2, completed.stdout + completed.stderr     # no crash
    assert "not computable (Q1 is 0)" in completed.stdout


def test_an_unreadable_log_is_skipped_and_named(tmp_path):
    repeat_logs(tmp_path, 6)
    (tmp_path / "Timing.broken.jsonl").write_text("{not json\n", encoding="utf-8")
    completed = run(tmp_path)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "Timing.broken.jsonl" in completed.stdout and "unreadable, skipped" in completed.stdout


def test_the_report_cites_every_log_by_hash_and_is_the_only_write(tmp_path):
    repeat_logs(tmp_path, 6)
    before = sorted(os.listdir(tmp_path))
    completed = run(tmp_path, "--write")
    assert completed.returncode == 0
    after = sorted(os.listdir(tmp_path))
    added = [name for name in after if name not in before]
    assert len(added) == 1 and added[0].startswith("Validation.classes.")
    text = (tmp_path / added[0]).read_text(encoding="utf-8")
    import hashlib
    for name in before:
        assert hashlib.sha256((tmp_path / name).read_bytes()).hexdigest() in text
