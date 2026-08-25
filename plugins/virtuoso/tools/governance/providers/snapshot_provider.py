"""Read-only snapshot register (items 23, 31).

A snapshot is a timestamped JSON capture of another register. It supports
offline, read-only reporting; it is *always* labelled with when it was taken and
flagged stale once it is older than the configured window, so no report can
silently present cached data as live.
"""
from __future__ import annotations

import datetime as _dt
import json

from .. import textio
from . import base, mapping as mapping_mod

SNAPSHOT_VERSION = 1


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
