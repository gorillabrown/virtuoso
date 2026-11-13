"""The progress band's data: the milestones and steps of the dispatch or epic a session runs.

Only the ``virtuoso`` skill feeds it, through ``virtuoso_registry.py progress``. Nothing here
is a project file and nothing touches the registry: every file lives in the user's own state
folder, ``<VIRTUOSO_HOME or ~>/.virtuoso/progress/``, never inside a working tree.

    runs/<run>.json       a run being implemented (one dispatch or one epic)
    archive/<run>.json    a run that ended, COMPLETE or STOPPED; the end line is drawn from it
    sessions/<id>.json    which run a session shows: {"run", "at"} (+ "cleared")

A run (schema 3)::

    {"schema": 3, "run": {"id", "title"}, "root": "<the run's working tree>",
     "colors": ["cyan", "blue"], "started", "updated",
     "milestones": [{"id", "label", "state", "started", "finished",
                     "plannedSteps": [{"id", "label"}]}],
     "current": "<milestone id>",
     "steps": [{"id", "label", "state", "started", "finished"}],   # the current milestone's
     "end": {"state": "complete" | "stopped", "at", "reason", ...}}  # archived runs only

The session pointer is written by the plugin's PreToolUse hook, which knows the session; the
command never does. Writes go to a temporary file renamed over the old one, under a lock.
"""
from __future__ import annotations

import contextlib
import datetime as _dt
import json
import os
import re
import statistics
import time
import zlib

from . import install

SCHEMA = 3
STATES = ("queued", "active", "done", "blocked", "cancelled")


def _live(items: list[dict]) -> list[dict]:
    """The items the counts follow: a cancelled step or milestone drops out of X/Y."""
    return [i for i in items if i.get("state") != "cancelled"]
BAR = 20
#: An active run with no feed for this long is drawn dim, "no update since hh:mmZ".
STALE_FEED_MINUTES = 30
#: A run no write has touched for this long belongs to a session that died: it is archived
#: as STOPPED (reason ``abandoned``) by the next write.
ABANDON_DAYS = 14
#: A lock older than this is a crashed writer's, and is taken over.
STALE_LOCK_SECONDS = 30.0
#: Colour pairs, one per run, chosen from the run id. The symbol and the words carry the
#: meaning; the colour only tells two runs apart.
PALETTE = (("cyan", "blue"), ("magenta", "red"), ("green", "yellow"),
           ("yellow", "magenta"), ("blue", "cyan"), ("red", "green"))
_STAMP = "%Y-%m-%dT%H:%M:%SZ"
_ID_RE = re.compile(r"^[A-Za-z0-9][\w.-]*$")


class ProgressError(ValueError):
    """A request the band's store cannot take (unknown run or step, bad state, wrong tree)."""


# --- the clock ---------------------------------------------------------------------------

def now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0)


def stamp(moment: _dt.datetime) -> str:
    return moment.astimezone(_dt.timezone.utc).strftime(_STAMP)


def parse_stamp(text) -> _dt.datetime | None:
    try:
        return _dt.datetime.strptime(str(text), _STAMP).replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return None


# --- the store ---------------------------------------------------------------------------

def store_dir() -> str:
    """The band's folder: the user's own state folder, never a project."""
    return os.path.join(install.state_dir(), "progress")


def _checked_id(run_id: str) -> str:
    if not isinstance(run_id, str) or not _ID_RE.match(run_id):
        raise ProgressError("a run id is letters, digits, '.', '_' or '-': %r" % (run_id,))
    return run_id


def _safe(name: str) -> str:
    return re.sub(r"[^\w.-]", "_", name)


def run_path(run_id: str) -> str:
    return os.path.join(store_dir(), "runs", _safe(_checked_id(run_id)) + ".json")


def archive_path(run_id: str) -> str:
    return os.path.join(store_dir(), "archive", _safe(_checked_id(run_id)) + ".json")


def session_path(session: str) -> str:
    if not session:
        raise ProgressError("no session id")
    return os.path.join(store_dir(), "sessions", _safe(session) + ".json")


def _inside(path: str) -> None:
    if not os.path.abspath(path).startswith(os.path.abspath(store_dir()) + os.sep):
        raise ProgressError("the band writes only under %s, not %s" % (store_dir(), path))


def read(path: str):
    """A file's JSON, or ``None`` when it is absent. Invalid JSON raises ``ValueError``."""
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write(path: str, doc) -> None:
    """Replace the file whole: a temporary file beside it, then a rename."""
    _inside(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp = "%s.%d.tmp" % (path, os.getpid())
    with open(temp, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(doc, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    # Windows refuses the rename while another process has the file open to read it (a
    # band refresh, say): wait for the reader, never lose the write.
    for attempt in range(100):
        try:
            os.replace(temp, path)
            return
        except PermissionError:
            if attempt == 99:
                with contextlib.suppress(OSError):
                    os.remove(temp)
                raise
            time.sleep(0.02)


def remove(path: str) -> None:
    _inside(path)
    with contextlib.suppress(OSError):
        os.remove(path)


@contextlib.contextmanager
def locked(path: str, wait_seconds: float = 10.0):
    """Hold ``<path>.lock`` for one read-change-write, so two sessions feeding one run (an
    epic's) never lose each other's change."""
    _inside(path)
    lock = path + ".lock"
    os.makedirs(os.path.dirname(lock), exist_ok=True)
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode("ascii"))
            os.close(fd)
            break
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(lock) > STALE_LOCK_SECONDS:
                    os.remove(lock)
                    continue
            except OSError:
                continue
            if time.monotonic() > deadline:
                raise ProgressError("%s is held by another writer; try again" % lock)
            time.sleep(0.05)
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            os.remove(lock)


# --- sessions ----------------------------------------------------------------------------

def bind_session(session: str, run_id: str, moment: _dt.datetime) -> None:
    """The session now shows ``run_id`` (the hook calls this as a feeding command runs)."""
    write(session_path(session), {"run": _checked_id(run_id), "at": stamp(moment)})


def clear_session(session: str, moment: _dt.datetime) -> bool:
    """Remove this session's end line; ``False`` when it has nothing to clear. A running
    run is never cleared: only an ended one's line."""
    path = session_path(session)
    pointer = read(path)
    if not isinstance(pointer, dict) or pointer.get("cleared"):
        return False
    run_id = pointer.get("run") or ""
    if run_id and read(run_path(run_id)) is not None:
        return False
    pointer["cleared"] = stamp(moment)
    write(path, pointer)
    return True


def session_run(session: str):
    """``(state, doc)`` for what a session shows: ``("running", run)``, ``("ended",
    archived run)``, or ``(None, None)`` when it shows nothing."""
    pointer = read(session_path(session))
    if not isinstance(pointer, dict) or pointer.get("cleared") or not pointer.get("run"):
        return None, None
    doc = read(run_path(pointer["run"]))
    if isinstance(doc, dict):
        return "running", doc
    doc = read(archive_path(pointer["run"]))
    return ("ended", doc) if isinstance(doc, dict) else (None, None)


# --- runs --------------------------------------------------------------------------------

def colors_for(run_id: str) -> list[str]:
    return list(PALETTE[zlib.crc32(run_id.encode("utf-8")) % len(PALETTE)])


def _plan(milestones) -> list[dict]:
    """The plan's milestones as the record keeps them: ids, labels and planned steps."""
    if not isinstance(milestones, list) or not milestones:
        raise ProgressError("a plan needs at least one milestone")
    out, seen = [], set()
    for mi, raw in enumerate(milestones, start=1):
        raw = raw or {}
        label = str(raw.get("label") or raw.get("name") or "").strip()
        if not label:
            raise ProgressError("milestone %d has no label" % mi)
        mid = str(raw.get("id") or "M%d" % mi)
        if mid in seen:
            raise ProgressError("milestone id %s is used twice" % mid)
        seen.add(mid)
        steps = []
        for si, step in enumerate(raw.get("steps") or [], start=1):
            step_label = str((step or {}).get("label") or (step or {}).get("name") or "").strip()
            if not step_label:
                raise ProgressError("step %d of milestone %s has no label" % (si, mid))
            steps.append({"id": str(step.get("id") or si), "label": step_label})
        out.append({"id": mid, "label": label, "plannedSteps": steps})
    return out


def _fresh_steps(milestone: dict) -> list[dict]:
    return [{"id": s["id"], "label": s["label"], "state": "queued"}
            for s in milestone.get("plannedSteps", [])]


def open_run(run_id: str, title: str, milestones, root: str, moment: _dt.datetime,
             colors=None, kind: str = "dispatch") -> str:
    """Start a run from its plan, or resume it. Never a second record for one run: an
    existing run (an epic's next session, a plan changed mid-run) keeps its states and
    stamps, and its milestone list follows the plan; a run that STOPPED is brought back from
    the archive. A run that finished COMPLETE is refused: give new work a new id."""
    plan = _plan(milestones)
    path = run_path(run_id)
    with locked(path):
        doc, outcome = read(path), "resumed"
        if doc is None:
            archived = read(archive_path(run_id))
            if isinstance(archived, dict) and (archived.get("end") or {}).get("state") == "complete":
                raise ProgressError("%s finished COMPLETE; new work takes a new run id" % run_id)
            if isinstance(archived, dict):
                doc, outcome = archived, "restored"
                doc.pop("end", None)
                remove(archive_path(run_id))
        if doc is None:
            at = stamp(moment)
            if kind not in ("dispatch", "epic"):
                raise ProgressError("a run is a dispatch or an epic, not %r" % kind)
            doc = {"schema": SCHEMA, "run": {"id": run_id, "title": title or run_id,
                                             "kind": kind},
                   "root": root, "colors": list(colors or colors_for(run_id)),
                   "started": at, "updated": at, "milestones": [], "steps": []}
            outcome = "begun"
        _same_tree(doc, root)
        if title:
            doc["run"]["title"] = title
        if colors:
            doc["colors"] = list(colors)
        _replan(doc, plan)
        doc["updated"] = stamp(moment)
        write(path, doc)
    return outcome


def _same_tree(doc: dict, root: str) -> None:
    held = doc.get("root") or ""
    if held and root and os.path.normcase(os.path.abspath(held)) != os.path.normcase(os.path.abspath(root)):
        raise ProgressError("run %s belongs to %s; a feeding command never targets another tree"
                            % (doc["run"]["id"], held))


def _replan(doc: dict, plan: list[dict]) -> None:
    """The milestone list follows the plan; a milestone that stays keeps its state and
    stamps, and the current milestone's steps follow its planned steps the same way."""
    old = {m["id"]: m for m in doc.get("milestones", [])}
    doc["milestones"] = []
    for planned in plan:
        kept = old.get(planned["id"], {})
        merged = {"id": planned["id"], "label": planned["label"],
                  "state": kept.get("state", "queued"), "plannedSteps": planned["plannedSteps"]}
        for key in ("started", "finished"):
            if kept.get(key):
                merged[key] = kept[key]
        doc["milestones"].append(merged)
    current = _current(doc)
    if current is None:
        doc["current"], doc["steps"] = None, []
        return
    if doc.get("current") != current["id"]:
        doc["current"], doc["steps"] = current["id"], _fresh_steps(current)
        return
    if current["plannedSteps"]:
        have = {s["id"]: s for s in doc.get("steps", [])}
        doc["steps"] = [dict(have.get(p["id"], {"state": "queued"}), id=p["id"], label=p["label"])
                        for p in current["plannedSteps"]]


def _current(doc: dict):
    milestones = _live(doc.get("milestones", []))
    for want in (lambda m: m.get("state") == "active", lambda m: m.get("state") != "done"):
        for m in milestones:
            if want(m):
                return m
    return milestones[-1] if milestones else None


def _move(item: dict, state: str, at: str) -> None:
    if state not in STATES:
        raise ProgressError("state %r is not one of %s" % (state, ", ".join(STATES)))
    if state == "active":
        item.setdefault("started", at)
        item.pop("finished", None)
    elif state == "done":
        item.setdefault("started", at)
        item["finished"] = at
    elif state == "queued":
        item.pop("started", None)
        item.pop("finished", None)
    item["state"] = state


def _feed(run_id: str, root: str, moment: _dt.datetime, change) -> str:
    path = run_path(run_id)
    with locked(path):
        doc = read(path)
        if not isinstance(doc, dict):
            raise ProgressError("no running record for %s; open it from its plan first "
                                "(--plan, --from-spec or --from-charter)" % run_id)
        _same_tree(doc, root)
        outcome = change(doc, stamp(moment))
        doc["updated"] = stamp(moment)
        write(path, doc)
    return outcome


def set_milestone(run_id: str, milestone_id: str, state: str, root: str,
                  moment: _dt.datetime, label: str = "") -> str:
    """Move one milestone; one made active becomes the current one, its steps from the plan."""
    def change(doc, at):
        found = next((m for m in doc["milestones"] if m["id"] == milestone_id), None)
        if found is None:
            if not label:
                raise ProgressError("run %s has no milestone %r; name it with --label to add it"
                                    % (run_id, milestone_id))
            found = {"id": milestone_id, "label": label, "state": "queued", "plannedSteps": []}
            doc["milestones"].append(found)
        elif label:
            found["label"] = label
        _move(found, state, at)
        current = _current(doc)
        if current is not None and current["id"] != doc.get("current"):
            doc["current"], doc["steps"] = current["id"], _fresh_steps(current)
        return "set"
    return _feed(run_id, root, moment, change)


def set_step(run_id: str, step_id: str, state: str, root: str, moment: _dt.datetime,
             label: str = "") -> str:
    """Move one step of the current milestone; a step the plan did not list is added when it
    is named with a label. The milestone a step starts in becomes active."""
    def change(doc, at):
        current = next((m for m in doc["milestones"] if m["id"] == doc.get("current")), None)
        if current is None:
            raise ProgressError("run %s has no current milestone" % run_id)
        found = next((s for s in doc["steps"] if s["id"] == step_id), None)
        if found is None:
            if not label:
                raise ProgressError("milestone %s of %s has no step %r; name it with --label to "
                                    "add it" % (current["id"], run_id, step_id))
            found = {"id": step_id, "label": label, "state": "queued"}
            doc["steps"].append(found)
        elif label:
            found["label"] = label
        _move(found, state, at)
        if state in ("active", "done") and current.get("state") == "queued":
            _move(current, "active", at)
        return "set"
    return _feed(run_id, root, moment, change)


def end_run(run_id: str, outcome: str, root: str, moment: _dt.datetime, reason: str = "",
            evidence: str = "") -> dict:
    """End a run and archive it; the end line is drawn from the archive. ``complete`` only
    with every milestone done and the completion check's evidence named; any other end is
    ``stopped``, with a one-word reason."""
    path = run_path(run_id)
    with locked(path):
        doc = read(path)
        if not isinstance(doc, dict):
            raise ProgressError("no running record for %s" % run_id)
        _same_tree(doc, root)
        at = stamp(moment)
        if outcome == "complete":
            open_ = [m["label"] for m in _live(doc["milestones"]) if m.get("state") != "done"]
            if open_:
                raise ProgressError("not COMPLETE: milestone%s %s not done; end it with --stop"
                                    % ("s" if len(open_) > 1 else "", ", ".join(open_)))
            if not evidence.strip():
                raise ProgressError("COMPLETE needs --evidence: the completion check that passed")
            doc["end"] = {"state": "complete", "at": at, "evidence": evidence.strip()}
        elif outcome == "stopped":
            word = reason.strip().split()[0] if reason.strip() else ""
            if not word:
                raise ProgressError("STOPPED needs a one-word reason (failed, aborted, halted, ...)")
            doc["end"] = {"state": "stopped", "at": at, "reason": word}
        else:
            raise ProgressError("an end is complete or stopped, not %r" % outcome)
        doc["updated"] = at
        write(archive_path(run_id), doc)
        remove(path)
    return doc["end"]


def abandon_stale(moment: _dt.datetime) -> list[str]:
    """Archive, as STOPPED (``abandoned``), every run no write has touched for
    :data:`ABANDON_DAYS`. Returns the run ids archived."""
    folder = os.path.join(store_dir(), "runs")
    gone = []
    if not os.path.isdir(folder):
        return gone
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(folder, name)
        try:
            with locked(path):
                doc = read(path)
                last = parse_stamp(doc.get("updated")) if isinstance(doc, dict) else None
                if last is not None and moment - last > _dt.timedelta(days=ABANDON_DAYS):
                    run_id = doc["run"]["id"]
                    doc["end"] = {"state": "stopped", "at": stamp(moment), "reason": "abandoned"}
                    write(archive_path(run_id), doc)
                    remove(path)
                    gone.append(run_id)
        except (ValueError, OSError, ProgressError):
            continue
    return gone


# --- what the band shows -----------------------------------------------------------------

def _duration(item: dict):
    a, b = parse_stamp(item.get("started")), parse_stamp(item.get("finished"))
    return (b - a).total_seconds() if a and b and b >= a else None


def eta(items: list[dict], moment: _dt.datetime):
    """``now + remaining × the median duration of the finished items``; ``None`` until two
    are finished (never a planned or guessed figure)."""
    items = _live(items)
    durations = [d for i in items if i.get("state") == "done" for d in [_duration(i)] if d is not None]
    if len(durations) < 2:
        return None
    remaining = sum(1 for i in items if i.get("state") != "done")
    return moment + _dt.timedelta(seconds=remaining * statistics.median(durations))


def _half_up(value: float) -> int:
    """Rounding as the band's ``Math.round`` does it (Python's ``round`` goes to even)."""
    return int(value + 0.5)


def bar(done: int, total: int, width: int = BAR) -> str:
    filled = _half_up(done / total * width) if total else 0
    return "█" * filled + "░" * (width - filled)


def _hhmm(moment) -> str:
    return moment.strftime("%H:%MZ")


def _when(moment, now) -> str:
    """A time the reader cannot misplace: "12:29Z" today (UTC), "11-20 18:05Z" on a later day."""
    return _hhmm(moment) if moment.date() == now.date() else moment.strftime("%m-%d %H:%MZ")


def _day(moment) -> str:
    return moment.strftime("%Y-%m-%d %H:%MZ")


def stale_after(steps: list[dict]) -> _dt.timedelta:
    """No feed for this long and the run is drawn stale: max(30 minutes, 2 × the median
    finished step); 30 minutes until two steps are finished."""
    durations = [d for s in _live(steps) if s.get("state") == "done"
                 for d in [_duration(s)] if d is not None]
    floor = _dt.timedelta(minutes=STALE_FEED_MINUTES)
    if len(durations) < 2:
        return floor
    return max(floor, _dt.timedelta(seconds=2 * statistics.median(durations)))


def took(start, end) -> str:
    """A run's length: "12m", "3h12m", "2d4h"."""
    minutes = max(0, int((end - start).total_seconds() // 60))
    days, rest = divmod(minutes, 1440)
    hours, mins = divmod(rest, 60)
    if days:
        return "%dd%dh" % (days, hours)
    return "%dh%02dm" % (hours, mins) if hours else "%dm" % mins


#: The narrowest a bar is shrunk to when a line must fit the terminal.
MIN_BAR = 10


#: Labels a line may lose, in order, when it is too wide at the narrowest bar; the end
#: lines' come last. Values are never cut.
SHORTEN = ((" complete;", ";"), ("milestone ETA", "ETA"), ("dispatch ETA", "ETA"),
           ("epic ETA", "ETA"), ("took ", ""), ("finished ", ""), ("stopped ", ""),
           ("Milestone ", "M"), ("Step ", "S"), (" of M", " M"))


def layout(rows, width=None) -> list[str]:
    """The band's two running lines, each ``<bar> <counter> (<% complete; ETA>) <name>``.
    Both bars have one width and the counters are padded to one width, so the ``(`` lines up.
    A line never wraps: with ``width`` the name is cut with "…" first, then both bars shrink
    alike down to :data:`MIN_BAR`; the counter, the percent and the ETA are never cut.
    ``rows`` is ``[(done, total, counter, paren, name), ...]``."""
    counter_width = max(len(r[2]) for r in rows)
    # Still too wide at the narrowest bar: shorten the labels, never the values.
    for old, new in SHORTEN:
        if width is None or MIN_BAR + 1 + counter_width + 1 + max(len(r[3]) for r in rows) <= width:
            break
        rows = [(d, t, c, p.replace(old, new), n) for d, t, c, p, n in rows]
    paren_width = max(len(r[3]) for r in rows)
    fixed = counter_width + 1 + paren_width
    width_bar = BAR
    if width is not None and width_bar + 1 + fixed > width:
        width_bar = max(MIN_BAR, width - 1 - fixed)
    out = []
    for done, total, counter, paren, name in rows:
        line = "%s %s %s" % (bar(done, total, width_bar), counter.ljust(counter_width),
                             paren.ljust(paren_width))
        if width is not None:
            room = width - len(line) - 1
            name = name if len(name) <= room else (
                name[:room - 1].rstrip() + "…" if room >= 2 else "")
        out.append(line + " " + name if name else line.rstrip())
    return out


def percent(value: int) -> str:
    """A percent three digits wide, right-aligned: "  0%", " 44%", "100%"."""
    return "%3d%%" % value


def summary(doc: dict, moment: _dt.datetime, ended: bool = False, width=None) -> dict:
    """The band's lines and the figures behind them. X/Y and % count finished items."""
    title = doc["run"]["title"]
    milestones, steps = _live(doc.get("milestones", [])), _live(doc.get("steps", []))
    current = next((m for m in milestones if m["id"] == doc.get("current")), None)
    steps_done = sum(1 for s in steps if s.get("state") == "done")
    ms_done = sum(1 for m in milestones if m.get("state") == "done")
    out = {"title": title, "colors": doc.get("colors") or colors_for(doc["run"]["id"]),
           "stepsDone": steps_done, "stepsTotal": len(steps),
           "milestonesDone": ms_done, "milestonesTotal": len(milestones),
           "status": "Step %d/%d · Milestone %d/%d" % (steps_done, len(steps), ms_done,
                                                      len(milestones))}
    end = doc.get("end") if ended else None
    if end:
        at = parse_stamp(end.get("at")) or moment
        if end["state"] == "complete":
            row = (1, 1, "✓ COMPLETE", "(Milestone %d/%d; finished %s; took %s)"
                   % (ms_done, len(milestones), _day(at),
                      took(parse_stamp(doc.get("started")) or at, at)), title)
        else:
            place = milestones.index(current) + 1 if current in milestones else ms_done
            row = (ms_done, len(milestones), "■ STOPPED",
                   "(Step %d/%d of Milestone %d/%d; stopped %s; %s)"
                   % (steps_done, len(steps), place, len(milestones), _day(at),
                      end.get("reason") or "stopped"), title)
        out["end"] = layout([row], width)[0]
        return out
    updated = parse_stamp(doc.get("updated")) or moment
    stale = moment - updated > stale_after(doc.get("steps", []))
    if stale:
        tail_step = tail_run = "no update since %s" % _when(updated, moment)
    else:
        step_eta, run_eta = eta(steps, moment), eta(milestones, moment)
        tail_step = "milestone ETA " + (_when(step_eta, moment) if step_eta else "—")
        tail_run = "%s ETA %s" % ("epic" if doc["run"].get("kind") == "epic" else "dispatch",
                                  _when(run_eta, moment) if run_eta else "—")
    active = next((s for s in steps if s.get("state") == "active"), None) \
        or next((s for s in steps if s.get("state") != "done"), None) \
        or (steps[-1] if steps else None)
    pct = lambda d, t: _half_up(100 * d / t) if t else 0
    step_label = active["label"] if active else (current["label"] if current else title)
    line1, line2 = layout([
        (steps_done, len(steps), "Step %d/%d" % (steps_done, len(steps)),
         "(%s complete; %s)" % (percent(pct(steps_done, len(steps))), tail_step), step_label),
        (ms_done, len(milestones), "Milestone %d/%d" % (ms_done, len(milestones)),
         "(%s complete; %s)" % (percent(pct(ms_done, len(milestones))), tail_run),
         current["label"] if current else title)], width)
    out.update(stale=stale, line1=line1, line2=line2)
    return out
