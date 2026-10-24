#!/usr/bin/env python3
"""Find where a dispatch's working time goes when its rows clock a fraction of their
estimates (VIR-057, F-022).

A read-only diagnosis. For each closed time log it prints one line:

- (a) ``rows``: the sum of every measured row's working minutes, parallel rows included;
- (b) ``actual``: the dispatch's measured actual, as ``timing.summary`` (``timing
  --summary``, the close-out's figure) reports it: sequential rows only;
- (c) ``gap``: the unclocked gap, minutes inside the clocked span (first start to last
  end) that no row covers and no wait explains. ``actual`` is itself a sum of row
  minutes, so ``actual - rows`` is only the parallel rows' minutes negated and can never
  show unclocked work; the gap is therefore measured against the span. ``double``
  (minutes of ``actual`` counted twice by sequential rows that overlap) and ``parallel``
  (minutes clocked only by background rows) are reported beside it;
- (d) ``waits``: minutes in waits, by reason;
- (e) ``added``: minutes in rows added after the first listing;
- (f) ``tiny`` and ``burst``: the share of rows under 1 minute, and of rows stamped in
  bursts (``BURST_SIZE`` or more rows ended within ``BURST_WINDOW`` seconds);
- (g) ``ratio``: for calculable rows with an estimate, the median of actual / estimate.

The verdict names the cause of the shortfall, the minutes by which calculable rows fell
under their written estimates. Each cause is weighed in minutes: ``unclocked-gap`` and
``waits`` by the dispatch's gap and wait minutes (each capped at its own dispatch's
shortfall); ``burst-stamping`` and ``row-granularity`` by the shortfall of the
calculable rows stamped in a burst, or under 1 minute; what is left was clocked
contiguously and is ``other: estimates-exceed-clocked-work``. A cause holding a majority
of the shortfall is the verdict; otherwise ``other: mixed (<top>, <second>)``.

Usage:
    python validate_pricing.py [CLOSE_OUTS | --root DIR] [--write]

``--write`` saves the report as ``<dir>/Validation.pricing.<YYYY-MM-DD>.md``, the only
file this script ever writes.

Exit codes: 0 a verdict; 3 not computable (no closed log, or no closeOuts role).
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

TINY = 1.0                 # minutes: a row under this is a granularity row
BURST_WINDOW = 60          # seconds: ends this close together are one burst
BURST_SIZE = 2             # rows: "several rows ended within the same minute"
MAJORITY = 0.5             # a cause above this share of the shortfall is the verdict
# Logs read but kept out of the verdict's counts, each with its reason.
EXCLUDED = {"VIR-051-S1": "the epic's P4–P5 rows were never opened"}
CAUSES = ("unclocked-gap", "waits", "burst-stamping", "row-granularity")
REMAINDER = "other: estimates-exceed-clocked-work"

# The one proposed fix per verdict, so the report picks it by the verdict and no one
# chooses it by hand: an item stub for the next review, never built here. A mixed
# verdict takes its top cause's stub.
STUBS = {
    "unclocked-gap": "Clock the work between rows — add to `timing --check` a finding for "
                     "every gap over 5 minutes between one row's end and the next row's "
                     "start that no wait explains, so the time between rows is attributed "
                     "instead of lost.",
    "waits": "Show owner time beside the estimate — add the wait minutes, by reason, to the "
             "close-out's Time table; `working` already leaves them out.",
    "burst-stamping": "Flag a burst — add to `timing --end` a warning when a row ends within "
                      "%d seconds of another row's end, and keep such a row out of "
                      "`history()` until the owner confirms it." % BURST_WINDOW,
    "row-granularity": "Price calculable rows from rows of at least a minute — change "
                       "`price()` to leave sub-minute rows out of the calculable pools.",
    REMAINDER: "Write calculable estimates at the clock's scale — add to `timing "
               "--rows-from-spec` and the readiness rubric a flag on a written estimate over "
               "3× the row's history price, so a specification's total stops promising "
               "minutes the work never takes.",
}

EXIT_VERDICT, EXIT_NOT_COMPUTABLE = 0, 3
REPORT_PREFIX = "Validation.pricing."


@dataclasses.dataclass
class Dispatch:
    name: str
    path: str
    sha256: str
    rows: float = 0.0                 # (a)
    actual: float | None = None       # (b); None: not computable
    gap: float = 0.0                  # (c)
    double: float = 0.0
    parallel: float = 0.0
    span: float = 0.0
    waits: dict = dataclasses.field(default_factory=dict)   # (d) reason -> minutes
    added: float = 0.0                # (e)
    tiny: float = 0.0                 # (f) share
    burst: float = 0.0                # (f) share
    ratio: float | None = None        # (g)
    ratios: list = dataclasses.field(default_factory=list)
    shortfall: float = 0.0            # gross: rows over their estimate offset nothing
    net: float = 0.0                  # estimate − working, rows over their estimate included
    burst_shortfall: float = 0.0
    tiny_shortfall: float = 0.0
    counted: bool = True
    note: str = ""


def _minutes(begin, end) -> float:
    return (end - begin).total_seconds() / 60


def _union(intervals: list) -> list:
    """Overlapping ``[start, end]`` intervals merged, in start order."""
    merged = []
    for begin, end in sorted(intervals):
        if merged and begin <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([begin, end])
    return merged


def _covered(intervals: list) -> float:
    return sum(_minutes(begin, end) for begin, end in _union(intervals))


def bursts(ran: list) -> set:
    """Ids of rows whose end falls within ``BURST_WINDOW`` seconds of the first end of a
    run of at least ``BURST_SIZE`` ends."""
    found, group = set(), []
    for row in sorted(ran, key=lambda r: r.ended):
        if group and (row.ended - group[0].ended).total_seconds() > BURST_WINDOW:
            if len(group) >= BURST_SIZE:
                found.update(r.id for r in group)
            group = []
        group.append(row)
    if len(group) >= BURST_SIZE:
        found.update(r.id for r in group)
    return found


def measure(name: str, path: str, sha256: str, events: list) -> Dispatch:
    logged = timing.rows(events)
    found = Dispatch(name, path, sha256)
    ran = [row for row in logged if row.measured]
    try:
        result = timing.summary(events)
        found.actual = result["actualMinutes"] if result["complete"] else None
    except GovernanceError:
        found.actual = None
    if found.actual is None:
        found.note = "actual: not computable"
    if not ran:
        return found
    found.rows = sum(row.working for row in ran)
    found.added = sum(row.working for row in ran if row.added)
    first, last = min(r.started for r in ran), max(r.ended for r in ran)
    found.span = _minutes(first, last)
    waits = [list(w) for row in ran for w in row.waits]
    sequential = [[r.started, r.ended] for r in ran if not r.parallel]
    covered_all = _covered([[r.started, r.ended] for r in ran] + waits)
    # ``working`` leaves waits out, so the sequential cover it is compared with does too.
    covered_sequential = _covered(sequential + waits) - _covered(waits)
    found.gap = max(0.0, found.span - covered_all)
    found.double = max(0.0, sum(r.working for r in ran if not r.parallel) - covered_sequential)
    found.parallel = max(0.0, _covered([[r.started, r.ended] for r in ran]) - _covered(
        sequential))
    for row in logged:
        for reason, (begin, end) in zip(row.wait_reasons, row.waits):
            if end is not None:
                found.waits[reason] = found.waits.get(reason, 0.0) + _minutes(begin, end)
    stamped = bursts(ran)
    found.tiny = sum(1 for r in ran if r.working < TINY) / len(ran)
    found.burst = len(stamped) / len(ran)
    for row in ran:
        if row.fields.get("class") != "calculable" or not row.estimate:
            continue
        found.ratios.append(row.working / row.estimate)
        short = max(0.0, row.estimate - row.working)
        found.shortfall += short
        found.net += row.estimate - row.working
        if row.id in stamped:
            found.burst_shortfall += short
        elif row.working < TINY:
            found.tiny_shortfall += short
    found.ratio = statistics.median(found.ratios) if found.ratios else None
    return found


def read(directory: str) -> tuple[list, list]:
    """``(dispatches, skipped)``: every closed log measured; an open log and an
    unreadable one are named in ``skipped``, never fatal."""
    found, skipped = [], []
    for path in timing.log_paths(directory):
        name = os.path.basename(path)[len(timing.LOG_PREFIX):-len(timing.LOG_SUFFIX)]
        try:
            with open(path, "rb") as handle:
                digest = hashlib.sha256(handle.read()).hexdigest()
            events = timing.load(path)
        except (OSError, GovernanceError) as exc:
            skipped.append((path, "unreadable: %s" % exc))
            continue
        logged = timing.rows(events)
        if not logged or not all(row.ended is not None or row.parked for row in logged):
            skipped.append((path, "open: a run in flight, not closed"))
            continue
        dispatch = measure(name, path, digest, events)
        if name in EXCLUDED:
            dispatch.counted, dispatch.note = False, "excluded: " + EXCLUDED[name]
        elif dispatch.actual is None:
            dispatch.counted = False
        found.append(dispatch)
    return found, skipped


def weigh(dispatches: list) -> dict:
    """Minutes of the calculable rows' shortfall each cause holds, over counted logs."""
    weights = dict.fromkeys(CAUSES + (REMAINDER,), 0.0)
    for d in dispatches:
        if not d.counted or d.shortfall <= 0:
            continue
        rows = d.burst_shortfall + d.tiny_shortfall
        weights["burst-stamping"] += d.burst_shortfall
        weights["row-granularity"] += d.tiny_shortfall
        left = d.shortfall - rows
        gap = min(d.gap, left)
        weights["unclocked-gap"] += gap
        waited = min(sum(d.waits.values()), left - gap)
        weights["waits"] += waited
        weights[REMAINDER] += left - gap - waited
    return weights


def decide(weights: dict) -> str:
    total = sum(weights.values())
    if total <= 0:
        return "not computable — no calculable row fell under its estimate"
    ranked = sorted(weights.items(), key=lambda pair: -pair[1])
    if ranked[0][1] > MAJORITY * total:
        return ranked[0][0]
    return "other: mixed (%s, %s)" % (ranked[0][0], ranked[1][0])


def _fmt(value, pattern="%.1f") -> str:
    return "—" if value is None else pattern % value


def line(d: Dispatch) -> str:
    waits = ", ".join("%s %.1f" % pair for pair in sorted(d.waits.items())) or "0.0"
    return ("%s: a rows %.1f · b actual %s · c gap %.1f (double %.1f, parallel %.1f, span "
            "%.1f) · d waits %s · e added %.1f · f tiny %.0f%% burst %.0f%% · g ratio %s%s"
            % (d.name, d.rows, _fmt(d.actual) if d.actual is not None else "not computable",
               d.gap, d.double, d.parallel, d.span, waits, d.added, d.tiny * 100,
               d.burst * 100, _fmt(d.ratio, "%.2f"),
               " · %s" % d.note if d.note else ""))


def report(dispatches: list, skipped: list, directory: str) -> tuple[str, str]:
    weights = weigh(dispatches)
    verdict = decide(weights)
    counted = [d for d in dispatches if d.counted]
    total = sum(weights.values())
    ratios = [r for d in counted for r in d.ratios]
    lines = ["# Where a dispatch's time goes — VIR-057 (F-022)", "",
             "Close-outs directory: `%s`. Read-only; every figure below is printed by "
             "`python plugins/virtuoso/scripts/validate_pricing.py`, none entered by hand." %
             directory, "",
             "## Dispatches", "",
             "| Log | a rows | b actual | c gap | double | parallel | span | d waits | "
             "e added | f tiny | f burst | g ratio | Counted | SHA-256 |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for d in dispatches:
        lines.append("| %s | %.1f | %s | %.1f | %.1f | %.1f | %.1f | %s | %.1f | %.0f%% | "
                     "%.0f%% | %s | %s | `%s` |" % (
                         d.name, d.rows, _fmt(d.actual) if d.actual is not None
                         else "not computable", d.gap, d.double, d.parallel, d.span,
                         ", ".join("%s %.1f" % p for p in sorted(d.waits.items())) or "0.0",
                         d.added, d.tiny * 100, d.burst * 100, _fmt(d.ratio, "%.2f"),
                         "yes" if d.counted else "no — " + d.note, d.sha256[:12]))
    for path, reason in skipped:
        lines.append("| %s | — | — | — | — | — | — | — | — | — | — | — | no — %s | — |" % (
            os.path.basename(path), reason.replace("|", "/")))
    lines += ["", "Minutes. *a* every measured row; *b* `timing --summary`'s actual "
              "(sequential rows); *c* minutes of the span no row or wait covers; *double* "
              "minutes of *b* counted twice by overlapping sequential rows; *parallel* "
              "minutes only background rows clock; *f* shares of measured rows (under %.0f "
              "minute; ended within %d s of %d or more others); *g* the median of actual ÷ "
              "estimate over calculable rows with an estimate." % (TINY, BURST_WINDOW,
                                                                  BURST_SIZE - 1), "",
              "## Totals over counted dispatches", "",
              "| Figure | Value |", "|---|---|",
              "| Counted dispatches | %d of %d closed |" % (len(counted), len(dispatches)),
              "| a rows | %.1f |" % sum(d.rows for d in counted),
              "| b actual | %.1f |" % sum(d.actual for d in counted),
              "| c gap | %.1f |" % sum(d.gap for d in counted),
              "| double-counted in b | %.1f |" % sum(d.double for d in counted),
              "| parallel only | %.1f |" % sum(d.parallel for d in counted),
              "| span | %.1f |" % sum(d.span for d in counted),
              "| d waits | %.1f |" % sum(sum(d.waits.values()) for d in counted),
              "| e added | %.1f |" % sum(d.added for d in counted),
              "| g ratio (all calculable rows, %d) | %s |" % (
                  len(ratios), _fmt(statistics.median(ratios) if ratios else None, "%.2f")),
              "", "## The shortfall, by cause", "",
              "Calculable rows with an estimate fell %.1f minutes under their written "
              "estimates." % total, "",
              "| Cause | Minutes | Share |", "|---|---|---|"]
    for cause, minutes in sorted(weights.items(), key=lambda pair: -pair[1]):
        lines.append("| %s | %.1f | %s |" % (cause, minutes, "%.0f%%" % (100 * minutes / total)
                                             if total else "—"))
    lines += ["", "Each calculable row's shortfall (written estimate − working minutes) is "
              "attributed to burst-stamping when the row ended in a burst, else to "
              "row-granularity when it clocked under a minute. The rest of a dispatch's "
              "shortfall goes first to its unclocked gap and then to its waits, each capped "
              "at what is left, and what remains was clocked contiguously by its rows: "
              "the work took that long, and the estimate was written higher.", "",
              "Read with these limits. The shortfall is gross: a row that ran over its "
              "estimate offsets nothing (net of such rows, the shortfall is %.1f minutes). "
              "Burst-stamping is an upper bound: a burst row's whole shortfall is charged to "
              "it even when the row ran for real minutes, and a burst is anchored at its "
              "first end, so where one ends depends on that anchor. The gap and the waits "
              "are dispatch-wide, so they may also cover rows that are not calculable. An "
              "epic log is read as one dispatch. The figures hold for the logs as they were "
              "when the report was written: each log is named with the start of its "
              "SHA-256." % sum(d.net for d in counted),
              "", "verdict: %s" % verdict, ""]
    lines += ["## Proposed fix — an item stub for the next review, not built here", "",
              stub(verdict), ""]
    return "\n".join(lines), verdict


def stub(verdict: str) -> str:
    if verdict in STUBS:
        return STUBS[verdict]
    for cause in STUBS:                      # "other: mixed (<top>, <second>)"
        if verdict.startswith("other: mixed (%s," % cause):
            return STUBS[cause]
    return "None: the verdict is not computable."


def _directory(args) -> str:
    if args.dir:
        return args.dir
    return registry_mod.load(args.root).resolve("closeOuts")


def main(argv=None) -> int:
    textio.utf8_stdio()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dir", nargs="?", help="the close-outs directory (default: the "
                    "registry's closeOuts role under --root)")
    ap.add_argument("--root", default=os.getcwd())
    ap.add_argument("--write", action="store_true",
                    help="save the report as Validation.pricing.<date>.md in the directory")
    args = ap.parse_args(argv)
    try:
        directory = _directory(args)
    except GovernanceError as exc:
        print("validate_pricing: %s" % exc, file=sys.stderr)
        return EXIT_NOT_COMPUTABLE
    dispatches, skipped = read(directory)
    for d in dispatches:
        print(line(d))
    for path, reason in skipped:
        print("%s: skipped — %s" % (os.path.basename(path), reason))
    text, verdict = report(dispatches, skipped, directory)
    print("verdict: %s" % verdict)
    if args.write:
        name = "%s%s.md" % (REPORT_PREFIX, timing.now().date().isoformat())
        with open(os.path.join(directory, name), "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    return EXIT_NOT_COMPUTABLE if verdict.startswith("not computable") else EXIT_VERDICT


if __name__ == "__main__":
    sys.exit(main())
