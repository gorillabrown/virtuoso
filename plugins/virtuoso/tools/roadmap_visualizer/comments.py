"""Row comments on the board, and the sidecar file that keeps them.

A static page cannot write to disk, so a comment lives first in the browser and
then in ``roadmap-board.comments.json`` (role ``boardComments``), which the page
saves or exports, the generator embeds, and roadmap-review B.3 reads. The file is
written with sorted keys, one entry per item, so comments on different items merge
cleanly in git. Reading is lenient (a damaged entry is skipped and named); writing
is strict (a malformed entry is refused).

    {"comments": {"<item id>": {"updated": "<UTC>", "notes": [
        {"at": "<UTC>", "text": "...", "resolved": false, "answer": "..."}]}},
     "version": 1}
"""
from __future__ import annotations

import json

from tools.governance import textio
from tools.governance.errors import GovernanceError
from tools.governance.providers import base

VERSION = 1


class CommentsError(GovernanceError):
    code = "board-comments-error"


def _note_problem(note) -> str:
    if not isinstance(note, dict):
        return "a note is not an object"
    if not isinstance(note.get("text"), str) or not note["text"].strip():
        return "a note has no text"
    if not isinstance(note.get("at"), str) or not note["at"]:
        return "a note has no time"
    if not isinstance(note.get("resolved", False), bool):
        return "a note's resolved flag is not true or false"
    if "answer" in note and not isinstance(note["answer"], str):
        return "a note's answer is not text"
    return ""


def entry_problem(item_id, entry) -> str:
    """Why ``entry`` is not a valid comment entry, or ``""``."""
    if not isinstance(item_id, str) or not item_id.strip():
        return "an entry has no item id"
    if not isinstance(entry, dict):
        return "%s: the entry is not an object" % item_id
    if not isinstance(entry.get("updated"), str) or not entry["updated"]:
        return "%s: the entry has no updated time" % item_id
    if not isinstance(entry.get("notes"), list):
        return "%s: the entry has no notes list" % item_id
    for note in entry["notes"]:
        problem = _note_problem(note)
        if problem:
            return "%s: %s" % (item_id, problem)
    return ""


def read_comments(path: str) -> tuple[dict, list[str]]:
    """``(comments by item id, problems)``. A missing file is no comments."""
    text = textio.read_text(path)
    if text is None or not text.strip():
        return {}, []
    try:
        payload = json.loads(text)
    except ValueError as exc:
        return {}, ["%s is not valid JSON (%s); no comments were read" % (path, exc)]
    raw = payload.get("comments") if isinstance(payload, dict) else None
    if not isinstance(raw, dict):
        return {}, ["%s has no \"comments\" object; no comments were read" % path]
    comments, problems = {}, []
    for item_id, entry in raw.items():
        problem = entry_problem(item_id, entry)
        if problem:
            problems.append("skipped %s" % problem)
        else:
            comments[item_id] = entry
    return comments, problems


def dumps(comments: dict) -> str:
    """The sidecar's exact text. Refuses anything a reader would have to skip."""
    for item_id, entry in comments.items():
        problem = entry_problem(item_id, entry)
        if problem:
            raise CommentsError("refusing to write a malformed comment: %s" % problem,
                                detail={"item": item_id})
    return json.dumps({"comments": comments, "version": VERSION}, sort_keys=True, indent=2,
                      ensure_ascii=False) + "\n"


def write_comments(path: str, comments: dict) -> bool:
    return textio.write_if_changed(path, dumps(comments))


def merge_entry(durable: dict | None, local: dict | None) -> dict | None:
    """One item's two copies as one. The newer entry (newest ``updated``; on a tie the
    durable copy) supplies the time; a note only the older copy holds is kept, so a note
    typed in the browser outlives a review that resolved the item meanwhile; and a note
    resolved in either copy stays resolved, with its answer. Notes are matched by time
    and text, ordered by time."""
    if not local:
        return durable
    if not durable:
        return local
    newer, older = ((local, durable) if str(local.get("updated") or "")
                    > str(durable.get("updated") or "") else (durable, local))
    twins = {(note.get("at"), note.get("text")): note for note in older.get("notes", [])}
    notes = []
    for note in newer.get("notes", []):
        merged = dict(note)
        twin = twins.get((note.get("at"), note.get("text")))
        if twin and twin.get("resolved") and not note.get("resolved"):
            merged["resolved"] = True
            if "answer" in twin:
                merged["answer"] = twin["answer"]
        notes.append(merged)
    seen = {(note.get("at"), note.get("text")) for note in notes}
    for note in older.get("notes", []):
        if (note.get("at"), note.get("text")) not in seen:
            notes.append(dict(note))
    notes.sort(key=lambda note: str(note.get("at") or ""))
    return dict(newer, notes=notes)


def merge(durable: dict, local: dict) -> dict:
    """Every item's copies merged by :func:`merge_entry`. The reference implementation:
    the page's ``mergeEntry`` is pinned to it by a test that runs both."""
    out = dict(durable)
    for item_id, entry in local.items():
        out[item_id] = merge_entry(out.get(item_id), entry)
    return out


def open_notes(comments: dict) -> list[dict]:
    """Every unresolved note, item by item, for roadmap-review B.3."""
    return [{"item": item_id, "at": note["at"], "text": note["text"]}
            for item_id in sorted(comments)
            for note in comments[item_id]["notes"] if not note.get("resolved")]


def resolve(comments: dict, item_id: str, answer: str, *, when: str = "") -> int:
    """Mark the item's open notes resolved with ``answer``; returns how many. The
    entry's time moves forward so the resolution outlives an older browser copy."""
    entry = comments.get(item_id)
    if entry is None:
        raise CommentsError("no comments on %s" % item_id, detail={"item": item_id})
    if not any(not note.get("resolved") for note in entry["notes"]):
        raise CommentsError("%s has no open comment to resolve" % item_id,
                            detail={"item": item_id})
    count = 0
    for note in entry["notes"]:
        if not note.get("resolved"):
            note["resolved"] = True
            note["answer"] = answer
            count += 1
    entry["updated"] = max(when or base.utc_now(), entry["updated"])
    return count
