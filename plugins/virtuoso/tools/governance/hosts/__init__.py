"""Host adapters: the only code that knows a host's transcript format, hook schema or cache
behaviour. Everything outside this package works from the host-neutral types defined here.

An adapter declares the capabilities it has (:data:`CAPABILITIES`). A guard checks the
capabilities it needs and, where one is missing, says so once and never claims to have run.

Two conventions tie a dispatch to a host session without guessing:

* a **binding**: the pre-tool hook sees a ``timing --dispatch <id>`` command and records
  dispatch id → session id, transcript path and host under ``~/.virtuoso/guard/bindings/``.
  A dispatch with no binding has no transcript figures (*not computable*), never the
  newest transcript in the folder;
* the **row rule**: a subagent spawned for a task row carries ``row N`` in its description,
  so its calls are that row's cost. A spawn naming no row is orchestration.
"""
from __future__ import annotations

import json
import os
import re
import shlex
from dataclasses import dataclass, field

from .. import guardstate

#: What an adapter may be able to do (design, Part 0).
CAPABILITIES = ("read-transcript", "read-subagent-transcript", "hold-prompt", "hold-tool",
                "hold-tool-in-subagent", "turn-end-message", "session-start-context",
                "cache-lifetime", "edit-tracking")

#: How long a host keeps a conversation's prompt cache: a fixed lifetime it reports, or a
#: lifetime the model provider decides and does not report.
FIXED, PROVIDER_DECIDED = "fixed", "provider-decided"

#: Verbs of ``timing`` that write the log (never ``--status``/``--summary``, which anyone may
#: read): a command using one with a dispatch binds that dispatch to the session.
BIND_VERBS = ("open", "add", "start", "wait", "resume", "end", "split", "park", "confirm",
              "timebox-reached")
#: The verbs that mark someone working a row — what the backfill counts as the dispatch's
#: own session (a planner confirming a row is not its worker).
WORK_VERBS = ("start", "end", "split", "wait", "resume")
_ID_RE = re.compile(r"^[A-Za-z0-9][\w.-]*$")
_HEREDOC_RE = re.compile(r"<<-?[ \t]*(['\"]?)(\w+)\1[^\n]*\n.*?\n[ \t]*\2[ \t]*(?=\n|$)", re.S)
_HERESTRING_RE = re.compile(r"@(['\"])\r?\n.*?\r?\n\1@", re.S)
#: The row a subagent's spawn names: ``row N`` in its description, or a task name that
#: starts ``row_N_`` where the host keeps only a task name.
_ROW_DESCRIPTION_RE = re.compile(r"\brow (\d+)\b", re.IGNORECASE)
_ROW_TASK_RE = re.compile(r"^row_(\d+)(?:_|$)", re.IGNORECASE)
#: Commands that only read or search: a failure of one is never a retry streak.
_READ_ONLY = frozenset({"ls", "dir", "cat", "type", "head", "tail", "less", "more", "grep",
                        "rg", "find", "fd", "pwd", "echo", "which", "where", "wc", "stat",
                        "file", "tree", "get-childitem", "get-content", "select-string",
                        "get-item", "test-path", "resolve-path", "get-command", "gci", "gc"})
_READ_ONLY_GIT = frozenset({"status", "log", "diff", "show", "rev-parse", "grep", "ls-files",
                            "blame", "describe"})
#: Git subcommands that only read when they only list.
_LISTING_GIT = frozenset({"branch", "worktree", "tag", "remote", "stash"})
_WRITES_RE = re.compile(r">|\s-delete\b|\s-exec\b|\s-execdir\b|\bxargs\b")
#: Redirects that write no file: joining streams (``2>&1``) and discarding to the null device.
_HARMLESS_REDIRECT_RE = re.compile(r"\d*>&\d|\d*>\s*(?:/dev/null|nul|\$null)(?=\s|$|[;|&])",
                                   re.IGNORECASE)


def _segment_read_only(segment: str) -> bool:
    try:
        words = shlex.split(segment, posix=True)
    except ValueError:
        words = segment.split()
    while words and "=" in words[0] and not words[0].startswith("-"):
        words = words[1:]                                   # VAR=x prefixes
    if not words:
        return True
    head = os.path.basename(words[0]).lower()
    if head in ("cd", "set-location", "pushd", "popd"):
        return True
    if head in ("git", "git.exe"):
        rest = words[1:]
        while rest and rest[0].startswith("-"):             # global options: -C <path>, -c k=v
            rest = rest[2:] if rest[0] in ("-C", "-c") else rest[1:]
        if not rest:
            return False
        if rest[0] in _LISTING_GIT:
            flags = [w for w in rest[1:] if w.startswith("-")]
            args = [w for w in rest[1:] if not w.startswith("-")]
            return (not args or args[0] == "list") and all(
                f in ("--list", "-l", "-a", "-r", "-v", "-vv", "--all", "--porcelain")
                for f in flags)
        return rest[0] in _READ_ONLY_GIT
    return head in _READ_ONLY


def is_read_only(command: str) -> bool:
    """Whether a shell command only reads or searches. Every part of a compound command
    (``;``, ``&&``, ``||``, ``|``) must read only; a redirect, ``-delete``, ``-exec`` or
    ``xargs`` writes. ``git`` is judged by its subcommand after its global options.
    Unknown commands are not read-only."""
    command = _HARMLESS_REDIRECT_RE.sub(" ", command or "")
    if _WRITES_RE.search(command):
        return False
    return all(_segment_read_only(part) for part in re.split(r"&&|\|\||[;|]", command or ""))


@dataclass
class Usage:
    """Token counts of one API response, by kind."""
    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write_5m: int = 0
    cache_write_1h: int = 0
    #: Cache writes a host reports without saying for how long they are kept.
    cache_write_no_lifetime: int = 0

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(*(a + b for a, b in zip(self.as_tuple(), other.as_tuple())))

    def as_tuple(self) -> tuple[int, ...]:
        return (self.input, self.output, self.cache_read, self.cache_write_5m,
                self.cache_write_1h, self.cache_write_no_lifetime)

    @property
    def total(self) -> int:
        return sum(self.as_tuple())

    @property
    def context(self) -> int:
        """The prompt the response was computed over: every input token, cached or not."""
        return (self.input + self.cache_read + self.cache_write_5m + self.cache_write_1h
                + self.cache_write_no_lifetime)

    def as_dict(self) -> dict:
        return {"input": self.input, "output": self.output, "cacheRead": self.cache_read,
                "cacheWrite5m": self.cache_write_5m, "cacheWrite1h": self.cache_write_1h,
                "cacheWriteNoLifetime": self.cache_write_no_lifetime}


@dataclass
class Call:
    """One API response, counted once however many records the host wrote for it."""
    id: str
    time: str                           # ISO 8601, UTC, as the host stamped it
    model: str
    usage: Usage
    #: Why this call's dollars cannot be worked out (its tokens still count), or ``""``.
    unpriceable: str = ""
    #: An assumption its dollars rest on, which makes them ``estimated``, or ``""``.
    assumption: str = ""


@dataclass
class TranscriptFacts:
    """What a transcript says, host-neutral (design, Part 0)."""
    session_id: str = ""
    last_prompt: str = ""               # typed text only
    last_reply: str = ""
    edited: list[str] = field(default_factory=list)       # oldest first, each once
    failing: dict[str, int] = field(default_factory=dict)  # command -> consecutive failures
    #: command -> (folder, stamp) of its latest failure; a streak in another folder restarts
    failure_seen: dict[str, tuple[str, str]] = field(default_factory=dict)
    last_change: str = ""               # id of the last mutating step that succeeded
    dropped: list[str] = field(default_factory=list)
    todos: list[str] = field(default_factory=list)
    headless: bool = False
    compacted_at: str = ""              # stamp of the latest compaction boundary, if any
    calls: list[Call] = field(default_factory=list)       # in order, de-duplicated
    spawns: dict[str, str] = field(default_factory=dict)  # spawn call id -> description
    spawn_threads: dict[str, str] = field(default_factory=dict)  # spawn call id -> thread id
    commands: list[str] = field(default_factory=list)     # shell commands, in order
    command_times: list[str] = field(default_factory=list)  # each command's stamp, in step
    host_version: str = ""                                # the host's own version, if written

    @property
    def last_call(self) -> Call | None:
        return self.calls[-1] if self.calls else None

    @property
    def usage(self) -> Usage:
        total = Usage()
        for call in self.calls:
            total = total + call.usage
        return total


MEASURED, INFERRED = "measured", "inferred"
#: How many times a command must fail in a row, with nothing changed since, to be dropped.
DROPPED_AFTER = 2


class Adapter:
    """One host. Subclasses fill in what they can; what they cannot is a missing capability,
    named in :attr:`missing` with the reason, so a guard can say why it did not run."""
    name = ""
    capabilities: frozenset[str] = frozenset()
    missing: dict[str, str] = {}
    cache_lifetime = PROVIDER_DECIDED
    #: Minutes, for a ``fixed`` lifetime when a transcript shows no cache write: the
    #: top-level conversation's and a subagent's.
    cache_minutes: tuple[int, int] | None = None

    def has(self, capability: str) -> bool:
        return capability in self.capabilities

    def read_transcript(self, path: str, tail_bytes: int | None = None) -> TranscriptFacts:
        raise NotImplementedError

    def lifetime(self, facts: TranscriptFacts, subagent: bool = False) -> tuple[int | None, str]:
        """How many minutes the cache of this transcript lives, and how that is known.

        A ``fixed`` host reports it per call: the most recent response with a cache write
        tells, by whichever lifetime wrote more tokens in it (on a tie, the longer). With no
        write in view, the host's usual lifetime is ``inferred``. A ``provider-decided`` host
        gives ``(None, inferred)``."""
        if self.cache_lifetime != FIXED or not self.cache_minutes:
            return None, INFERRED
        for call in reversed(facts.calls):
            hour, five = call.usage.cache_write_1h, call.usage.cache_write_5m
            if hour or five:
                return (60 if hour >= five else 5), MEASURED
        return self.cache_minutes[1 if subagent else 0], INFERRED


def _segments(command: str) -> list[str]:
    """A shell command cut at ``;``, ``&&``, ``||``, ``|`` and newlines outside quotes."""
    parts, current, quote, i = [], [], "", 0
    text = _HEREDOC_RE.sub("\n", command or "")       # a heredoc's body is text, not commands
    text = _HERESTRING_RE.sub("''", text)
    while i < len(text):
        ch = text[i]
        if quote:
            current.append(ch)
            if ch == quote:
                quote = ""
        elif ch in "'\"":
            quote = ch
            current.append(ch)
        elif ch in ";\n|" or text.startswith("&&", i):
            parts.append("".join(current))
            current = []
            if text.startswith(("&&", "||"), i):
                i += 1
        else:
            current.append(ch)
        i += 1
    parts.append("".join(current))
    return [p.strip() for p in parts if p.strip()]


def _words(segment: str) -> list[str]:
    """Words of one segment, quotes removed (a quoted span stays one word)."""
    return [a or b or c for a, b, c in re.findall(r'"([^"]*)"|\'([^\']*)\'|(\S+)', segment)]


def _registry_call(words: list[str]) -> list[str] | None:
    """The words after ``timing`` when the segment calls the registry helper's ``timing``
    from a command position (the launcher, or a Python running the script)."""
    start = 0
    while start < len(words):                         # wrappers that run what follows
        word = words[start].lower()
        if word in ("&", "eval", "exec", "sh", "bash", "env", "time", "nice", "command"):
            start += 1
        elif word == "timeout" and start + 1 < len(words):
            start += 2
        else:
            break
    if len(words) <= start:
        return None
    head = os.path.basename(words[start].replace("\\", "/")).lower()
    rest = words[start + 1:]
    if re.match(r"^\$\{?\w+\}?$", words[start]) and rest and rest[0] == "virtuoso_registry":
        head = "virtuoso"                             # the launcher, held in a variable
    if head.startswith("python") or head == "py":
        while rest and rest[0].startswith("-"):
            rest = rest[1:]
        if not rest or not os.path.basename(rest[0].replace("\\", "/")).lower().startswith(
                "virtuoso_registry"):
            return None
        rest = rest[1:]
    elif head in ("virtuoso", "virtuoso.ps1", "virtuoso.cmd"):
        if not rest or rest[0] != "virtuoso_registry":
            return None
        rest = rest[1:]
    elif not head.startswith("virtuoso_registry"):
        return None
    if "timing" not in rest:
        return None
    return rest[rest.index("timing") + 1:]


def _flags(args: list[str]) -> tuple[str, set[str]]:
    """The dispatch named (``--dispatch X``, ``--dispatch=X``, ``--sprint X``) and the
    ``--`` flags given, in any order."""
    dispatch, flags = "", set()
    for n, word in enumerate(args):
        if not word.startswith("--"):
            continue
        name, _eq, value = word[2:].partition("=")
        flags.add(name)
        if name in ("dispatch", "sprint"):
            value = value or (args[n + 1] if n + 1 < len(args) else "")
            value = value.strip("\"'").rstrip(".,")
            if _ID_RE.match(value):
                dispatch = value
    return dispatch, flags


def timing_call(command: str) -> tuple[str, set[str]]:
    """``(dispatch, verbs)`` of a command that runs the registry helper's ``timing`` on a
    dispatch, else ``("", set())``. A call held in a shell variable and run in the same
    command (``T='… timing --dispatch X'; eval "$T --start 1"``) is followed; quoted text
    (a commit message, an echo, a search) is never a call."""
    variables: dict[str, list[str]] = {}
    for segment in _segments(command):
        assign = re.match(r"^\$?([A-Za-z_]\w*)\s*=\s*(.+)$", segment)
        if assign and not segment.startswith(("python", "py ")):
            value = _words(assign.group(2))
            inner = _registry_call(_words(value[0]) if len(value) == 1 else value)
            if inner is not None:
                variables[assign.group(1)] = inner
            continue
        words = _words(segment)
        start = 1 if words and words[0] in ("&", "eval", "exec") else 0
        held = re.match(r"^\$\{?([A-Za-z_]\w*)\}?(?:\s+(.*))?$", words[start]) \
            if len(words) > start else None
        if held:
            name, tail = held.group(1), held.group(2) or ""
            if name in variables:
                args = variables[name] + _words(tail) + words[start + 1:]
                dispatch, flags = _flags(args)
                verbs = flags & set(BIND_VERBS)
                if dispatch and verbs:
                    return dispatch, verbs
                continue                              # a held call, without a verb here
        args = _registry_call(words)
        if args is not None:
            dispatch, flags = _flags(args)
            verbs = flags & set(BIND_VERBS)
            if dispatch and verbs:
                return dispatch, verbs
    return "", set()


def binding_dispatch(command: str) -> str:
    """The dispatch a shell command works on with ``timing --dispatch <id> --<verb>``, or
    ``""``. Reading a log (``--status``) never binds."""
    return timing_call(command)[0]


def work_dispatch(command: str) -> str:
    """The dispatch a command works a row of (``--start``, ``--end``, ``--split``,
    ``--wait``, ``--resume``), or ``""`` — the backfill's stricter signal."""
    dispatch, verbs = timing_call(command)
    return dispatch if verbs & set(WORK_VERBS) else ""


def spawn_row_detail(description: str = "", task_name: str = "") -> tuple[int | None, bool]:
    """``(row, ambiguous)``: the row a spawn names, and whether its description and its task
    name each name one and disagree (then the row is ``None``, never guessed)."""
    found = {int(m.group(1)) for m in (_ROW_DESCRIPTION_RE.search(description or ""),
                                       _ROW_TASK_RE.search(task_name or "")) if m}
    return (found.pop(), False) if len(found) == 1 else (None, len(found) > 1)


def spawn_row(description: str = "", task_name: str = "") -> int | None:
    """The task row a subagent's spawn names: ``row N`` in its description, or a task name
    starting ``row_N_``. ``None`` when it names none — or when both name one and they
    disagree, which is ambiguous and so never resolved by guessing."""
    return spawn_row_detail(description, task_name)[0]


def read_jsonl(path: str, tail_bytes: int | None = None):
    """Each readable JSON object of a JSON-lines file, in order, streamed. With
    ``tail_bytes``, only the whole lines in its last ``tail_bytes`` bytes (a tail read can
    see a result whose call lies before it: counts from one are a floor, not a total). A
    damaged or undecodable line is skipped; a file that cannot be opened yields nothing."""
    try:
        handle = open(path, "rb")
    except OSError:
        return
    with handle:
        if tail_bytes:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            if size > tail_bytes:
                handle.seek(size - tail_bytes - 1)
                if handle.read(1) != b"\n":
                    handle.readline()           # a partial first line
            else:
                handle.seek(0)                  # the whole file fits in the tail
        for line in handle:
            try:
                record = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                continue
            if isinstance(record, dict):
                yield record


def count_failure(facts: "TranscriptFacts", command: str, folder: str, at: str) -> None:
    """One more failure of ``command``; a failure in another folder starts a new streak."""
    seen = facts.failure_seen.get(command)
    if seen and folder and seen[0] and os.path.normcase(seen[0]) != os.path.normcase(folder):
        facts.failing[command] = 0
    facts.failing[command] = facts.failing.get(command, 0) + 1
    facts.failure_seen[command] = (folder, at)


def head_records(path: str, limit_bytes: int = 65536):
    """The readable records of a file's first ``limit_bytes`` bytes: facts a host writes
    once, near the start, which a tail read cannot see."""
    try:
        with open(path, "rb") as handle:
            raw = handle.read(limit_bytes)
    except OSError:
        return
    for line in raw.splitlines()[:-1] if len(raw) == limit_bytes else raw.splitlines():
        try:
            record = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            continue
        if isinstance(record, dict):
            yield record


def _binding_path(dispatch: str) -> str:
    safe = re.sub(r"[^\w.-]", "_", dispatch)
    return os.path.join(guardstate.guard_dir(), "bindings", safe + ".json")


def record_binding(dispatch: str, session_id: str, transcript: str, host: str) -> None:
    """Bind a dispatch to the session running it. A later binding of the same dispatch
    replaces it (the run moved to a new session); the earlier sessions are kept in order."""
    path = _binding_path(dispatch)
    current = read_binding(dispatch) or {}
    sessions = [s for s in current.get("sessions", []) if s.get("session") != session_id]
    sessions.append({"session": session_id, "transcript": transcript, "host": host})
    guardstate.write_json_atomic(path, {"dispatch": dispatch, "session": session_id,
                              "transcript": transcript, "host": host, "sessions": sessions})


def read_binding(dispatch: str) -> dict | None:
    """The binding for a dispatch, or ``None`` when there is none or it cannot be read."""
    data = guardstate.read_json(_binding_path(dispatch))
    return data if isinstance(data, dict) and data.get("session") else None


def adapter(name: str) -> Adapter | None:
    """The adapter for a host name, or ``None`` for a host this plugin does not know."""
    from . import claude_code, codex
    for module in (claude_code, codex):
        if module.ADAPTER.name == name:
            return module.ADAPTER
    return None
