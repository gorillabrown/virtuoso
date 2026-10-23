"""The time log: each task row's working time, measured by the machine clock.

One append-only file per dispatch, ``Timing.<dispatch-id>.jsonl`` in the ``closeOuts``
role, one JSON object per line. The virtuoso skill opens it when it first lists the
task rows, then records each row's start, any wait on the owner, its resume and its
end. Every event is stamped here, in UTC, from the clock: no caller supplies a time or
a duration, so nothing typed in is ever read back as measured.

A row's working time is end − start − waits. A row missing its start or its end, or
whose end is stamped before its start, is *not measured*: it has no working time and
never enters the history. Everything read back is a function of the file and the
clock alone, so the status after a context compaction matches the status before it.

Each row is priced when it is listed (``--open``) or added (``--add``), from the
measured rows of every time log in the directory, the current one included: the
median of rows of the same *kind* when there are at least ``CALIBRATION_MINIMUM``,
else the median of rows of the same tier and effort, else the row's own ``estimate``,
labelled ``estimated``. A frontier row is priced at its timebox, ``timeboxed``. The
prediction and its basis are stored on the row, so the first listing's total never moves.

A row may also carry ``NEW_FIELDS`` (class, model, host, spec revision, parallel group,
timebox and its action, the row it was split from); a wait names its reason, and an end
may carry the host's token count. An append-only log cannot be backfilled, so a log
written before these fields existed reads them as ``not recorded``; writers refuse a
malformed one.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import statistics
from dataclasses import dataclass, field

from .errors import GovernanceError
from .learning import CALIBRATION_MINIMUM
from .providers.kpi import MEASURED, Metric, confidence_for

LOG_PREFIX = "Timing."
LOG_SUFFIX = ".jsonl"
EVENTS = ("open", "add", "start", "wait", "resume", "end", "confirm", "timebox-reached",
          "park", "cost")
#: Where an added row came from, stored on its ``add`` event, and its label's prefix. A
#: log written before origins existed reads every added row as ``added``.
ORIGINS = {"added": "+", "review": "R", "audit": "A"}
PARKED = "parked"
SPLIT = "split"
#: How a row ends. ``split`` is written only by ``--split``, never by ``--end``.
RESULTS = ("done", "blocked", "cancelled", SPLIT)
_SHIPPED_FIELDS = ("id", "title", "owner", "tier", "effort", "item", "parallel", "kind",
                   "estimate")
#: Added by VIR-020. An older log has none of them: readers show each as ``not recorded``.
NEW_FIELDS = ("class", "model", "host", "specRevision", "group", "timebox", "onTimebox",
              "splitFrom")
ROW_FIELDS = _SHIPPED_FIELDS + NEW_FIELDS
#: Stored on a row by ``timing`` when it prices it; never read from a rows file.
PRICE_FIELDS = ("predicted", "basis")
#: The price a specification's task list was written with, kept beside the launch-time
#: ``PRICE_FIELDS`` by ``--open --from-spec``; never read from a rows file.
WRITTEN_FIELDS = ("writtenPredicted", "writtenBasis")
TIER_EFFORT = {"mechanical": "low", "bounded": "medium", "cross-cutting": "high"}
ESTIMATED = "estimated"
TIMEBOXED = "timeboxed"
NOT_RECORDED = "not recorded"
CLASSES = ("calculable", "repeat", "frontier")
WAIT_REASONS = ("owner", "approval", "blocked", "session-ended")
#: A row whose actual exceeds this multiple of its prediction may hide a wait the agent
#: could not see (a host approval prompt): it is flagged, and kept out of pricing until
#: the owner confirms it was real work (``timing --confirm N``).
UNSEEN_WAIT_MULTIPLE = 3
UNSEEN_WAIT = "possible unseen wait"
_DISPATCH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_STAMP = "%Y-%m-%dT%H:%M:%SZ"


# --- the clock ---------------------------------------------------------------------------

def now() -> _dt.datetime:
    """The machine clock in UTC, to the second."""
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0)


def stamp(moment: _dt.datetime) -> str:
    return moment.astimezone(_dt.timezone.utc).strftime(_STAMP)


def parse_stamp(text: str) -> _dt.datetime | None:
    try:
        return _dt.datetime.strptime(str(text), _STAMP).replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return None


def minutes_text(minutes: float) -> str:
    """``12 min`` under an hour, ``3h 04m`` from an hour up."""
    whole = int(round(minutes))
    if whole < 60:
        return "%d min" % whole
    return "%dh %02dm" % divmod(whole, 60)


# --- the file ------------------------------------------------------------------------------

def log_name(dispatch: str) -> str:
    dispatch = (dispatch or "").strip()
    if not _DISPATCH_RE.match(dispatch):
        raise GovernanceError("%r is not a dispatch identifier a file can carry (letters, "
                              "digits, '.', '_' and '-')" % dispatch)
    return LOG_PREFIX + dispatch + LOG_SUFFIX


def load(path: str) -> list[dict]:
    """Every event in the log, in order. A missing file is an empty log."""
    if not os.path.isfile(path):
        return []
    events = []
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.read().split("\n")      # not splitlines(): U+2028 is JSON text
    except UnicodeDecodeError as exc:
        raise GovernanceError("%s is not UTF-8 text (%s); a time log is written only by "
                              "`timing`" % (path, exc))
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError as exc:
            event = exc
        if not isinstance(event, dict):
            raise GovernanceError(
                "%s line %d is not a JSON event (%s) — most likely a write that was cut "
                "off. Ask the owner before removing that one line; never rewrite the rest"
                % (path, number, event if isinstance(event, ValueError) else "not an object"))
        events.append(event)
    return events


def append(path: str, event: dict, moment: _dt.datetime | None = None) -> dict:
    """Stamp ``event`` with the clock (or ``moment``, for tests) and append it. The writer
    is strict: an event the log does not know is refused (a reader skips one)."""
    if event.get("event") not in EVENTS:
        raise GovernanceError("%r is not a time-log event (%s)"
                              % (event.get("event"), ", ".join(EVENTS)))
    stamped = dict(event, at=stamp(moment or now()))
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        raise GovernanceError("the closeOuts directory %s does not exist; create it with "
                              "`virtuoso_registry closeout --item <ID> --date <YYYY-MM-DD> "
                              "--prepare`" % parent)
    with open(path, "a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell():
            handle.seek(-1, os.SEEK_END)
            if handle.read(1) != b"\n":      # a line cut off mid-write stays its own line
                handle.write(b"\n")
        handle.write((json.dumps(stamped, ensure_ascii=False) + "\n").encode("utf-8"))
    return stamped


# --- rows ----------------------------------------------------------------------------------

@dataclass
class Row:
    id: int
    title: str = ""
    owner: str = ""
    tier: str = ""
    effort: str = ""
    item: str = ""
    parallel: bool = False
    kind: str = ""
    estimate: float | None = None
    predicted: int | None = None                   # minutes, priced when listed
    basis: str = ""                                # "median of N runs" or "estimated"
    added: bool = False
    started: _dt.datetime | None = None
    ended: _dt.datetime | None = None
    result: str = ""
    waits: list = field(default_factory=list)      # [start, end-or-None]
    working: float | None = None                   # measured minutes, or None
    waited: float = 0.0                            # minutes waiting on the owner
    confirmed: bool = False                        # the owner confirmed a flagged row
    fields: dict = field(default_factory=dict)     # the NEW_FIELDS the row carries
    wait_reasons: list = field(default_factory=list)   # one per wait, in order
    tokens: int | None = None                      # host-reported, from the end event
    timebox_reached: bool = False                  # a timebox-reached event was recorded
    origin: str = ""                               # an added row's ORIGINS key
    evidence: str = ""                             # what proves the row, from its end event
    park_reason: str = ""                          # set by a park event: the run will not do it

    @property
    def parked(self) -> bool:
        return bool(self.park_reason) and self.ended is None

    @property
    def label(self) -> str:
        """``N``, or ``+N``, ``RN`` or ``AN`` for a row added mid-run, by its origin."""
        return ("%s%d" % (ORIGINS.get(self.origin, "+"), self.id)) if self.added \
            else "%d" % self.id

    @property
    def timebox(self) -> float | None:
        value = self.fields.get("timebox")      # a hand-edited log may hold anything
        return value if isinstance(value, (int, float)) and not isinstance(value, bool) \
            and value >= 1 else None

    def past_timebox(self, moment: _dt.datetime) -> bool:
        return self.timebox is not None and self.worked_so_far(moment) >= self.timebox

    @property
    def measured(self) -> bool:
        return self.working is not None

    @property
    def flagged(self) -> bool:
        """Measured at over ``UNSEEN_WAIT_MULTIPLE`` x its prediction, and not confirmed."""
        return (self.measured and bool(self.predicted) and not self.confirmed
                and self.working > UNSEEN_WAIT_MULTIPLE * self.predicted)

    @property
    def state(self) -> str:
        if self.ended is not None:
            return self.result or "done"
        if self.park_reason:
            return PARKED
        if self.started is None:
            return "open"
        if self.waits and self.waits[-1][1] is None:
            return "waiting"
        return "running"

    def worked_so_far(self, moment: _dt.datetime) -> float:
        """Working minutes up to ``moment`` for a running or waiting row (0 if not
        started). Never negative."""
        if self.started is None:
            return 0.0
        until = self.ended or moment
        total = (until - self.started).total_seconds() / 60 - _waited(self.waits, until)
        return max(0.0, total)

    def remainder(self, moment: _dt.datetime) -> float:
        """Predicted minutes still to run: the whole prediction for an open row, what
        is left of it for a running or waiting row (never below 0), 0 once ended."""
        if self.ended is not None:
            return 0.0
        return max(0.0, (self.predicted or 0) - self.worked_so_far(moment))

    @property
    def effort_level(self) -> str:
        """The row's effort, or its tier's default when it declares none."""
        return self.effort or TIER_EFFORT.get(self.tier, "")

    def as_dict(self) -> dict:
        data = {name: getattr(self, name) for name in _SHIPPED_FIELDS + PRICE_FIELDS}
        data.update(added=self.added, state=self.state, result=self.result,
                    working=self.working, waited=round(self.waited, 1),
                    measured=self.measured, flagged=self.flagged, confirmed=self.confirmed)
        data.update({name: self.fields.get(name, NOT_RECORDED)
                     for name in NEW_FIELDS + WRITTEN_FIELDS})
        data.update(tokens=NOT_RECORDED if self.tokens is None else self.tokens,
                    waitReasons=self.wait_reasons, timeboxReached=self.timebox_reached)
        data.update(label=self.label, origin=(self.origin or "added") if self.added else "",
                    evidence=self.evidence, parkReason=self.park_reason)
        return data


def _waited(waits: list, until: _dt.datetime) -> float:
    total = 0.0
    for begin, end in waits:
        end = end or until
        if end > begin:
            total += (end - begin).total_seconds() / 60
    return total


def _row(spec: dict, added: bool = False) -> Row:
    estimate, predicted = spec.get("estimate"), spec.get("predicted")
    return Row(id=int(spec["id"]), title=str(spec.get("title", "")),
               owner=str(spec.get("owner", "")), tier=str(spec.get("tier", "")).lower(),
               effort=str(spec.get("effort", "")).lower(), item=str(spec.get("item", "")),
               parallel=bool(spec.get("parallel", False)), kind=normal_kind(spec.get("kind")),
               estimate=float(estimate) if estimate not in (None, "") else None,
               predicted=int(predicted) if predicted not in (None, "") else None,
               basis=str(spec.get("basis", "")),
               added=added or bool(spec.get("added", False)),
               fields={name: spec[name] for name in NEW_FIELDS + WRITTEN_FIELDS
                       if spec.get(name) not in (None, "")})


def normal_kind(text) -> str:
    """A kind name as lowercase words joined by hyphens: ``Merge slot`` → ``merge-slot``."""
    return "-".join(re.findall(r"[a-z0-9]+", str(text or "").lower()))


def rows(events: list[dict], moment: _dt.datetime | None = None) -> list[Row]:
    """The rows the log describes, in id order, each with its state and measured
    working and waited minutes. ``moment`` closes a wait still open on an ended row;
    it does not otherwise change a finished row's figures."""
    found: dict[int, Row] = {}
    for event in events:
        kind = event.get("event")
        if kind not in EVENTS:
            continue          # a newer writer's event: read what is known, skip the rest
        at = parse_stamp(event.get("at", ""))
        if kind in ("open", "add"):
            specs = event.get("rows")
            origin = event.get("origin") if event.get("origin") in ORIGINS else "added"
            for spec in specs if isinstance(specs, list) else []:
                try:
                    row = _row(spec, added=(kind == "add"))
                except (AttributeError, KeyError, TypeError, ValueError):
                    continue      # plan_rows admits no such row; a hand edit is not a row
                if row.added:
                    row.origin = origin
                found[row.id] = row
            continue
        row = found.get(_row_id(event.get("row")))
        if row is None or at is None:
            continue
        if kind == "start" and row.started is None and not row.park_reason:
            row.started = at
            # The row keeps the model and host named at its start; a resume's stay on it.
            row.fields.update({name: event[name] for name in ("model", "host")
                               if event.get(name) not in (None, "")})
        elif kind == "wait" and not (row.waits and row.waits[-1][1] is None):
            row.waits.append([at, None])
            row.wait_reasons.append(str(event.get("reason") or NOT_RECORDED))
        elif kind == "resume" and row.waits and row.waits[-1][1] is None:
            row.waits[-1][1] = at
        elif kind == "end" and row.ended is None:
            row.ended = at
            row.result = str(event.get("result") or "done")
            tokens = event.get("tokens")
            row.tokens = tokens if isinstance(tokens, int) and not isinstance(tokens, bool) \
                else None
            evidence = event.get("evidence")
            row.evidence = evidence.strip() if isinstance(evidence, str) else ""
            parts = event.get("rows") if row.result == SPLIT else None
            for spec in parts if isinstance(parts, list) else []:
                try:
                    part = _row(spec, added=True)
                except (AttributeError, KeyError, TypeError, ValueError):
                    continue
                found.setdefault(part.id, part)
        elif kind == "park" and row.started is None and row.ended is None:
            reason = event.get("reason")
            row.park_reason = reason.strip() if isinstance(reason, str) and reason.strip() \
                else NOT_RECORDED
        elif kind == "confirm":
            row.confirmed = True
        elif kind == "timebox-reached":
            row.timebox_reached = True
    for row in found.values():
        if row.ended is not None and row.waits and row.waits[-1][1] is None:
            row.waits[-1][1] = row.ended
        until = row.ended or moment
        row.waited = _waited(row.waits, until) if until else 0.0
        if row.started is not None and row.ended is not None and row.ended >= row.started:
            row.working = round(row.worked_so_far(row.ended), 1)
    return [found[key] for key in sorted(found)]


def _row_id(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# --- what a caller may record ----------------------------------------------------------------

def check(events: list[dict], action: str, row_id: int | None = None,
          moment: _dt.datetime | None = None) -> None:
    """Refuse an event the log cannot take, naming why. ``open`` needs an empty log;
    every other event needs an open log and, except ``add``, a row the plan holds in
    the state the event leaves. ``timebox-reached`` reads the clock (``moment``, for
    tests): the row's working time must have reached its timebox."""
    if action == "open":
        if events:
            raise GovernanceError("this dispatch's time log is already open; add a row with "
                                  "--add, never a second --open")
        return
    if not any(event.get("event") == "open" for event in events):
        raise GovernanceError("no time log is open for this dispatch; open one with --open "
                              "--rows-file when the task rows are first listed")
    if action == "add":
        return
    by_id = {row.id: row for row in rows(events)}
    row = by_id.get(row_id)
    if row is None:
        raise GovernanceError("row %s is not in this dispatch's plan (rows %s); add it with "
                              "--add first" % (row_id, ", ".join(str(k) for k in sorted(by_id))))
    state = row.state
    if state == PARKED:
        raise GovernanceError("row %d is parked (%s); the run set it aside, and a parked row "
                              "is reported at the close-out, not worked" % (row.id, row.park_reason))
    if action == "park" and state != "open":
        raise GovernanceError("row %d is %s; only a row not yet started is parked — end a "
                              "started row with --result cancelled" % (row.id, state))
    if action == "start" and row.started is not None:
        raise GovernanceError("row %d is already %s; a second start would double-count it "
                              "(is another session running this dispatch?)"
                              % (row.id, "started" if state == "running" else state))
    if action == "wait" and state != "running":
        raise GovernanceError("row %d is %s; only a running row waits on the owner"
                              % (row.id, state))
    if action == "resume" and state != "waiting":
        raise GovernanceError("row %d is %s, not waiting; nothing to resume" % (row.id, state))
    if action in ("end", SPLIT) and row.ended is not None:
        raise GovernanceError("row %d has already ended (%s)" % (row.id, row.result))
    if action == "confirm" and not row.flagged:
        raise GovernanceError("row %d is not flagged as a %s; there is nothing to confirm"
                              % (row.id, UNSEEN_WAIT))
    if action == "timebox-reached":
        if row.timebox is None:
            raise GovernanceError("row %d has no timebox; only a frontier row is timeboxed"
                                  % row.id)
        if row.started is None or row.ended is not None or row.timebox_reached:
            raise GovernanceError("row %d is %s%s; a timebox is reached by a row at work"
                                  % (row.id, state, ", its timebox already reached"
                                     if row.timebox_reached else ""))
        worked = row.worked_so_far(moment or now())
        if worked < row.timebox:
            raise GovernanceError("row %d has worked %s of its %s timebox; the clock, not "
                                  "the caller, says when it is reached"
                                  % (row.id, minutes_text(worked), minutes_text(row.timebox)))


def event_fields(action: str, reason=None, tokens=None, model=None, host=None,
                 evidence=None, origin=None) -> dict:
    """The extra fields a ``timing`` event carries, validated: a ``wait`` names its
    ``reason`` from ``WAIT_REASONS``, a ``park`` its own reason in words; an ``end`` may
    carry the host's ``tokens`` count and the ``evidence`` that proves the row; a ``start``
    or ``resume`` may name the ``model`` and ``host``; an ``add`` names its ``origin``
    (default ``added``). A field given to an action that does not take it is refused, so
    nothing typed is silently dropped."""
    given = {"reason": reason, "tokens": tokens, "model": model, "host": host,
             "evidence": evidence, "origin": origin}
    takes = {"wait": ("reason",), "park": ("reason",), "end": ("tokens", "evidence"),
             "start": ("model", "host"), "resume": ("model", "host"),
             "add": ("origin",)}.get(action, ())
    stray = [name for name, value in given.items() if value is not None and name not in takes]
    if stray:
        raise GovernanceError("--%s does not go with --%s" % (", --".join(stray), action))
    fields = {}
    if action == "wait":
        if reason not in WAIT_REASONS:
            raise GovernanceError("a wait names its reason: --reason %s%s"
                                  % (" | ".join(WAIT_REASONS),
                                     "" if reason is None else " (not %r)" % reason))
        fields["reason"] = reason
    if action == "park":
        if not str(reason or "").strip():
            raise GovernanceError("a parked row names why the run will not do it: "
                                  "--reason \"<why>\"")
        fields["reason"] = str(reason).strip()
    if action == "add":
        origin = "added" if origin is None else origin
        if origin not in ORIGINS:
            raise GovernanceError("--origin is one of %s, not %r"
                                  % (", ".join(ORIGINS), origin))
        fields["origin"] = origin
    if evidence is not None:
        if not str(evidence).strip():
            raise GovernanceError("--evidence names what proves the row; it cannot be empty")
        fields["evidence"] = str(evidence).strip()
    elif action == "end":
        fields["evidence"] = None     # asked for and not given: `--check` reports it
    if tokens is not None:
        text = str(tokens).strip()
        if not re.fullmatch(r"[0-9]+", text):
            raise GovernanceError("--tokens is the host's reported token count, a whole "
                                  "number, not %r (never minutes)" % tokens)
        fields["tokens"] = int(text)
    for name, value in (("model", model), ("host", host)):
        if value is not None:
            if not str(value).strip():
                raise GovernanceError("--%s names an identity; it cannot be empty" % name)
            fields[name] = str(value).strip()
    return fields


def plan_rows(specs, existing: list[Row] | None = None, added: bool = False) -> list[dict]:
    """Validate rows read from a rows file. An added row without an ``id`` takes the
    next number after every row the log holds."""
    if isinstance(specs, dict):
        specs = specs.get("rows")
    if not isinstance(specs, list) or not specs:
        raise GovernanceError("the rows file holds a non-empty JSON list of rows (or "
                              "{\"rows\": [...]}), each with at least a title")
    taken = {row.id for row in existing or []}
    next_id = max(taken, default=0) + 1
    result = []
    for spec in specs:
        if not isinstance(spec, dict) or not str(spec.get("title", "")).strip():
            raise GovernanceError("every row is an object with a title: %r" % (spec,))
        unknown = sorted(set(spec) - set(ROW_FIELDS))
        if unknown:
            raise GovernanceError("row %r carries fields the log does not know: %s (a row "
                                  "never carries a time)" % (spec.get("title"), ", ".join(unknown)))
        if "splitFrom" in spec:
            raise GovernanceError("row %r: splitFrom is written by --split N, never by a "
                                  "rows file" % spec.get("title"))
        spec = {key: value for key, value in spec.items() if value not in (None, "")}
        _check_types(spec)
        if "id" not in spec:
            if not added:
                raise GovernanceError("row %r has no id; the first listing numbers every row"
                                      % spec["title"])
            spec["id"] = next_id
        row_id = spec["id"]
        if row_id < 1 or row_id in taken:
            raise GovernanceError("row id %r is not a new positive number" % (spec["id"],))
        spec["id"] = row_id
        taken.add(row_id)
        next_id = max(taken) + 1
        result.append(spec)
    return result


def _check_types(spec: dict) -> None:
    """A row's values are the types the log reads back: whole-number ``id``, boolean
    ``parallel``, a non-negative number of minutes for ``estimate``, text otherwise."""
    title = spec["title"]
    if "id" in spec and (isinstance(spec["id"], bool) or not isinstance(spec["id"], int)):
        raise GovernanceError("row %r: id %r is not a whole number" % (title, spec["id"]))
    if "parallel" in spec and not isinstance(spec["parallel"], bool):
        raise GovernanceError("row %r: parallel is true or false, not %r"
                              % (title, spec["parallel"]))
    estimate = spec.get("estimate", 0)
    if isinstance(estimate, bool) or not isinstance(estimate, (int, float)) or estimate < 0:
        raise GovernanceError("row %r: estimate is a number of minutes (0 or more), not %r"
                              % (title, estimate))
    for name in ("title", "owner", "tier", "effort", "item", "kind", "model", "host",
                 "specRevision", "group", "onTimebox"):
        if name in spec and not isinstance(spec[name], str):
            raise GovernanceError("row %r: %s is text, not %r" % (title, name, spec[name]))
    if "class" in spec and spec["class"] not in CLASSES:
        raise GovernanceError("row %r: class is one of %s, not %r"
                              % (title, ", ".join(CLASSES), spec["class"]))
    frontier = spec.get("class") == "frontier"
    timebox = spec.get("timebox")
    if timebox is not None and (isinstance(timebox, bool) or not isinstance(timebox, (int, float))
                                or timebox < 1):
        raise GovernanceError("row %r: timebox is a number of minutes, 1 or more, not %r"
                              % (title, timebox))
    if (timebox is not None or "onTimebox" in spec) and not frontier:
        raise GovernanceError("row %r: only a frontier row is timeboxed (class: frontier)"
                              % title)
    if frontier and (timebox is None or "onTimebox" not in spec):
        raise GovernanceError("row %r: a frontier row carries a timebox (minutes) and "
                              "onTimebox (the action when it is reached)" % title)
    if frontier and "estimate" in spec:
        raise GovernanceError("row %r: a frontier row is timeboxed, never estimated" % title)


# --- pricing ---------------------------------------------------------------------------------

def log_paths(directory: str) -> list[str]:
    """Every time log under ``directory``, in path order."""
    found = []
    if not directory or not os.path.isdir(directory):
        return found
    for dirpath, dirnames, filenames in os.walk(directory):
        dirnames.sort()
        for name in sorted(filenames):
            if name.startswith(LOG_PREFIX) and name.endswith(LOG_SUFFIX):
                found.append(os.path.join(dirpath, name))
    return found


def history(directory: str, skipped: list | None = None) -> list[Row]:
    """The measured rows of every time log under ``directory`` that ran to ``done`` —
    the evidence every prediction is priced from. A row the clock could not measure is
    not evidence, nor is one blocked or cancelled partway, nor a flagged row until the
    owner confirms it. A log that cannot be read is left out and named in
    ``skipped``, so one damaged old log never stops pricing."""
    found = []
    for path in log_paths(directory):
        try:
            events = load(path)
        except GovernanceError as exc:
            if skipped is not None:
                skipped.append(str(exc))
            continue
        found.extend(row for row in rows(events) if row.measured and row.state == "done"
                     and not row.flagged)
    return found


def _whole(minutes: float) -> int:
    """Whole minutes, halves rounded up (``round`` would round 12.5 down to 12)."""
    return int(minutes + 0.5)


def _median(values: list[float]) -> int:
    return _whole(statistics.median(values))


def price(row: Row, past: list[Row]) -> tuple[int, str] | None:
    """``(minutes, basis)`` for ``row``: a frontier row's timebox as ``timeboxed`` (it
    is never given an estimate); else its kind's median over at least
    ``CALIBRATION_MINIMUM`` measured runs, else its tier and effort's, else its own
    estimate as ``estimated``. ``None`` when there is nothing to price it from."""
    if row.fields.get("class") == "frontier" and row.timebox is not None:
        return _whole(row.timebox), TIMEBOXED
    if row.kind:
        same = [r.working for r in past if r.kind == row.kind]
        if len(same) >= CALIBRATION_MINIMUM:
            return _median(same), "median of %d runs" % len(same)
    if row.tier:
        same = [r.working for r in past
                if r.tier == row.tier and r.effort_level == row.effort_level]
        if len(same) >= CALIBRATION_MINIMUM:
            return _median(same), "median of %d runs" % len(same)
    if row.estimate is not None:
        return _whole(row.estimate), ESTIMATED
    return None


def price_rows(specs: list[dict], past: list[Row]) -> list[dict]:
    """``specs`` with ``predicted`` and ``basis`` on each; refuses, naming them, the
    rows nothing prices."""
    priced, unpriced = [], []
    for spec in specs:
        found = price(_row(spec), past)
        if found is None:
            unpriced.append(spec["id"])
            continue
        priced.append(dict(spec, predicted=found[0], basis=found[1]))
    if unpriced:
        raise GovernanceError(
            "row%s %s ha%s no history to price from and no estimate; give each an "
            "\"estimate\" in minutes and try again — never invent a basis"
            % ("s" if len(unpriced) > 1 else "", ", ".join(str(i) for i in unpriced),
               "ve" if len(unpriced) > 1 else "s"))
    return priced


def kinds(past: list[Row]) -> dict[str, int]:
    """The kind names already in use, with how many measured runs each has, most
    used first — reuse one rather than coin a near-duplicate."""
    counts: dict[str, int] = {}
    for row in past:
        if row.kind:
            counts[row.kind] = counts.get(row.kind, 0) + 1
    return dict(sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])))


# --- a specification's task list (references/task-rows.md) ---------------------------------

SPEC_COLUMNS = ("#", "Task", "Class", "Kind", "Tier", "Effort", "Estimate", "Timebox", "Group")
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")
FRONTIER_ESTIMATE = "a frontier task receives no single-number estimate"
_BLANK = ("", "—", "–", "-")
_DURATION_RE = re.compile(r"(?:(\d+)\s*h)?\s*(?:(\d+)\s*m(?:in)?)?")
_ESTIMATE_RE = re.compile(r"(?P<duration>[^(]*?)\s*(?:\((?P<basis>[^()]*)\))?")
_TIMEBOX_RE = re.compile(r"[≤<=]*\s*(?P<duration>\d+\s*h(?:\s*\d+\s*m(?:in)?)?|\d+\s*m(?:in)?)"
                         r"\s*(?:[—–:-]\s*(?P<action>.*\S))?\s*")


def parse_duration(text) -> int | None:
    """Minutes in ``45m``, ``45 min``, ``2h``, ``1h30m``; ``None`` for anything else."""
    match = _DURATION_RE.fullmatch(str(text or "").strip())
    if not match or not any(match.groups()):
        return None
    return int(match.group(1) or 0) * 60 + int(match.group(2) or 0)


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def spec_rows(text: str, item: str = "") -> list[dict]:
    """The rows of a specification's ``Task list`` table, as rows a time log opens from:
    each keeps its ``#`` as its id, and the spec's price as ``writtenPredicted`` /
    ``writtenBasis``. ``item`` locates a specification stored inline in a roadmap.
    Refuses, naming what is missing or wrong: no task list, a missing column, a row
    without a class, a duration in ``Effort``, a frontier row with an estimate."""
    from . import lessons as lessons_mod, overlays as overlays_mod
    lines = overlays_mod.without_fenced_blocks(text or "").splitlines()
    if item:
        lines = lessons_mod.item_section(text, item)
        if lines is None:
            raise GovernanceError("no heading in the document names %s" % item)
    body = lessons_mod._find_section(lines, ("task list",))
    if body is None:
        raise GovernanceError("no \"Task list\" section%s (references/task-rows.md)"
                              % (" for %s" % item if item else ""))
    table = []                          # the first table in the section, and only it
    for line in body:
        if line.strip().startswith("|"):
            table.append(line)
        elif table:
            break
    if table[1:] and re.fullmatch(r"[\s|:-]+", table[1]):
        del table[1]                    # the separator row
    if len(table) < 2:
        raise GovernanceError("the Task list holds no table rows")
    header = _cells(table[0])
    missing = [name for name in SPEC_COLUMNS if name not in header]
    if missing:
        raise GovernanceError("the Task list table has no %s column%s"
                              % (", ".join(missing), "s" if len(missing) > 1 else ""))
    found, taken = [], set()
    for line in table[1:]:
        cell = dict(zip(header, _cells(line)))
        get = lambda name: "" if cell.get(name, "") in _BLANK else cell[name]
        title = get("Task")
        if not get("#").isdigit() or not title:
            raise GovernanceError("task row %r has no whole-number # and a Task" % line.strip())
        row = {"id": int(get("#")), "title": title, "class": get("Class").lower()}
        if row["id"] < 1 or row["id"] in taken:
            raise GovernanceError("task %d: # is a new positive number, once per task"
                                  % row["id"])
        taken.add(row["id"])
        if item:
            row["item"] = item
        if row["class"] not in CLASSES:
            raise GovernanceError("task %d: Class is one of %s, not %r"
                                  % (row["id"], ", ".join(CLASSES), get("Class")))
        for name, allowed in (("Tier", tuple(TIER_EFFORT)), ("Effort", EFFORT_LEVELS)):
            value = get(name).lower()
            if value and parse_duration(value) is not None:
                raise GovernanceError("task %d: %s is a level, never a duration (%r); the "
                                      "duration goes in Estimate" % (row["id"], name, value))
            if value and value not in allowed:
                raise GovernanceError("task %d: %s is one of %s, not %r"
                                      % (row["id"], name, ", ".join(allowed), value))
            if value:
                row[name.lower()] = value
        if get("Kind"):
            row["kind"] = normal_kind(get("Kind"))
        if get("Group"):
            row["group"] = get("Group")
        if get("Estimate"):
            if row["class"] == "frontier":
                raise GovernanceError("task %d: %s; give it a Timebox"
                                      % (row["id"], FRONTIER_ESTIMATE))
            match = _ESTIMATE_RE.fullmatch(get("Estimate"))
            minutes = parse_duration(match.group("duration")) if match else None
            if minutes is None:
                raise GovernanceError("task %d: Estimate is a duration such as 45m or 1h30m, "
                                      "with its basis in brackets, not %r"
                                      % (row["id"], get("Estimate")))
            row.update(estimate=minutes, writtenPredicted=minutes,
                       writtenBasis=(match.group("basis") or "").strip() or ESTIMATED)
        elif row["class"] != "frontier":
            raise GovernanceError("task %d: an estimated task carries its Estimate, the "
                                  "price it was written with" % row["id"])
        if get("Timebox"):
            match = _TIMEBOX_RE.fullmatch(get("Timebox"))
            if row["class"] != "frontier":
                raise GovernanceError("task %d: only a frontier task is timeboxed"
                                      % row["id"])
            if not match or not match.group("action"):
                raise GovernanceError("task %d: a Timebox reads \"≤2h — <the action when "
                                      "it is reached>\", not %r" % (row["id"], get("Timebox")))
            row.update(timebox=parse_duration(match.group("duration")),
                       onTimebox=match.group("action"))
        elif row["class"] == "frontier":
            raise GovernanceError("task %d: a frontier task carries a Timebox and the action "
                                  "when it is reached" % row["id"])
        found.append(row)
    return found


def kindless_warnings(rows, used: dict) -> list[str]:
    """One sentence per ``repeat`` row with no kind, naming the kinds in use: such a row
    prices from its estimate alone, since no history of its kind can be found."""
    reuse = ("reuse one of: %s" % ", ".join(used)) if used else "no kind is in use yet"
    return ['task %s ("%s") is a repeat task with no kind, so no history can price it; %s'
            % (row.get("id"), row.get("title"), reuse)
            for row in rows
            if row.get("class") == "repeat" and not normal_kind(row.get("kind"))]


def _span(minutes: float) -> str:
    """``duration``, with whole hours shortened: ``2h``, ``4h10m``, ``45m``."""
    text = duration(minutes)
    return text[:-3] if text.endswith("h00m") else text


def total_line(priced: list[dict]) -> str:
    """The frame-1 total of priced task rows. The *chain* is the longest path through
    the rows (rows sharing a ``group`` run side by side, so a group counts its longest
    row), for clock forecasts; the *sum* counts every row, for calibration and usage.
    Neither stands in for the other. Frontier rows are timeboxed apart, never summed."""
    estimated = [row for row in priced if row.get("class") != "frontier"]
    boxed = [row for row in priced if row.get("class") == "frontier"]
    groups: dict[str, int] = {}
    chain = 0
    for row in estimated:
        if row.get("group"):
            groups[row["group"]] = max(groups.get(row["group"], 0), row["predicted"])
        else:
            chain += row["predicted"]
    chain += sum(groups.values())
    calibrated = sum(1 for row in estimated if str(row.get("basis")).startswith("median of"))
    text = "chain %s · sum %s" % (_span(chain), _span(sum(r["predicted"] for r in estimated)))
    if boxed:
        text += " + %d timeboxed ≤%s" % (len(boxed), _span(sum(r["timebox"] for r in boxed)))
    return text + ("; %d of %d estimated tasks calibrated (priced by kind, then tier and "
                   "effort, then the task's own estimate)" % (calibrated, len(estimated)))


# --- the summary: what the close-out, the ledger and kpis read ------------------------------

def duration(minutes: float) -> str:
    """Minutes as a ledger duration ``learning.hours`` reads: ``45m``, ``4h10m``."""
    hours, rest = divmod(_whole(minutes), 60)
    return "%dh%02dm" % (hours, rest) if hours else "%dm" % rest


def summary(events: list[dict], item: str | None = None) -> dict:
    """The run's rows and totals. ``estimate`` is the first listing's predicted total
    over non-parallel rows (rows added later are what it missed); ``actual`` is the
    measured working total over non-parallel rows. ``item`` limits both to one item's
    rows, for a combined epic that closes several items from one run; a log whose rows
    name no item at all is one item's run, so ``item`` then takes every row.

    ``complete`` is false when a sequential row that ran was not measured, or was never
    ended: the totals are then partial, and the ledger takes neither of them. A row
    cancelled before it started did no work and leaves the totals whole."""
    logged = rows(events)
    carries_items = any(row.item for row in logged)
    found = [row for row in logged if not item or not carries_items or row.item == item]
    if not found:
        raise GovernanceError("the time log holds no rows%s"
                              % (" for item %s" % item if item else ""))
    sequential = [row for row in found if not row.parallel]
    estimate = sum(row.predicted or 0 for row in sequential if not row.added)
    actual = sum(row.working for row in sequential if row.measured)
    partial = [row.id for row in sequential if not row.measured
               and not (row.state in ("cancelled", SPLIT, PARKED) and row.started is None)]
    return {
        "item": item or "",
        "estimate": duration(estimate), "actual": duration(actual),
        "estimateMinutes": estimate, "actualMinutes": round(actual, 1),
        "complete": not partial,
        "rows": [dict(row.as_dict(), flag=UNSEEN_WAIT if row.flagged else "",
                      effortLevel=row.effort_level) for row in found],
        "flagged": [row.id for row in found if row.flagged],
        "notMeasured": partial,
        "byModelEffort": by_model_effort(found, _ratio),
        # Each becomes a findings entry (Disposition open) at the close-out.
        "parked": [{"id": row.id, "label": row.label, "title": row.title,
                    "reason": row.park_reason} for row in found if row.parked],
    }


def check_log(events: list[dict]) -> list[str]:
    """What ``timing --check`` reports: a row number used twice, a row ended ``done``
    without the evidence its end was asked for, a parked row with no reason, and a row
    still running or waiting. An ``end`` written before evidence existed carries no
    ``evidence`` key and is never reported: the check holds a log only to what its
    writer promised."""
    findings = []
    numbers: dict[int, int] = {}
    ends: dict[int, dict] = {}
    for event in events:
        listed = event.get("rows") if event.get("event") in ("open", "add", "end") else None
        for spec in listed if isinstance(listed, list) else []:
            number = _row_id(spec.get("id")) if isinstance(spec, dict) else None
            if number is not None:
                numbers[number] = numbers.get(number, 0) + 1
        if event.get("event") == "end":
            ends.setdefault(_row_id(event.get("row")), event)
    findings += ["row %d is numbered %d times; a number is used once" % (number, count)
                 for number, count in sorted(numbers.items()) if count > 1]
    for row in rows(events):
        end = ends.get(row.id, {})
        if row.state == "done" and "evidence" in end and not row.evidence:
            findings.append("row %s ended done with no evidence (--end %d --evidence ...)"
                            % (row.label, row.id))
        if row.state == PARKED and row.park_reason == NOT_RECORDED:
            findings.append("row %s is parked with no reason" % row.label)
        if row.state in ("running", "waiting"):
            findings.append("row %s is still %s; end it before the summary" % (row.label,
                                                                               row.state))
    return findings


def _ratio(row: Row) -> float:
    return row.working / row.predicted


def _error(row: Row) -> float:
    return abs(row.working - row.predicted) / row.predicted


def by_model_effort(found: list[Row], figure) -> dict:
    """``figure`` of each (model, effort) pair's measured, priced rows: the median, or not
    computable below ``CALIBRATION_MINIMUM`` rows. The model is the one the row's start
    named; the effort is the row's own, else its tier's. A row whose log recorded no model
    (an older log) is skipped and counted, never refused."""
    pairs: dict[tuple, list] = {}
    skipped = 0
    for row in found:
        if not (row.measured and row.predicted) or row.flagged or row.state == SPLIT:
            continue
        model = row.fields.get("model")
        if not isinstance(model, str) or not model.strip():
            skipped += 1
            continue
        pairs.setdefault((model, row.effort_level or NOT_RECORDED), []).append(figure(row))
    found_pairs = []
    for (model, effort), values in sorted(pairs.items()):
        entry = {"model": model, "effort": effort, "rows": len(values)}
        if len(values) >= CALIBRATION_MINIMUM:
            entry["value"] = round(statistics.median(values), 2)
        else:
            entry.update(value=None, computable=False, note="not computable",
                         missingInputs=["%d measured rows (%d found)"
                                        % (CALIBRATION_MINIMUM, len(values))])
        found_pairs.append(entry)
    return {"pairs": found_pairs, "skippedNoModel": skipped}


def summary_markdown(result: dict, why: bool = False) -> str:
    """The close-out's ``## Time`` table; with ``why``, how each total was worked out."""
    lines = ["| Row | Task | Kind | Model | Effort | Predicted | Actual | Waited | Added | Flag "
             "| Evidence |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for row in result["rows"]:
        if row["state"] == PARKED:
            continue                                   # listed under Parked below
        model = row.get("model")
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            row.get("label") or row["id"], row["title"].replace("|", "/"),
            row["kind"] or "—",
            model if model and model != NOT_RECORDED else "—",
            row.get("effortLevel") or "—",
            "%s min (%s)" % (row["predicted"], row["basis"]) if row["predicted"] is not None
            else "—",
            "%d min" % int(round(row["working"])) if row["measured"] else "not measured",
            minutes_text(row["waited"]) if row["waited"] >= 0.5 else "—",
            "yes" if row["added"] else "—",
            row["flag"] or ("confirmed" if row["confirmed"] else "—"),
            (row.get("evidence") or "—").replace("|", "/")))
    if result.get("parked"):
        lines += ["", "Parked — each becomes a findings entry (Disposition open) at the "
                      "close-out:"]
        lines += ["- ◇ %s. %s — %s" % (p["label"], p["title"], p["reason"])
                  for p in result["parked"]]
    lines.append("")
    lines.append("Estimate %s (the first listing, sequential rows) · Actual %s (measured "
                 "working time, sequential rows)%s" % (
                     result["estimate"], result["actual"],
                     " · item %s" % result["item"] if result["item"] else ""))
    if not result["complete"]:
        lines.append("Partial: rows %s ran without a measured time, so neither total goes "
                     "to the ledger." % ", ".join(str(i) for i in result["notMeasured"]))
    if why:
        lines += ["", "How this was calculated:",
                  "- Estimate (estimated): the sum of the predictions the first listing gave "
                  "its sequential rows; rows added later and parallel rows are left out.",
                  "- Actual (measured): the sum of the machine-clock working minutes (end − "
                  "start − waits) of the same sequential rows.",
                  "Assumptions: a parallel row overlaps the sequential work; a row added "
                  "after the first listing was not part of the plan being estimated."]
    return "\n".join(lines)


# --- the loop's figures --------------------------------------------------------------------

TIMING_METRICS = ("row-error", "total-error", "added-share")
#: Needs rows per (model, effort) pair rather than closed logs, so it is read at any count.
PAIR_METRIC = "row-error-by-model-effort"


def closed_logs(directory: str) -> list[list[Row]]:
    """The rows of every time log whose rows have all ended or been parked. A log that
    cannot be read is not closed evidence; ``history`` names it when a row is priced."""
    found = []
    for path in log_paths(directory):
        try:
            logged = rows(load(path))
        except GovernanceError:
            continue
        # A parked row is finished business: the run set it aside and will not do it.
        if logged and all(row.ended is not None or row.parked for row in logged):
            found.append(logged)
    return found


def starting_load(directory: str) -> Metric:
    """The median context a dispatch's top-level session carried when its time log opened
    (``startingLoad`` on the ``open`` event, recorded for a bound dispatch)."""
    loads = []
    try:
        names = sorted(os.listdir(directory))
    except OSError:
        names = []
    for name in names:
        if not (name.startswith(LOG_PREFIX) and name.endswith(LOG_SUFFIX)):
            continue
        try:
            events = load(os.path.join(directory, name))
        except GovernanceError:
            continue
        opened = next((e for e in events if e.get("event") == "open"), {})
        tokens = (opened.get("startingLoad") or {}).get("tokens")
        if isinstance(tokens, int):
            loads.append(tokens)
    if not loads:
        return Metric("starting-load", computable=False, missing_inputs=[
            "a time log opened by a bound session (its open event carries startingLoad)"])
    return Metric("starting-load", statistics.median(loads), unit="tokens",
                  basis="median context at dispatch open, %d logs" % len(loads),
                  confidence=confidence_for(MEASURED, len(loads)))


def figures(directory: str) -> list[Metric]:
    """How far off the predictions were, from the closed time logs: ``row-error``
    (median |actual - predicted| / predicted over measured rows), ``total-error`` (the
    same over each run's sequential totals) and ``added-share`` (the share of working
    minutes spent on rows the first listing missed). Each needs
    ``CALIBRATION_MINIMUM`` closed logs, else it is not computable."""
    logs = closed_logs(directory)
    if len(logs) < CALIBRATION_MINIMUM:
        missing = "%d closed time logs in the closeOuts role (%d found)" % (
            CALIBRATION_MINIMUM, len(logs))
        return [Metric(name, computable=False, missing_inputs=[missing])
                for name in TIMING_METRICS] + [
            _row_error_by_model_effort([row for logged in logs for row in logged])]
    # A split row's time so far is part of its work, not a miss against its prediction.
    measured = [row for logged in logs for row in logged
                if row.measured and row.predicted and not row.flagged and row.state != SPLIT]
    row_errors = [abs(row.working - row.predicted) / row.predicted for row in measured]
    totals = []
    for logged in logs:
        sequential = [row for row in logged if not row.parallel]
        estimate = sum(row.predicted or 0 for row in sequential if not row.added)
        if estimate:
            actual = sum(row.working for row in sequential if row.measured)
            totals.append(abs(actual - estimate) / estimate)
    worked = sum(row.working for logged in logs for row in logged if row.measured)
    added = sum(row.working for logged in logs for row in logged
                if row.measured and row.added)
    return [
        Metric("row-error", round(statistics.median(row_errors), 2),
               basis="median |actual - predicted| / predicted, %d rows" % len(row_errors),
               confidence=confidence_for(MEASURED, len(row_errors)))
        if row_errors else Metric("row-error", computable=False,
                                  missing_inputs=["a measured, priced row in a closed log"]),
        Metric("total-error", round(statistics.median(totals), 2),
               basis="median |actual - estimate| / estimate, %d runs" % len(totals),
               confidence=confidence_for(MEASURED, len(totals)))
        if totals else Metric("total-error", computable=False,
                              missing_inputs=["a closed log with a priced first listing"]),
        Metric("added-share", round(added / worked, 2),
               basis="working minutes on rows added after the first listing ÷ all working "
                     "minutes")
        if worked else Metric("added-share", computable=False,
                              missing_inputs=["a measured row in a closed log"]),
        _row_error_by_model_effort([row for logged in logs for row in logged]),
    ]


def _row_error_by_model_effort(found: list[Row]) -> Metric:
    """``row-error`` per (model, effort) pair: ``{"<model> {<effort>}": value}`` over the
    pairs with ``CALIBRATION_MINIMUM`` measured rows; not computable when none has."""
    split = by_model_effort(found, _error)
    values = {"%s {%s}" % (p["model"], p["effort"]): p["value"]
              for p in split["pairs"] if p["value"] is not None}
    skipped = (", %d rows with no model recorded skipped" % split["skippedNoModel"]
               if split["skippedNoModel"] else "")
    if not values:
        return Metric(PAIR_METRIC, computable=False, missing_inputs=[
            "%d measured rows for one model and effort (%d pairs below it%s)"
            % (CALIBRATION_MINIMUM, len(split["pairs"]), skipped)])
    return Metric(PAIR_METRIC, values,
                  basis="median |actual - predicted| / predicted per model {effort}, %d pairs%s"
                  % (len(values), skipped))


# --- rendering -------------------------------------------------------------------------------

_MARKER = {"open": "□", "running": "■", "waiting": "■", "done": "✓", "blocked": "✗",
           "cancelled": "✗", SPLIT: "✗", PARKED: "◇"}


def _prediction(row: Row) -> str:
    if row.predicted is None:
        return ""
    return "%d min (%s)" % (row.predicted, row.basis or ESTIMATED)


def row_line(row: Row, moment: _dt.datetime) -> str:
    text = "%s %s. %s%s" % (_MARKER.get(row.state, "□"), row.label,
                            ("%s: " % row.owner) if row.owner else "", row.title)
    if row.tier:
        text += " [%s]" % row.tier
    if row.effort_level:
        text += " {%s}" % row.effort_level
    model = row.fields.get("model")
    if isinstance(model, str) and model.strip():
        text += " ‹%s›" % model
    if row.kind:
        text += " @%s" % row.kind
    if row.parallel:
        text += " (parallel)"
    if row.state == PARKED:
        text += " — parked: %s" % row.park_reason
    elif row.state == "open":
        text += "  " + (_prediction(row) or "unpriced")
    elif row.state in ("running", "waiting"):
        text += "  %s — %s, %s worked" % (_prediction(row) or "unpriced",
                                           "waiting on the owner" if row.state == "waiting"
                                           else "running",
                                           minutes_text(row.worked_so_far(moment)))
    elif not row.measured:
        text += " — not measured"
    elif row.flagged:
        text += " — %d → %d min · %s" % (row.predicted, int(round(row.working)), UNSEEN_WAIT)
    elif row.predicted is not None:
        text += " — %d → %d min" % (row.predicted, int(round(row.working)))
    else:
        text += " — %s worked" % minutes_text(row.working)
    if row.ended is not None and row.state != "done":
        text += " (%s)" % row.state
    if row.waited >= 0.5:
        text += " · waited %s" % minutes_text(row.waited)
    if row.timebox_reached or row.past_timebox(moment):
        text += " · timebox reached — %s" % row.fields.get("onTimebox", NOT_RECORDED)
    return text


def remaining(found: list[Row], moment: _dt.datetime) -> tuple[float, list[int], list[int]]:
    """Predicted minutes left over the unfinished sequential rows (a running row counts
    only its remainder), the ids summed, and the unfinished parallel rows left out."""
    unfinished = [row for row in found if row.ended is None and not row.parked]
    sequential = [row for row in unfinished if not row.parallel]
    parallel = [row.id for row in unfinished if row.parallel]
    return (sum(row.remainder(moment) for row in sequential),
            [row.id for row in sequential], parallel)


def _ids(ids: list[int]) -> str:
    return ("rows " if len(ids) > 1 else "row ") + ", ".join(str(i) for i in ids)


def _clock(moment: _dt.datetime, reference: _dt.datetime) -> str:
    text = moment.strftime("%H:%M")
    return text if moment.date() == reference.date() else moment.strftime("%a %d %b ") + text


def header(found: list[Row], moment: _dt.datetime, zone: _dt.tzinfo | None = None) -> str:
    """``[D/N ✓ · R ■ · X ✗ · O □ · P ◇] Remaining M (…) → est. finish HH:MM local
    (±HH:MM) · HH:MM UTC. Now: …`` — computed, so the lead never sums minutes. Only a row
    ended ``done`` counts as ✓; blocked, cancelled and split rows count as ✗."""
    counts = counted(found)
    left, sequential, parallel = remaining(found, moment)
    scope = "sequential " + _ids(sequential) if sequential else "no sequential rows remain"
    if parallel:
        scope += "; %s parallel, excluded" % _ids(parallel)
    unpriced = [row.id for row in found if row.ended is None and row.predicted is None]
    if unpriced:
        scope += "; %s unpriced, counted as 0" % _ids(unpriced)
    finish = moment + _dt.timedelta(minutes=left)
    local = finish.astimezone(zone) if zone else finish.astimezone()
    offset = local.strftime("%z")
    offset = "%s:%s" % (offset[:3], offset[3:]) if offset else "+00:00"
    utc = finish.astimezone(_dt.timezone.utc)
    running = [row.id for row in found if row.state == "running"]
    waiting = [row.id for row in found if row.state == "waiting"]
    now_parts = []
    if running:
        now_parts.append("%s running" % _ids(running))
    if waiting:
        now_parts.append("%s waiting on the owner" % _ids(waiting))
    if not now_parts:
        upcoming = [row.id for row in found if row.state == "open"]
        now_parts.append("%s next" % _ids(upcoming[:1]) if upcoming else "every row has ended")
    return ("[%d/%d ✓ · %d ■ · %d ✗ · %d □ · %d ◇] Remaining %d min (%s) → est. finish %s "
            "local (%s) · %s UTC. Now: %s." % (counts["✓"], len(found), counts["■"],
                                              counts["✗"], counts["□"], counts["◇"],
                                              _whole(left), scope,
                          _clock(local, moment.astimezone(local.tzinfo)), offset,
                          _clock(utc, moment.astimezone(_dt.timezone.utc)),
                          "; ".join(now_parts)))


def counted(found: list[Row]) -> dict:
    """Rows per marker: ✓ done, ■ running or waiting, ✗ blocked, cancelled or split,
    □ open, ◇ parked."""
    counts = dict.fromkeys(("✓", "■", "✗", "□", "◇"), 0)
    for row in found:
        counts[_MARKER.get(row.state, "□")] += 1
    return counts


#: Past this many rows, ``--compact`` keeps every row not done and the last few done.
COMPACT_ABOVE = 12
COMPACT_DONE_KEPT = 3


def render_status(found: list[Row], moment: _dt.datetime,
                  zone: _dt.tzinfo | None = None, compact: bool = False) -> str:
    shown = [row for row in found if not row.parked]
    hidden = 0
    if compact and len(found) > COMPACT_ABOVE:
        done = sorted((row for row in shown if row.state == "done"),
                      key=lambda row: (row.ended, row.id))
        keep = {row.id for row in done[-COMPACT_DONE_KEPT:]}
        hidden = len(done) - len(keep)
        shown = [row for row in shown if row.state != "done" or row.id in keep]
    lines = [header(found, moment, zone)]
    if hidden:
        lines.append("… %d earlier done row%s not shown (timing --status lists every row)"
                     % (hidden, "" if hidden == 1 else "s"))
    lines += [row_line(row, moment) for row in shown]
    parked = [row_line(row, moment) for row in found if row.parked]
    if parked:
        lines += ["Parked:"] + parked
    return "\n".join(lines)
