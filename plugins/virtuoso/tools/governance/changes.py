"""The change ledger: when each change took effect, so ``results`` can split the work
before it from the work after it.

One JSON line per change, never rewritten; an undo is its own line::

    {"at": "…Z", "id": "CH-014", "action": "apply|undo", "kind": "guard|policy|lesson|
     standing-rule|plugin-version|manual", "subject": "guards.retry", "from": …, "to": …,
     "scope": {"hosts": […], "agents": […]}, "effectiveFrom": "…Z", "actor": "…",
     "note": "…"}

A ceremony the role allows (``roadmap-review``, ``dispatch-closeout``, ``project-profile``)
records a change by hand with ``changes --record`` or ``--undo``. An *automatic* line is
not a separate permission: it is written as part of an operation already authorized on its
own role (``policy-set``, ``lessons --record-status``), right after that operation's write is
verified, and the ledger's own state is checked before the operation writes anything. No
project without the role records anything; every ``results`` figure then names it.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re

from .errors import GovernanceError

ROLE = "changeLedger"
ACTIONS = ("apply", "undo")
KINDS = ("guard", "policy", "lesson", "standing-rule", "plugin-version", "manual")
_ID_RE = re.compile(r"^CH-(\d+)$")


def now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def load(path: str, skipped: list | None = None) -> list[dict]:
    """Every readable line of the ledger, in order. A damaged line is skipped and named."""
    if not os.path.isfile(path):
        return []
    lines = []
    with open(path, "rb") as handle:
        for number, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            try:
                line = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                if skipped is not None:
                    skipped.append("%s line %d is not a JSON change line" % (path, number))
                continue
            if isinstance(line, dict) and line.get("id"):
                lines.append(line)
    return lines


def next_id(lines: list[dict], path: str = "") -> str:
    """The next ``CH-NNN``: past every id read, and past any id a damaged line still shows,
    so a line cut short never has its id reused."""
    numbers = [int(m.group(1)) for m in (_ID_RE.match(str(l.get("id"))) for l in lines) if m]
    if path and os.path.isfile(path):
        with open(path, "rb") as handle:
            numbers += [int(n) for n in re.findall(rb'"CH-(\d+)"', handle.read())]
    return "CH-%03d" % (max(numbers, default=0) + 1)


def path_for(reg) -> str | None:
    """The registered ledger file, or ``None`` when the project has no such role."""
    if ROLE not in reg.roles:
        return None
    return reg.resolve(ROLE)


def ready(reg) -> str:
    """Why a line could not be appended now, or ``""``: checked before the operation that
    would cause the line writes anything, so that operation and its line succeed together."""
    path = path_for(reg)
    if path is None:
        return ""                                     # no ledger: nothing is recorded
    folder = os.path.dirname(path) or "."
    if not os.path.isdir(folder):
        return "the changeLedger directory %s does not exist" % folder
    if os.path.exists(path) and not os.access(path, os.W_OK):
        return "the change ledger %s cannot be written" % path
    return ""


def line(kind: str, subject: str, before, after, actor: str, *, action: str = "apply",
         note: str = "", effective_from: str = "", scope: dict | None = None) -> dict:
    if kind not in KINDS:
        raise GovernanceError("a change kind is one of %s, not %r" % (", ".join(KINDS), kind))
    if action not in ACTIONS:
        raise GovernanceError("a change action is apply or undo, not %r" % action)
    stamp = now()
    return {"at": stamp, "action": action, "kind": kind, "subject": subject,
            "from": before, "to": after, "scope": scope or {"hosts": [], "agents": []},
            "effectiveFrom": effective_from or stamp, "actor": actor, "note": note}


#: How long a writer waits for the ledger's lock, and how old a lock may grow before it is
#: taken for one a crashed writer left behind (it is this module's own file, nothing else's).
LOCK_WAIT_SECONDS = 10.0
LOCK_STALE_SECONDS = 60.0


class _Lock:
    """An exclusive lock beside the ledger, so two writers never take the same id."""

    def __init__(self, path: str):
        self.path = path + ".lock"

    def __enter__(self):
        import time
        deadline = time.monotonic() + LOCK_WAIT_SECONDS
        while True:
            try:
                handle = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(handle, str(os.getpid()).encode())
                os.close(handle)
                return self
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(self.path) > LOCK_STALE_SECONDS:
                        os.remove(self.path)          # our own lock, left by a crashed writer
                        continue
                except OSError:
                    continue
                if time.monotonic() > deadline:
                    raise GovernanceError("the change ledger is locked by another writer (%s)"
                                          % self.path)
                time.sleep(0.05)

    def __exit__(self, *exc):
        try:
            os.remove(self.path)
        except OSError:
            pass


def append(path: str, entry: dict, skip_if=None) -> dict | None:
    """Give ``entry`` the next id and append it — one line, never a rewrite — under the
    ledger's lock. ``skip_if(lines)`` is asked again inside the lock: true, nothing is
    written and ``None`` is returned (another writer already recorded it)."""
    with _Lock(path):
        lines = load(path)
        if skip_if is not None and skip_if(lines):
            return None
        entry = dict(entry, id=next_id(lines, path))
        data = (json.dumps(entry, ensure_ascii=True, sort_keys=True) + "\n").encode("utf-8")
        with open(path, "a+b") as handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell():
                handle.seek(-1, os.SEEK_END)
                if handle.read(1) != b"\n":
                    data = b"\n" + data               # a line cut short before: never join it
            handle.write(data)
    return entry


def record_automatic(reg, entry: dict) -> dict | None:
    """Append an automatic line when the project keeps a ledger; ``None`` when it does not.
    The caller has already checked :func:`ready` before its own write."""
    path = path_for(reg)
    if path is None:
        return None
    return append(path, entry)


def in_force(lines: list[dict]) -> dict[str, dict]:
    """``subject -> the apply line in force`` for every subject. Changes stack: undoing the
    latest puts back the one before it (if that was not undone too); undoing all of them
    leaves the subject with none."""
    stacks: dict[str, list[dict]] = {}
    for entry in lines:
        subject = str(entry.get("subject"))
        if entry.get("action") == "apply":
            stacks.setdefault(subject, []).append(entry)
        elif entry.get("action") == "undo":
            for name, stack in stacks.items():
                stacks[name] = [s for s in stack if s.get("id") != entry.get("undoes")]
    return {subject: stack[-1] for subject, stack in stacks.items() if stack}


def ended(lines: list[dict], change: dict) -> dict | None:
    """The line that ended ``change``'s time in force — its undo, or the next change to the
    same subject — or ``None`` while it is still in force."""
    after = False
    for entry in lines:
        if entry.get("id") == change.get("id"):
            after = True
            continue
        if not after:
            continue
        if entry.get("action") == "undo" and entry.get("undoes") == change.get("id"):
            return entry
        if entry.get("action") == "apply" and entry.get("subject") == change.get("subject"):
            return entry
    return None


def find(lines: list[dict], change_id: str) -> dict | None:
    return next((l for l in lines if l.get("id") == change_id), None)


PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def plugin_version() -> str:
    """The version of the plugin this code is, from its own manifest."""
    try:
        with open(os.path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json"),
                  encoding="utf-8") as handle:
            return str(json.load(handle).get("version") or "")
    except (OSError, ValueError):
        return ""


def _installed_at() -> str:
    """When this plugin version was put in place: its manifest's modification time."""
    try:
        moment = os.path.getmtime(os.path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json"))
    except OSError:
        return ""
    return _dt.datetime.fromtimestamp(moment, _dt.timezone.utc).replace(microsecond=0) \
        .strftime("%Y-%m-%dT%H:%M:%SZ")


def record_plugin_version(reg, actor: str) -> dict | None:
    """Inside the write of a ceremony that writes: append a ``plugin-version`` line when the
    running version differs from the last one the ledger records (merged work takes effect
    only once released and installed). Never at preflight or session start."""
    path = path_for(reg)
    version = plugin_version()
    if path is None or not version or ready(reg):
        return None

    def recorded(lines: list[dict]) -> bool:
        last = next((l for l in reversed(lines) if l.get("kind") == "plugin-version"), None)
        return bool(last) and last.get("to") == version

    lines = load(path)
    if recorded(lines):
        return None
    last = next((l for l in reversed(lines) if l.get("kind") == "plugin-version"), None)
    effective = _installed_at() or now()
    floor = max((str(l.get("at")) for l in lines if l.get("at")), default="")
    if floor and effective < floor:
        effective = floor                             # a copied file's time can predate it
    return append(path, line("plugin-version", "plugin", (last or {}).get("to"), version,
                             actor or "virtuoso", effective_from=effective,
                             note="first ceremony write on this version"),
                  skip_if=recorded)
