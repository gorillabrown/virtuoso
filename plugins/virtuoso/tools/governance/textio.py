"""Byte-faithful text helpers.

The governance layer's central promise is that it does not churn user files
(items 5, 88, 89). Every write goes through :func:`write_if_changed`, which:

* compares LF-normalized content so a settled CRLF tree never compares unequal
  against an LF-built string,
* preserves the file's own dominant line ending on the write,
* and returns ``False`` without touching the filesystem when nothing changed —
  no mtime churn, no write syscall.
"""
from __future__ import annotations

import hashlib
import os


def read_bytes(path: str) -> bytes | None:
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError:
        return None


def read_text(path: str) -> str | None:
    raw = read_bytes(path)
    if raw is None:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def detect_eol(path: str) -> str | None:
    """The dominant line ending already on disk (``"\\r\\n"`` / ``"\\n"``), or
    ``None`` when the file is absent, unreadable, or carries no newline."""
    raw = read_bytes(path)
    if raw is None:
        return None
    crlf = raw.count(b"\r\n")
    bare = raw.count(b"\n") - crlf
    if crlf == 0 and bare == 0:
        return None
    return "\r\n" if crlf > bare else "\n"


def normalized(text: str) -> str:
    return text.replace("\r\n", "\n")


def write_if_changed(path: str, content: str) -> bool:
    """Write ``content`` to ``path`` only when it differs (LF-normalized).

    Returns True when bytes were written. Preserves the existing file's own line
    ending; a new file uses ``\\n`` (explicitly, not the platform default, so the
    same tree round-trips identically on every OS — item 96).
    """
    current = read_text(path)
    if current is not None and normalized(current) == normalized(content):
        return False
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    eol = detect_eol(path) if current is not None else "\n"
    with open(path, "w", encoding="utf-8", newline=eol or "\n") as handle:
        handle.write(content)
    return True


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
