"""The cost baseline, recovered after the fact from transcripts the host still keeps.

A time log recorded before dispatch bindings existed carries no token count. While the host
still keeps the transcripts (about 30 days), the next ceremony that writes the ``closeOuts``
role backfills each such log, inside its own write and on its own authorization — nothing is
run by hand:

* **Which logs:** closed, settled (no work stamp in the last :data:`SETTLE_HOURS` hours, so
  a log that closes and is added to again is not measured half-way), with no dispatch
  binding (a bound dispatch is measured live), never the dispatch whose write this is.
* **Which sessions:** a top-level transcript of this project (its working folder is the
  repository or one of its worktrees) that runs ``timing`` with a verb that works a row
  (``--start``, ``--end``, ``--split``, ``--wait``, ``--resume``) on the dispatch, at a time
  inside the log's work. A session that only confirmed a row, or only read the log, is not
  the dispatch's. Never by time window alone, never "the newest transcript".
* **What:** the top-level calls inside the log's work window (its rows' starts, waits,
  resumes and ends) are orchestration; with every subagent's calls in that window, the total.
  Tokens are ``measured``; dollars carry their own kind. Each response is counted once
  across every file read. Old dispatches named no row in their spawns, so per-row cost is
  *not computable*. Two dispatches whose windows overlap in one session are both marked
  ``overlaps``: their figures share calls.
* **Marked once:** a log with no transcript left is marked *not computable* once; it is
  measured again only if its work later extends past the window it was marked with.

The record is one ``cost`` event appended to the time log; a reader of an older release
skips it. A run spends at most :data:`BUDGET_SECONDS`; what it does not reach waits for the
next write.
"""
from __future__ import annotations

import datetime as _dt
import os
import subprocess
import time

from . import cost as cost_mod, costreport, guardstate, hosts, timing

ADAPTERS = ("claude-code", "codex")
SETTLE_HOURS = 24
BUDGET_SECONDS = 15.0
#: Minutes either side of the work window a working command may fall (a row's `--start`
#: is stamped by the command itself).
SLACK_MINUTES = 5
#: Hours a log that failed to be measured is left alone before it is tried again.
RETRY_HOURS = 24
_SKIPS = "backfill-skips.json"


def _stamp(text: str) -> _dt.datetime | None:
    return timing.parse_stamp(text) or costreport.call_time(text)


def _work_window(events: list[dict]) -> tuple[str, str]:
    return costreport.window(events)


def _record(events: list[dict]) -> dict | None:
    return costreport.recorded(events)


def candidates(directory: str, current: str = "", now: _dt.datetime | None = None
               ) -> list[tuple[str, list[dict]]]:
    """Closed, settled, unbound logs not yet recorded — or recorded with a window their
    work has since outgrown."""
    now = now or timing.now()
    found = []
    for dispatch, events in costreport.closed_dispatches(directory):
        if dispatch == current or hosts.read_binding(dispatch):
            continue
        if any(e.get("event") == "end" and e.get("tokens") for e in events):
            continue                                  # counted when it ran
        start, end = _work_window(events)
        last = _stamp(end)
        if not start or last is None or now - last < _dt.timedelta(hours=SETTLE_HOURS):
            continue
        record = _record(events)
        if record and (record.get("window") or ["", ""])[1] >= end:
            continue                                  # recorded, and the work has not moved
        found.append((dispatch, events))
    return found


def project_roots(project: str) -> list[str]:
    """The project root and every worktree of its repository, as folders a session of this
    project may have been started in (read-only git)."""
    roots = [os.path.normcase(os.path.abspath(project))]
    try:
        done = subprocess.run(["git", "--no-optional-locks", "-C", project, "worktree",
                               "list", "--porcelain"], capture_output=True, text=True,
                              timeout=10)
    except (OSError, subprocess.SubprocessError):
        return roots
    for line in done.stdout.splitlines():
        if line.startswith("worktree "):
            roots.append(os.path.normcase(os.path.abspath(line[len("worktree "):].strip())))
    return roots


def _session_cwd(adapter, path: str) -> str:
    for record in hosts.head_records(path, 262144):
        cwd = record.get("cwd")
        payload = record.get("payload")
        if not cwd and isinstance(payload, dict):
            cwd = payload.get("cwd")
        if isinstance(cwd, str) and cwd:
            return cwd
    return ""


def _in_project(cwd: str, roots: list[str]) -> bool:
    if not cwd:
        return False
    folder = os.path.normcase(os.path.abspath(cwd))
    return any(folder == root or folder.startswith(root.rstrip("\\/") + os.sep)
               for root in roots)


def _guarded_roots(roots: dict[str, list[str]] | None) -> dict[str, list[str]]:
    """The transcript roots to read. Under a test run, a root outside the isolated home is
    refused rather than read: no test may read this machine's real transcripts."""
    chosen = roots or {n: hosts.adapter(n).transcript_roots() for n in ADAPTERS}
    if os.environ.get("PYTEST_CURRENT_TEST"):
        home = os.path.normcase(os.path.abspath(os.environ.get("VIRTUOSO_HOME", "")))
        for name, paths in chosen.items():
            for path in paths:
                if not os.path.normcase(os.path.abspath(path)).startswith(home):
                    raise RuntimeError("a test may not read transcripts outside VIRTUOSO_HOME "
                                       "(%s)" % path)
    return chosen


def _sessions(wanted: dict[str, tuple[str, str]], roots, project: str, reader,
              deadline: float) -> tuple[dict[str, list], bool]:
    """``dispatch -> [(adapter, transcript)]`` from one pass over the transcripts, and
    whether the pass finished inside its budget."""
    found: dict[str, list] = {d: [] for d in wanted}
    earliest = min((_stamp(w[0]) for w in wanted.values() if _stamp(w[0])), default=None)
    allowed = project_roots(project) if project else None
    needles = {d: d.encode() for d in wanted}
    for name in ADAPTERS:
        adapter = hosts.adapter(name)
        for root in roots.get(name, []):
            for path in adapter.top_level_transcripts(root):
                if time.monotonic() > deadline:
                    return found, False
                try:
                    if earliest and os.path.getmtime(path) < earliest.timestamp():
                        continue
                    with open(path, "rb") as handle:
                        data = handle.read()
                except OSError:
                    continue
                hit = [d for d, needle in needles.items() if needle in data and b"timing" in data]
                if not hit:
                    continue
                if allowed is not None and not _in_project(_session_cwd(adapter, path), allowed):
                    continue
                try:
                    facts = reader.facts(adapter, path)
                except Exception:                     # one damaged transcript never stops a run
                    continue
                if facts is None:
                    continue
                for dispatch in hit:
                    start, end = (_stamp(s) for s in wanted[dispatch])
                    slack = _dt.timedelta(minutes=SLACK_MINUTES)
                    for command, at in zip(facts.commands, facts.command_times):
                        moment = costreport.call_time(at) if at else None
                        if (hosts.work_dispatch(command) == dispatch and moment and start
                                and end and start - slack <= moment <= end + slack):
                            found[dispatch].append((adapter, path))
                            break
    return found, True


def _calls_in(adapter, path, window, reader, seen: dict[str, str], session: str) -> list:
    """The calls of one file inside the window, each response once across every file read
    (the copy in its own session's file wins)."""
    try:
        facts = reader.facts(adapter, path)
    except Exception:
        return []
    kept = []
    for call in (facts.calls if facts else []):
        if not costreport._within(call, window[0], window[1], False):
            continue
        owner = seen.get(call.id)
        if owner is None:
            seen[call.id] = session
            kept.append(call)
    return kept


def measure(dispatch: str, events: list[dict], sessions: list, reader=None, prices=None) -> dict:
    """The ``cost`` event for one log: dispatch-level cost, or *not computable* once."""
    prices = prices if prices is not None else cost_mod.catalogue()
    reader = reader or costreport.Reader()
    window = _work_window(events)
    base = {"event": "cost", "source": "backfilled", "window": list(window),
            "attribution": "session-window",
            "perRow": {"computable": False,
                       "missing": ["a row N in each subagent's spawn (the dispatch predates "
                                   "the row rule)"]}}
    if not sessions:
        return dict(base, computable=False, missing=[
            "a transcript of this project, still kept by the host, that works a row of %s "
            "(`timing --dispatch %s --start|--end`) inside its work" % (dispatch, dispatch)])
    seen: dict[str, str] = {}
    top, every = [], []
    for adapter, path in sessions:
        session = os.path.splitext(os.path.basename(path))[0]
        inside = _calls_in(adapter, path, window, reader, seen, session)
        top += inside
        every += inside
        facts = reader.facts(adapter, path)
        for sub_path, _description, _task in (adapter.subagents(path, facts) if facts else []):
            every += _calls_in(adapter, sub_path, window, reader, seen, session)
    orchestration, total = costreport.priced(top, prices), costreport.priced(every, prices)
    return dict(base, computable=True, host=sorted({a.name for a, _p in sessions}),
                sessions=[os.path.basename(p) for _a, p in sessions],
                orchestration=orchestration, total=total)


def _skips() -> dict:
    data = guardstate.read_json(os.path.join(guardstate.guard_dir(), _SKIPS))
    return data if isinstance(data, dict) else {}


def _skip(directory: str, dispatch: str, reason: str) -> None:
    skips = _skips()
    skips["%s|%s" % (directory, dispatch)] = {"at": timing.stamp(timing.now()), "reason": reason}
    try:
        guardstate.write_json_atomic(os.path.join(guardstate.guard_dir(), _SKIPS), skips)
    except (OSError, ValueError):
        pass


def _skipped_recently(directory: str, dispatch: str, now: _dt.datetime) -> bool:
    entry = _skips().get("%s|%s" % (directory, dispatch))
    at = _stamp(entry.get("at", "")) if isinstance(entry, dict) else None
    return bool(at) and now - at < _dt.timedelta(hours=RETRY_HOURS)


def _overlaps(measured: dict[str, dict]) -> None:
    """Mark records whose windows overlap in a shared session: their figures share calls."""
    names = sorted(measured)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ea, eb = measured[a], measured[b]
            shared = set(ea.get("sessions") or []) & set(eb.get("sessions") or [])
            (a0, a1), (b0, b1) = ea["window"], eb["window"]
            if shared and a0 <= b1 and b0 <= a1:
                ea.setdefault("overlaps", []).append(b)
                eb.setdefault("overlaps", []).append(a)


def run(directory: str, roots=None, prices=None, *, project: str = "", current: str = "",
        now: _dt.datetime | None = None, budget: float = BUDGET_SECONDS) -> list[dict]:
    """Backfill the candidate logs in ``directory``: one ``cost`` event each. Returns, per
    log, ``{"dispatch", "computable", "tokens"}`` — or ``"error"`` when it could not be
    measured or written (left for a later write, never half-written)."""
    now = now or timing.now()
    roots = _guarded_roots(roots)
    pending = [(d, e) for d, e in candidates(directory, current, now)
               if not _skipped_recently(directory, d, now)]
    if not pending:
        return []
    deadline = time.monotonic() + budget
    reader = costreport.Reader()
    wanted = {d: _work_window(e) for d, e in pending}
    sessions, finished = _sessions(wanted, roots, project, reader, deadline)
    measured, done = {}, []
    if not finished:                                  # what was found is certain; the rest waits
        done = [{"dispatch": d, "computable": None, "deferred": True}
                for d, _e in pending if not sessions.get(d)]
        pending = [(d, e) for d, e in pending if sessions.get(d)]
    for dispatch, events in pending:
        try:
            measured[dispatch] = measure(dispatch, events, sessions.get(dispatch, []),
                                         reader, prices)
        except Exception as exc:
            _skip(directory, dispatch, str(exc))
            done.append({"dispatch": dispatch, "computable": None, "error": str(exc)})
    _overlaps({d: m for d, m in measured.items() if m.get("computable")})
    for dispatch, event in measured.items():
        try:
            timing.append(os.path.join(directory, timing.log_name(dispatch)), event)
        except Exception as exc:
            _skip(directory, dispatch, str(exc))
            done.append({"dispatch": dispatch, "computable": None, "error": str(exc)})
            continue
        done.append({"dispatch": dispatch, "computable": event["computable"],
                     "tokens": (event.get("total") or {}).get("tokens"),
                     "overlaps": event.get("overlaps", [])})
    return done
