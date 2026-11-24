"""Preserving a session before it is cleared: the scripted spine of ``/preserve-session``.

Three parts, each read-only except the record's ``--apply``:

* **the gate** finds this session's transcript by a marker the skill has just printed, reads
  it whole, and names every holding still running: a background launch or subagent with no
  completion, a scheduled check-in, a bound dispatch whose time log is open, a running
  progress band. It refuses when it cannot tell (A1): no transcript or more than one carries
  the marker, the transcript cannot be read, or the host has no reader for launches;
* **the inventory** lists the files this session's transcript edited, split by git into
  uncommitted, untracked and committed since the session's base, apart from the dirty files
  nobody in this transcript edited, which belong to another session and are never staged;
* **the record** check verifies every destination a session record names and refuses
  "safe to clear" while one is missing, while the record carries a credential, or while
  no ``sessionRecords`` role is registered.

The agent decides what is worth keeping and where; this module only proves it landed.
"""
from __future__ import annotations

import datetime as _dt
import os
import re
import subprocess
import time
from dataclasses import dataclass, field

from . import guards as guards_mod, guardstate, hosts, progress as progress_mod
from . import registry as registry_mod, schema, timing as timing_mod
from .errors import RoleNotRegistered

GATE_CLEAR, GATE_RUNNING, GATE_UNKNOWN = 0, 1, 3
RECORD_OK, RECORD_REFUSED, RECORD_NO_ROLE = 0, 1, 3
ROLE = "sessionRecords"
ACTOR = "preserve-session"
SAFE_LINE = "Safe to clear: run /clear"

MARKER_RE = re.compile(r"^preserve-session:[0-9a-f]{8}$")
#: A transcript that carries a marker printed moments ago was written after it, so older
#: files are never read: this keeps the whole-file search to the sessions active today.
RECENT_HOURS = 6
_CHUNK = 1 << 20

#: Why the gate cannot tell, by case.
NO_MATCH, TWO_MATCHES, UNREADABLE, NO_READER = "no-match", "two-matches", "unreadable", "no-reader"


@dataclass
class GateResult:
    code: int
    host: str = ""
    transcript: str = ""
    session: str = ""
    running: list = field(default_factory=list)       # {"kind", "id", "detail"}
    reason: str = ""
    case: str = ""

    def as_dict(self) -> dict:
        return {"code": self.code, "host": self.host, "transcript": self.transcript,
                "session": self.session, "running": list(self.running),
                "reason": self.reason, "case": self.case or None}


def check_marker(marker: str) -> str:
    if not MARKER_RE.match(marker or ""):
        raise ValueError("the marker is preserve-session:<8 lowercase hex>, not %r" % marker)
    return marker


# --- finding the transcript ---------------------------------------------------------------


def _adapters():
    from .hosts import antigravity, claude_code, codex
    return (claude_code.ADAPTER, codex.ADAPTER, antigravity.ADAPTER)


def _contains(path: str, needle: bytes) -> bool:
    """Whether the file carries ``needle``, read whole in chunks (never only a tail)."""
    tail = b""
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(_CHUNK)
            if not chunk:
                return False
            if needle in tail + chunk:
                return True
            tail = chunk[-(len(needle) - 1):]


def find_transcripts(marker: str, now: float | None = None) -> tuple[list, list]:
    """``([(host, path)], [unreadable paths])`` of every recent top-level transcript that
    carries the marker, newest first."""
    needle, found, unreadable = marker.encode("utf-8"), [], []
    since = (now or time.time()) - RECENT_HOURS * 3600
    for adapter in _adapters():
        for root in adapter.transcript_roots():
            for path in adapter.top_level_transcripts(root):
                try:
                    if os.path.getmtime(path) < since:
                        continue
                    if _contains(path, needle):
                        found.append((adapter.name, path))
                except OSError:
                    unreadable.append(path)
    found.sort(key=lambda hp: os.path.getmtime(hp[1]), reverse=True)
    return found, unreadable


def locate(marker: str) -> GateResult:
    """The one transcript carrying ``marker``, or a ``cannot tell`` result naming why."""
    check_marker(marker)
    found, unreadable = find_transcripts(marker)
    if unreadable:
        return GateResult(GATE_UNKNOWN, case=UNREADABLE, reason=(
            "%d recent transcript(s) could not be read, so this session's cannot be singled "
            "out: %s" % (len(unreadable), ", ".join(unreadable))))
    if not found:
        why = "no transcript carries %s" % marker
        if unreadable:
            return GateResult(GATE_UNKNOWN, reason=why + "; %d could not be read: %s" % (
                len(unreadable), ", ".join(unreadable)), case=UNREADABLE)
        return GateResult(GATE_UNKNOWN, reason=why + ": print it in this session first",
                          case=NO_MATCH)
    if len(found) > 1:
        return GateResult(GATE_UNKNOWN, case=TWO_MATCHES,
                          reason="%d transcripts carry %s, so none is singled out: %s" % (
                              len(found), marker, ", ".join(p for _h, p in found)))
    host, path = found[0]
    return GateResult(GATE_CLEAR, host=host, transcript=path)


# --- reading launches, per host -----------------------------------------------------------

_NOTIFY_RE = re.compile(r"<task-notification>.*?</task-notification>", re.S)
_NOTIFY_ID_RE = re.compile(r"<tool-use-id>\s*([^<\s]+)\s*</tool-use-id>")
#: A notification for an agent that stopped while its own background work still runs is
#: interim: the same task notifies again when that work ends.
_INTERIM_RE = re.compile(r"<status>\s*(?:running|pending)\s*</status>|waiting on its own "
                         r"background work|background work of its own still running", re.I)
_JOB_ID_RE = re.compile(r"\b(?:id|job(?:[ _-]?id)?)\b[\"']?\s*[:=]?\s*[\"']?([A-Za-z0-9_-]{4,})",
                        re.IGNORECASE)


def _all_text(value) -> str:
    """Every string inside a record's value, joined: where a notification may sit."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "\n".join(_all_text(v) for v in value.values())
    if isinstance(value, list):
        return "\n".join(_all_text(v) for v in value)
    return ""


def _claude_launches(path: str) -> list[dict]:
    """The ``claude-code`` adapter's transcripts: background shells, subagents and
    workflows with no completion; cron
    jobs created and not deleted; a wakeup still scheduled. Launches pair with completions
    by tool-use id, never by description."""
    from .hosts import claude_code as cc
    launched: dict[str, dict] = {}          # tool-use id -> holding
    background: set[str] = set()            # launched ids that wait for a notification
    done: set[str] = set()
    crons: dict[str, dict] = {}             # tool-use id -> holding (job id resolved later)
    cron_ids: dict[str, str] = {}           # tool-use id -> job id from its result
    deleting: dict[str, str] = {}           # CronDelete tool-use id -> the job id it names
    deleted: set[str] = set()               # job ids a CronDelete removed successfully
    names: dict[str, tuple] = {}            # tool-use id -> (tool name, its input)
    wakeup: dict | None = None
    for record in hosts.read_jsonl(path):
        kind, message = record.get("type"), record.get("message") or {}
        if kind == "assistant" and isinstance(message, dict):
            for block in message.get("content") or []:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                name, args, use = block.get("name"), block.get("input") or {}, block.get("id")
                if not use:
                    continue
                names[use] = (name, args)
                if name in cc.SHELL_TOOLS and args.get("run_in_background"):
                    launched[use] = {"kind": "background shell", "id": use,
                                     "detail": str(args.get("description") or
                                                   args.get("command") or "")[:120]}
                    background.add(use)
                elif name in cc.SPAWN_TOOLS:
                    launched[use] = {"kind": "subagent", "id": use,
                                     "detail": str(args.get("description") or "")[:120]}
                    if args.get("run_in_background"):
                        background.add(use)
                elif name in ("Workflow", "Monitor"):
                    launched[use] = {"kind": name.lower(), "id": use,
                                     "detail": str(args.get("name") or args.get("description")
                                                   or "")[:120]}
                    background.add(use)
                elif name == "CronCreate":
                    crons[use] = {"kind": "scheduled check-in", "id": use,
                                  "detail": str(args.get("cron") or args.get("schedule")
                                                or args.get("prompt") or "")[:120]}
                elif name == "CronDelete":
                    deleting[use] = str(args.get("id") or args.get("job_id") or
                                        args.get("jobId") or "")
                elif name == "ScheduleWakeup":
                    wakeup = None if args.get("stop") else {
                        "kind": "scheduled wakeup", "id": use,
                        "detail": str(args.get("reason") or "")[:120]}
        if kind == "user" and isinstance(message, dict):
            content = message.get("content")
            blocks = [b for b in (content if isinstance(content, list) else [])
                      if isinstance(b, dict) and b.get("type") == "tool_result"]
            # The record's toolUseResult belongs to its one result; with several, none
            # can be told apart, so none is read as finished.
            result = record.get("toolUseResult") if len(blocks) == 1 else None
            for block in blocks:
                use = block.get("tool_use_id")
                if use in deleting and not block.get("is_error"):
                    deleted.add(deleting[use])
                if use in crons:
                    own = result.get("id") if isinstance(result, dict) else None
                    if own:
                        cron_ids[use] = str(own)
                    else:
                        match = _JOB_ID_RE.search(_all_text(block.get("content")))
                        if match:
                            cron_ids[use] = match.group(1)
                is_async = isinstance(result, dict) and bool(
                    result.get("backgroundTaskId") or result.get("isAsync")
                    or result.get("status") == "async_launched")
                if is_async and use not in launched:
                    # moved to the background after it started (by the person or the
                    # host), whatever its own arguments said
                    name, args = names.get(use, ("tool", {}))
                    launched[use] = {"kind": "background %s" % (
                        "shell" if name in cc.SHELL_TOOLS else str(name).lower()),
                        "id": use, "detail": str(args.get("description") or
                                                 args.get("command") or "")[:120]}
                if use not in launched:
                    continue
                if is_async:
                    background.add(use)
                elif use not in background and len(blocks) == 1:
                    done.add(use)              # a foreground call returned its result
        for notification in _NOTIFY_RE.findall(_all_text(message) if kind == "user"
                                               else _all_text(record.get("content"))):
            if _INTERIM_RE.search(notification):
                continue                        # it stopped with its own work still running
            done.update(_NOTIFY_ID_RE.findall(notification))
    running = [h for use, h in launched.items() if use not in done]
    running += [h for use, h in crons.items() if cron_ids.get(use) is None
                or cron_ids[use] not in deleted]
    if wakeup:
        running.append(wakeup)
    return running


def _codex_launches(path: str) -> list[dict]:
    """The ``codex`` adapter's rollouts: a spawned subagent runs until a
    ``SubAgentActivity`` ``completed`` names its thread; the spawn call id ties the thread
    to the launch."""
    spawned: dict[str, dict] = {}
    thread_of: dict[str, str] = {}
    finished: set[str] = set()
    import json
    for record in hosts.read_jsonl(path):
        payload, kind = record.get("payload") or {}, record.get("type")
        if not isinstance(payload, dict):
            continue
        if kind == "response_item" and payload.get("type") == "function_call" \
                and payload.get("name") == "spawn_agent":
            try:
                args = json.loads(payload.get("arguments") or "{}")
            except ValueError:
                args = {}
            call = str(payload.get("call_id"))
            spawned[call] = {"kind": "subagent", "id": call,
                             "detail": str(args.get("task_name") or "")[:120]}
        elif kind == "event_msg" and payload.get("type") == "item_completed":
            item = payload.get("item") or {}
            if item.get("type") == "SubAgentActivity":
                thread = str(item.get("agent_thread_id") or "")
                if item.get("kind") == "started":
                    thread_of[str(item.get("id"))] = thread
                elif item.get("kind") == "completed":
                    finished.add(thread)
    return [h for call, h in spawned.items()
            if not thread_of.get(call) or thread_of[call] not in finished]


#: The hosts whose transcripts this gate can read launches from. A host not named here
#: is "cannot tell", never "nothing running".
LAUNCH_READERS = {"claude-code": _claude_launches, "codex": _codex_launches}


def _session_of(host: str, path: str) -> str:
    adapter = hosts.adapter(host)
    if adapter is None:
        return ""
    try:
        return adapter.read_transcript(path).session_id or ""
    except Exception:                       # a reader that fails is a reader we lack
        return ""


def _bound_dispatches(session: str) -> list[str]:
    folder = os.path.join(guardstate.guard_dir(), "bindings")
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return []
    bound = []
    for name in names:
        binding = guardstate.read_json(os.path.join(folder, name))
        if isinstance(binding, dict) and any(s.get("session") == session
                                             for s in binding.get("sessions") or []):
            bound.append(str(binding.get("dispatch") or ""))
    return [b for b in bound if b]


def _dispatch_holdings(root: str, session: str) -> tuple[list, str]:
    """This session's own open dispatch and time-log rows, and why it cannot tell (or
    ``""``). Another session's dispatch is not this one's to hold."""
    bound = _bound_dispatches(session)
    if not bound:
        return [], ""
    try:
        directory = registry_mod.load(root).resolve("closeOuts")
    except Exception as exc:
        return [], "this session is bound to %s, but its time logs cannot be read (%s)" % (
            ", ".join(bound), exc)
    held = []
    for dispatch in bound:
        events = timing_mod.load(os.path.join(directory, timing_mod.log_name(dispatch)))
        rows = [r for r in timing_mod.rows(events) or [] if r.ended is None and not r.parked]
        if rows:
            held.append({"kind": "dispatch", "id": dispatch,
                         "detail": "open time-log rows: %s" % ", ".join(
                             str(getattr(r, "id", "?")) for r in rows)})
    return held, ""


def gate(root: str, marker: str) -> GateResult:
    """Every holding of this session still running. Writes nothing."""
    result = locate(marker)
    if result.code != GATE_CLEAR:
        return result
    reader = LAUNCH_READERS.get(result.host)
    if reader is None:
        result.code, result.case = GATE_UNKNOWN, NO_READER
        result.reason = ("this host (%s) has no reader for background launches, so whether "
                         "anything still runs cannot be told" % result.host)
        return result
    try:
        with open(result.transcript, "rb"):
            pass
        result.running = reader(result.transcript)
    except OSError as exc:
        result.code, result.case = GATE_UNKNOWN, UNREADABLE
        result.reason = "the transcript cannot be read: %s" % exc
        return result
    result.session = _session_of(result.host, result.transcript)
    if not result.session:
        result.code, result.case = GATE_UNKNOWN, UNREADABLE
        result.reason = ("the transcript names no session id, so this session's dispatch, "
                         "time log and progress run cannot be checked")
        return result
    if result.session:
        held, unsure = _dispatch_holdings(root, result.session)
        result.running += held
        if unsure:
            result.code, result.case, result.reason = GATE_UNKNOWN, UNREADABLE, unsure
            return result
        state, doc = progress_mod.session_run(result.session)
        if state == "running":
            result.running.append({"kind": "progress run", "id": str((doc or {}).get("id")
                                                                      or ""), "detail": ""})
    if result.running:
        result.code = GATE_RUNNING
        result.reason = "%d holding(s) still running" % len(result.running)
    return result


# --- the inventory ------------------------------------------------------------------------


def _git(root: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "--no-optional-locks", *args], cwd=root, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def _first_stamp(path: str) -> str:
    for record in hosts.read_jsonl(path):
        stamp = record.get("timestamp")
        if isinstance(stamp, str) and stamp:
            return stamp
    return ""


def _relative(root: str, path: str) -> str | None:
    full = os.path.normcase(os.path.abspath(os.path.join(root, path)))
    base = os.path.normcase(os.path.abspath(root))
    if full != base and full.startswith(base.rstrip("\\/") + os.sep):
        return os.path.relpath(os.path.abspath(os.path.join(root, path)),
                               os.path.abspath(root)).replace(os.sep, "/")
    return None


def _status(root: str) -> tuple[set, set]:
    """``(tracked changed, untracked)`` paths relative to the repository root."""
    proc = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    if proc.returncode:
        raise LookupError(proc.stderr.strip() or "git status failed")
    changed, untracked = set(), set()
    entries = proc.stdout.split("\0")
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if len(entry) < 4:
            continue
        code, path = entry[:2], entry[3:]
        if "R" in code or "C" in code:
            i += 1                              # the rename's source follows
        (untracked if code == "??" else changed).add(path)
    return changed, untracked


def inventory(root: str, edited: list[str], first_stamp: str) -> dict:
    """This session's files, split by git, apart from another session's dirty files."""
    top = _git(root, "rev-parse", "--show-toplevel")
    if top.returncode:
        raise LookupError("%s is not inside a git repository" % root)
    repo = top.stdout.strip()
    mine, outside = [], []
    for path in edited:
        rel = _relative(repo, path)
        (mine if rel is not None else outside).append(rel if rel is not None else path)
    mine = sorted(set(mine))
    changed, untracked = _status(repo)
    base, notes, committed = "", [], None
    if first_stamp:
        proc = _git(repo, "rev-list", "-1", "--before=%s" % first_stamp, "HEAD")
        base = proc.stdout.strip() if proc.returncode == 0 else ""
    if base:
        diff = _git(repo, "diff", "--name-only", base, "HEAD")
        since = set(p for p in diff.stdout.splitlines() if p) if diff.returncode == 0 else set()
        committed = sorted(p for p in mine if p in since and p not in changed
                           and p not in untracked)
    else:
        notes.append("committed-since-base is not computable: no commit precedes the "
                     "transcript's first record (%s)" % (first_stamp or "no stamp"))
    return {
        "repository": repo,
        "base": base or None,
        "uncommitted": [p for p in mine if p in changed],
        "untracked": [p for p in mine if p in untracked],
        "committed": committed,
        "others": sorted((changed | untracked) - set(mine)),
        "outside": sorted(set(outside)),
        "notes": notes,
    }


def session_edits(host: str, transcript: str) -> list[str]:
    """Every file this session edited: its own transcript's edits and its subagents'."""
    adapter = hosts.adapter(host)
    edited = list(adapter.read_transcript(transcript).edited)
    try:
        children = adapter.subagent_transcripts(transcript)
    except TypeError:                       # an adapter that needs the parent's facts
        children = []
    except Exception:
        children = []
    for child in children:
        try:
            edited += [p for p in adapter.read_transcript(child).edited if p not in edited]
        except Exception:
            continue
    return edited


def shared_paths(repo: str, paths: list[str], own: str, now: float | None = None) -> list[str]:
    """Which of this session's dirty ``paths`` another recent transcript also names: a file
    two sessions changed is never staged whole by one of them."""
    since = (now or time.time()) - RECENT_HOURS * 3600
    others = []
    for adapter in _adapters():
        for root in adapter.transcript_roots():
            for path in adapter.top_level_transcripts(root):
                try:
                    if (os.path.normcase(os.path.abspath(path)) !=
                            os.path.normcase(os.path.abspath(own))
                            and os.path.getmtime(path) >= since):
                        others.append(path)
                except OSError:
                    continue
    shared = []
    for rel in paths:
        full = os.path.abspath(os.path.join(repo, rel))
        needles = {full, full.replace("\\", "/"), full.replace("\\", "\\\\")}
        for other in others:
            try:
                if any(_contains(other, n.encode("utf-8")) for n in needles):
                    shared.append(rel)
                    break
            except OSError:
                shared.append(rel)          # cannot tell: never staged
                break
    return shared


def stage_paths(found: dict) -> list[str]:
    """The exact paths this session may stage: its own uncommitted and untracked files,
    never a path another session left dirty or also changed."""
    blocked = set(found.get("others") or []) | set(found.get("shared") or [])
    return [p for p in (found.get("uncommitted") or []) + (found.get("untracked") or [])
            if p not in blocked]


# --- the record ---------------------------------------------------------------------------

#: A credential written as ``name = value`` or ``name: value``: the guards' secret names,
#: held to an assignment so prose that only mentions a key or an author is not refused.
_CREDENTIAL_RE = re.compile(
    r"(?i)(?:\b[\w-]*(?:key|token|secret|passw(?:or)?d|auth(?!or)|credential)[\w-]*"
    r"[\"'`]?\s*[=:]\s*[\"'`]?(?!\d+\b)[^\s\"'`|]{6,}"
    r"|://[^/\s:@]+:[^@\s/]+@)")
_HEADER_RE = re.compile(r"^[-*][ \t]+\*\*(?P<name>[^*]+?):\*\*[ \t]*(?P<value>.*)$")
_DEST_RE = re.compile(r"^(?P<kind>path|commit|finding|held|issue|memory):(?P<target>.+)$")
_FINDING_ID_RE = re.compile(r"^F-\d{3,}$")
KINDS = ("path", "commit", "finding", "held", "issue", "memory")


@dataclass
class Record:
    title: str = ""
    fields: dict = field(default_factory=dict)
    items: list = field(default_factory=list)          # {"item", "kind", "dest", "line"}
    not_kept: list = field(default_factory=list)
    uncommitted: list = field(default_factory=list)
    problems: list = field(default_factory=list)


def _cells(line: str) -> list[str]:
    body = line.strip().strip("|")
    return [c.strip() for c in body.split("|")]


def parse_record(text: str) -> Record:
    rec, section = Record(), ""
    header_seen = False
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        if line.startswith("# ") and not rec.title:
            rec.title = line[2:].strip()
            continue
        if line.startswith("## "):
            section = line[3:].strip().lower()
            header_seen = False
            continue
        if not section:
            match = _HEADER_RE.match(line.strip())
            if match:
                rec.fields[match.group("name").strip().lower()] = match.group("value").strip()
            continue
        if section.startswith("items") and line.strip().startswith("|"):
            cells = _cells(line)
            if not header_seen:
                header_seen = True
                continue
            if all(set(c) <= set("-: ") for c in cells):
                continue
            cells += ["", "", "", ""]
            rec.items.append({"item": cells[0], "kind": cells[1],
                              "dest": cells[2].strip("`"), "line": number})
        elif section.startswith("not kept") and line.strip()[:2] in ("- ", "* "):
            rec.not_kept.append(line.strip()[2:])
        elif section.startswith("uncommitted") and line.strip()[:2] in ("- ", "* "):
            rec.uncommitted.append(line.strip()[2:].strip("`"))
    for name in ("date", "session", "host", "marker"):
        if not rec.fields.get(name):
            rec.problems.append("the header has no **%s:** line" % name.capitalize())
    if not rec.title:
        rec.problems.append("the record has no `# ` title")
    if not rec.items:
        rec.problems.append("the **Items** table lists nothing")
    if not any(s.lower().startswith("provenance") for s in text.splitlines()):
        rec.problems.append("no provenance line (transcript and git HEAD)")
    return rec


def credentials(text: str) -> list[str]:
    """Each line of ``text`` that carries a credential, numbered."""
    return ["line %d: %s" % (n, guards_mod.redact(line.strip()))
            for n, line in enumerate(text.splitlines(), 1) if _CREDENTIAL_RE.search(line)]


def _finding_exists(path: str, finding: str) -> bool:
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return False
    return re.search(r"(?m)^#{2,4}[ \t]+%s\b" % re.escape(finding), text) is not None


def _inside(root: str, path: str) -> bool:
    return _relative(root, path) is not None


def verify(root: str, reg, dest: str) -> str:
    """Why ``dest`` is not verified, or ``""`` when it is."""
    match = _DEST_RE.match(dest.strip())
    if not match:
        return "%r is not <%s>:<target>" % (dest, "|".join(KINDS))
    kind, target = match.group("kind"), match.group("target").strip().strip("`")
    if kind == "path":
        if not _inside(root, target):
            return "%s is not inside the project" % target
        return "" if os.path.exists(os.path.join(root, target)) else "%s does not exist" % target
    if kind == "commit":
        if not re.match(r"^[0-9a-fA-F]{7,40}$", target):
            return "%s is not a commit id" % target
        ok = _git(root, "cat-file", "-e", target + "^{commit}").returncode == 0
        return "" if ok else "commit %s does not resolve" % target
    if kind == "memory":
        if not os.path.isabs(target):
            return "memory %s is not an absolute path" % target
        return "" if os.path.isfile(target) else "memory file %s does not exist" % target
    role = {"finding": "findings", "held": "holdingBay", "issue": "issues"}[kind]
    try:
        location = reg.resolve(role)
    except RoleNotRegistered:
        return "no %s role is registered" % role
    if kind == "finding":
        if not _FINDING_ID_RE.match(target):
            return "%s is not F-NNN" % target
        return "" if _finding_exists(location, target) else "%s is not in %s" % (target, role)
    name = target if target.endswith(".md") else target + ".md"
    if os.path.basename(name) != name:
        return "%s names a folder; give the file name in %s" % (target, role)
    return "" if os.path.isfile(os.path.join(location, name)) else "%s is not in %s" % (
        target, role)


def role_entry() -> str:
    import json
    return '"%s": ' % ROLE + json.dumps(dict(
        [("path", "<directory>")] + [(key, schema.DEFAULT_ROLES[ROLE][key]) for key in (
            "provider", "authority", "mutability", "owner", "allowedWriters")]))


def _slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return (slug[:48].rstrip("-")) or "session"


def record_name(title: str, moment: _dt.datetime) -> str:
    return "%s-%s.md" % (moment.strftime("%Y-%m-%d-%H%M"), _slug(title))


def with_verified(text: str, rec: Record) -> str:
    """The record with each Items row's *Verified* cell filled in."""
    lines = text.splitlines(keepends=True)
    for item in rec.items:
        index = item["line"] - 1
        raw = lines[index]
        ending = raw[len(raw.rstrip("\r\n")):]
        cells = _cells(raw)
        cells += [""] * (4 - len(cells))
        cells[3] = "yes"
        lines[index] = "| " + " | ".join(cells[:4]) + " |" + ending
    return "".join(lines)
