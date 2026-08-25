"""Configurable field and status mappings (items 26, 27).

A project maps its own column names and its own status vocabulary onto the
plugin's canonical set. Nothing in the plugin requires the literal words
``Queued``, ``In Flight``, ``Blocked``, ``Completed``, ``Stub``, or ``Full Spec``
— those are only the *defaults* used when a project declares no mapping.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import base

#: Canonical field -> the default column/property name a register is read with.
DEFAULT_FIELDS = {
    "id": "id",
    "title": "title",
    "sequence": "sequence",
    "status": "status",
    "written_status": "written_status",
    "prerequisites": "prerequisites",
    "effort": "effort",
    "lane": "lane",
    "group": "group",
    "spec_link": "spec_link",
    "branch": "branch",
    "started": "started",
    "completed": "completed",
    "evidence": "evidence",
    "description": "description",
    "notes": "notes",
}

#: Column names the plugin also recognizes without configuration, so an existing
#: catalog keeps working. These are *aliases*, not requirements.
DEFAULT_ALIASES = {
    "id": ["sprint code", "code", "key", "item", "item id", "ticket", "issue"],
    "title": ["name", "summary", "subject"],
    "sequence": ["seq", "order", "rank", "position", "priority"],
    "status": ["implementation status", "state", "workflow status"],
    "written_status": ["written status", "spec status", "specification status"],
    "prerequisites": ["dependencies", "depends on", "blocked by", "prereqs"],
    "effort": ["loe", "size", "estimate", "story points", "points"],
    "lane": ["stage", "swimlane", "track"],
    "group": ["phase", "epic", "milestone", "category"],
    "spec_link": ["spec", "spec link", "specification", "close-out file", "link"],
    "branch": ["branch name"],
    "started": ["date started", "start date", "started on"],
    "completed": ["date completed", "end date", "completed on", "done date"],
    "evidence": ["close-out", "close out file", "artifact", "proof"],
    "description": ["desc", "details"],
    "notes": ["note", "comment", "comments"],
}

#: Canonical status -> the project spellings recognized by default.
DEFAULT_STATUS_VOCABULARY = {
    base.QUEUED: ["queued", "todo", "to do", "backlog", "not started", "ready", "open"],
    base.IN_FLIGHT: ["in flight", "in-flight", "in progress", "doing", "active", "wip",
                     "started"],
    base.BLOCKED: ["blocked", "on hold", "waiting", "stuck"],
    base.COMPLETED: ["completed", "complete", "done", "closed", "shipped", "finished"],
    base.DISSOLVED: ["dissolved", "cancelled", "canceled", "dropped", "won't do", "wontfix"],
    base.SUPERSEDED: ["superseded", "replaced", "obsolete"],
}

DEFAULT_WRITTEN_VOCABULARY = {
    base.STUB: ["stub", "", "placeholder", "draft", "outline"],
    base.FULL_SPEC: ["full spec", "full-spec", "spec", "specified", "dispatch-ready", "ready"],
}


def _norm(value) -> str:
    return str(value or "").strip().lower()


@dataclass
class FieldMapping:
    """Canonical field name -> the project's own column name."""

    fields: dict = field(default_factory=lambda: dict(DEFAULT_FIELDS))
    aliases: dict = field(default_factory=lambda: {k: list(v) for k, v in DEFAULT_ALIASES.items()})

    def column_for(self, canonical: str) -> str:
        return self.fields.get(canonical, DEFAULT_FIELDS.get(canonical, canonical))

    def resolve_index(self, headers: list[str]) -> dict[str, int]:
        """Map canonical field -> column index, using the configured name first and
        the recognized aliases second. Unmatched fields are simply absent, which is
        how a provider reports which fields it can serve."""
        lowered = {_norm(h): i for i, h in enumerate(headers) if str(h or "").strip()}
        index: dict[str, int] = {}
        for canonical in DEFAULT_FIELDS:
            configured = _norm(self.column_for(canonical))
            if configured in lowered:
                index[canonical] = lowered[configured]
                continue
            if _norm(canonical) in lowered:
                index[canonical] = lowered[_norm(canonical)]
                continue
            for alias in self.aliases.get(canonical, []):
                if _norm(alias) in lowered:
                    index[canonical] = lowered[_norm(alias)]
                    break
        return index


@dataclass
class StatusMapping:
    """Canonical status <-> the project's own vocabulary."""

    vocabulary: dict = field(
        default_factory=lambda: {k: list(v) for k, v in DEFAULT_STATUS_VOCABULARY.items()})
    written_vocabulary: dict = field(
        default_factory=lambda: {k: list(v) for k, v in DEFAULT_WRITTEN_VOCABULARY.items()})

    def to_canonical(self, raw) -> str:
        text = _norm(raw)
        if not text:
            return base.UNKNOWN
        for canonical, spellings in self.vocabulary.items():
            for spelling in spellings:
                spelling = _norm(spelling)
                if not spelling:
                    continue
                if text == spelling or text.startswith(spelling + " "):
                    return canonical
        return base.UNKNOWN

    def to_project(self, canonical: str) -> str:
        """The project's preferred spelling for a canonical status: the first entry
        in its vocabulary list, so a write speaks the project's language."""
        spellings = [s for s in self.vocabulary.get(canonical, []) if str(s).strip()]
        return spellings[0] if spellings else canonical

    def written_to_canonical(self, raw) -> str:
        text = _norm(raw)
        for canonical, spellings in self.written_vocabulary.items():
            if text in {_norm(s) for s in spellings}:
                return canonical
        return base.STUB if not text else ""

    def written_to_project(self, canonical: str) -> str:
        spellings = [s for s in self.written_vocabulary.get(canonical, []) if str(s).strip()]
        return spellings[0] if spellings else canonical


@dataclass
class Mapping:
    fields: FieldMapping = field(default_factory=FieldMapping)
    statuses: StatusMapping = field(default_factory=StatusMapping)

    @classmethod
    def from_policy(cls, work_register_policy: dict | None) -> "Mapping":
        config = work_register_policy or {}
        fields = FieldMapping()
        configured_fields = config.get("fieldMappings")
        if isinstance(configured_fields, dict):
            fields.fields = dict(DEFAULT_FIELDS)
            fields.fields.update({k: v for k, v in configured_fields.items() if isinstance(v, str)})
        statuses = StatusMapping()
        configured_statuses = config.get("statusMappings")
        if isinstance(configured_statuses, dict):
            vocabulary = {k: list(v) for k, v in DEFAULT_STATUS_VOCABULARY.items()}
            for canonical, spellings in configured_statuses.items():
                if canonical == "written":
                    continue
                if isinstance(spellings, str):
                    spellings = [spellings]
                if isinstance(spellings, list):
                    # The project's spellings come FIRST so `to_project` returns them.
                    vocabulary[canonical] = [str(s) for s in spellings] + \
                        [s for s in DEFAULT_STATUS_VOCABULARY.get(canonical, [])
                         if str(s) not in {str(x) for x in spellings}]
            statuses.vocabulary = vocabulary
            written = configured_statuses.get("written")
            if isinstance(written, dict):
                wv = {k: list(v) for k, v in DEFAULT_WRITTEN_VOCABULARY.items()}
                for canonical, spellings in written.items():
                    if isinstance(spellings, str):
                        spellings = [spellings]
                    if isinstance(spellings, list):
                        wv[canonical] = [str(s) for s in spellings] + \
                            [s for s in DEFAULT_WRITTEN_VOCABULARY.get(canonical, [])
                             if str(s) not in {str(x) for x in spellings}]
                statuses.written_vocabulary = wv
        return cls(fields=fields, statuses=statuses)
