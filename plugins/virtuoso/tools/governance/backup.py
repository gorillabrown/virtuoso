"""Verifiable backups (items 9, 55, 56, 62).

Every existing target touched by a repair, migration, or sweep mutation is
copied into a timestamped backup set first, and every copy is recorded with its
source path, destination path, byte count, SHA-256, timestamp, and the operation
that prompted it. The set carries a ``manifest.json`` so it can be *restored* and
*independently verified* — not merely "copied into a timestamped directory".

Backup sets live under ``Virtuoso/.backups/`` and are excluded from governance
sweeps by default (item 56); :func:`prune` applies the retention policy so old
sets do not become new governance findings.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import shutil
from dataclasses import asdict, dataclass, field

from . import textio
from .errors import BackupError

BACKUP_DIRNAME = os.path.join("Virtuoso", ".backups")
MANIFEST_NAME = "manifest.json"
MANIFEST_VERSION = 1


def utc_stamp(now: _dt.datetime | None = None) -> str:
    now = now or _dt.datetime.now(_dt.timezone.utc)
    return now.strftime("%Y%m%dT%H%M%SZ")


@dataclass
class BackupEntry:
    source: str          # project-relative source path
    destination: str     # backup-set-relative destination path
    bytes: int
    sha256: str
    timestamp: str
    operation: str


@dataclass
class BackupSet:
    root: str            # project root
    directory: str       # absolute path of this backup set
    label: str
    created: str
    entries: list[BackupEntry] = field(default_factory=list)

    @property
    def manifest_path(self) -> str:
        return os.path.join(self.directory, MANIFEST_NAME)

    @property
    def relative_directory(self) -> str:
        return os.path.relpath(self.directory, self.root).replace("\\", "/")

    def add(self, source_abs: str, operation: str) -> BackupEntry | None:
        """Copy ``source_abs`` into the set. Returns None when the source does not
        exist (nothing to preserve); raises :class:`BackupError` on copy failure —
        a repair must never proceed past a failed backup."""
        if not os.path.exists(source_abs):
            return None
        rel = os.path.relpath(source_abs, self.root).replace("\\", "/")
        if rel.startswith(".."):
            rel = "_external/" + os.path.basename(source_abs)
        destination = os.path.join(self.directory, *rel.split("/"))
        try:
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            if os.path.isdir(source_abs):
                shutil.copytree(source_abs, destination, dirs_exist_ok=True)
                size = _tree_bytes(destination)
                digest = _tree_digest(destination)
            else:
                shutil.copy2(source_abs, destination)
                size = os.path.getsize(destination)
                digest = textio.sha256_file(destination)
        except OSError as exc:
            raise BackupError("could not back up %s: %s" % (rel, exc),
                              detail={"source": rel}) from exc
        entry = BackupEntry(
            source=rel,
            destination=os.path.relpath(destination, self.directory).replace("\\", "/"),
            bytes=size,
            sha256=digest,
            timestamp=utc_stamp(),
            operation=operation,
        )
        self.entries.append(entry)
        return entry

    def write_manifest(self) -> str:
        payload = {
            "manifestVersion": MANIFEST_VERSION,
            "label": self.label,
            "created": self.created,
            "projectRoot": os.path.basename(self.root),
            "entries": [asdict(e) for e in self.entries],
        }
        os.makedirs(self.directory, exist_ok=True)
        with open(self.manifest_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        return self.manifest_path

    def as_dict(self) -> dict:
        return {
            "directory": self.relative_directory,
            "label": self.label,
            "created": self.created,
            "entries": [asdict(e) for e in self.entries],
        }


def _tree_bytes(path: str) -> int:
    total = 0
    for dirpath, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(dirpath, name))
            except OSError:
                pass
    return total


def _tree_digest(path: str) -> str:
    """A stable digest over a directory: sha256 of the sorted `relpath:filehash` list."""
    parts = []
    for dirpath, dirs, files in os.walk(path):
        dirs.sort()
        for name in sorted(files):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, path).replace("\\", "/")
            try:
                parts.append("%s:%s" % (rel, textio.sha256_file(full)))
            except OSError:
                parts.append("%s:unreadable" % rel)
    return textio.sha256_bytes("\n".join(parts).encode("utf-8"))


def open_set(root: str, label: str, *, now: _dt.datetime | None = None) -> BackupSet:
    stamp = utc_stamp(now)
    directory = os.path.join(root, *BACKUP_DIRNAME.split(os.sep), "%s-%s" % (stamp, label))
    return BackupSet(root=root, directory=directory, label=label, created=stamp)


def load_set(directory: str, root: str) -> BackupSet:
    manifest_path = os.path.join(directory, MANIFEST_NAME)
    text = textio.read_text(manifest_path)
    if text is None:
        raise BackupError("backup manifest not found: %s" % manifest_path)
    try:
        payload = json.loads(text)
    except ValueError as exc:
        raise BackupError("backup manifest is not valid JSON: %s" % exc) from exc
    entries = [BackupEntry(**e) for e in payload.get("entries", [])]
    return BackupSet(root=root, directory=directory,
                     label=payload.get("label", ""), created=payload.get("created", ""),
                     entries=entries)


def verify(backup_set: BackupSet) -> list[str]:
    """Independently verify every stored copy against its recorded hash.
    Returns a list of problems; empty means the set is restorable."""
    problems: list[str] = []
    for entry in backup_set.entries:
        stored = os.path.join(backup_set.directory, *entry.destination.split("/"))
        if not os.path.exists(stored):
            problems.append("missing backup copy: %s" % entry.destination)
            continue
        digest = _tree_digest(stored) if os.path.isdir(stored) else textio.sha256_file(stored)
        if digest != entry.sha256:
            problems.append("hash mismatch for %s (recorded %s, found %s)"
                            % (entry.destination, entry.sha256[:12], digest[:12]))
    return problems


def restore(backup_set: BackupSet, *, only: list[str] | None = None) -> list[str]:
    """Restore backed-up copies over their sources. Verifies hashes first and
    refuses to restore anything when verification fails."""
    problems = verify(backup_set)
    if problems:
        raise BackupError("backup set failed verification; refusing to restore",
                          detail={"problems": problems})
    restored: list[str] = []
    for entry in backup_set.entries:
        if only is not None and entry.source not in only:
            continue
        stored = os.path.join(backup_set.directory, *entry.destination.split("/"))
        target = os.path.join(backup_set.root, *entry.source.split("/"))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if os.path.isdir(stored):
            shutil.copytree(stored, target, dirs_exist_ok=True)
        else:
            shutil.copy2(stored, target)
        restored.append(entry.source)
    return restored


def prune(root: str, *, keep: int = 10) -> list[str]:
    """Retention policy (item 56): keep the newest ``keep`` sets, remove the rest.
    Returns the project-relative directories removed."""
    base = os.path.join(root, *BACKUP_DIRNAME.split(os.sep))
    if not os.path.isdir(base) or keep < 0:
        return []
    sets = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)))
    removed = []
    for name in sets[: max(0, len(sets) - keep)]:
        shutil.rmtree(os.path.join(base, name), ignore_errors=True)
        removed.append("%s/%s" % (BACKUP_DIRNAME.replace(os.sep, "/"), name))
    return removed
