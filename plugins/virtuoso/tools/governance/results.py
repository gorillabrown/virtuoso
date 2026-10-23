"""Did it work? The runs after a change put against the runs before it.

For a change in the change ledger, ``results`` splits the project's closed time logs at the
change's ``effectiveFrom`` instant and compares the two sides, honest about sample size,
trade-offs and confounders:

* **Primary measure**: cost per measured row (tokens; and dollars at API prices, unless the
  units are tokens) — or, for a change whose subject is not cost (a lesson, a standing rule),
  the share of working time spent on rows the first listing missed (``added-share``).
* **Sides**: a dispatch that ended before the change is *before*; one that started at or after
  it is *after*, until the change was undone or replaced (then the after side stops there). A
  dispatch whose work straddles the change belongs to neither and is named.
* **Baseline**: the 14 days before, extended to as many days as the change has been in, up to
  30. Baselines of 3, 5 and 7 days are worked out too; when their spread is wider than the
  no-effect band, or they disagree in direction, the verdict gives the range, lowest to
  highest, never the one that reads best.
* **Minimum sample** before any verdict (``results.minimum``): 3 active days, 3 closed time
  logs and 30 measured rows after the change. Until then it says how far along it is.
* **No clear effect** under a 10% move either way (``results.noEffect``).
* **Trade-offs**: every other figure is shown, and one that moved the wrong way is marked; a
  figure one side never observed is not compared.
* **Confounders**: another change in the same window, a different mix of work, a baseline
  covering less than its span, a difference already under way just before.

A verdict's kind is the weaker of its two sides'. Tokens are compared always; dollars too,
except across a change of price card — then they are *not computable* and the token verdict is
the verdict (a price change never reads as the effect of a change).
"""
from __future__ import annotations

import datetime as _dt
import statistics

from . import cost as cost_mod, costreport, timing
from .providers.kpi import ESTIMATED, INFERRED, MEASURED, confidence_for

DEFAULT_MINIMUM = {"activeDays": 3, "closedLogs": 3, "measuredRows": 30}
DEFAULT_NO_EFFECT = 0.10
COST_SUBJECTS = ("guard", "policy", "plugin-version", "manual")
_KIND_ORDER = (MEASURED, INFERRED, ESTIMATED)
UTC = _dt.timezone.utc


def _moment(stamp: str) -> _dt.datetime | None:
    return timing.parse_stamp(stamp) or costreport.call_time(stamp)


def dispatch_facts(directory: str, reader=None, prices=None,
                   since: _dt.datetime | None = None) -> list[dict]:
    """One record per closed time log (ended at or after ``since``): when its work started
    and ended, its measured rows, errors, added share, tiers, hosts and cost. A log whose
    cost cannot be worked out is kept, its cost *not computable*."""
    prices = prices if prices is not None else cost_mod.catalogue()
    reader = reader or costreport.Reader()
    found = []
    for dispatch, events in costreport.closed_dispatches(directory):
        rows = timing.rows(events)
        measured = [r for r in rows if r.measured]
        start, end = costreport.window(events)
        began, ended = _moment(start), _moment(end)
        if not measured or ended is None or (since and ended < since):
            continue
        try:
            report = costreport.dispatch_cost(directory, dispatch, prices, reader)
        except Exception as exc:                      # one log never breaks the verdicts
            report = {"missing": [str(exc)]}
        total = report.get("total") or {}
        errors = [abs(r.working - r.predicted) / r.predicted for r in measured
                  if r.predicted and not r.parallel]
        worked = sum(r.working for r in measured)
        added = sum(r.working for r in measured if r.added)
        found.append({
            "dispatch": dispatch, "start": began, "end": ended, "day": ended.date(),
            "rows": len(measured),
            "rowError": statistics.median(errors) if errors else None,
            "addedShare": added / worked if worked else None,
            "waited": sum(r.waited for r in measured) / len(measured),
            "tiers": sorted(r.tier for r in measured if r.tier),
            "hosts": report.get("host") if isinstance(report.get("host"), list) else [],
            "tokens": total.get("tokens"), "usd": total.get("usd"),
            "tokensKind": total.get("kind") or MEASURED,
            "usdKind": total.get("usdKind"), "source": report.get("source"),
            "coldReturns": (len(report["coldReturns"]) / len(measured)
                            if "coldReturns" in report else None)})
    return found


def _weaker(*kinds: str) -> str:
    ranked = [k for k in kinds if k in _KIND_ORDER]
    return max(ranked, key=_KIND_ORDER.index) if ranked else ESTIMATED


def _side(records: list[dict], measure: str) -> dict:
    """One side: cost per measured row (summed cost over the rows of the priced dispatches),
    or the median of a per-dispatch figure over the dispatches that observed it."""
    out = {"dispatches": len(records), "rows": sum(r["rows"] for r in records),
           "activeDays": len({r["day"] for r in records})}
    if measure in ("tokens", "usd"):
        priced = [r for r in records if r[measure] is not None]
        rows = sum(r["rows"] for r in priced)
        out["value"] = sum(r[measure] for r in priced) / rows if rows else None
        out["unpriced"] = len(records) - len(priced)
        kinds = [r["tokensKind" if measure == "tokens" else "usdKind"] for r in priced]
        out["kind"] = _weaker(*kinds) if kinds else None
    else:
        values = [r[measure] for r in records if r[measure] is not None]
        out["value"] = statistics.median(values) if values else None
        out["kind"] = MEASURED if values else None
    return out


def _move(before, after) -> float | None:
    if before in (None, 0) or after is None:
        return None
    return (after - before) / before


def _verdict(move: float | None, threshold: float) -> str:
    if move is None:
        return "not computable"
    if abs(move) < threshold:
        return "no clear effect"
    return "better" if move < 0 else "worse"


def _card_boundary(prices: dict, start: _dt.date, end: _dt.date) -> list[str]:
    """Models whose price card changed between the two sides' days."""
    changed = []
    for model, entry in (prices.get("models") or {}).items():
        froms = sorted(str(c.get("from")) for c in entry.get("cards") or [] if c.get("from"))
        if any(start.isoformat() < f <= end.isoformat() for f in froms[1:]):
            changed.append(model)
    return changed


def _compare(measure: str, before, after, records, at, no_effect, rows_after) -> dict:
    sides = {"before": _side(before, measure), "after": _side(after, measure)}
    move = _move(sides["before"]["value"], sides["after"]["value"])
    found = {"measure": measure, "sides": sides, "move": move,
             "kind": _weaker(sides["before"]["kind"] or ESTIMATED,
                             sides["after"]["kind"] or ESTIMATED)}
    moves = [move] if move is not None else []
    for days in (3, 5, 7):
        short = [r for r in records if at - _dt.timedelta(days=days) <= r["end"] < at]
        moved = _move(_side(short, measure)["value"], sides["after"]["value"])
        if moved is not None:
            moves.append(moved)
    spread = (max(moves) - min(moves)) if moves else 0
    directions = {_verdict(m, no_effect) for m in moves} - {"no clear effect"}
    if move is None:
        found["verdict"] = "not computable"
        if sides["before"]["value"] == 0:
            found["why"] = "the before side is zero, so a share of it cannot be taken"
    elif len(moves) > 1 and (spread > no_effect or len(directions) > 1):
        found["verdict"] = "range %+.0f%% to %+.0f%%" % (100 * min(moves), 100 * max(moves))
        found["range"] = [min(moves), max(moves)]
    else:
        found["verdict"] = _verdict(move, no_effect)
    found["confidence"] = confidence_for(found["kind"], rows_after,
                                         changes_tokens=measure in ("tokens", "usd"))
    return found


def judge(change: dict, records: list[dict], ledger: list[dict], *, unit: str = "both",
          minimum: dict | None = None, no_effect: float = DEFAULT_NO_EFFECT,
          prices: dict | None = None, today: _dt.date | None = None) -> dict:
    """The before/after verdict for one change."""
    from . import changes as changes_mod
    minimum = dict(DEFAULT_MINIMUM, **{k: v for k, v in (minimum or {}).items()
                                       if k in DEFAULT_MINIMUM})
    prices = prices if prices is not None else cost_mod.catalogue()
    at = _moment(str(change.get("effectiveFrom") or change.get("at")))
    now = _dt.datetime.combine(today, _dt.time(23, 59, 59), UTC) if today else timing.now()
    result = {"change": change.get("id"), "subject": change.get("subject"),
              "kind": change.get("kind"), "effectiveFrom": change.get("effectiveFrom"),
              "noEffect": no_effect}
    if at is None:
        return dict(result, verdict="not computable", missing=["the change's effectiveFrom"])
    stop = changes_mod.ended(ledger, change)
    until = _moment(str(stop.get("effectiveFrom") or stop.get("at"))) if stop else None
    if stop:
        result["endedBy"] = {"change": stop.get("id"), "action": stop.get("action"),
                             "at": stop.get("effectiveFrom") or stop.get("at")}
    hosts_in_scope = set((change.get("scope") or {}).get("hosts") or [])
    if hosts_in_scope:
        records = [r for r in records if not r["hosts"] or hosts_in_scope & set(r["hosts"])]
    days_in = max(1, ((until or now) - at).days)
    baseline_days = min(30, max(14, days_in))
    after = [r for r in records if r["start"] and r["start"] >= at
             and (until is None or r["end"] < until)]
    before = [r for r in records if at - _dt.timedelta(days=baseline_days) <= r["end"] < at]
    straddling = [r["dispatch"] for r in records if r["start"] and r["start"] < at <= r["end"]]
    if straddling:
        result["straddling"] = straddling
    progress = {"activeDays": len({r["day"] for r in after}), "closedLogs": len(after),
                "measuredRows": sum(r["rows"] for r in after)}
    result.update(baselineDays=baseline_days, progress=progress, minimum=minimum)
    short = [k for k in minimum if progress.get(k, 0) < minimum[k]]
    if short:
        result["verdict"] = "not yet"
        result["needs"] = {k: minimum[k] - progress.get(k, 0) for k in short}
        return result
    rows_after = progress["measuredRows"]
    if change.get("kind") in COST_SUBJECTS:
        measures = {"tokens": _compare("tokens", before, after, records, at, no_effect,
                                       rows_after)}
        if unit != "tokens":
            span_start = (at - _dt.timedelta(days=baseline_days)).date()
            boundary = _card_boundary(prices, span_start, (until or now).date())
            if boundary:
                measures["usd"] = {"measure": "usd", "verdict": "not computable", "missing": [
                    "one price card for both sides: the card changed between them for %s"
                    % ", ".join(boundary)]}
            else:
                measures["usd"] = _compare("usd", before, after, records, at, no_effect,
                                           rows_after)
        dollars = measures.get("usd")
        primary = dollars if (unit == "dollars" or unit == "both") and dollars \
            and dollars["verdict"] != "not computable" else measures["tokens"]
    else:
        measures = {"addedShare": _compare("addedShare", before, after, records, at, no_effect,
                                           rows_after)}
        primary = measures["addedShare"]
    result["measures"] = measures
    result["primary"] = primary
    others = {}
    for name in ("rowError", "addedShare", "waited", "coldReturns", "rowsPerDispatch"):
        if name == primary["measure"]:
            continue
        if name == "rowsPerDispatch":
            b = progress_b = (sum(r["rows"] for r in before) / len(before)) if before else None
            a = sum(r["rows"] for r in after) / len(after) if after else None
            others[name] = {"before": progress_b, "after": a, "move": _move(b, a)}
            continue
        b, a = _side(before, name)["value"], _side(after, name)["value"]
        moved = _move(b, a)
        from_zero = b == 0 and a is not None and a > 0      # no share to move by: still worse
        others[name] = {"before": b, "after": a, "move": moved,
                        "tradeOff": from_zero or (moved is not None and moved >= no_effect)}
    result["others"] = others
    result["tradeOffs"] = sorted(n for n, o in others.items() if o.get("tradeOff"))
    confounders = []
    window_start = at - _dt.timedelta(days=baseline_days)
    for other in ledger:
        when = _moment(str(other.get("effectiveFrom") or other.get("at")))
        if (other.get("id") in (change.get("id"), (stop or {}).get("id"))
                or other.get("undoes") == change.get("id") or other.get("kind") == "plugin-version"
                and change.get("kind") != "plugin-version"):
            continue
        if when and window_start <= when <= (until or now):
            confounders.append("another change in the window: %s (%s, %s)"
                               % (other.get("id"), other.get("subject"), when.date()))
    mix_before, mix_after = _mix(before), _mix(after)
    if mix_before and mix_after and any(abs(mix_before.get(t, 0) - mix_after.get(t, 0)) > 0.2
                                        for t in set(mix_before) | set(mix_after)):
        confounders.append("a different mix of work: tiers %s before, %s after"
                           % (_mix_text(mix_before), _mix_text(mix_after)))
    if before:
        covered = (at - min(r["end"] for r in before)).days
        if covered < baseline_days - 1:
            confounders.append("a baseline covering %d of its %d days" % (covered,
                                                                          baseline_days))
    else:
        confounders.append("no baseline: no closed time log in the %d days before"
                           % baseline_days)
    early = [r for r in before if r["end"] >= at - _dt.timedelta(days=7)]
    earlier = [r for r in before if r["end"] < at - _dt.timedelta(days=7)]
    trend = _move(_side(earlier, primary["measure"])["value"],
                  _side(early, primary["measure"])["value"])
    if trend is not None and abs(trend) >= no_effect:
        confounders.append("a difference already under way in the week before (%+.0f%%)"
                           % (100 * trend))
    result["confounders"] = confounders
    usd = measures.get("usd")
    if usd and usd["verdict"] == "not computable" and usd.get("missing"):
        result["basis"] = ("tokens per measured row; dollars not compared: %s"
                           % usd["missing"][0])
    elif primary["measure"] == "usd":
        result["basis"] = ("dollars per measured row at API prices, each call at the card in "
                           "force on its day; no card changed between the sides")
    elif primary["measure"] == "tokens":
        result["basis"] = "tokens per measured row (host-reported, every kind of token)"
    else:
        result["basis"] = "median share of working minutes on rows added after the listing"
    result["verdict"] = primary["verdict"]
    if stop:
        result["verdict"] += " (undone %s)" % str(result["endedBy"]["at"])[:10] \
            if stop.get("action") == "undo" else " (replaced by %s)" % stop.get("id")
    return result


def _mix(records: list[dict]) -> dict[str, float]:
    tiers = [t for r in records for t in r["tiers"]]
    if not tiers:
        return {}
    return {t: tiers.count(t) / len(tiers) for t in set(tiers)}


def _mix_text(mix: dict[str, float]) -> str:
    return ", ".join("%s %d%%" % (t, round(100 * v)) for t, v in sorted(mix.items()))


def render(results: list[dict], unit: str, why: bool = False) -> str:
    lines = []
    for r in results:
        lines.append("%s  %s (%s), in force from %s" % (r["change"], r["subject"], r["kind"],
                                                       r.get("effectiveFrom")))
        if r["verdict"] == "not yet":
            lines.append("  not yet: %s" % ", ".join("%d more %s" % (n, k) for k, n in
                                                     r["needs"].items()))
            continue
        if "primary" not in r:
            lines.append("  not computable (missing: %s)" % "; ".join(r.get("missing", [])))
            continue
        for name, m in r["measures"].items():
            if "sides" not in m:
                lines.append("  %s: not computable (%s)" % (name, "; ".join(m.get("missing", []))))
                continue
            b, a = m["sides"]["before"], m["sides"]["after"]
            fmt = lambda v: "—" if v is None else ("$%.4f" % v if name == "usd" else
                                                   "%.0f tokens" % v if name == "tokens"
                                                   else "%.2f" % v)
            lines.append("  %s: %s · %s · %s — before %s (%d rows) -> after %s (%d rows)" % (
                name, m["verdict"], m["confidence"], m["kind"], fmt(b["value"]), b["rows"],
                fmt(a["value"]), a["rows"]))
        for name in r["tradeOffs"]:
            lines.append("  trade-off: %s moved the wrong way" % name)
        for confounder in r["confounders"]:
            lines.append("  confounder: %s" % confounder)
        for name in r.get("straddling") or []:
            lines.append("  left out (its work straddles the change): %s" % name)
        if why:
            lines.append("  How this was calculated: %s; baseline %d days before the change; "
                         "no clear effect under %d%%." % (r["basis"], r["baselineDays"],
                                                          round(100 * r["noEffect"])))
    return "\n".join(lines) or "no change recorded yet"
