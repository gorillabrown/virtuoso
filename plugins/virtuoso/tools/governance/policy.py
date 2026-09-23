"""Project policy — everything the plugin must stop hardcoding.

Redesign items 26, 27, 47, 49, 50, 51, 53, 64-73, 74, 76, 79.

Policy lives under ``policy`` in the manifest. Every value here has a documented
default, so an existing project keeps working, but nothing in the plugin may
*assume* a default that policy can override: branch names, the default remote,
the dispatch buffer size, the status vocabulary, the lane/phase hierarchy, the
readiness-rubric extensions, actor names, and sweep boundaries are all project
configuration.
"""
from __future__ import annotations

import copy
import datetime as _dt
import json
import re
from dataclasses import dataclass

#: Git workflow policies (item 64). Ordered from least to most permissive.
GIT_POLICIES = (
    "read-only",            # inspect only; never mutate the repository
    "prepare-no-stage",     # write files; never `git add`
    "explicit-path-stage",  # `git add <exact paths>`; never commit
    "explicit-path-commit", # stage exact paths and commit
    "push",                 # commit and push
)

DEFAULTS: dict = {
    # --- actors (items 74, 75) ------------------------------------------------
    "actors": {
        "planner": "planner",
        "implementer": "implementation agent",
        "reviewer": "reviewer",
        "operator": "repository operator",
    },
    # --- interaction adapter (item 76) ---------------------------------------
    "interaction": {
        # "auto" uses structured questions when the host offers them and concise
        # plain-text questions otherwise.
        "mode": "auto",
        "maxOptions": 4,
    },
    # --- git (items 64-73) ----------------------------------------------------
    "git": {
        "policy": "explicit-path-commit",
        "separationOfDuties": False,
        "independentReviewer": False,
        # null/"" => detect from the repository. Never assume "main"/"origin".
        "defaultBranch": "",
        "remote": "",
        "requireRemote": False,
        "networkOperations": "ask",     # "ask" | "allow" | "deny"
        "branchNameTemplate": "{item-id}",
        "branchCleanup": "maintenance",  # never a dispatch prerequisite (item 68)
        "staleLock": "report",           # "report" | "prompt"; never "auto-delete" (item 69)
        "worktreeAware": True,
    },
    # --- work register / ceremonies (items 26, 27, 49, 50, 51) ---------------
    "workRegister": {
        "fieldMappings": {},            # canonical field -> project column name
        "statusMappings": {},           # canonical status -> project vocabulary
        "snapshot": "",                 # optional cached snapshot role name
        "staleAfterHours": 24,
        # Who may bring a NEW item into existence. None => every writer the
        # role's allowedWriters names; a list narrows creation to those actors
        # (an empty list means nobody). Creation is a separately authorized act.
        "creators": None,
    },
    "roadmap": {
        "dispatchBuffer": 5,            # item 49 — configurable, may be 0 (disabled)
        "eagerSpec": True,
        "hierarchy": ["phase", "stage"],  # item 50 — may be [] for a flat project
        "lanes": [],
        "specStorage": "inline",        # "inline" | "files" | "external"
        "specDirectory": "",
        "lengthCeilingLines": 2000,
        # size -> points for effort-weighted metrics. {} means the generic t-shirt
        # scale in providers/kpi.py; a project's own scale replaces it, never merges.
        "effortScale": {},
        # Dated finish lines, keyed by a project-named id; each entry has the shape
        # of DEADLINE_TEMPLATE. None by default: a date is an owner's ruling.
        "deadlines": {},
        # How pace against a deadline is measured (providers/pace.py).
        "pace": {
            "trailingWeeks": 4,     # the window the trailing rate is measured over
            "tolerance": 0.1,       # within ±10% of the required rate reads "on track"
        },
    },
    # --- readiness rubric (items 52, 53) -------------------------------------
    "rubric": {
        "version": "1.1",               # 1.1 added U9, Lessons applied
        "extensions": [],               # project-specific check ids
    },
    # --- standing rules / escalation (items 48b, 49b) -------------------------
    "standingRules": {
        "source": "roadmap",            # role name carrying the standing rules
        "ids": [],                      # project rule identifiers; none hardcoded
    },
    "issues": {
        "targets": ["local"],           # "local", "external", or both (item 49b)
        "externalRole": "",             # role name of the external tracker
        "filenameTemplate": "Issue.{item-id}.{date}.md",
    },
    # --- terminal ledger (items 47, 48) --------------------------------------
    "terminalLedger": {
        "writers": ["pointer-closeout"],
        "correctionWriters": ["pointer-closeout", "roadmap-review"],
        "format": "markdown",           # "markdown" | "csv" | "jsonl"
        # ledger field -> the project's own column header, for a CSV or JSONL ledger
        # whose columns are not the documented ones (see TERMINAL_LEDGER_FIELDS).
        "fieldMappings": {},
    },
    # --- lessons: the learning loop (tools/governance/lessons.py) -------------
    "lessons": {
        "idPrefix": "SRL",              # lesson identifiers are <prefix>-NNN
        # a live observation older than this, never applied in a close-out, is a
        # retire candidate in `lessons --hygiene`; 0 turns the check off
        "staleAfterDays": 180,
    },
    # --- governance sweep (items 51b, 52b, 53b, 56) --------------------------
    "sweep": {
        "include": ["**/*"],
        "exclude": [
            "Virtuoso/.backups/**",
            "Virtuoso/.quarantine/**",
            "**/node_modules/**",
            "**/.git/**",
            "**/__pycache__/**",
            "**/.venv/**",
            "**/vendor/**",
            "**/dist/**",
            "**/build/**",
        ],
        "ignoreDirectories": [".git", "node_modules", "__pycache__", ".venv", "vendor"],
        "followSymlinks": False,
        "maxFileBytes": 5 * 1024 * 1024,
        "binaryPolicy": "skip",          # "skip" | "hash-only"
        "quarantineDirectory": "Virtuoso/.quarantine",
        "deletionPolicy": "quarantine",  # "quarantine" | "permanent"
        "backupRetention": 10,
        "protectedAuthorities": ["archive", "terminal", "evidence"],
        "structuralAuthority": "registry",  # never "directory-readme" unless declared
    },
    # --- runtime dependencies (item 79) --------------------------------------
    "dependencies": {
        "openpyxl": ">=3.1",
    },
}

#: The terminal ledger's fields, in the order the documented format lays them out.
TERMINAL_LEDGER_FIELDS = ("recordId", "itemId", "completed", "result", "evidence", "corrects",
                          "effortEstimate", "effortActual")


def ledger_mapping_problems(mappings) -> list[str]:
    """Every reason the value of ``terminalLedger.fieldMappings`` is not usable."""
    if mappings is None or mappings == {}:
        return []
    if not isinstance(mappings, dict):
        return ["policy.terminalLedger.fieldMappings is %s; it is a mapping of ledger field "
                "to column header" % value_kind(mappings)[1]]
    problems = []
    unknown = sorted(k for k in mappings if k not in TERMINAL_LEDGER_FIELDS)
    if unknown:
        problems.append("policy.terminalLedger.fieldMappings has unknown field(s) %s (the "
                        "ledger's fields are %s)" % (", ".join(unknown),
                                                     ", ".join(TERMINAL_LEDGER_FIELDS)))
    for key, column in mappings.items():
        if key in TERMINAL_LEDGER_FIELDS and (not isinstance(column, str) or not column.strip()):
            problems.append("policy.terminalLedger.fieldMappings.%s must name a column header"
                            % key)
    return problems


_LESSON_PREFIX_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def lessons_problems(section) -> list[str]:
    """Every reason the value of ``lessons`` is not usable."""
    if section is None:
        return []
    if not isinstance(section, dict):
        return ["policy.lessons is %s; it is a mapping" % value_kind(section)[1]]
    problems = []
    unknown = sorted(k for k in section if k not in DEFAULTS["lessons"])
    if unknown:
        problems.append("policy.lessons has unknown field(s) %s" % ", ".join(unknown))
    stale = section.get("staleAfterDays", 180)
    if isinstance(stale, bool) or not isinstance(stale, int) or stale < 0:
        problems.append("policy.lessons.staleAfterDays=%s is not a whole number of days "
                        "(0 turns the stale check off)" % _shown(stale))
    prefix = section.get("idPrefix", "SRL")
    if not isinstance(prefix, str) or not _LESSON_PREFIX_RE.match(prefix):
        problems.append("policy.lessons.idPrefix=%s is not a prefix: letters, digits and "
                        "'_', starting with a letter (identifiers are <prefix>-NNN)"
                        % _shown(prefix))
    return problems


#: What one deadline holds. The children of ``roadmap.deadlines`` are named by the
#: project (``game-build``), so the defaults cannot list them; this template
#: documents their fields and the type each takes, for :func:`documented_default`
#: and :func:`type_problem`, exactly as ``DEFAULTS`` does for every other key.
DEADLINE_TEMPLATE: dict = {
    "date": "",                              # required: YYYY-MM-DD; due by the end of that day
    "owner": "",                             # required: who ruled
    "label": "",
    "finishLine": "",                        # the roadmap heading that defines done
    "scope": {"field": "", "values": []},    # absent or {} => every item in the register
    "recorded": "",                          # YYYY-MM-DD it was set or last moved
}

#: Documented mappings whose keys a project names. A child of one is documented
#: by its template: ``roadmap.deadlines.game-build.date`` is a string, and
#: ``roadmap.deadlines.game-build.dat`` is nothing at all.
OPEN_MAPPINGS: dict = {"roadmap.deadlines": DEADLINE_TEMPLATE}

#: A deadline id is one segment of a dotted policy key, so it cannot hold a dot.
DEADLINE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _deep_merge(base: dict, overlay: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in (overlay or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def assign(raw: dict | None, path: str, value) -> dict:
    """``raw`` with the dotted ``path`` set to ``value``. Pure; returns a new dict.

    Intermediate levels are created as needed. A non-dict standing where a level
    must go is replaced, because the caller has just declared what that level is.
    Siblings at every level survive, so setting one key never silently drops the
    rest of a project's configuration.
    """
    parts = [p for p in path.split(".") if p]
    if not parts:
        raise ValueError("an empty policy key sets nothing")
    out = copy.deepcopy(raw or {})
    cursor = out
    for part in parts[:-1]:
        if not isinstance(cursor.get(part), dict):
            cursor[part] = {}
        cursor = cursor[part]
    cursor[parts[-1]] = copy.deepcopy(value)
    return out


#: What a documented default's type means for a value replacing it. ``bool`` is
#: tested before ``int`` because ``isinstance(True, int)`` is true in Python, and
#: a flag is not a count.
_KINDS = ((bool, "a true/false flag"), (dict, "a mapping"), (list, "a list"),
          (str, "a string"), ((int, float), "a number"))


def value_kind(value) -> tuple[str, str]:
    """``(kind, human name)`` for ``value``. ``kind`` is an opaque comparison key."""
    for types, name in _KINDS:
        if isinstance(value, types):
            return (name, name)
    return ("null", "null")


def type_problem(path: str, value) -> str:
    """Why ``value`` is the wrong shape for ``path``, or ``""`` when it is right.

    A key check is not enough. Every documented key has a documented *type*, and a
    value of the wrong one is stored happily and then ignored: a string where
    ``rubric.extensions`` wants a list declares a readiness check that no ceremony
    can read and that session start never mentions, so the project believes it has
    a gate and has an inert string. That is precisely the "looks live, is inert"
    failure the documented-key check exists to prevent — the check simply stopped
    one field short.

    A default of ``None`` carries no type information (it encodes "unset", as
    ``workRegister.creators`` does), so anything is accepted there and said so.
    """
    default = documented_default(path)
    if default is _MISSING or default is None:
        return ""
    wanted, wanted_name = value_kind(default)
    got, got_name = value_kind(value)
    if wanted == got:
        return ""
    return ("policy.%s is documented as %s and this value is %s. A value of the wrong "
            "shape is stored and then ignored, which reads as configured and is not."
            % (path, wanted_name, got_name))


#: Distinguishes "the defaults have no such key" from "the default is None".
_MISSING = object()


def documented_default(path: str):
    """The documented default at ``path``, or :data:`_MISSING` when undocumented.

    Presence is walked rather than read through :meth:`Policy.get`, which cannot
    tell an absent key from one whose documented default is ``None`` — and
    ``workRegister.creators`` is exactly that: documented, meaningful, and
    ``None`` to mean "unset". Testing the value made the one key that governs who
    may create work items impossible to set.

    A child of an :data:`OPEN_MAPPINGS` key is documented by that mapping's
    template, because the defaults cannot list the ids a project chooses.
    """
    cursor = DEFAULTS
    walked: list[str] = []
    for part in path.split("."):
        template = OPEN_MAPPINGS.get(".".join(walked))
        if template is not None and part:
            cursor = template
        elif not isinstance(cursor, dict) or part not in cursor:
            return _MISSING
        else:
            cursor = cursor[part]
        walked.append(part)
    return cursor


def is_documented(path: str) -> bool:
    """Whether ``path`` names a key the defaults document.

    A key nothing documents is a storage slot rather than a setting: no ceremony
    reads it, so writing one produces configuration that looks live and is inert.
    Project-owned configuration has the ``x-`` extension prefix and its own rules.
    """
    return documented_default(path) is not _MISSING


def open_child(path: str) -> bool:
    """Whether ``path`` names one project-named entry of an :data:`OPEN_MAPPINGS`
    key: ``roadmap.deadlines.game-build``, not the mapping itself or a field of it."""
    parent, _, leaf = path.rpartition(".")
    return bool(leaf) and parent in OPEN_MAPPINGS


def withdraw(raw: dict | None, path: str) -> dict:
    """``raw`` without the entry at ``path``. Pure; siblings at every level survive.

    Withdrawing one deadline must not require restating the others — that is the
    operation where a list-valued key loses one.
    """
    parts = [p for p in path.split(".") if p]
    out = copy.deepcopy(raw or {})
    cursor = out
    for part in parts[:-1]:
        cursor = cursor.get(part) if isinstance(cursor, dict) else None
        if not isinstance(cursor, dict):
            return out
    if parts and isinstance(cursor, dict):
        cursor.pop(parts[-1], None)
    return out


def iso_date(value) -> _dt.date | None:
    """A strict ``YYYY-MM-DD`` calendar date, or ``None``.

    ``date.fromisoformat`` alone is not strict enough: from Python 3.11 it also
    accepts ``20270101`` and week dates such as ``2027-W01-1``, so a deadline
    spelled either way would parse on one interpreter and not on another.
    """
    if not isinstance(value, str) or not _ISO_DATE_RE.match(value):
        return None
    try:
        return _dt.date.fromisoformat(value)
    except ValueError:
        return None


def _shown(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def deadline_problems(deadlines) -> list[str]:
    """Every reason the value of ``roadmap.deadlines`` is not usable, one per fault.

    Each message names the entry and the field, so a hand edit can be fixed from
    the message alone. The type gate is not enough here: a deadline is a small
    record, and a record whose date will not parse or whose field is misspelled
    is stored happily and then ignored — configured-looking and inert.
    """
    if deadlines is None or deadlines == {}:
        return []
    if not isinstance(deadlines, dict):
        return ["policy.roadmap.deadlines is %s; it is a mapping of deadline id to deadline"
                % value_kind(deadlines)[1]]
    problems: list[str] = []
    for key, entry in deadlines.items():
        where = "policy.roadmap.deadlines.%s" % key
        if not isinstance(key, str) or not DEADLINE_ID_RE.match(key):
            problems.append("%s: a deadline id is letters, digits, '-' and '_', starting with "
                            "a letter or digit; it is one segment of a dotted key" % where)
        if not isinstance(entry, dict):
            problems.append("%s is %s, not a deadline" % (where, value_kind(entry)[1]))
            continue
        unknown = sorted(k for k in entry if k not in DEADLINE_TEMPLATE)
        if unknown:
            problems.append("%s has unknown field(s) %s: a misspelled field is stored and "
                            "ignored" % (where, ", ".join(unknown)))
        if iso_date(entry.get("date")) is None:
            problems.append("%s.date %s is not a YYYY-MM-DD calendar date"
                            % (where, _shown(entry.get("date"))))
        owner = entry.get("owner")
        if not isinstance(owner, str) or not owner.strip():
            problems.append("%s.owner is required: a date nobody owns is not a ruling" % where)
        for name in ("label", "finishLine"):
            if name in entry and not isinstance(entry[name], str):
                problems.append("%s.%s is %s; it is a string"
                                % (where, name, value_kind(entry[name])[1]))
        if "recorded" in entry and iso_date(entry["recorded"]) is None:
            problems.append("%s.recorded %s is not a YYYY-MM-DD calendar date"
                            % (where, _shown(entry["recorded"])))
        if "scope" in entry:
            problems.extend(_scope_problems(where + ".scope", entry["scope"]))
    return problems


def _scope_problems(where: str, scope) -> list[str]:
    if scope == {}:
        return []
    if not isinstance(scope, dict):
        return ['%s is %s; it is {"field": ..., "values": [...]}'
                % (where, value_kind(scope)[1])]
    problems = []
    extra = sorted(k for k in scope if k not in ("field", "values"))
    if extra:
        problems.append("%s has unknown field(s) %s" % (where, ", ".join(extra)))
    field_name = scope.get("field")
    if not isinstance(field_name, str) or not field_name.strip():
        problems.append("%s.field is required: the register field that selects the items"
                        % where)
    values = scope.get("values")
    if (not isinstance(values, list) or not values
            or not all(isinstance(v, str) and v.strip() for v in values)):
        problems.append("%s.values is required: a non-empty list of the values that count"
                        % where)
    return problems


def pace_problems(pace) -> list[str]:
    """Every reason the value of ``roadmap.pace`` is not usable."""
    if pace is None:
        return []
    if not isinstance(pace, dict):
        return ["policy.roadmap.pace is %s; it is a mapping" % value_kind(pace)[1]]
    problems = []
    unknown = sorted(k for k in pace if k not in DEFAULTS["roadmap"]["pace"])
    if unknown:
        problems.append("policy.roadmap.pace has unknown field(s) %s" % ", ".join(unknown))
    weeks = pace.get("trailingWeeks", 4)
    # bool first: isinstance(True, int) is true, and a flag is not a count.
    if isinstance(weeks, bool) or not isinstance(weeks, int) or not 1 <= weeks <= 52:
        problems.append("policy.roadmap.pace.trailingWeeks=%s is not a whole number of weeks "
                        "from 1 to 52" % _shown(weeks))
    tolerance = pace.get("tolerance", 0.1)
    if (isinstance(tolerance, bool) or not isinstance(tolerance, (int, float))
            or not 0 <= tolerance < 1):
        problems.append("policy.roadmap.pace.tolerance=%s is not a number from 0 up to, "
                        "not including, 1" % _shown(tolerance))
    return problems


@dataclass
class Policy:
    data: dict

    def section(self, name: str) -> dict:
        value = self.data.get(name)
        return value if isinstance(value, dict) else {}

    def get(self, path: str, default=None):
        """Dotted lookup: ``policy.get("git.policy")``."""
        cursor = self.data
        for part in path.split("."):
            if not isinstance(cursor, dict) or part not in cursor:
                return default
            cursor = cursor[part]
        return cursor

    # -- convenience accessors used across ceremonies -----------------------

    @property
    def git_policy(self) -> str:
        return str(self.get("git.policy", "explicit-path-commit"))

    @property
    def may_stage(self) -> bool:
        return self.git_policy in ("explicit-path-stage", "explicit-path-commit", "push")

    @property
    def may_commit(self) -> bool:
        return self.git_policy in ("explicit-path-commit", "push")

    @property
    def may_push(self) -> bool:
        return self.git_policy == "push"

    @property
    def dispatch_buffer(self) -> int:
        try:
            return max(0, int(self.get("roadmap.dispatchBuffer", 5)))
        except (TypeError, ValueError):
            return 5

    @property
    def lesson_prefix(self) -> str:
        """The project's lesson identifier prefix, or the default when it is unusable."""
        prefix = self.get("lessons.idPrefix", "SRL")
        return prefix if not lessons_problems({"idPrefix": prefix}) else "SRL"

    @property
    def hierarchy(self) -> list[str]:
        value = self.get("roadmap.hierarchy", [])
        return [str(v) for v in value] if isinstance(value, list) else []

    def validate(self) -> list[str]:
        problems = []
        if self.git_policy not in GIT_POLICIES:
            problems.append("policy.git.policy=%r is not one of %s"
                            % (self.git_policy, ", ".join(GIT_POLICIES)))
        stale = self.get("git.staleLock", "report")
        if stale not in ("report", "prompt"):
            problems.append(
                "policy.git.staleLock=%r is not allowed; automatic lock-file deletion is "
                "never prescribed (use 'report' or 'prompt')" % (stale,))
        deletion = self.get("sweep.deletionPolicy", "quarantine")
        if deletion not in ("quarantine", "permanent"):
            problems.append("policy.sweep.deletionPolicy=%r is not one of quarantine, permanent"
                            % (deletion,))
        storage = self.get("roadmap.specStorage", "inline")
        if storage not in ("inline", "files", "external"):
            problems.append("policy.roadmap.specStorage=%r is not one of inline, files, external"
                            % (storage,))
        problems.extend(ledger_mapping_problems(self.get("terminalLedger.fieldMappings", {})))
        problems.extend(lessons_problems(self.get("lessons", {})))
        problems.extend(deadline_problems(self.get("roadmap.deadlines", {})))
        problems.extend(pace_problems(self.get("roadmap.pace", {})))
        return problems


def audit(raw) -> list[tuple[str, str]]:
    """``(key, problem)`` for every wrong-typed value in a project's own policy block
    and every problem :meth:`Policy.validate` finds — the checks ``policy-set``
    applies before a write, applied to whatever is on disk, however it got there.

    A hand-edited value of the wrong shape is stored and then ignored; without this,
    only a value written through ``policy-set`` was ever checked. Deadline problems
    are left to the ``deadlines:`` line, which already reports each one.
    Undocumented keys are not reported here: they are inert, not wrong.
    """
    if not isinstance(raw, dict):
        return [("policy", "the policy block is %s, not a mapping" % value_kind(raw)[1])]
    found: list[tuple[str, str]] = []

    def walk(node: dict, prefix: str) -> None:
        for key, value in node.items():
            path = "%s.%s" % (prefix, key) if prefix else str(key)
            if path in OPEN_MAPPINGS:
                continue
            default = documented_default(path)
            if default is _MISSING:
                continue
            if isinstance(default, dict) and default and isinstance(value, dict):
                walk(value, path)
                continue
            problem = type_problem(path, value)
            if problem:
                found.append((path, problem))

    walk(raw, "")
    if not found:
        for problem in load(raw).validate():
            if not problem.startswith("policy.roadmap.deadlines"):
                found.append((problem.split("=", 1)[0].split(" ", 1)[0], problem))
    return found


def load(raw: dict | None) -> Policy:
    """Merge a project's ``policy`` block over the documented defaults."""
    return Policy(_deep_merge(DEFAULTS, raw or {}))
