"""Local Markdown work register (item 23).

Two shapes are supported:

* **table mode** — a pipe table whose header row resolves an ``id`` column
  through the field mapping. Fully readable and writable (a status write edits
  that one cell; every other byte of the document is preserved).
* **heading mode** — items as headings (``#### ITEM-1 — Title``) under an
  "Active" section. Read-only: there is no unambiguous cell to write a status
  into, and the provider says so through capability negotiation rather than
  guessing.
"""
from __future__ import annotations

import re

from .. import textio
from . import base, mapping as mapping_mod

_TABLE_ROW_RE = re.compile(r"^\s*\|(?P<body>.+)\|\s*$")
_SEPARATOR_RE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
_HEADING_RE = re.compile(r"^(#{2,6})\s+(?P<heading>.+?)\s*$", re.MULTILINE)
_ITEM_HEADING_RE = re.compile(
    r"^\[?(?P<id>[A-Za-z][A-Za-z0-9]*(?:[-_.][A-Za-z0-9]+)+)\]?\s*[—–\-:]\s*(?P<title>.+)$"
)


def _cells(line: str) -> list[str]:
    match = _TABLE_ROW_RE.match(line)
    if not match:
        return []
    return [c.strip() for c in match.group("body").split("|")]


class MarkdownWorkRegister(base.WorkRegisterProvider):
    name = "markdown"

    def __init__(self, *, source: str, mapping=None, read_only: bool = False,
                 active_section: str = "") -> None:
        super().__init__(source=source, mapping=mapping or mapping_mod.Mapping(),
                         read_only=read_only)
        self.active_section = active_section
        self._mode = ""

    @property
    def capabilities(self) -> frozenset[str]:
        reads = {base.LIST_ACTIVE, base.READ_SEQUENCE, base.READ_STATUS,
                 base.READ_PREREQUISITES, base.READ_EFFORT, base.NEXT_ELIGIBLE}
        if self._detect_mode() == "table":
            return frozenset(reads | {base.WRITE_STATUS, base.STORE_SPEC_LINK,
                                      base.RECORD_COMPLETION})
        return frozenset(reads)

    # -- parsing -------------------------------------------------------------

    def _text(self) -> str:
        text = textio.read_text(self.source)
        if text is None:
            raise FileNotFoundError("work register not found: %s" % self.source)
        return text

    def _detect_mode(self) -> str:
        if self._mode:
            return self._mode
        try:
            self._mode = "table" if self._find_table(self._text())[0] is not None else "headings"
        except OSError:
            self._mode = "headings"
        return self._mode

    def _find_table(self, text: str):
        """Return ``(start_line, headers, index, rows)`` for the first table whose
        header resolves an id column, or ``(None, [], {}, [])``."""
        lines = text.splitlines()
        for position, line in enumerate(lines):
            headers = _cells(line)
            if len(headers) < 2:
                continue
            if position + 1 >= len(lines) or not _SEPARATOR_RE.match(lines[position + 1]):
                continue
            index = self.mapping.fields.resolve_index(headers)
            if "id" not in index:
                continue
            rows = []
            for row_position in range(position + 2, len(lines)):
                cells = _cells(lines[row_position])
                if not cells:
                    break
                rows.append((row_position, cells))
            return position, headers, index, rows
        return None, [], {}, []

    def snapshot(self) -> base.Snapshot:
        text = self._text()
        start, headers, index, rows = self._find_table(text)
        if start is not None:
            self._mode = "table"
            items = [self._row_item(headers, index, cells) for _pos, cells in rows]
            fields = sorted(index)
        else:
            self._mode = "headings"
            items = self._heading_items(text)
            fields = ["id", "title", "sequence"]
        return base.Snapshot(items=[i for i in items if i.id], provider=self.name,
                             source=self.source, taken_at=base.utc_now(), fields=fields)

    def _row_item(self, headers, index, cells) -> base.WorkItem:
        def value(name: str) -> str:
            position = index.get(name)
            if position is None or position >= len(cells):
                return ""
            return cells[position].strip().strip("`")

        raw_status = value("status")
        sequence_raw = value("sequence")
        try:
            sequence = int(float(sequence_raw)) if sequence_raw else None
        except ValueError:
            sequence = None
        return base.WorkItem(
            id=value("id"),
            title=value("title"),
            sequence=sequence,
            status=self.mapping.statuses.to_canonical(raw_status),
            raw_status=raw_status,
            written_status=self.mapping.statuses.written_to_canonical(value("written_status")),
            raw_written_status=value("written_status"),
            prerequisites=[p.strip() for p in
                           value("prerequisites").replace(";", ",").split(",") if p.strip()],
            effort=value("effort"),
            lane=value("lane"),
            group=value("group"),
            spec_link=value("spec_link"),
            branch=value("branch"),
            started=value("started"),
            completed=value("completed"),
            evidence=value("evidence"),
            description=value("description"),
            notes=value("notes"),
            revision=textio.sha256_bytes("|".join(cells).encode("utf-8")),
        )

    def _heading_items(self, text: str) -> list[base.WorkItem]:
        section = text
        if self.active_section:
            pattern = re.compile(r"^#{2,3}\s+%s\s*$" % re.escape(self.active_section),
                                 re.MULTILINE)
            match = pattern.search(text)
            if match:
                rest = text[match.end():]
                following = re.search(r"^##\s+", rest, re.MULTILINE)
                section = rest[: following.start()] if following else rest
        items = []
        for order, match in enumerate(_HEADING_RE.finditer(section), start=1):
            parsed = _ITEM_HEADING_RE.match(match.group("heading").strip())
            if not parsed:
                continue
            items.append(base.WorkItem(
                id=parsed.group("id"),
                title=parsed.group("title").strip(),
                sequence=order,
                status=base.UNKNOWN,
                revision=textio.sha256_bytes(match.group("heading").encode("utf-8")),
            ))
        return items

    # -- mutations -----------------------------------------------------------

    def _write_cell(self, item_id: str, field_name: str, value: str, revision: str) -> base.WorkItem:
        if self.read_only:
            raise base.CapabilityError(
                "work register %s is registered read-only" % self.source)
        text = self._text()
        lines = text.splitlines(keepends=True)
        start, headers, index, rows = self._find_table(text)
        if start is None:
            raise base.CapabilityError(
                "%s has no work-item table; heading-mode registers are read-only" % self.source)
        position = index.get(field_name)
        if position is None:
            raise base.CapabilityError(
                "%s has no %r column; configure policy.workRegister.fieldMappings.%s"
                % (self.source, field_name, field_name))
        for row_position, cells in rows:
            if cells[index["id"]].strip().strip("`") != item_id:
                continue
            current = self._row_item(headers, index, cells)
            self.check_revision(current, revision)
            if position < len(cells) and cells[position].strip() == value:
                return current                      # idempotent
            updated = list(cells)
            while len(updated) <= position:
                updated.append("")
            updated[position] = value
            ending = "\r\n" if lines[row_position].endswith("\r\n") else "\n"
            lines[row_position] = "| " + " | ".join(updated) + " |" + ending
            with open(self.source, "w", encoding="utf-8", newline="") as handle:
                handle.write("".join(lines))
            return self.get(item_id)
        raise KeyError("item %r is not in %s" % (item_id, self.source))

    def set_status(self, item_id: str, status: str, *, revision: str = "",
                   raw: str = "") -> base.WorkItem:
        self.require(base.WRITE_STATUS)
        return self._write_cell(item_id, "status",
                                raw or self.mapping.statuses.to_project(status), revision)

    def store_spec_link(self, item_id: str, link: str, *, revision: str = "") -> base.WorkItem:
        self.require(base.STORE_SPEC_LINK)
        return self._write_cell(item_id, "spec_link", link, revision)

    def record_completion(self, item_id: str, *, completed: str = "", evidence: str = "",
                          revision: str = "") -> base.WorkItem:
        self.require(base.RECORD_COMPLETION)
        item = self._write_cell(item_id, "status",
                                self.mapping.statuses.to_project(base.COMPLETED), revision)
        if completed:
            item = self._write_cell(item_id, "completed", completed, "")
        if evidence:
            item = self._write_cell(item_id, "evidence", evidence, "")
        return item
