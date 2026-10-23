"""The ``cost`` command: what a dispatch cost, row by row, and which dispatches cost most.

A dispatch's transcript is found through its binding (``hosts.read_binding``), never by
guessing a session. Its cost is split two ways:

* **row cost**: the calls of every subagent whose spawn names that row (``row N``);
* **orchestration**: the top-level session's own calls between the time log's first and
  last row stamp, and every subagent whose spawn names no row (or names two that disagree).

A dispatch with no binding has no transcript figures (*not computable*, naming the missing
binding) — unless its time log carries a ``cost`` event, which the backfill writes for
dispatches that ran before bindings existed (dispatch-level only, marked ``backfilled``).
A transcript that is no longer on disk is named, never read as zero.
"""
from __future__ import annotations

import datetime as _dt
import os
import re

from . import cost as cost_mod, hosts, timing
from .providers.kpi import ESTIMATED, INFERRED, MEASURED

NO_BINDING = ("a dispatch binding for %s (recorded when its session first runs "
              "`timing --dispatch %s` with a row verb under the plugin's pre-tool hook)")
_LOG_RE = re.compile(r"^Timing\.(.+)\.jsonl$")
#: A cache expiry is called a twelfth of the lifetime early (the stamp is the call's end).
EARLY = 1 / 12
#: The stamps of work itself; ``open``/``add`` list rows, ``confirm``/``park`` are rulings
#: made later, and ``cost`` is a record — none of them is when the work ran.
_ROW_EVENTS = ("start", "end", "wait", "resume")


def call_time(text: str) -> _dt.datetime | None:
    """A host's call stamp (ISO 8601, ``Z`` or an offset, fractions allowed), in UTC."""
    try:
        moment = _dt.datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=_dt.timezone.utc)


def window(events: list[dict]) -> tuple[str, str]:
    """The first and last stamp of a log's work (its rows' starts, waits, resumes and ends)."""
    stamps = sorted(str(e.get("at")) for e in events
                    if e.get("at") and e.get("event") in _ROW_EVENTS)
    return (stamps[0], stamps[-1]) if stamps else ("", "")


def _within(call: hosts.Call, start: str, end: str, open_ended: bool) -> bool:
    moment = call_time(call.time) if call.time else None
    low, high = timing.parse_stamp(start), timing.parse_stamp(end)
    if moment is None or low is None:
        return False
    return moment >= low and (open_ended or high is None or moment <= high)


class Reader:
    """Reads each transcript once per command, by path and modification time."""

    def __init__(self):
        self._memo: dict[tuple[str, float], hosts.TranscriptFacts] = {}
        #: A transcript that is on disk but could not be read: path -> why.
        self.errors: dict[str, str] = {}

    def facts(self, adapter, path: str) -> hosts.TranscriptFacts | None:
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            return None                               # gone: the caller names it
        key = (path, mtime)
        if key not in self._memo:
            try:
                self._memo[key] = adapter.read_transcript(path)
            except Exception as exc:                  # damaged: named, never a crash
                self.errors[path] = str(exc)
                return None
        return self._memo[key]


def _usage_total(calls) -> hosts.Usage:
    total = hosts.Usage()
    for call in calls:
        total = total + call.usage
    return total


def priced(calls, prices) -> dict:
    """Tokens (``measured``) and dollars (with their own kind) of a list of calls."""
    usage = _usage_total(calls)
    usd, kind, missing = cost_mod.price_calls(calls, prices)
    return {"tokens": usage.total, "usage": usage.as_dict(), "usd": usd,
            "usdKind": kind if usd is not None else None, "missing": missing,
            "calls": len(calls), "kind": MEASURED}


def _rewrite_usd(tokens: int, call: hosts.Call, prices) -> float | None:
    """What re-writing ``tokens`` cost over reading them from cache, at ``call``'s card."""
    day = (call.time or "")[:10]
    written = cost_mod.price(hosts.Usage(cache_write_5m=call.usage.cache_write_5m,
                                         cache_write_1h=call.usage.cache_write_1h,
                                         cache_write_no_lifetime=call.usage.cache_write_no_lifetime),
                             call.model, day, prices)
    read = cost_mod.price(hosts.Usage(cache_read=tokens), call.model, day, prices)
    if not written.computable or not read.computable:
        return None
    return max(0.0, written.usd - read.usd)


def cold_returns(calls, adapter, facts, prices=None) -> list[dict]:
    """Each top-level call made after the cache had expired. The evidence is the call's own
    usage — it wrote again more than it read from cache — after an idle gap past the
    lifetime (less a twelfth). Its kind is the lifetime's: ``measured`` when the transcript
    shows it, else ``inferred``."""
    minutes, how = adapter.lifetime(facts)
    if not minutes:
        return []
    found = []
    for before, after in zip(calls, calls[1:]):
        a, b = call_time(before.time), call_time(after.time)
        if a is None or b is None:
            continue
        idle = (b - a).total_seconds() / 60
        rewrite = (after.usage.cache_write_5m + after.usage.cache_write_1h
                   + after.usage.cache_write_no_lifetime)
        if idle >= minutes * (1 - EARLY) and rewrite > after.usage.cache_read:
            found.append({"at": after.time, "idleMinutes": round(idle), "tokens": rewrite,
                          "usd": _rewrite_usd(rewrite, after, prices) if prices else None,
                          "kind": how, "callId": after.id})
    return found


def model_reloads(calls, prices) -> list[dict]:
    """Each top-level change of model between two calls, and what the new model wrote into
    its cache on that call (``measured``) and that costs over reading it."""
    found = []
    for before, after in zip(calls, calls[1:]):
        old, new = cost_mod.normal_model(before.model), cost_mod.normal_model(after.model)
        if not old or not new or old == new:
            continue
        tokens = (after.usage.cache_write_5m + after.usage.cache_write_1h
                  + after.usage.cache_write_no_lifetime)
        found.append({"at": after.time, "from": old, "to": new, "tokens": tokens,
                      "usd": _rewrite_usd(tokens, after, prices) if tokens else 0.0,
                      "kind": MEASURED})
    return found


def recorded(events: list[dict]) -> dict | None:
    """The cost record a backfill left in a time log — priced, or marked not computable."""
    for event in reversed(events):
        if event.get("event") == "cost" and event.get("source") == "backfilled":
            return event
    return None


def dispatch_cost(directory: str, dispatch: str, prices: dict | None = None,
                  reader: Reader | None = None) -> dict:
    """What one dispatch cost: orchestration apart, each row beside its working time and
    prediction, cold returns and model reloads; every figure with its kind."""
    prices = prices if prices is not None else cost_mod.catalogue()
    reader = reader or Reader()
    path = os.path.join(directory, timing.log_name(dispatch))
    events = timing.load(path) if os.path.isfile(path) else []
    rows = timing.rows(events) if events else []
    result = {"dispatch": dispatch, "log": path if events else None,
              "rows": [{"id": r.id, "label": r.label, "title": r.title, "taskKind": r.kind,
                        "working": r.working, "workingKind": MEASURED,
                        "predicted": r.predicted, "predictedKind": ESTIMATED} for r in rows],
              "guardCatches": {"computable": False,
                               "missing": ["a guardLog role with this dispatch's receipts"]}}
    binding = hosts.read_binding(dispatch)
    if not binding:
        record = recorded(events)
        result["source"] = "backfilled" if record else None
        if record and record.get("computable", True):
            result["orchestration"] = record.get("orchestration")
            result["total"] = record.get("total")
            result["perRow"] = record.get("perRow") or {"computable": False, "missing": [
                "a row N in each subagent's spawn (the dispatch predates the row rule)"]}
        else:
            result["missing"] = (record or {}).get("missing") or [NO_BINDING % (dispatch,
                                                                               dispatch)]
        return result
    start, end = window(events)
    open_ended = any(r.ended is None and not r.parked for r in rows)
    if open_ended:
        result["window"] = "open"                     # every later call counts until it closes
    begin = timing.parse_stamp(start)
    calls, row_calls, unattributed, missing = [], {}, [], []
    result["coldReturns"], result["modelReloads"] = [], []
    for session in binding.get("sessions") or [binding]:
        adapter = hosts.adapter(session.get("host") or binding.get("host", ""))
        transcript = session.get("transcript") or ""
        if adapter is None:
            missing.append("an adapter for host %s" % session.get("host"))
            continue
        facts = reader.facts(adapter, transcript)
        if facts is None:
            missing.append("the transcript %s (%s)" % (
                transcript, "cannot be read: %s" % reader.errors[transcript]
                if transcript in reader.errors else "no longer on disk"))
            continue
        top = [c for c in facts.calls if _within(c, start, end, open_ended)]
        calls += top
        for sub_path, description, task_name in adapter.subagents(transcript, facts):
            try:
                if begin and os.path.getmtime(sub_path) < begin.timestamp():
                    continue                          # last written before the dispatch
            except OSError:
                continue
            sub_facts = reader.facts(adapter, sub_path)
            sub = [c for c in (sub_facts.calls if sub_facts else [])
                   if _within(c, start, end, open_ended)]
            if not sub:
                continue
            row, ambiguous = hosts.spawn_row_detail(description, task_name)
            if row is None:
                unattributed += sub
                if ambiguous:
                    result.setdefault("ambiguous", []).append(os.path.basename(sub_path))
            else:
                row_calls.setdefault(row, []).extend(sub)
        result["coldReturns"] += cold_returns(top, adapter, facts, prices)
        result["modelReloads"] += model_reloads(top, prices)
    result["source"] = "bound"
    result["host"] = sorted({s.get("host") for s in binding.get("sessions") or [binding]
                             if s.get("host")})
    if missing and not calls and not row_calls:
        result["missing"] = missing
        return result
    if missing:
        result["incomplete"] = missing
    result["orchestration"] = priced(calls + unattributed, prices)
    for row in result["rows"]:
        if row["id"] in row_calls:
            row["cost"] = priced(row_calls[row["id"]], prices)
        else:
            row["cost"] = None
            row["costNote"] = "no subagent named this row: its work is in orchestration"
    result["unlistedRows"] = sorted(r for r in row_calls if r not in {x.id for x in rows})
    every = calls + unattributed + [c for group in row_calls.values() for c in group]
    result["total"] = priced(every, prices)
    if open_ended or missing:
        for figure in (result["orchestration"], result["total"]):
            figure["kind"] = ESTIMATED                # an open window or a lost session
    return result


def closed_dispatches(directory: str, skipped: list | None = None):
    """``(dispatch, events)`` of every time log whose rows have all ended or been parked. A
    log that cannot be read is named in ``skipped`` and left out."""
    found = []
    try:
        names = sorted(os.listdir(directory))
    except OSError:
        return found
    for name in names:
        match = _LOG_RE.match(name)
        if not match:
            continue
        try:
            events = timing.load(os.path.join(directory, name))
        except Exception as exc:
            if skipped is not None:
                skipped.append("%s: %s" % (name, exc))
            continue
        rows = timing.rows(events)
        if rows and all(r.ended is not None or r.parked for r in rows):
            found.append((match.group(1), events))
    return found


def recent(directory: str, last: int = 10, prices: dict | None = None,
           unit: str = "both") -> dict:
    """The last ``last`` closed dispatches (by when they ended), costliest first — by
    dollars when the units show dollars and every one has a dollar figure, else by tokens —
    and the three costliest's share of the total."""
    if last < 1:
        raise ValueError("--last is a count of dispatches, 1 or more")
    prices = prices if prices is not None else cost_mod.catalogue()
    skipped: list[str] = []
    closed = sorted(closed_dispatches(directory, skipped),
                    key=lambda pair: timing.parse_stamp(window(pair[1])[1])
                    or _dt.datetime.min.replace(tzinfo=_dt.timezone.utc))
    reader, entries = Reader(), []
    for dispatch, _events in closed[-last:]:
        report = dispatch_cost(directory, dispatch, prices, reader)
        total = report.get("total") or {}
        entries.append({"dispatch": dispatch, "source": report.get("source"),
                        "tokens": total.get("tokens"), "usd": total.get("usd"),
                        "usdKind": total.get("usdKind"),
                        "missing": report.get("missing") or total.get("missing") or []})
    priced_ = [e for e in entries if e["tokens"] is not None]
    by = "usd" if unit != "tokens" and priced_ and all(e["usd"] is not None for e in priced_) \
        else "tokens"
    priced_.sort(key=lambda e: e[by], reverse=True)
    whole = sum(e[by] for e in priced_)
    top = priced_[:3]
    return {"dispatches": priced_ + [e for e in entries if e["tokens"] is None],
            "rankedBy": by, "skipped": skipped,
            "topShare": round(sum(e[by] for e in top) / whole, 2) if whole else None,
            "topCount": len(top), "notComputable": len(entries) - len(priced_)}


# --- rendering ---------------------------------------------------------------------------------

def _amount(figure: dict | None, unit: str) -> str:
    if not figure or figure.get("tokens") is None:
        return "not computable"
    text = cost_mod.amount(figure["tokens"], figure.get("usd"), unit)
    if unit == "tokens":
        return "%s  %s" % (text, figure.get("kind") or MEASURED)
    kind = figure.get("usdKind") or "not computable"
    gap = "  (missing: %s)" % "; ".join(figure["missing"]) if figure.get("missing") else ""
    return "%s  %s%s" % (text, kind, gap)


def render_dispatch(report: dict, unit: str, why: bool = False) -> str:
    lines = ["cost %s  (at API prices)" % report["dispatch"]]
    if report.get("missing"):
        lines.append("  transcript figures: not computable (missing: %s)"
                     % "; ".join(report["missing"]))
    else:
        if report.get("source") == "backfilled":
            lines.append("  source: backfilled from the host's transcript after the fact")
        if report.get("window") == "open":
            lines.append("  the time log is still open: every later call counts (estimated)")
        for note in report.get("incomplete") or []:
            lines.append("  incomplete: %s" % note)
        lines.append("  %-14s %s" % ("orchestration", _amount(report.get("orchestration"), unit)))
        lines.append("  %-14s %s" % ("total", _amount(report.get("total"), unit)))
    for row in report["rows"]:
        working = "%d min measured" % round(row["working"]) if row["working"] is not None \
            else "—"
        predicted = "%s min estimated" % row["predicted"] if row["predicted"] is not None \
            else "—"
        if row.get("cost") is not None:
            figure = _amount(row["cost"], unit)
        elif row.get("costNote"):
            figure = row["costNote"]
        else:
            figure = ((report.get("perRow") or {}).get("missing") or ["not computable"])[0]
        lines.append("  %-4s %-36s %s (predicted %s)  %s" % (
            row["label"], row["title"][:36], working, predicted, figure))
    for cold in report.get("coldReturns") or []:
        lines.append("  cold return %s: idle %d min, %s  %s" % (
            cold["at"], cold["idleMinutes"], cost_mod.amount(cold["tokens"], cold["usd"], unit),
            cold["kind"]))
    for reload in report.get("modelReloads") or []:
        lines.append("  model change %s: %s -> %s, %s written  %s" % (
            reload["at"], reload["from"], reload["to"],
            cost_mod.amount(reload["tokens"], reload["usd"], unit), reload["kind"]))
    for name in report.get("ambiguous") or []:
        lines.append("  %s: its spawn names two different rows, so it counts as orchestration"
                     % name)
    catches = report["guardCatches"]
    lines.append("  guard catches: not computable (missing: %s)" % "; ".join(catches["missing"]))
    if why:
        lines += ["", "How this was calculated:",
                  "- Tokens (measured): the host-reported usage of the dispatch's calls, "
                  "counted once per API response.",
                  "- Dollars: each call priced at the card in force on its day "
                  "(references/model-prices.json); a call before a model's first card is "
                  "priced at that card and is estimated.",
                  "- Orchestration: the top-level session's calls between the time log's "
                  "first and last row stamp, plus subagents whose spawn names no row.",
                  "- A row's cost: the calls of the subagents whose spawn names it (row N).",
                  "- A cold return: a call after an idle gap past the cache lifetime (less a "
                  "twelfth) that wrote again more than it read; priced as the write over the "
                  "read. A model change: what the new model wrote on its first call.",
                  "Assumptions: two dispatches sharing a session at the same time would both "
                  "count its calls; the working minutes are measured, the predictions estimated."]
    return "\n".join(lines)


def render_recent(report: dict, unit: str, why: bool = False) -> str:
    lines = ["cost — the last closed dispatches, costliest first (at API prices)"]
    for entry in report["dispatches"]:
        if entry["tokens"] is None:
            lines.append("  %-28s not computable (missing: %s)"
                         % (entry["dispatch"], "; ".join(entry["missing"])))
        else:
            lines.append("  %-28s %s%s" % (entry["dispatch"], _amount(entry, unit),
                                          "  backfilled" if entry["source"] == "backfilled"
                                          else ""))
    if report["topShare"] is not None:
        lines.append("  top %d: %d%% of the total by %s%s" % (
            report["topCount"], round(100 * report["topShare"]),
            "dollars" if report["rankedBy"] == "usd" else "tokens",
            " (%d not computable, left out)" % report["notComputable"]
            if report["notComputable"] else ""))
    for name in report.get("skipped") or []:
        lines.append("  skipped, cannot be read: %s" % name)
    if why:
        lines += ["", "How this was calculated:",
                  "- The closed time logs in the closeOuts role, latest by their last row "
                  "stamp; each dispatch's total as `cost --dispatch` gives it.",
                  "- Ranked by dollars when shown and known for every dispatch, else by tokens; "
                  "the share is the three costliest's part of the listed total."]
    return "\n".join(lines)
