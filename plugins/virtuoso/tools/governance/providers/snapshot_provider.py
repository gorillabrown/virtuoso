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
import re
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
            blob = _renamed(blob)
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
            fields=[mapping_mod.RENAMED_FIELDS.get(f, f) for f in payload.get("fields") or []],
            stale=stale, stale_reason=reason,
            headers={str(k): str(v) for k, v in
                     _renamed(payload.get("headers") or {}).items()},
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


def _renamed(blob: dict) -> dict:
    """A snapshot written before a field was renamed, read under the new name. The file
    is never rewritten; the next import writes the new name."""
    out = dict(blob)
    for old, new in mapping_mod.RENAMED_FIELDS.items():
        if old in out and new not in out:
            out[new] = out.pop(old)
    return out


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
    #: Column drift, for a raw page only: declared mappings the board has no column for
    #: ({"field", "column"}), and board columns nothing maps ({"id", "title"}).
    missing_columns: list = field(default_factory=list)
    unmapped_columns: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"rows": self.rows, "items": self.items, "parentColumn": self.parent_column,
                "subitemsExcluded": list(self.subitems), "withoutId": self.without_id,
                "unknownStatus": list(self.unknown_status),
                "unmappedFields": list(self.unmapped_fields),
                "missingColumns": list(self.missing_columns),
                "unmappedColumns": list(self.unmapped_columns)}


#: A link a connector's Markdown read wraps around plain text: ``[a.md](http://a.md)``
#: (``.md`` is a top-level domain) or ``[url](url)``. A plain-text read has none.
_AUTOLINK = re.compile(r"\[([^\]]+)\]\((?:https?://)?\1\)")


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
    return _AUTOLINK.sub(r"\1", str(value))


#: Keys a row built from a raw page carries besides its columns.
PAGE_EXTRAS = ("providerId", "revision", "url")


def _raw_pages(payload) -> list[dict] | None:
    """The pages, when ``payload`` is a connector's raw items page (or a list of them):
    objects whose ``items`` entries carry ``column_values``."""
    def is_page(p):
        return (isinstance(p, dict) and isinstance(p.get("items"), list)
                and all(isinstance(i, dict) and "column_values" in i for i in p["items"]))

    pages = payload if isinstance(payload, list) else [payload]
    found = [is_page(p) for p in pages]
    if pages and all(found):
        return pages
    if any(found):
        raise ValueError("the file mixes raw items pages with other objects; import the "
                         "pages on their own")
    return None


def parse_rows(text: str) -> tuple[list[dict], str, bool]:
    """``(rows, takenAt, False)`` from what the host wrote: a list of row objects, or an
    object carrying ``rows`` and optionally the ``takenAt`` of the read. A connector's
    raw items page is recognized and returned as ``(pages, "", True)``; it becomes rows
    only with the board's columns (:func:`page_to_rows`)."""
    payload = json.loads(text)
    pages = _raw_pages(payload)
    if pages is not None:
        return pages, "", True
    taken_at = ""
    if isinstance(payload, dict):
        taken_at = str(payload.get("takenAt") or "")
        payload = payload.get("rows")
    if not isinstance(payload, list) or not all(isinstance(r, dict) for r in payload):
        raise ValueError("the rows file must hold a JSON list of row objects, or an object "
                         "whose `rows` is one")
    return payload, taken_at, False


def board_columns(payload) -> list[dict]:
    """The column list from a list of ``{id, title, …}``, or an object whose ``columns``
    or ``board.columns`` is that list (a ``get_board_info`` response)."""
    columns = payload
    if isinstance(payload, dict):
        columns = payload.get("columns")
        if columns is None and isinstance(payload.get("board"), dict):
            columns = payload["board"].get("columns")
    if not isinstance(columns, list) or not all(
            isinstance(c, dict) and c.get("id") and c.get("title") for c in columns):
        raise ValueError("the columns file must hold a list of {id, title} objects, or an "
                         "object whose `columns` or `board.columns` is one")
    return columns


def page_to_rows(pages: list[dict], columns, mapping,
                 declared: dict) -> tuple[list[dict], dict]:
    """``(rows, drift)`` from raw items pages and the board's column list.

    Each cell is keyed by its column's title, the item's ``name`` fills the title
    column and its ``group.title`` the group column, and ``providerId``, ``revision``
    (``updated_at``) and ``url`` ride along. A board column nothing maps is left out
    and named in ``drift["unmappedColumns"]``; a declared mapping no board column title
    matches is named in ``drift["missingColumns"]`` (``title`` and ``group`` come from
    the item itself, so they are never missing). A page set whose last page says
    ``has_more`` is a partial read, and refused.
    """
    if (pages[-1].get("pagination") or {}).get("has_more"):
        raise ValueError("the last page says pagination.has_more: true — this is a partial "
                         "read; fetch every page and import them together")
    columns = board_columns(columns)
    titles = {str(c["id"]): str(c["title"]) for c in columns}
    title_list = list(titles.values())
    mapped = {title_list[i] for i in mapping.fields.resolve_index(title_list).values()}
    reused = sorted({t for t in mapped if [x.lower() for x in title_list].count(t.lower()) > 1}
                    | {t for t in mapped if t in PAGE_EXTRAS})
    if reused:
        raise ValueError("board column title(s) %s are ambiguous (two columns, or a key the "
                         "import adds: %s); rename the column on the board"
                         % (", ".join(reused), ", ".join(PAGE_EXTRAS)))
    lowered = {t.strip().lower() for t in title_list}
    drift = {
        "missingColumns": [{"field": name, "column": column}
                           for name, column in (declared or {}).items()
                           if name not in ("title", "group")
                           and str(column).strip().lower() not in lowered],
        "unmappedColumns": [{"id": cid, "title": title} for cid, title in titles.items()
                            if cid != "name" and title not in mapped],
    }
    rows = []
    for page in pages:
        for entry in page["items"]:
            values = entry.get("column_values") or {}
            if isinstance(values, list):         # the GraphQL form: [{id, text, …}]
                values = {str(v.get("id")): v for v in values if isinstance(v, dict)}
            row = {titles[cid]: value for cid, value in values.items()
                   if titles.get(cid) in mapped}
            row[mapping.fields.column_for("title")] = entry.get("name", "")
            row[mapping.fields.column_for("group")] = (entry.get("group") or {}).get("title", "")
            row.update(zip(PAGE_EXTRAS, (entry.get("id", ""), entry.get("updated_at", ""),
                                         entry.get("url", ""))))
            rows.append(row)
    return rows, drift


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
                         taken_at=taken_at, fields=sorted(index),
                         headers=base.header_map(headers, index))
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
    if snap.headers:
        payload["headers"] = dict(snap.headers)
    textio.write_if_changed(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
