"""VIR-057: the pricing diagnosis — an unclocked hour reads as the gap, and rows stamped
in one minute are counted as a burst, each on synthetic logs in the real event format."""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

from conftest import PLUGIN_ROOT

import validate_pricing as vp
from tools.governance import timing

SCRIPT = str(Path(PLUGIN_ROOT) / "scripts" / "validate_pricing.py")
T = dt.datetime(2026, 10, 1, 9, 0, tzinfo=dt.timezone.utc)


def at(minutes: float) -> str:
    return timing.stamp(T + dt.timedelta(minutes=minutes))


def write_log(directory: Path, name: str, rows):
    """A closed time log: each row ``(start, end, estimate)`` in minutes from ``T``, a
    calculable row priced at 2 minutes, as ``timing --open`` writes it."""
    specs, events = [], []
    for number, (start, end, estimate) in enumerate(rows, 1):
        specs.append({"id": number, "title": "row %d" % number, "class": "calculable",
                      "item": name, "tier": "bounded", "effort": "medium",
                      "estimate": estimate, "predicted": 2, "basis": "median of 60 runs"})
        events.append({"event": "start", "row": number, "at": at(start),
                       "model": "m", "host": "h"})
        events.append({"event": "end", "row": number, "at": at(end), "result": "done",
                       "evidence": "e"})
    events.sort(key=lambda event: event["at"])
    lines = [{"event": "open", "at": at(0), "rows": specs}] + events
    directory.mkdir(parents=True, exist_ok=True)
    (directory / ("Timing.%s.jsonl" % name)).write_text(
        "".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")


def run(directory: Path):
    return subprocess.run([sys.executable, SCRIPT, str(directory)], capture_output=True,
                          text=True, encoding="utf-8")


def test_a_dispatch_with_an_unclocked_hour_reads_unclocked_gap(tmp_path):
    # Two 5-minute rows written at 40 minutes each, with an hour between them that no
    # row clocks: the shortfall is 70 minutes, and the gap holds 60 of it.
    write_log(tmp_path, "GAP-1", [(0, 5, 40), (65, 70, 40)])
    completed = run(tmp_path)
    assert completed.returncode == 0, completed.stderr
    first = completed.stdout.splitlines()[0]
    assert first.startswith("GAP-1: a rows 10.0 · b actual 10.0 · c gap 60.0 ")
    assert completed.stdout.rstrip("\n").splitlines()[-1] == "verdict: unclocked-gap"


def test_burst_stamped_rows_are_counted(tmp_path):
    # Three rows ended within one minute (two after an earlier, separate row): three of
    # the four rows are a burst, and their shortfall outweighs the clocked row's.
    write_log(tmp_path, "BURST-1", [(0, 15, 25), (15, 20.2, 30), (20.2, 20.5, 30),
                                    (20.5, 20.8, 30)])
    (found,), skipped = vp.read(str(tmp_path))
    assert skipped == []
    assert vp.bursts([r for r in timing.rows(timing.load(found.path))]) == {2, 3, 4}
    assert found.burst == 0.75
    assert found.tiny == 0.5
    assert found.gap == 0.0
    completed = run(tmp_path)
    assert completed.returncode == 0, completed.stderr
    assert " f tiny 50% burst 75% " in completed.stdout
    assert completed.stdout.rstrip("\n").splitlines()[-1] == "verdict: burst-stamping"
