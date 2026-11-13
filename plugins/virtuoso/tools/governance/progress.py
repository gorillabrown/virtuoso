"""The progress band's data: one JSON file the plugin's hooks module draws above the prompt.

The file is the registry's opt-in ``progress`` role (``references/registry-contract.md``,
*The progress band*). Every skill that commits to a deliverable flags it here, and every
skill that finishes one marks it done, through ``virtuoso_registry.py progress``; nobody
hand-edits the file, so ``updated`` always comes from the machine clock.

Shape::

    {"title": "...", "deadline": "YYYY-MM-DD", "updated": "YYYY-MM-DDTHH:MMZ",
     "now": "...", "items": [{"id": "...", "label": "...", "state": "..."}]}

``items`` is queue order. ``done`` fills the bar, ``active`` is shown as "Now", and the
first item neither ``done`` nor ``active`` is "Next". Any other state counts as not started.
"""
from __future__ import annotations

import contextlib
import datetime as _dt
import json
import os
import re
import time

STATES = ("queued", "active", "done", "blocked")
DEFAULT_TITLE = "Build queue"
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ProgressError(ValueError):
    """A request the progress file cannot take (unknown id, bad state, bad date)."""


def now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc).replace(second=0, microsecond=0)


def stamp(moment: _dt.datetime) -> str:
    return moment.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def empty() -> dict:
    return {"title": DEFAULT_TITLE, "items": []}


def load(path: str) -> dict:
    """The file's content, or an empty queue where there is no file yet."""
    if not os.path.isfile(path):
        return empty()
    with open(path, encoding="utf-8") as handle:
        doc = json.load(handle)
    if not isinstance(doc, dict) or not isinstance(doc.get("items"), list):
        raise ProgressError("%s holds no \"items\" array" % path)
    return doc


def save(path: str, doc: dict, moment: _dt.datetime | None = None) -> None:
    """Stamp ``updated`` from the clock and replace the file whole (never half-written)."""
    doc["updated"] = stamp(moment or now())
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(doc, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp, path)


#: A lock older than this is a crashed writer's, and is taken over.
STALE_LOCK_SECONDS = 30.0


@contextlib.contextmanager
def locked(path: str, wait_seconds: float = 10.0):
    """Hold ``<path>.lock`` for one read-change-write, so two sessions writing at once
    (an epic's sessions, a planner beside its workers) never lose each other's change."""
    lock = path + ".lock"
    folder = os.path.dirname(lock)
    if folder:
        os.makedirs(folder, exist_ok=True)
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode("ascii"))
            os.close(fd)
            break
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(lock) > STALE_LOCK_SECONDS:
                    os.remove(lock)
                    continue
            except OSError:
                continue
            if time.monotonic() > deadline:
                raise ProgressError("%s is held by another writer; try again" % lock)
            time.sleep(0.05)
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            os.remove(lock)


def prune_done(doc: dict) -> int:
    """Drop every ``done`` item: a new phase starts its bar from what is still to do."""
    before = len(doc["items"])
    doc["items"] = [i for i in doc["items"] if i.get("state") != "done"]
    return before - len(doc["items"])


def _find(doc: dict, item_id: str) -> int:
    for index, item in enumerate(doc["items"]):
        if item.get("id") == item_id:
            return index
    return -1


def _check_state(state: str) -> str:
    if state not in STATES:
        raise ProgressError("state %r is not one of %s" % (state, ", ".join(STATES)))
    return state


def flag(doc: dict, item_id: str, label: str, state: str = "queued",
         after: str | None = None) -> str:
    """Add a deliverable to the queue. Flagging an id already there changes nothing but a
    new label, and never moves its state backwards (a done item stays done)."""
    _check_state(state)
    index = _find(doc, item_id)
    if index >= 0:
        item = doc["items"][index]
        changed = bool(label) and item.get("label") != label
        if changed:
            item["label"] = label
        return "relabelled" if changed else "unchanged"
    item = {"id": item_id, "label": label or item_id, "state": state}
    if after:
        anchor = _find(doc, after)
        if anchor < 0:
            raise ProgressError("no item %r to place %r after" % (after, item_id))
        doc["items"].insert(anchor + 1, item)
    else:
        doc["items"].append(item)
    return "flagged"


def set_state(doc: dict, item_id: str, state: str) -> str:
    _check_state(state)
    index = _find(doc, item_id)
    if index < 0:
        raise ProgressError("no item %r in the progress file; flag it first (--flag)"
                            % item_id)
    item = doc["items"][index]
    if item.get("state") == state:
        return "unchanged"
    item["state"] = state
    return "set"


def drop(doc: dict, item_id: str) -> str:
    index = _find(doc, item_id)
    if index < 0:
        return "unchanged"
    del doc["items"][index]
    return "dropped"


def set_deadline(doc: dict, deadline: str) -> None:
    if deadline == "":
        doc.pop("deadline", None)
        return
    if not _DATE.match(deadline):
        raise ProgressError("deadline %r is not YYYY-MM-DD" % deadline)
    doc["deadline"] = deadline


def drift(doc: dict, register: dict[str, bool]) -> dict:
    """Where the band and the work register disagree. ``register`` maps each register
    item id to whether it is terminal. A band id the register does not hold (a held plan,
    an audit deliverable, a sweep group) is not drift, only reported apart."""
    behind, ahead, apart, same = [], [], [], 0
    for item in doc.get("items", []):
        item_id, done = item.get("id"), item.get("state") == "done"
        if item_id not in register:
            apart.append(item_id)
        elif register[item_id] and not done:
            behind.append(item_id)       # the register closed it; the band has not
        elif done and not register[item_id]:
            ahead.append(item_id)        # the band says done; the register does not
        else:
            same += 1
    return {"registerDoneBandNot": behind, "bandDoneRegisterNot": ahead,
            "notInRegister": apart, "inSync": same}


def summary(doc: dict) -> dict:
    items = doc.get("items", [])
    done = sum(1 for i in items if i.get("state") == "done")
    nxt = next((i for i in items if i.get("state") not in ("done", "active")), None)
    return {
        "title": doc.get("title") or DEFAULT_TITLE,
        "done": done,
        "total": len(items),
        "percent": round(100 * done / len(items)) if items else 0,
        "active": [i.get("label") for i in items if i.get("state") == "active"],
        "next": nxt.get("label") if nxt else None,
        "deadline": doc.get("deadline"),
        "updated": doc.get("updated"),
    }
