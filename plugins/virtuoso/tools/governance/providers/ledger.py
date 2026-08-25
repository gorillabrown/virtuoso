"""The append-only terminal ledger (items 24, 33, 43, 47, 48).

Terminal records are final. This module can only *append*. There is no update
path, no delete path, and no reorder path — a correction is a new record that
names the record it corrects, and both stay in the file forever.

Who may append is project policy (item 47): ``policy.terminalLedger.writers``
for ordinary records and ``correctionWriters`` for corrections.

Appends are idempotent (item 33): a record whose idempotency key already appears
in the ledger is a no-op, so re-running a close-out never duplicates history.
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
from dataclasses import dataclass, field

from .. import textio
from ..errors import GovernanceError
from . import base

FORMATS = ("markdown", "csv", "jsonl")

_MARKDOWN_HEADER = (
    "| Record | Item | Completed | Result | Evidence | Corrects |\n"
    "|--------|------|-----------|--------|----------|----------|"
)
_SEPARATOR_RE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")


class LedgerError(GovernanceError):
    code = "ledger-error"


@dataclass
class LedgerRecord:
    record_id: str
    item_id: str
    completed: str
    result: str
    evidence: str = ""
    corrects: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def idempotency_key(self) -> str:
        return "%s|%s|%s|%s" % (self.item_id, self.completed, self.result, self.corrects)

    def as_dict(self) -> dict:
        data = {
            "recordId": self.record_id,
            "itemId": self.item_id,
            "completed": self.completed,
            "result": self.result,
            "evidence": self.evidence,
            "corrects": self.corrects,
        }
        data.update(self.extra)
        return data


class TerminalLedger:
    def __init__(self, path: str, *, fmt: str = "markdown",
                 writers: list[str] | None = None,
                 correction_writers: list[str] | None = None) -> None:
        if fmt not in FORMATS:
            raise LedgerError("unknown terminal-ledger format %r (one of %s)"
                              % (fmt, ", ".join(FORMATS)))
        self.path = path
        self.format = fmt
        self.writers = list(writers or [])
        self.correction_writers = list(correction_writers or self.writers)

    # -- authorization -------------------------------------------------------

    def may_append(self, actor: str, *, correction: bool = False) -> bool:
        allowed = self.correction_writers if correction else self.writers
        return bool(allowed) and (actor in allowed or "*" in allowed)

    def _authorize(self, actor: str, correction: bool) -> None:
        if not self.may_append(actor, correction=correction):
            allowed = self.correction_writers if correction else self.writers
            raise LedgerError(
                "%r may not append %s to the terminal ledger (allowed: %s). Change "
                "policy.terminalLedger.%s to permit it."
                % (actor, "a correction" if correction else "a record",
                   ", ".join(allowed) or "nobody",
                   "correctionWriters" if correction else "writers"),
                detail={"actor": actor, "allowed": allowed})

    # -- reads ---------------------------------------------------------------

    def records(self) -> list[LedgerRecord]:
        text = textio.read_text(self.path)
        if text is None:
            return []
        if self.format == "jsonl":
            out = []
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except ValueError:
                    continue
                out.append(_from_payload(payload))
            return out
        if self.format == "csv":
            reader = csv.DictReader(io.StringIO(text))
            return [_from_payload(row) for row in reader]
        return self._markdown_records(text)

    def _markdown_records(self, text: str) -> list[LedgerRecord]:
        out: list[LedgerRecord] = []
        rows_started = False
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("|"):
                rows_started = False
                continue
            if _SEPARATOR_RE.match(line):
                rows_started = True
                continue
            if not rows_started:
                continue
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            while len(cells) < 6:
                cells.append("")
            out.append(LedgerRecord(record_id=cells[0], item_id=cells[1], completed=cells[2],
                                    result=cells[3], evidence=cells[4], corrects=cells[5]))
        return out

    def contains(self, record: LedgerRecord) -> bool:
        key = record.idempotency_key
        return any(r.idempotency_key == key for r in self.records())

    def next_record_id(self, prefix: str = "TR") -> str:
        highest = 0
        pattern = re.compile(r"^%s-(\d+)$" % re.escape(prefix))
        for record in self.records():
            match = pattern.match(record.record_id.strip())
            if match:
                highest = max(highest, int(match.group(1)))
        return "%s-%03d" % (prefix, highest + 1)

    # -- append (the only mutation) ------------------------------------------

    def append(self, record: LedgerRecord, *, actor: str, correction: bool = False) -> bool:
        """Append ``record``. Returns False when an identical record already exists
        (idempotent). Never rewrites or reorders existing history."""
        self._authorize(actor, correction)
        if correction and not record.corrects:
            raise LedgerError("a correction must name the record it corrects")
        if record.corrects and not correction:
            raise LedgerError("a record naming `corrects` must be appended as a correction")
        if self.contains(record):
            return False

        existing = textio.read_text(self.path)
        if self.format == "jsonl":
            line = json.dumps(record.as_dict(), ensure_ascii=False)
            content = (existing or "") + ("" if not existing or existing.endswith("\n") else "\n") \
                + line + "\n"
        elif self.format == "csv":
            content = self._csv_append(existing, record)
        else:
            content = self._markdown_append(existing, record)
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        textio.write_if_changed(self.path, content)
        return True

    def _csv_append(self, existing: str | None, record: LedgerRecord) -> str:
        fieldnames = ["recordId", "itemId", "completed", "result", "evidence", "corrects"]
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n",
                                extrasaction="ignore")
        if not existing:
            writer.writeheader()
            base_text = ""
        else:
            base_text = existing if existing.endswith("\n") else existing + "\n"
        writer.writerow(record.as_dict())
        return base_text + buffer.getvalue()

    def _markdown_append(self, existing: str | None, record: LedgerRecord) -> str:
        row = "| %s | %s | %s | %s | %s | %s |" % (
            record.record_id, record.item_id, record.completed, record.result,
            record.evidence, record.corrects)
        if not existing:
            return "# Completed Work — Terminal Ledger\n\nAppend-only.\n\n" \
                   + _MARKDOWN_HEADER + "\n" + row + "\n"
        lines = existing.rstrip("\n").splitlines()
        last_table_line = -1
        for position, line in enumerate(lines):
            if line.strip().startswith("|"):
                last_table_line = position
        if last_table_line < 0:
            return existing.rstrip("\n") + "\n\n" + _MARKDOWN_HEADER + "\n" + row + "\n"
        lines.insert(last_table_line + 1, row)
        return "\n".join(lines) + "\n"


def _from_payload(payload: dict) -> LedgerRecord:
    known = {"recordId", "itemId", "completed", "result", "evidence", "corrects"}
    return LedgerRecord(
        record_id=str(payload.get("recordId", "") or ""),
        item_id=str(payload.get("itemId", "") or ""),
        completed=str(payload.get("completed", "") or ""),
        result=str(payload.get("result", "") or ""),
        evidence=str(payload.get("evidence", "") or ""),
        corrects=str(payload.get("corrects", "") or ""),
        extra={k: v for k, v in payload.items() if k not in known},
    )


def utc_today() -> str:
    return base.utc_now()[:10]
