"""Partial-failure recovery records (item 34).

When a cross-system operation commits locally but its external half fails, the
plugin writes a recovery record naming exactly what remains. A record is
resolved, never deleted, so the trail survives.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field

from .. import textio
from . import base

RECOVERY_DIR = os.path.join("Virtuoso", ".recovery")


@dataclass
class RecoveryRecord:
    id: str
    operation: str
    item_id: str
    created: str
    completed_steps: list[str] = field(default_factory=list)
    remaining_steps: list[str] = field(default_factory=list)
    detail: dict = field(default_factory=dict)
    resolved: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def path_for(root: str, record_id: str) -> str:
    return os.path.join(root, *RECOVERY_DIR.split(os.sep), "%s.json" % record_id)


def write(root: str, record: RecoveryRecord) -> str:
    target = path_for(root, record.id)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    textio.write_if_changed(target, json.dumps(record.as_dict(), indent=2, ensure_ascii=False) + "\n")
    return os.path.relpath(target, root).replace("\\", "/")


def _filename_token(value: str) -> str:
    """Keep external item identifiers inside the recovery directory."""
    token = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value)).strip(".-")
    return token or "item"


def open_record(root: str, *, operation: str, item_id: str, completed_steps: list[str],
                remaining_steps: list[str], detail: dict | None = None) -> RecoveryRecord:
    created = base.utc_now()
    record_id = "%s-%s-%s" % (
        created.replace(":", "").replace("-", ""),
        _filename_token(operation), _filename_token(item_id))
    record = RecoveryRecord(
        id=record_id, operation=operation, item_id=item_id, created=created,
        completed_steps=list(completed_steps), remaining_steps=list(remaining_steps),
        detail=detail or {},
    )
    write(root, record)
    return record


def get_record(root: str, record_id: str) -> dict | None:
    """Read one recovery record without permitting a path-shaped identifier."""
    if _filename_token(record_id) != record_id:
        return None
    text = textio.read_text(path_for(root, record_id))
    if text is None:
        return None
    payload = json.loads(text)
    return payload if isinstance(payload, dict) else None


def note(root: str, record_id: str, detail: dict) -> bool:
    """Merge durable detail into an unresolved or resolved recovery record."""
    target = path_for(root, record_id)
    text = textio.read_text(target)
    if text is None:
        return False
    payload = json.loads(text)
    current = payload.get("detail")
    if not isinstance(current, dict):
        current = {}
    current.update(detail)
    payload["detail"] = current
    return textio.write_if_changed(
        target, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def resolve(root: str, record_id: str) -> bool:
    target = path_for(root, record_id)
    text = textio.read_text(target)
    if text is None:
        return False
    payload = json.loads(text)
    if payload.get("resolved"):
        return False
    payload["resolved"] = base.utc_now()
    return textio.write_if_changed(target, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def outstanding(root: str) -> list[dict]:
    directory = os.path.join(root, *RECOVERY_DIR.split(os.sep))
    if not os.path.isdir(directory):
        return []
    records = []
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".json"):
            continue
        text = textio.read_text(os.path.join(directory, name))
        if text is None:
            continue
        try:
            payload = json.loads(text)
        except ValueError:
            continue
        if not payload.get("resolved"):
            records.append(payload)
    return records
