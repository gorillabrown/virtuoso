"""Local CSV work register (item 23).

Reads and writes a delimited file the project already owns. Column names come
from the configured field mapping (item 26), unmapped columns are preserved
verbatim on write, and the file's own line ending is preserved.
"""
from __future__ import annotations

import csv
import io
import os

from .. import textio
from . import base, mapping as mapping_mod


class CsvWorkRegister(base.WorkRegisterProvider):
    name = "csv"

    def __init__(self, *, source: str, mapping=None, read_only: bool = False) -> None:
        super().__init__(source=source, mapping=mapping or mapping_mod.Mapping(),
                         read_only=read_only)

    @property
    def capabilities(self) -> frozenset[str]:
        return frozenset(base.ALL_CAPABILITIES)

    # -- io ------------------------------------------------------------------

    def _read_rows(self) -> tuple[list[str], list[dict]]:
        text = textio.read_text(self.source)
        if text is None:
            raise FileNotFoundError("work register not found: %s" % self.source)
        reader = csv.DictReader(io.StringIO(text))
        headers = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
        return headers, rows

    def _line_terminator(self) -> str:
        return textio.detect_eol(self.source) or "\n"

    def _write_rows(self, headers: list[str], rows: list[dict]) -> None:
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=headers, lineterminator="\n",
                                extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({h: row.get(h, "") for h in headers})
        content = buffer.getvalue()
        eol = self._line_terminator()
        os.makedirs(os.path.dirname(self.source) or ".", exist_ok=True)
        with open(self.source, "w", encoding="utf-8", newline=eol) as handle:
            handle.write(content)

    # -- reads ---------------------------------------------------------------

    def snapshot(self) -> base.Snapshot:
        headers, rows = self._read_rows()
        index = self.mapping.fields.resolve_index(headers)
        items = [self._to_item(headers, index, row) for row in rows]
        items = [i for i in items if i.id]
        return base.Snapshot(
            items=items,
            provider=self.name,
            source=self.source,
            taken_at=base.utc_now(),
            fields=sorted(index),
        )

    def _to_item(self, headers: list[str], index: dict, row: dict) -> base.WorkItem:
        def value(field_name: str) -> str:
            position = index.get(field_name)
            if position is None or position >= len(headers):
                return ""
            return str(row.get(headers[position], "") or "").strip()

        raw_status = value("status")
        raw_written = value("written_status")
        sequence_raw = value("sequence")
        try:
            sequence = int(float(sequence_raw)) if sequence_raw else None
        except ValueError:
            sequence = None
        prerequisites = [p.strip() for p in
                         value("prerequisites").replace(";", ",").split(",") if p.strip()]
        known = {headers[i] for i in index.values() if i < len(headers)}
        return base.WorkItem(
            id=value("id"),
            title=value("title"),
            sequence=sequence,
            status=self.mapping.statuses.to_canonical(raw_status),
            raw_status=raw_status,
            written_status=self.mapping.statuses.written_to_canonical(raw_written),
            raw_written_status=raw_written,
            prerequisites=prerequisites,
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
            revision=_row_revision(row),
            extra={k: v for k, v in row.items() if k not in known},
        )

    # -- mutations -----------------------------------------------------------

    def _mutate(self, item_id: str, revision: str, apply_row) -> base.WorkItem:
        if self.read_only:
            raise base.CapabilityError(
                "work register %s is registered read-only; register it as writable to mutate"
                % self.source)
        headers, rows = self._read_rows()
        index = self.mapping.fields.resolve_index(headers)
        id_position = index.get("id")
        if id_position is None or id_position >= len(headers):
            raise base.CapabilityError(
                "work register %s has no identifiable id column; configure "
                "policy.workRegister.fieldMappings.id" % self.source)
        id_column = headers[id_position]

        target = None
        for row in rows:
            if str(row.get(id_column, "") or "").strip() == item_id:
                target = row
                break
        if target is None:
            raise KeyError("item %r is not in %s" % (item_id, self.source))

        current = self._to_item(headers, index, target)
        self.check_revision(current, revision)

        changed = apply_row(target, headers, index, current)
        if changed:
            self._write_rows(headers, rows)
        headers, rows = self._read_rows()
        index = self.mapping.fields.resolve_index(headers)
        for row in rows:
            if str(row.get(id_column, "") or "").strip() == item_id:
                return self._to_item(headers, index, row)
        raise KeyError("item %r vanished during mutation of %s" % (item_id, self.source))

    def set_status(self, item_id: str, status: str, *, revision: str = "",
                   raw: str = "") -> base.WorkItem:
        self.require(base.WRITE_STATUS)
        spelling = raw or self.mapping.statuses.to_project(status)

        def apply_row(row, headers, index, current):
            position = index.get("status")
            if position is None:
                raise base.CapabilityError(
                    "work register %s has no status column; configure "
                    "policy.workRegister.fieldMappings.status" % self.source)
            column = headers[position]
            if str(row.get(column, "") or "").strip() == spelling:
                return False        # idempotent (item 33)
            row[column] = spelling
            return True

        return self._mutate(item_id, revision, apply_row)

    def store_spec_link(self, item_id: str, link: str, *, revision: str = "") -> base.WorkItem:
        self.require(base.STORE_SPEC_LINK)

        def apply_row(row, headers, index, current):
            position = index.get("spec_link")
            if position is None:
                raise base.CapabilityError(
                    "work register %s has no specification-link column; configure "
                    "policy.workRegister.fieldMappings.spec_link" % self.source)
            column = headers[position]
            if str(row.get(column, "") or "").strip() == link:
                return False
            row[column] = link
            return True

        return self._mutate(item_id, revision, apply_row)

    def record_completion(self, item_id: str, *, completed: str = "", evidence: str = "",
                          revision: str = "") -> base.WorkItem:
        self.require(base.RECORD_COMPLETION)
        spelling = self.mapping.statuses.to_project(base.COMPLETED)

        def apply_row(row, headers, index, current):
            changed = False
            for field_name, new_value in (("status", spelling), ("completed", completed),
                                          ("evidence", evidence)):
                if not new_value:
                    continue
                position = index.get(field_name)
                if position is None:
                    continue
                column = headers[position]
                if str(row.get(column, "") or "").strip() != new_value:
                    row[column] = new_value
                    changed = True
            return changed

        return self._mutate(item_id, revision, apply_row)


def _row_revision(row: dict) -> str:
    payload = "\n".join("%s=%s" % (k, row.get(k, "")) for k in sorted(row))
    return textio.sha256_bytes(payload.encode("utf-8"))
