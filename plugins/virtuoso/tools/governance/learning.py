"""The learning loop's outcomes: what close-outs say about lessons, and what follows.

``lessons.py`` reads the catalog and checks one document against it. This module
reads the catalog *together with every close-out* and answers the questions a
catalog alone cannot:

* **hygiene** — which live lessons duplicate one another (merge them), have gone
  stale without ever being applied (retire them), are incomplete (tidy them), or
  reuse an identifier (repair them). ``governance-sweep`` acts on it.
* **candidates** — which lessons have earned promotion to a standing rule: a
  pattern that recurred, or a lesson applied and held in two close-outs.
  ``roadmap-review`` acts on it.
* **metrics** — six figures that say whether the loop is improving, each computed
  with provenance or *not computable* with its missing inputs named.

Everything here is read-only. The one write the loop needs — a status record —
is :func:`status_record`, appended by the ``lessons --record-status`` command.
"""
from __future__ import annotations

import datetime as _dt
import os
import re
import statistics
from dataclasses import dataclass, field

from . import lessons as lessons_mod, overlays as overlays_mod, textio
from .providers.kpi import Metric

#: A close-out report's file name; the date is its last ``YYYY-MM-DD``.
CLOSEOUT_NAME_RE = re.compile(r"^CloseOut\..+\.md$", re.IGNORECASE)
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_NOT_HELD_RE = re.compile(r"did\s*n[o']t\s+hold|not\s+held|failed\s+to\s+hold", re.IGNORECASE)
_HELD_RE = re.compile(r"\bheld\b", re.IGNORECASE)
_NO_LESSON_RE = re.compile(r"no new lesson", re.IGNORECASE)
_STOPWORDS = {"with", "from", "that", "this", "when", "before", "after", "into", "every",
              "each", "item", "items", "their", "there", "which", "about", "only", "have"}

STATUS_WORDS = ("Observation", "Promoted", "Retired", "Superseded")


# --- close-out outcomes ---------------------------------------------------------------

@dataclass
class Outcomes:
    """What the close-outs say. ``held`` / ``not_held``: lesson id -> close-out count.
    ``applied_on``: lesson id -> the dates it was applied (close-out dates)."""
    closeouts: int = 0
    no_lesson: int = 0
    held: dict = field(default_factory=dict)
    not_held: dict = field(default_factory=dict)
    applied_on: dict = field(default_factory=dict)
    read: list = field(default_factory=list)

    def applied(self, lesson_id: str) -> int:
        return self.held.get(lesson_id, 0) + self.not_held.get(lesson_id, 0)


def closeout_files(directory: str) -> list[str]:
    """Every close-out report under ``directory``, in path order. Staging memos and
    other notes are not reports."""
    found = []
    if not directory or not os.path.isdir(directory):
        return found
    for dirpath, dirnames, filenames in os.walk(directory):
        dirnames.sort()
        for name in sorted(filenames):
            if CLOSEOUT_NAME_RE.match(name):
                found.append(os.path.join(dirpath, name))
    return found


def closeout_date(name: str, text: str) -> _dt.date | None:
    match = re.search(r"(?m)^date:[ \t]*(\d{4}-\d{2}-\d{2})", text or "")
    candidates = [match.group(1)] if match else _DATE_RE.findall(os.path.basename(name))[-1:]
    for value in candidates:
        try:
            return _dt.date.fromisoformat(value)
        except ValueError:
            return None
    return None


def read_outcomes(reports: list[tuple[str, str]], prefix: str) -> Outcomes:
    """Outcomes from ``(name, text)`` close-out reports: each report's *Lessons*
    section, line by line — a line naming a lesson with "held" counts it held, with
    "did not hold" counts it not held; "No new lesson" counts the report."""
    outcomes = Outcomes()
    ids = lessons_mod.id_pattern(prefix)
    for name, text in reports:
        outcomes.closeouts += 1
        outcomes.read.append(name)
        lines = overlays_mod.without_fenced_blocks(text or "").splitlines()
        body = lessons_mod._find_section(lines, ("lessons",), refuse=("lessons applied",)) or []
        when = closeout_date(name, text)
        if any(_NO_LESSON_RE.search(line) for line in body):
            outcomes.no_lesson += 1
        for line in body:
            named = ["%s-%s" % (prefix, m.group(1)) for m in ids.finditer(line)]
            if not named:
                continue
            if _NOT_HELD_RE.search(line):
                bucket = outcomes.not_held
            elif _HELD_RE.search(line):
                bucket = outcomes.held
            else:
                continue
            for lesson_id in dict.fromkeys(named):
                bucket[lesson_id] = bucket.get(lesson_id, 0) + 1
                if when:
                    outcomes.applied_on.setdefault(lesson_id, []).append(when)
    return outcomes


def load_outcomes(directory: str, prefix: str) -> Outcomes:
    reports = []
    for path in closeout_files(directory):
        text = textio.read_text(path)
        if text is not None:
            reports.append((os.path.basename(path), text))
    return read_outcomes(reports, prefix)


# --- hygiene ----------------------------------------------------------------------------

def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower())
            if len(w) >= 4 and w not in _STOPWORDS}


def _normal(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", (text or "").lower()))


def _similar(a: lessons_mod.Lesson, b: lessons_mod.Lesson) -> str:
    """Why ``a`` and ``b`` look like one pattern, or ``""``."""
    if a.applies_to and _normal(a.applies_to) == _normal(b.applies_to):
        return "the same Applies to (%s)" % a.applies_to
    wa, wb = _words(a.title), _words(b.title)
    if wa and wb and len(wa & wb) / len(wa | wb) >= 0.6:
        return "near-identical titles"
    return ""


def duplicate_groups(lessons: list[lessons_mod.Lesson]) -> list[dict]:
    """Live lessons that record one pattern, grouped; the first recorded is kept."""
    live = [lesson for lesson in lessons if lesson.live]
    groups: list[dict] = []
    placed: set[str] = set()
    for i, first in enumerate(live):
        if first.id in placed:
            continue
        members, why = [], ""
        for other in live[i + 1:]:
            if other.id in placed:
                continue
            reason = _similar(first, other)
            if reason:
                members.append(other.id)
                placed.add(other.id)
                why = why or reason
        if members:
            placed.add(first.id)
            groups.append({"keep": first.id, "supersede": members, "why": why})
    return groups


def hygiene(lessons: list[lessons_mod.Lesson], outcomes: Outcomes, *,
            today: _dt.date, stale_after_days: int) -> dict:
    """What ``governance-sweep`` should tidy, merge and retire. Proposals only."""
    stale, incomplete, malformed = [], [], []
    for lesson in lessons:
        if lesson.reused:
            malformed.append({"id": lesson.id, "why": "a later entry under this id records a "
                              "different lesson's fields; give that lesson its own id and "
                              "retire the reuse with a status record"})
        if not lesson.live:
            continue
        missing = [f for f in lessons_mod.LESSON_FIELDS if not lesson.fields.get(f)]
        if missing:
            incomplete.append({"id": lesson.id, "missing": missing})
        when = lesson.date
        if (stale_after_days and lesson.status.lower().startswith("observation")
                and when and (today - when).days > stale_after_days
                and not outcomes.applied(lesson.id)):
            stale.append({"id": lesson.id, "recorded": when.isoformat(),
                          "ageDays": (today - when).days})
    return {"duplicates": duplicate_groups(lessons), "stale": stale,
            "incomplete": incomplete, "malformed": malformed,
            "staleAfterDays": stale_after_days}


def candidates(lessons: list[lessons_mod.Lesson], outcomes: Outcomes) -> list[dict]:
    """Lessons that have earned a decision at the next review: promote a pattern
    that recurred or held twice; revise or retire one that failed to hold twice."""
    by_id = {lesson.id: lesson for lesson in lessons}
    found: dict[str, dict] = {}
    for group in duplicate_groups(lessons):
        found[group["keep"]] = {"id": group["keep"], "action": "promote",
                                "why": "the pattern recurred in %s (%s)"
                                       % (", ".join(group["supersede"]), group["why"])}
    for lesson_id, count in sorted(outcomes.held.items()):
        lesson = by_id.get(lesson_id)
        if lesson and lesson.live and count >= 2 and not outcomes.not_held.get(lesson_id):
            found.setdefault(lesson_id, {"id": lesson_id, "action": "promote",
                                         "why": "applied and held in %d close-outs" % count})
    for lesson_id, count in sorted(outcomes.not_held.items()):
        lesson = by_id.get(lesson_id)
        if lesson and lesson.live and count >= 2:
            found[lesson_id] = {"id": lesson_id, "action": "revise or retire",
                                "why": "applied and did not hold in %d close-outs" % count}
    return [found[k] for k in sorted(found)]


# --- the one write: a status record -------------------------------------------------------

def status_problem(lessons: list[lessons_mod.Lesson], lesson_id: str, status: str) -> str:
    """Why ``status`` cannot be recorded for ``lesson_id``, or ``""``."""
    by_id = {lesson.id: lesson for lesson in lessons}
    lesson = by_id.get(lesson_id)
    if lesson is None:
        return "%s is not a recorded lesson; a status record needs an entry to follow" % lesson_id
    word = status.strip().split(" ", 1)[0].rstrip(":—-").capitalize() if status.strip() else ""
    if word not in STATUS_WORDS:
        return "a status begins with one of %s" % ", ".join(STATUS_WORDS)
    if not lesson.live:
        return "%s is already closed (%s); append nothing further" % (lesson_id, lesson.status)
    if word == "Superseded":
        target = re.search(r"%s-\d+" % re.escape(lesson_id.rsplit("-", 1)[0]), status)
        if not target or target.group(0) == lesson_id or target.group(0) not in by_id:
            return ("a Superseded status names the recorded lesson that replaces it, e.g. "
                    "\"Superseded -> %s-001\"" % lesson_id.rsplit("-", 1)[0])
    if word in ("Promoted", "Retired") and len(status.strip()) <= len(word) + 2:
        return "say where it went or why: \"%s -> <destination>\" / \"%s — <reason>\"" % (word, word)
    return ""


def status_record(lesson_id: str, status: str, item: str, date: str) -> str:
    """The markdown appended to record ``status`` — a new entry under the same id."""
    return "### %s — status (%s, %s)\n**Status:** %s\n" % (lesson_id, item, date, status.strip())


# --- effort calibration ----------------------------------------------------------------------

_DURATION_RE = re.compile(r"^\s*(?:(\d+(?:\.\d+)?)\s*h)?\s*(?:(\d+(?:\.\d+)?)\s*m(?:in)?)?\s*$",
                          re.IGNORECASE)
#: Fewer paired records than this is an anecdote, not a calibration.
CALIBRATION_MINIMUM = 3


def hours(text) -> float | None:
    """A duration as hours: ``"90m"``, ``"1.5h"``, ``"2h30m"``, or a bare number of
    hours. ``None`` when it is not one — a T-shirt size is a size, not a duration."""
    text = str(text or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        pass
    match = _DURATION_RE.match(text)
    if not match or not (match.group(1) or match.group(2)):
        return None
    return float(match.group(1) or 0) + float(match.group(2) or 0) / 60


def effort_calibration(records) -> Metric:
    """Median of actual ÷ estimate over ledger records that carry both as durations.
    Above 1 the project under-estimates; below 1 it over-estimates."""
    ratios = []
    for record in records:
        estimate, actual = hours(record.effort_estimate), hours(record.effort_actual)
        if estimate and actual is not None:
            ratios.append(actual / estimate)
    if len(ratios) < CALIBRATION_MINIMUM:
        return Metric("effort-calibration", computable=False, missing_inputs=[
            "%d terminal records with effortEstimate and effortActual as durations (%d have both)"
            % (CALIBRATION_MINIMUM, len(ratios))])
    return Metric("effort-calibration", round(statistics.median(ratios), 2),
                  unit="actual ÷ estimate, median of %d records" % len(ratios))


# --- loop-health metrics ---------------------------------------------------------------------

def metrics(lessons: list[lessons_mod.Lesson], outcomes: Outcomes) -> list[Metric]:
    """Six figures on whether the loop is improving. Each is computed from the catalog
    and the close-outs, or *not computable* with the missing input named."""
    found: list[Metric] = []
    live = sum(1 for lesson in lessons if lesson.live)
    total = len(lessons)
    no_catalog = "a recorded lesson"
    no_closeouts = "a close-out report in the closeOuts role"

    found.append(Metric("live-count", live, unit="lessons") if lessons or outcomes.closeouts
                 else Metric("live-count", computable=False, missing_inputs=[no_catalog]))
    if outcomes.closeouts:
        found.append(Metric("lesson-yield", round(total / outcomes.closeouts, 2),
                            unit="lessons per close-out (%d of %d said no new lesson)"
                                 % (outcomes.no_lesson, outcomes.closeouts)))
    else:
        found.append(Metric("lesson-yield", computable=False, missing_inputs=[no_closeouts]))
    held = sum(outcomes.held.values())
    tried = held + sum(outcomes.not_held.values())
    found.append(Metric("held-rate", round(held / tried, 2), unit="of applied lessons held")
                 if tried else Metric("held-rate", computable=False, missing_inputs=[
                     "a close-out recording whether an applied lesson held"]))
    if total:
        promoted = sum(1 for lesson in lessons
                       if lesson.status.strip().lower().startswith("promoted"))
        found.append(Metric("promotion-rate", round(promoted / total, 2),
                            unit="of lessons promoted to a standing rule"))
    else:
        found.append(Metric("promotion-rate", computable=False, missing_inputs=[no_catalog]))
    delays = []
    for lesson in lessons:
        applied = sorted(outcomes.applied_on.get(lesson.id, []))
        if lesson.date and applied:
            delays.append((applied[0] - lesson.date).days)
    found.append(Metric("time-to-apply", statistics.median(delays),
                        unit="days, median, recorded to first applied (%d lessons)" % len(delays))
                 if delays else Metric("time-to-apply", computable=False, missing_inputs=[
                     "a dated lesson applied in a dated close-out"]))
    if total >= 2:
        recurring = sum(1 + len(g["supersede"]) for g in duplicate_groups(lessons))
        found.append(Metric("repeated-trap-rate", round(recurring / total, 2),
                            unit="of lessons recording a pattern already recorded"))
    else:
        found.append(Metric("repeated-trap-rate", computable=False,
                            missing_inputs=["two or more recorded lessons"]))
    return found
