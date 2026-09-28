"""Read-only snapshot register (items 23, 31).

A snapshot is a timestamped JSON capture of another register. It supports
offline, read-only reporting; it is *always* labelled with when it was taken and
flagged stale once it is older than the configured window, so no report can
silently present cached data as live.

A connector-backed register reaches the plugin only through a snapshot, and the
host builds it. :func:`from_rows` is that builder (``snapshot --import``): the rows
the host's connector read, keyed by the register's own column names, become
canonical items through the project's field and status mappings, and a subitem —
a row that names a parent — is kept out of the work list. A subitem is a part of
its parent card (a decision, a checklist line), never a card of its own, and a
snapshot that flattened one into the list could name it the head of the belt.
"""
from __future__ import annotations

import datetime as _dt
import json
from dataclasses import dataclass, field

from .. import textio
from . import base, mapping as mapping_mod
from .csv_provider import row_to_item

SNAPSHOT_VERSION = 1

#: Column names a subitem's parent reference is recognized under, beside the
#: project's own ``--parent-column``.
PARENT_ALIASES = ("parent", "parent item", "parent_item", "parent id", "parent_id",
                  "parentid", "parent item id", "parent_item_id")


class SnapshotWorkRegister(base.WorkRegisterProvider):
    name = "snapshot"

    def __init__(self, *, source: str, mapping=None, stale_after_hours: float = 24.0,
                 origin: str = "") -> None:
        super().__init__(source=source, mapping=mapping or mapping_mod.Mapping(),
                         read_only=True)
        self.stale_after_hours = stale_after_hours
        self.origin = origin

    @property
    def capabilities(self) -> frozenset[str]:
        return frozenset({base.LIST_ACTIVE, base.READ_SEQUENCE, base.READ_STATUS,
                          base.READ_PREREQUISITES, base.READ_EFFORT, base.NEXT_ELIGIBLE})

    def snapshot(self) -> base.Snapshot:
        text = textio.read_text(self.source)
        if text is None:
            raise FileNotFoundError("snapshot not found: %s" % self.source)
        payload = json.loads(text)
        taken_at = str(payload.get("takenAt") or "")
        items = []
        for blob in payload.get("items", []):
            if not isinstance(blob, dict) or not blob.get("id"):
                continue
            if _parent_of(blob):
                continue            # a subitem is part of its parent, never a card
            known = {f: blob.get(f) for f in base.WorkItem.__dataclass_fields__
                     if f in blob}
            known.setdefault("id", blob["id"])
            known["prerequisites"] = list(known.get("prerequisites") or [])
            known["extra"] = dict(known.get("extra") or {})
            items.append(base.WorkItem(**known))
        stale, reason = self._staleness(taken_at)
        return base.Snapshot(
            items=items, provider=self.name,
            source=self.origin or str(payload.get("source") or self.source),
            taken_at=taken_at or "unknown",
            fields=list(payload.get("fields") or []),
            stale=stale, stale_reason=reason,
        )

    def _staleness(self, taken_at: str) -> tuple[bool, str]:
        if not taken_at:
            return True, "snapshot carries no takenAt timestamp"
        try:
            when = _dt.datetime.strptime(taken_at, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=_dt.timezone.utc)
        except ValueError:
            return True, "snapshot timestamp %r is not parseable" % taken_at
        age = (_dt.datetime.now(_dt.timezone.utc) - when).total_seconds() / 3600.0
        if age > self.stale_after_hours:
            return True, "snapshot is %.1fh old (stale after %.1fh)" % (age, self.stale_after_hours)
        return False, ""


def _parent_of(blob: dict) -> str:
    """The parent a snapshot item names, from its own ``parent`` key or the one its
    ``extra`` carried through from the register."""
    extra = blob.get("extra") if isinstance(blob.get("extra"), dict) else {}
    if blob.get("parent") not in (None, "", [], {}):
        return str(blob["parent"])
    for key, value in extra.items():
        if str(key).strip().lower() in PARENT_ALIASES and value not in (None, "", [], {}):
            return str(value)
    return ""


@dataclass
class ImportReport:
    """What ``snapshot --import`` did with the rows it was given."""

    rows: int = 0
    items: int = 0
    parent_column: str = ""
    subitems: list = field(default_factory=list)       # {"id", "title", "parent"}
    without_id: int = 0
    unknown_status: list = field(default_factory=list)  # {"id", "status"}
    unmapped_fields: list = field(default_factory=list)  # canonical fields no column fed

    def as_dict(self) -> dict:
        return {"rows": self.rows, "items": self.items, "parentColumn": self.parent_column,
                "subitemsExcluded": list(self.subitems), "withoutId": self.without_id,
                "unknownStatus": list(self.unknown_status),
                "unmappedFields": list(self.unmapped_fields)}


def _cell(value) -> str:
    """A connector value as the text a row-based register would hold."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return ", ".join(_cell(v) for v in value if _cell(v))
    if isinstance(value, dict):
        for key in ("text", "name", "id", "value"):
            if value.get(key) not in (None, ""):
                return _cell(value[key])
        return ""
    return str(value)


def parse_rows(text: str) -> tuple[list[dict], str]:
    """``(rows, takenAt)`` from what the host wrote: a list of row objects, or an
    object carrying ``rows`` and optionally the ``takenAt`` of the read."""
    payload = json.loads(text)
    taken_at = ""
    if isinstance(payload, dict):
        taken_at = str(payload.get("takenAt") or "")
        payload = payload.get("rows")
    if not isinstance(payload, list) or not all(isinstance(r, dict) for r in payload):
        raise ValueError("the rows file must hold a JSON list of row objects, or an object "
                         "whose `rows` is one")
    return payload, taken_at


def from_rows(rows: list[dict], mapping, *, source: str, taken_at: str,
              parent_column: str = "") -> tuple[base.Snapshot, ImportReport]:
    """Build a canonical snapshot from rows a host connector read.

    Each row is keyed by the register's own column names; the project's field and
    status mappings turn it into a canonical item exactly as a local CSV row would
    be. A row whose parent column holds a value is a subitem: it is left out of the
    items and listed in the report. A row with no identifier is skipped and counted.
    Duplicate identifiers are refused, because the head of the belt would be
    ambiguous.
    """
    report = ImportReport(rows=len(rows))
    headers: list[str] = []
    for row in rows:
        for key in row:
            if str(key) not in headers:
                headers.append(str(key))
    wanted = [c for c in ([parent_column] if parent_column else []) + list(PARENT_ALIASES)]
    lowered = {h.strip().lower(): h for h in headers}
    parent_header = next((lowered[c.strip().lower()] for c in wanted
                          if c.strip().lower() in lowered), "")
    report.parent_column = parent_header
    index = mapping.fields.resolve_index(headers)
    report.unmapped_fields = [f for f in ("id", "title", "sequence", "status",
                                          "written_status", "prerequisites")
                              if f not in index]
    if "id" not in index:
        raise ValueError(
            "no column in the rows maps to the item identifier (tried %r and its aliases); "
            "name the column in policy.workRegister.fieldMappings.id"
            % mapping.fields.column_for("id"))

    items: list[base.WorkItem] = []
    seen: dict[str, int] = {}
    for raw in rows:
        row = {str(k): _cell(v) for k, v in raw.items()}
        item = row_to_item(mapping, headers, index, row)
        parent = row.get(parent_header, "").strip() if parent_header else ""
        if parent:
            report.subitems.append({"id": item.id, "title": item.title, "parent": parent})
            continue
        if not item.id:
            report.without_id += 1
            continue
        seen[item.id] = seen.get(item.id, 0) + 1
        if item.status == base.UNKNOWN:
            report.unknown_status.append({"id": item.id, "status": item.raw_status})
        items.append(item)
    duplicates = sorted(i for i, n in seen.items() if n > 1)
    if duplicates:
        raise ValueError("identifier(s) %s appear on more than one row; a snapshot with two "
                         "items under one id cannot say which is the head of the belt"
                         % ", ".join(duplicates))
    report.items = len(items)
    snap = base.Snapshot(items=items, provider="snapshot", source=source,
                         taken_at=taken_at, fields=sorted(index))
    return snap, report


def parse_taken_at(value: str) -> str:
    """``value`` as the snapshot's ``YYYY-MM-DDTHH:MM:SSZ``, from any ISO 8601 time
    with an offset (or a trailing ``Z``); a time without one is refused, because a
    snapshot's age is computed in UTC."""
    text = (value or "").strip()
    try:
        when = _dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("takenAt %r is not an ISO 8601 time" % value)
    if when.tzinfo is None:
        raise ValueError("takenAt %r carries no UTC offset; add Z or +hh:mm" % value)
    return when.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_snapshot(path: str, snap: base.Snapshot) -> None:
    """Persist a snapshot for offline use."""
    payload = {
        "snapshotVersion": SNAPSHOT_VERSION,
        "takenAt": snap.taken_at,
        "provider": snap.provider,
        "source": snap.source,
        "fields": list(snap.fields),
        "items": [item.as_dict() for item in snap.items],
    }
    textio.write_if_changed(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
