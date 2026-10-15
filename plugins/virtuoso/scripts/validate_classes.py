#!/usr/bin/env python3
"""Validate the class design on the closed time logs that carry a class (VIR-022).

A read-only analysis. For each measured, ``done``, unflagged row of a closed log with
``class`` on every row, it computes ``r = actual / p``, where ``p`` is the row's price
under the shipped ``timing.price`` with that row's own log left out of the history
(leave-one-log-out, so no row prices itself). A frontier row gets the same
counterfactual price — its kind or tier history, never its timebox — which is what the
class design claims would mislead. It reports per class the count and the spread
``Q3/Q1`` of ``r``, the share of repeat rows outside ``MISCLASS_BAND``, an item-level
table, and ends in one verdict line, then one frontier line that never gates.

Usage:
    python validate_classes.py [--root DIR | --dir CLOSE_OUTS] [--write]

``--root`` resolves the ``closeOuts`` role through the registry (default: the working
directory); ``--dir`` reads a directory directly. ``--write`` saves the report as
``<dir>/Validation.classes.<YYYY-MM-DD>.md`` — the only file this script ever writes.

Exit codes: 0 go; 2 no-go; 3 not computable (or no closeOuts role).
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.governance import registry as registry_mod, textio, timing  # noqa: E402
from tools.governance.errors import GovernanceError  # noqa: E402
from tools.governance.learning import CALIBRATION_MINIMUM  # noqa: E402

# The gate, fixed before any log was examined (Roadmap § VIR-022, owner ruling 2026-10-12).
MIN_LOGS = 6                      # G1: closed logs with `class` on every row
MIN_REPEAT = 12                   # G1: measured repeat rows priced from history
MIN_FRONTIER = 6                  # G3's computability floor, not a gate
MAX_REPEAT_SPREAD = 2.0           # G2: repeat Q3/Q1
SEPARATION = 1.5                  # G3: frontier spread >= SEPARATION x repeat spread
MISCLASS_BAND = (0.5, 2.0)        # G4: r outside this band is a misclassified repeat row
MAX_MISCLASS = 0.25               # G4: the largest share of repeat rows outside the band

EXIT_GO, EXIT_NO_GO, EXIT_NOT_COMPUTABLE = 0, 2, 3
REPORT_PREFIX = "Validation.classes."


@dataclasses.dataclass
class Log:
    path: str
    sha256: str
    rows: list            # timing.Row
    counted: bool = False  # closed, with a class on every row: counts toward G1
    note: str = ""         # why a log is not counted


@dataclasses.dataclass
class Priced:
    log: str
    row: object           # timing.Row
    price: int
    basis: str

    @property
    def ratio(self) -> float:
        return self.row.working / self.price


@dataclasses.dataclass
class Result:
    logs: list
    skipped: list         # (path, reason) for logs that could not be read
    priced: dict          # class -> [Priced]
    unpriced: dict        # class -> rows measured but priced by no history
    kinds: dict           # kind -> measured runs, for kinds with >= CALIBRATION_MINIMUM
    verdict: str
    exit_code: int
    frontier: str


def _evidence(row) -> bool:
    """A row ``timing.history`` would price from."""
    return row.measured and row.state == "done" and not row.flagged


def read_logs(directory: str) -> tuple[list, list]:
    """``(logs, skipped)``: every readable log with its hash at claim time, each marked
    counted or not; an unreadable log is skipped and named, never fatal."""
    logs, skipped = [], []
    for path in timing.log_paths(directory):
        try:
            with open(path, "rb") as handle:
                digest = hashlib.sha256(handle.read()).hexdigest()
            logged = timing.rows(timing.load(path))
        except (OSError, GovernanceError) as exc:
            skipped.append((path, str(exc)))
            continue
        log = Log(path, digest, logged)
        if not logged or not all(row.ended is not None or row.parked for row in logged):
            log.note = "open: a run in flight, not closed"
        elif not all(row.fields.get("class") in timing.CLASSES for row in logged):
            log.note = "no class on every row (before VIR-020)"
        else:
            log.counted = True
        logs.append(log)
    return logs, skipped


def price_counted(logs: list) -> tuple[dict, dict]:
    """Each counted log's evidence rows priced from every other log's evidence."""
    evidence = {log.path: [row for row in log.rows if _evidence(row)] for log in logs}
    priced = {name: [] for name in timing.CLASSES}
    unpriced = {name: 0 for name in timing.CLASSES}
    for log in logs:
        if not log.counted:
            continue
        past = [row for path, found in evidence.items() if path != log.path for row in found]
        for row in evidence[log.path]:
            name = row.fields["class"]
            # Priced as if it had no class: a frontier row's timebox is not a prediction.
            probe = dataclasses.replace(
                row, fields={k: v for k, v in row.fields.items() if k != "class"})
            found = timing.price(probe, past)
            if found is None or found[1] in (timing.ESTIMATED, timing.TIMEBOXED) \
                    or found[0] <= 0:
                unpriced[name] += 1
                continue
            priced[name].append(Priced(log.path, row, found[0], found[1]))
    return priced, unpriced


def spread(ratios: list) -> tuple[float | None, str]:
    """``(Q3/Q1, "")``, or ``(None, why)`` when it cannot be computed."""
    if len(ratios) < 2:
        return None, "%d row%s" % (len(ratios), "" if len(ratios) == 1 else "s")
    q1, _, q3 = statistics.quantiles(ratios, n=4, method="inclusive")
    if q1 <= 0:
        return None, "Q1 is 0"
    return q3 / q1, ""


def misclassified(ratios: list) -> float | None:
    low, high = MISCLASS_BAND
    return sum(1 for r in ratios if r < low or r > high) / len(ratios) if ratios else None


def decide(n_logs: int, repeat: list) -> tuple[str, int]:
    """The verdict line's text and the exit code, from the table in the specification."""
    short = []
    if n_logs < MIN_LOGS:
        short.append("%d of %d closed logs" % (n_logs, MIN_LOGS))
    if len(repeat) < MIN_REPEAT:
        short.append("%d of %d repeat rows priced from history" % (len(repeat), MIN_REPEAT))
    if short:
        return "not computable — " + "; ".join(short), EXIT_NOT_COMPUTABLE
    failed = []
    value, _ = spread(repeat)
    if value is None or value > MAX_REPEAT_SPREAD:     # G2 must be shown to hold
        failed.append("G2")
    if misclassified(repeat) > MAX_MISCLASS:
        failed.append("G4")
    if failed:
        return "no-go — " + ", ".join(failed), EXIT_NO_GO
    return "go", EXIT_GO


def frontier_line(repeat: list, frontier: list) -> str:
    if len(frontier) < MIN_FRONTIER:
        return "frontier: not computable — %d of %d frontier rows" % (len(frontier), MIN_FRONTIER)
    (front, why_f), (rep, why_r) = spread(frontier), spread(repeat)
    if front is None or rep is None:
        return "frontier: not computable — spread (%s)" % (why_f or why_r)
    return "frontier: separates (G3 holds)" if front >= SEPARATION * rep \
        else "frontier: does not separate (G3 fails)"


def validate(directory: str) -> Result:
    logs, skipped = read_logs(directory)
    priced, unpriced = price_counted(logs)
    ratios = {name: [p.ratio for p in found] for name, found in priced.items()}
    past = [row for log in logs for row in log.rows if _evidence(row)]
    kinds = {k: n for k, n in timing.kinds(past).items() if n >= CALIBRATION_MINIMUM}
    verdict, code = decide(sum(log.counted for log in logs), ratios["repeat"])
    return Result(logs, skipped, priced, unpriced, kinds, verdict, code,
                  frontier_line(ratios["repeat"], ratios["frontier"]))


def _fmt(value) -> str:
    return "—" if value is None else "%.2f" % value


def item_table(logs: list) -> list[str]:
    """Actual ÷ estimate per item, over each counted log's measured, priced rows."""
    totals: dict = {}
    for log in logs:
        if not log.counted:
            continue
        name = os.path.basename(log.path)[len(timing.LOG_PREFIX):-len(timing.LOG_SUFFIX)]
        for row in log.rows:
            if row.measured and row.predicted:
                actual, estimate = totals.get(row.item or name, (0.0, 0))
                totals[row.item or name] = (actual + row.working, estimate + row.predicted)
    lines = ["| Item | Actual (min) | Estimate (min) | Actual ÷ estimate |", "|---|---|---|---|"]
    for item, (actual, estimate) in sorted(totals.items()):
        lines.append("| %s | %.1f | %d | %.2f |" % (item, actual, estimate, actual / estimate))
    return lines


def report(result: Result, directory: str) -> str:
    counted = [log for log in result.logs if log.counted]
    lines = ["# Validation of the class design — VIR-022", "",
             "Close-outs directory: `%s`. Read-only; every log cited by path and its "
             "SHA-256 at claim time." % directory, "",
             "## Logs", "", "| Log | SHA-256 | Counted | Note |", "|---|---|---|---|"]
    for log in result.logs:
        lines.append("| `%s` | `%s` | %s | %s |" % (
            log.path, log.sha256, "yes" if log.counted else "no",
            log.note or "closed, class on every row"))
    for path, reason in result.skipped:
        lines.append("| `%s` | — | no | unreadable, skipped: %s |" % (path, reason.replace("|", "/")))
    lines += ["", "Every readable log's evidence rows form the history, an open or class-less "
              "log's included (as `timing.history` reads them); a counted log's rows are priced "
              "from every log but their own. A row priced only by its own estimate, by a "
              "timebox, or at 0 minutes (a median under half a minute) has no ratio and is "
              "counted under *Not priced from history*.", "",
              "## Per class", "",
              "| Class | Priced from history | Not priced from history | Q1 | Q3 | Q3/Q1 "
              "| Share outside %s–%s |" % MISCLASS_BAND, "|---|---|---|---|---|---|---|"]
    for name in timing.CLASSES:
        ratios = [p.ratio for p in result.priced[name]]
        quartiles = statistics.quantiles(ratios, n=4, method="inclusive") \
            if len(ratios) >= 2 else (None, None, None)
        value, why = spread(ratios)
        lines.append("| %s | %d | %d | %s | %s | %s | %s |" % (
            name, len(ratios), result.unpriced[name], _fmt(quartiles[0]), _fmt(quartiles[2]),
            _fmt(value) if value is not None else "not computable (%s)" % why,
            _fmt(misclassified(ratios))))
    repeat = [p.ratio for p in result.priced["repeat"]]
    value, why = spread(repeat)
    share = misclassified(repeat)
    lines += ["", "## The gate", "", "| # | Condition | Threshold | Measured |", "|---|---|---|---|",
              "| G1 | Data sufficiency | ≥ %d closed logs; ≥ %d repeat rows priced from "
              "history | %d logs; %d repeat rows |" % (MIN_LOGS, MIN_REPEAT, len(counted),
                                                       len(repeat)),
              "| G2 | Repeat rows are predictable | Q3/Q1 ≤ %.1f | %s |" % (
                  MAX_REPEAT_SPREAD, _fmt(value) if value is not None
                  else "not computable (%s)" % why),
              "| G3 | The classes separate (not gating) | frontier ≥ %.1f × repeat, with ≥ %d "
              "frontier rows | %d frontier rows |" % (SEPARATION, MIN_FRONTIER,
                                                     len(result.priced["frontier"])),
              "| G4 | Misclassification is rare | ≤ %d%% outside %s–%s | %s |" % (
                  MAX_MISCLASS * 100, MISCLASS_BAND[0], MISCLASS_BAND[1],
                  "—" if share is None else "%.1f%%" % (share * 100)),
              "", "## Repeat rows", "", "| Log | Row | Kind | Actual | Price (basis) | r |",
              "|---|---|---|---|---|---|"]
    for p in result.priced["repeat"]:
        lines.append("| %s | %s | %s | %.1f | %d (%s) | %.2f |" % (
            os.path.basename(p.log), p.row.label, p.row.kind or "—", p.row.working, p.price,
            p.basis, p.ratio))
    lines += ["", "## Items (reported, never gating)", ""] + item_table(result.logs)
    lines += ["", "## Kinds with at least %d measured runs (for VIR-023)" % CALIBRATION_MINIMUM, ""]
    lines += ["- %s: %d" % pair for pair in result.kinds.items()] or ["- none"]
    lines += ["", "verdict: %s" % result.verdict, result.frontier, ""]
    return "\n".join(lines)


def _directory(args) -> str:
    if args.dir:
        return args.dir
    return registry_mod.load(args.root).resolve("closeOuts")


def main(argv=None) -> int:
    textio.utf8_stdio()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=os.getcwd())
    ap.add_argument("--dir", help="read this close-outs directory instead of the registry's")
    ap.add_argument("--write", action="store_true",
                    help="save the report as Validation.classes.<date>.md in the directory")
    args = ap.parse_args(argv)
    try:
        directory = _directory(args)
    except GovernanceError as exc:
        print("validate_classes: %s" % exc, file=sys.stderr)
        return EXIT_NOT_COMPUTABLE
    result = validate(directory)
    text = report(result, directory)
    if args.write:
        name = "%s%s.md" % (REPORT_PREFIX, timing.now().date().isoformat())
        with open(os.path.join(directory, name), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    print(text, end="")
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
