"""Cost guards: catch waste as it happens, hold a costly step once, and let the identical
step through when it comes again.

The hooks call :func:`handle` with the host's hook input. Every guard follows one mechanism:

* **Only where a Virtuoso registry exists.** No ``Virtuoso/workspace-layout.json`` above the
  working folder: the step goes through and nothing is read or written.
* **Hold once.** A hold writes a mark keyed to the step (session, guard, and the streak or
  call it belongs to); the identical step, seen again, goes through. Marks live in
  ``~/.virtuoso/guard/marks/``, one file per step created exclusively (two hooks firing at
  once never both hold), replaced after 7 days.
* **Receipts.** Each hold, and each held step sent again, is a line in
  ``~/.virtuoso/guard/receipts.jsonl`` keyed by project and session. Hooks never write a
  project file; ``dispatch-closeout`` copies a dispatch's receipts into its ``guardLog``.
* **Never in the way.** Any error, unknown input or missing capability lets the step through.
  A headless run is never held where a person would have to send again. A cost hold never
  replaces or pre-empts an issue-document stop, a git-safety rule, or write permission.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re

from . import cost as cost_mod, guardstate, hosts, policy as policy_mod, schema

MARK_DAYS = 7
HANDOFF_MINUTES = 30
TAIL_BYTES = 2 * 1024 * 1024
EXEMPT_READS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".pdf", ".ipynb")
EARLY = 1 / 12


def now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0)


def _stamp(moment: _dt.datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse(text: str) -> _dt.datetime | None:
    try:
        moment = _dt.datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=_dt.timezone.utc)


# --- where guards act ------------------------------------------------------------------------

def registry_root(cwd: str) -> str:
    """The nearest folder at or above ``cwd`` holding a Virtuoso registry or marker, or
    ``""``. Read only. Unlike preflight, which tests the project folder alone, it walks up:
    a hook can fire in a subfolder of the project."""
    folder = os.path.abspath(cwd or ".")
    while True:
        if any(os.path.isfile(os.path.join(folder, *rel.split("/")))
               for rel in (schema.MANIFEST_RELPATH, schema.MARKER_RELPATH)):
            return folder
        parent = os.path.dirname(folder)
        if parent == folder:
            return ""
        folder = parent


def load_policy(root: str):
    """The project's policy over the defaults, or ``None`` when it cannot be read (then no
    guard acts)."""
    try:
        with open(os.path.join(root, *schema.MANIFEST_RELPATH.split("/")),
                  encoding="utf-8") as handle:
            raw = json.load(handle).get("policy") or {}
    except (OSError, ValueError, AttributeError):
        return None
    pol = policy_mod.load(raw if isinstance(raw, dict) else {})
    pol.raw = raw if isinstance(raw, dict) else {}
    return pol


def on(pol, guard: str) -> bool:
    return bool(pol.get("guards.enabled", True)) and bool(pol.get("guards.%s.enabled" % guard,
                                                                    True))


# --- marks and receipts --------------------------------------------------------------------------

def _path(name: str) -> str:
    return os.path.join(guardstate.guard_dir(), name)


def _mark_path(key: str) -> str:
    return _path(os.path.join("marks", hashlib.sha256(key.encode()).hexdigest()[:32]))


def mark(key: str) -> bool:
    """Mark ``key`` seen: ``True`` for the one caller that marked it (created atomically, so
    two hooks firing at once never both hold); a mark older than ``MARK_DAYS`` is replaced."""
    path = _mark_path(key)
    if guardstate.create_once(path):
        return True
    try:
        age = _dt.datetime.now().timestamp() - os.path.getmtime(path)
    except OSError:
        return guardstate.create_once(path)
    if age > MARK_DAYS * 86400:
        guardstate.remove(path)
        return guardstate.create_once(path)
    return False


def held_before(key: str) -> bool:
    path = _mark_path(key)
    try:
        return _dt.datetime.now().timestamp() - os.path.getmtime(path) <= MARK_DAYS * 86400
    except OSError:
        return False


def receipt(guard: str, event: str, hook: dict, root: str, **figures) -> None:
    guardstate.append_jsonl(_path("receipts.jsonl"), dict({
        "at": _stamp(now()), "guard": guard, "event": event, "project": root,
        "session": hook.get("session_id") or "", "agent": hook.get("agent_id") or ""},
        **figures))


def hold_once(guard: str, key: str, hook: dict, root: str, **figures) -> bool:
    """``True`` the first time this step is seen (hold it); ``False`` when it was held
    before (let it through, noting that it was sent again)."""
    if not mark(key):
        receipt(guard, "sent", hook, root, key=key, **figures)
        return False
    receipt(guard, "hold", hook, root, key=key, **figures)
    return True


# --- the dispatch a session is running -------------------------------------------------------------

def open_dispatch(root: str, session: str) -> str:
    """The dispatch this session is bound to whose time log is still open, or ``""``."""
    from . import registry as registry_mod, timing
    folder = os.path.join(guardstate.guard_dir(), "bindings")
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        names = []
    bound = []
    for name in names:
        binding = guardstate.read_json(os.path.join(folder, name))
        if isinstance(binding, dict) and any(s.get("session") == session
                                             for s in binding.get("sessions") or []):
            bound.append(binding.get("dispatch"))
    try:
        directory = registry_mod.load(root).resolve("closeOuts")
    except Exception:
        return ""
    is_open = lambda path: any(r.ended is None and not r.parked
                               for r in timing.rows(timing.load(path)) or [])
    for dispatch in bound:
        if is_open(os.path.join(directory, timing.log_name(dispatch))):
            return dispatch
    if bound:
        return ""
    # Not bound yet (no row worked this session): the project's one open time log, if
    # exactly one is open; with several, naming one would be a guess.
    prefix, suffix = timing.LOG_PREFIX, timing.LOG_SUFFIX
    try:
        names = [n for n in os.listdir(directory) if n.startswith(prefix) and n.endswith(suffix)]
    except OSError:
        return ""
    found = [n[len(prefix):len(n) - len(suffix)] for n in sorted(names)
             if is_open(os.path.join(directory, n))]
    return found[0] if len(found) == 1 else ""


# --- G1: a cold return ------------------------------------------------------------------------------

def _units(pol) -> str:
    return cost_mod.units(getattr(pol, "raw", None))


def cold_return(hook: dict, adapter, pol, root: str):
    """Hold a typed message once when the cache has expired on a large conversation."""
    if not (on(pol, "coldReturn") and adapter.has("hold-prompt")):
        return None
    if adapter.is_injected_prompt(hook.get("prompt") or ""):
        return None                                   # a subagent's report, a notification
    facts = adapter.read_transcript(hook.get("transcript_path") or "", TAIL_BYTES)
    last = facts.last_call
    if facts.headless or last is None:
        return None
    minutes, how = adapter.lifetime(facts)
    threshold = minutes * (1 - EARLY) if minutes else float(
        pol.get("guards.coldReturn.idleMinutes", 5))
    ended = _parse(last.time)
    if ended is None:
        return None
    compacted = _parse(facts.compacted_at)
    if compacted and compacted >= ended:
        return None                                   # compacted since: that prompt is gone
    # The latest sign of work, not only the latest call: a long command still running
    # (a prompt typed mid-turn) is not an idle conversation.
    busy = [t for t in (_parse(s) for s in facts.command_times[-1:]) if t]
    ended = max([ended] + busy)
    idle = (now() - ended).total_seconds() / 60
    context = last.usage.context
    if idle < threshold or context < pol.get("guards.coldReturn.minContextTokens", 50000):
        return None
    write = hosts.Usage(cache_write_1h=context) if minutes == 60 else hosts.Usage(
        cache_write_5m=context)
    price = cost_mod.price(write, last.model, _stamp(now())[:10])
    unit = _units(pol)
    if unit == "tokens" or not price.computable:
        if context < pol.get("guards.coldReturn.minRewriteTokens", 50000):
            return None
    elif price.usd < pol.get("guards.coldReturn.minRewrite", 0.50):
        return None
    key = "%s|cold|%s" % (hook.get("session_id"), last.id)
    figures = {"tokens": context, "usd": price.usd, "kind": "measured" if minutes and how ==
               "measured" else "inferred", "idleMinutes": round(idle)}
    if not hold_once("coldReturn", key, hook, root, **figures):
        return None
    dispatch = open_dispatch(root, hook.get("session_id") or "")
    cost_text = cost_mod.amount(context, price.usd, unit)
    lifetime = ("its cache lifetime of %d minutes" % minutes if minutes and how == "measured"
                else "about %d minutes, so it is probably cold" % threshold)
    lines = ["Idle %s, past %s. Sending this will re-read ~%s at API prices." % (
        _idle_text(idle), lifetime, cost_text), "Send again to go ahead"]
    if dispatch:
        lines[-1] += (", or paste: /compact keep %s, the time log, open decisions — it makes "
                      "the calls after it cheaper." % dispatch)
    else:
        write_handoff(hook, adapter, root, facts)
        lines[-1] += (", or /clear and continue from a handoff note of this conversation, "
                      "which the next session starts with.")
    return adapter.hold_prompt(" ".join(lines))


def _idle_text(minutes: float) -> str:
    whole = int(round(minutes))
    return "%dh %02dm" % divmod(whole, 60) if whole >= 60 else "%d min" % whole


# --- G4: the handoff note ---------------------------------------------------------------------------

def _project_key(root: str) -> str:
    return hashlib.sha256(os.path.normcase(os.path.abspath(root)).encode()).hexdigest()[:16]


def handoff_note(facts) -> str:
    """The previous conversation's own state, built with no model call."""
    clip = lambda text, n: (text[:n] + "…") if len(text) > n else text
    lines = ["Asked last: %s" % clip(facts.last_prompt or "(none)", 400),
             "Changed: %s" % (", ".join(facts.edited[-20:]) or "nothing recorded"),
             "Dropped (tried and failed, do not retry as is): %s" % (
                 "; ".join(redact(d) for d in facts.dropped) or "nothing"),
             "Still open: %s" % ("; ".join(facts.todos) or "nothing recorded"),
             "Last reply: %s" % clip(facts.last_reply or "(none)", 400)]
    return "\n".join(lines)


def write_handoff(hook: dict, adapter, root: str, facts=None) -> None:
    facts = facts or adapter.read_transcript(hook.get("transcript_path") or "", TAIL_BYTES)
    guardstate.write_json_atomic(_path(os.path.join("handoffs", _project_key(root) + ".json")), {
        "at": _stamp(now()), "project": root, "session": hook.get("session_id") or "",
        "note": handoff_note(facts)})


def drop_handoff(root: str, session: str) -> None:
    """A prompt the same session sent after a hold (it went ahead) makes its note stale:
    delete it, so a later, unrelated clear never starts from it."""
    path = _path(os.path.join("handoffs", _project_key(root) + ".json"))
    data = guardstate.read_json(path)
    if isinstance(data, dict) and data.get("session") == session:
        guardstate.remove(path)


def sweep_handoffs() -> None:
    """Delete every handoff note past its 30 minutes, for any project: a note nobody
    cleared into is never left lying in the user's folder."""
    folder = _path("handoffs")
    try:
        names = os.listdir(folder)
    except OSError:
        return
    for name in names:
        path = os.path.join(folder, name)
        data = guardstate.read_json(path)
        written = _parse(data.get("at", "")) if isinstance(data, dict) else None
        if written is None or now() - written > _dt.timedelta(minutes=HANDOFF_MINUTES):
            guardstate.remove(path)


_SECRET_RE = re.compile(r"(?i)\b([\w-]*(?:key|token|secret|passw(?:or)?d|auth)[\w-]*)"
                        r"(\s*[=:]\s*|\s+)(\"[^\"]*\"|'[^']*'|\S+)")


def redact(text: str) -> str:
    """A dropped command as a note may carry it: values after a key, token, secret or
    password name are masked, and the line is clipped."""
    text = _SECRET_RE.sub(lambda m: m.group(1) + m.group(2) + "[redacted]", text)
    return (text[:200] + "…") if len(text) > 200 else text


def take_handoff(root: str) -> str:
    """The handoff note for this project when one was written in the last 30 minutes;
    the note is deleted once used or expired."""
    path = _path(os.path.join("handoffs", _project_key(root) + ".json"))
    data = guardstate.read_json(path)
    if not isinstance(data, dict):
        return ""
    guardstate.remove(path)
    written = _parse(data.get("at", ""))
    if written is None or now() - written > _dt.timedelta(minutes=HANDOFF_MINUTES):
        return ""
    return ("This is the previous conversation's own state, written when it was held cold. "
            "Check it against the code before acting on it.\n" + str(data.get("note", "")))


# --- G5: a repeated failure -----------------------------------------------------------------------

def retry(hook: dict, adapter, pol, root: str):
    """Deny once a shell command that failed ``limit`` times in a row with nothing changed."""
    if not on(pol, "retry"):
        return None
    tool_input = hook.get("tool_input") or {}
    command = str(tool_input.get("command") or "")
    if not command or hosts.is_read_only(command):
        return None
    inside = adapter.is_subagent(hook) if hasattr(adapter, "is_subagent") else False
    if not adapter.has("hold-tool-in-subagent" if inside else "hold-tool"):
        return None
    transcript = adapter.subagent_transcript(hook) if inside else hook.get("transcript_path")
    facts = adapter.read_transcript(transcript or "", TAIL_BYTES)
    if facts.headless and not inside:
        return None
    limit = int(pol.get("guards.retry.limit", 2))
    failures = facts.failing.get(command, 0)
    if failures < limit:
        return None
    folder, at = facts.failure_seen.get(command, ("", ""))
    here = hook.get("cwd") or ""
    if folder and here and os.path.normcase(os.path.abspath(folder)) != os.path.normcase(
            os.path.abspath(here)):
        return None                                   # the same words, run somewhere else
    failed_at = _parse(at)
    within = float(pol.get("guards.retry.withinMinutes", 30))
    if failed_at and (now() - failed_at).total_seconds() / 60 > within:
        return None                                   # a stale streak: things may have moved
    key = "%s|%s|retry|%s|%s" % (hook.get("session_id"), hook.get("agent_id") or "",
                                 hashlib.sha256(command.encode()).hexdigest()[:16],
                                 facts.last_change)
    if not hold_once("retry", key, hook, root, failures=failures):
        return None
    return adapter.deny_tool(
        "This exact command has failed %d times in a row with nothing changed since. Change "
        "something before running it again, or say what blocks it. Running it again unchanged "
        "goes ahead." % failures)


# --- G6: a big read in the top-level session --------------------------------------------------------

def big_read(hook: dict, adapter, pol, root: str):
    """Deny once a whole-file read in the top-level session over ``bytes``."""
    if not (on(pol, "bigRead") and adapter.has("hold-tool")) or adapter.is_subagent(hook):
        return None
    tool_input = hook.get("tool_input") or {}
    path = str(tool_input.get("file_path") or "")
    if not path or tool_input.get("offset") or tool_input.get("limit") \
            or path.lower().endswith(EXEMPT_READS):
        return None
    try:
        size, mtime = os.path.getsize(path), os.path.getmtime(path)
    except OSError:
        return None
    limit = int(pol.get("guards.bigRead.bytes", 65536))
    if size <= limit:
        return None
    key = "%s|read|%s|%d" % (hook.get("session_id"), os.path.normcase(path), int(mtime))
    if not hold_once("bigRead", key, hook, root, bytes=size):
        return None
    return adapter.deny_tool(
        "This reads the whole file (%d KB) into the main conversation, which every later call "
        "pays for again. Search for the part, or read a range; read again to read it whole."
        % (size // 1024))


# --- the binding --------------------------------------------------------------------------------

def bind(hook: dict, adapter) -> None:
    """Record which session runs a dispatch, from a ``timing`` command that works a row."""
    if hook.get("agent_id"):
        return                                        # a subagent's command: bind the session
    dispatch, verbs = hosts.timing_call(str((hook.get("tool_input") or {}).get("command") or ""))
    if dispatch and verbs:
        hosts.record_binding(dispatch, hook.get("session_id") or "",
                             hook.get("transcript_path") or "", adapter.name)


# --- session start ------------------------------------------------------------------------------

def notices(adapter, version: str) -> list[str]:
    """A missing capability, said once per user per plugin version."""
    found = []
    for capability, why in sorted(adapter.missing.items()):
        if mark("notice|%s|%s|%s" % (version, adapter.name, capability)):
            found.append("%s: %s" % (capability, why))
    return found


def weekly_line(root: str) -> str:
    """Once a week per project: the last 7 days of guard receipts against the 7 before."""
    with guardstate.Lock(_path("weekly.json")):
        seen = guardstate.read_json(_path("weekly.json"))
        seen = seen if isinstance(seen, dict) else {}
        last = _parse(seen.get(root, ""))
        if last and now() - last < _dt.timedelta(days=7):
            return ""
        seen[root] = _stamp(now())
        guardstate.write_json_atomic(_path("weekly.json"), seen)
    counts = {"recent": {}, "before": {}}
    try:
        with open(_path("receipts.jsonl"), encoding="utf-8") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                at = _parse(entry.get("at", ""))
                if entry.get("project") != root or at is None:
                    continue
                age = (now() - at).days
                side = "recent" if age < 7 else "before" if age < 14 else None
                if side and entry.get("event") == "hold":
                    counts[side][entry.get("guard")] = counts[side].get(entry.get("guard"), 0) + 1
    except OSError:
        pass
    if not counts["recent"] and not counts["before"]:
        return ""
    text = lambda side: ", ".join("%s %d" % kv for kv in sorted(counts[side].items())) or "none"
    return ("Cost guards, last 7 days against the 7 before (holds by guard): %s; before: %s."
            % (text("recent"), text("before")))


def session_start(hook: dict, adapter, pol, root: str, version: str):
    parts = []
    sweep_handoffs()
    if hook.get("source") == "clear":
        note = take_handoff(root)
        if note:
            parts.append(note)
    missing = notices(adapter, version)
    if missing:
        parts.append("Tell the person, in one line in your first reply: Virtuoso cost guards "
                     "cannot do everything on this host (said once per version): "
                     + "; ".join(missing) + ".")
    # Where the person cannot be told at a turn's end, the weekly line rides on a fresh
    # interactive session's start, relayed once by the agent; when the session cannot be
    # known to be interactive, nothing is said.
    if (on(pol, "weekly") and not adapter.has("turn-end-message")
            and hook.get("source") == "startup" and _interactive(adapter, hook)):
        line = weekly_line(root)
        if line:
            parts.append("Relay this one line to the person, verbatim, in your first reply, and "
                         "add nothing about it: " + line)
    if parts and adapter.has("session-start-context"):
        return adapter.session_context("\n\n".join(parts))
    return None


def _interactive(adapter, hook: dict) -> bool:
    """Whether the session is known to be interactive (a transcript showing it was not
    started headless); unknown is not interactive."""
    path = hook.get("transcript_path") or ""
    if not path or not os.path.isfile(path):
        return False
    facts = adapter.read_transcript(path, TAIL_BYTES)
    return bool(facts.calls or facts.last_prompt) and not facts.headless


# --- G8 and the weekly line, at a turn's end ------------------------------------------------------

def turn_end(hook: dict, adapter, pol, root: str):
    """Once per context epoch past ``compactNudge.share`` of the window, a nudge to compact
    at a boundary; at the end of a session's first turn, once a week, the weekly line.
    Never in a headless run; nothing else is said."""
    if not adapter.has("turn-end-message") or hook.get("stop_hook_active"):
        return None
    facts = adapter.read_transcript(hook.get("transcript_path") or "", TAIL_BYTES)
    last = facts.last_call
    if facts.headless or last is None:
        return None
    session = hook.get("session_id") or ""
    lines = []
    if on(pol, "weekly") and mark("%s|first-turn" % session):
        line = weekly_line(root)
        if line:
            lines.append(line)
    if on(pol, "compactNudge"):
        share = float(pol.get("guards.compactNudge.share", 0.75))
        window = float(pol.get("guards.compactNudge.windowTokens", 200000))
        sized = [c for c in facts.calls if c.usage.context] if facts.calls else []
        context = (sized[-1] if sized else last).usage.context
        with guardstate.Lock(_path("epochs.json")):
            epochs = guardstate.read_json(_path("epochs.json"))
            epochs = epochs if isinstance(epochs, dict) else {}
            state = epochs.get(session) or {"epoch": 0, "above": False}
            above = context >= share * window
            if above and not state["above"]:
                dispatch = open_dispatch(root, session)
                keep = dispatch or "the task in hand"
                if hold_once("compactNudge", "%s|compact|%d" % (session, state["epoch"]), hook,
                             root, tokens=context):
                    lines.append("The conversation is at %s of a %s window. At the next "
                                 "boundary, paste: /compact keep %s, the time log, open "
                                 "decisions." % (cost_mod.tokens_text(context),
                                                 cost_mod.tokens_text(int(window)), keep))
            if context and not above and state["above"]:
                state["epoch"] += 1                   # compacted: a new epoch may nudge again
            if context:
                state["above"] = above
            epochs[session] = state
            guardstate.write_json_atomic(_path("epochs.json"), epochs)
    return adapter.turn_end_message(" ".join(lines)) if lines else None


# --- what a dispatch's guards did, and what it tried ------------------------------------------------

def dispatch_receipts(dispatch: str) -> list[dict]:
    """The receipts of every session bound to ``dispatch``, oldest first, each hold marked
    ``kept`` when its step never came again (only holds that stuck count as savings)."""
    binding = hosts.read_binding(dispatch) or {}
    sessions = {s.get("session") for s in binding.get("sessions") or [] if s.get("session")}
    found = []
    try:
        with open(_path("receipts.jsonl"), encoding="utf-8") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if entry.get("session") in sessions:
                    found.append(entry)
    except OSError:
        return []
    sent = {e.get("key") for e in found if e.get("event") == "sent"}
    for entry in found:
        if entry.get("event") == "hold":
            entry["kept"] = entry.get("key") not in sent
    return found


def tried_and_failed(dispatch: str) -> dict:
    """What a dispatch tried and dropped, read mechanically from its bound transcripts (the
    top-level session and every subagent): the carriers' *Tried and failed* list."""
    binding = hosts.read_binding(dispatch)
    if not binding:
        return {"computable": False, "missing": [
            "a dispatch binding for %s (recorded when its session runs `timing --dispatch %s` "
            "with a row verb)" % (dispatch, dispatch)], "dropped": []}
    dropped = []
    for session in binding.get("sessions") or [binding]:
        adapter = hosts.adapter(session.get("host") or binding.get("host", ""))
        if adapter is None:
            continue
        transcript = session.get("transcript") or ""
        facts = adapter.read_transcript(transcript)
        dropped += facts.dropped
        for path, _d, _t in adapter.subagents(transcript, facts):
            dropped += adapter.read_transcript(path).dropped
    seen, unique = set(), []
    for item in dropped:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return {"computable": True, "dropped": unique}


def context_now(dispatch: str, model: str = "", units: str = "") -> dict:
    """The top-level conversation's current context, read-only from the dispatch's bound
    transcript: the figure the gate's ``/compact`` line and a model change's reload cost
    (the context rewritten at ``model``'s cache-write rate) need before acting."""
    binding = hosts.read_binding(dispatch)
    if not binding:
        return {"computable": False, "missing": [
            "a dispatch binding for %s (recorded when its session runs `timing --dispatch %s` "
            "with a row verb)" % (dispatch, dispatch)]}
    sessions = binding.get("sessions") or [binding]
    session = sessions[-1]
    adapter = hosts.adapter(session.get("host") or binding.get("host", ""))
    if adapter is None:
        return {"computable": False, "missing": ["an adapter for host %r" % session.get("host")]}
    facts = adapter.read_transcript(session.get("transcript") or "", TAIL_BYTES)
    sized = [c for c in facts.calls if c.usage.context]
    if not sized:
        return {"computable": False, "missing": ["a call with a context size in %s"
                                                 % (session.get("transcript") or "(none)")]}
    last = sized[-1]
    found = {"computable": True, "dispatch": dispatch, "tokens": last.usage.context,
             "model": last.model, "at": last.time, "kind": "measured"}
    if model:
        write = hosts.Usage(cache_write_5m=last.usage.context)
        price = cost_mod.price(write, model, _stamp(now())[:10])
        found["reload"] = {"model": model, "usd": price.usd if price.computable else None,
                           "computable": price.computable, "kind": "estimated",
                           "text": cost_mod.amount(last.usage.context, price.usd, units or
                                                   "both") if price.computable else
                           "not computable (no cache-write rate for %s)" % model}
    return found


# --- the entry ----------------------------------------------------------------------------------

def handle(hook: dict, host: str, version: str = ""):
    """The hook's answer for the host (a dict to print), or ``None`` to let the step through
    and print nothing. Never raises: any error lets the step through."""
    try:
        adapter = hosts.adapter(host)
        if adapter is None or not isinstance(hook, dict):
            return None
        cwd = os.path.abspath(hook.get("cwd") or os.getcwd())
        project = os.path.abspath(os.environ.get("CLAUDE_PROJECT_DIR") or cwd)
        inside = os.path.normcase(cwd + os.sep).startswith(os.path.normcase(project + os.sep))
        root = (registry_root(project) if inside else "") or registry_root(cwd)
        if not root:
            return None                               # not a project that chose Virtuoso
        event = hook.get("hook_event_name")
        if event == "PreToolUse" and hook.get("tool_name") in ("Bash", "PowerShell"):
            bind(hook, adapter)                       # measurement, kept with guards off
        pol = load_policy(root)
        if pol is None or not pol.get("guards.enabled", True):
            return None
        if event == "UserPromptSubmit":
            held = cold_return(hook, adapter, pol, root)
            if held is None:
                drop_handoff(root, hook.get("session_id") or "")   # it went ahead after all
            return held
        if event == "Stop":
            return turn_end(hook, adapter, pol, root)
        if event == "PreToolUse":
            tool = hook.get("tool_name")
            if tool in ("Bash", "PowerShell"):
                return retry(hook, adapter, pol, root)
            if tool == "Read":
                return big_read(hook, adapter, pol, root)
            return None
        if event == "SessionStart":
            return session_start(hook, adapter, pol, root, version)
    except Exception:
        return None
    return None
