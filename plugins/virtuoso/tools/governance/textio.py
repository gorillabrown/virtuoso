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

import codecs
import hashlib
import os


def read_bytes(path: str) -> bytes | None:
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError:
        return None


#: BOMs, longest first. UTF-32 LE begins with the UTF-16 LE BOM, so testing
#: UTF-16 first would decode a UTF-32 file as UTF-16 and produce mojibake.
_BOMS = (
    (codecs.BOM_UTF8, "utf-8-sig"),
    (codecs.BOM_UTF32_LE, "utf-32"),
    (codecs.BOM_UTF32_BE, "utf-32"),
    (codecs.BOM_UTF16_LE, "utf-16"),
    (codecs.BOM_UTF16_BE, "utf-16"),
)


def read_text(path: str) -> str | None:
    """The file's text, or ``None`` when its bytes are not decodable as text.

    A byte-order mark is honoured rather than rejected. Governance documents are
    written by people and by their shells: Windows PowerShell's ``>`` writes
    UTF-16 with a BOM, and several editors add a UTF-8 one. Refusing those made
    the plugin report a file it could plainly see as absent, which is a worse
    answer than reading it.

    ``None`` still means "these bytes are not text I can read", and callers
    report that; it no longer also means "these bytes are text with a BOM".
    """
    raw = read_bytes(path)
    if raw is None:
        return None
    for bom, encoding in _BOMS:
        if raw.startswith(bom):
            try:
                return raw.decode(encoding)
            except (UnicodeDecodeError, LookupError):
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
    # `content` may already carry CRLF -- `read_text` decodes raw bytes without
    # newline translation, so text read back from a CRLF file keeps its \r\n.
    # Opening with newline=eol translates every \n on write, so writing that text
    # unnormalized turns each \r\n into \r\r\n, which reads back as TWO line
    # breaks and silently grows the file on every repair. Normalize to \n first
    # and let `newline` apply the file's own ending exactly once.
    with open(path, "w", encoding="utf-8", newline=eol or "\n") as handle:
        handle.write(normalized(content))
    return True


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
