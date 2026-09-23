"""The learning loop: lessons captured at close-out, applied in the next specification.

A lesson lives in the registered ``lessons`` role, which is append-only. One entry:

    ### SRL-NNN — Short title (ITEM-ID, 2026-09-23)
    **Verdict:** what was learned, in a sentence or two
    **Evidence:** what happened, with numbers
    **Recommendation:** the concrete change a future specification should make
    **Applies to:** when it bears on future work — a domain, an item kind, a lane
    **Status:** Observation

The prefix (``SRL``) is ``policy.lessons.idPrefix``. A status never changes in
place: promoting or retiring a lesson appends another entry under the same id,
and the latest ``**Status:**`` recorded for an id is its current status. A lesson
is **live** until it is promoted (it lives on as the rule it became), retired, or
superseded.

Three ceremonies close the loop, and this module is what they check against:

* ``pointer-closeout`` appends the lessons a dispatch taught — or says, with a
  reason, that it taught none — and records how the lessons its specification
  applied turned out;
* ``roadmap-review`` and ``next-pointer`` fold the live lessons into every
  specification (readiness rubric U9, *Lessons applied*);
* ``epic`` folds them into a charter's direction before a long run begins.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import overlays as overlays_mod

#: A status beginning with one of these words closes a lesson.
CLOSED_STATUSES = ("promoted", "retired", "superseded")
DEFAULT_STATUS = "Observation"

_FIELD_RE = re.compile(r"^\*\*(?P<name>[^*]+?):\*\*[ \t]*(?P<value>.*)$")
_HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})[ \t]+(?P<text>.+?)[ \t]*$")
_SOURCE_RE = re.compile(r"^(?P<title>.*?)[ \t]*\((?P<source>[^()]*)\)[ \t]*$")

#: Finding codes for ``--check``. Failures make a specification or close-out not ready.
SECTION_MISSING = "lessons-section-missing"
SECTION_EMPTY = "lessons-section-empty"
UNKNOWN = "lesson-unknown"
NOT_APPENDED = "lesson-not-appended"
CLOSED_CITED = "lesson-closed-cited"
NOT_CITED = "lessons-not-cited"
ITEM_MISSING = "lessons-item-section-missing"
FINDING_CODES = (SECTION_MISSING, SECTION_EMPTY, UNKNOWN, NOT_APPENDED, CLOSED_CITED,
                 NOT_CITED, ITEM_MISSING)


@dataclass
class Lesson:
    id: str
    title: str = ""
    source: str = ""
    fields: dict = field(default_factory=dict)
    history: list = field(default_factory=list)      # every status recorded, in order

    @property
    def status(self) -> str:
        return self.history[-1] if self.history else DEFAULT_STATUS

    @property
    def live(self) -> bool:
        return not self.status.strip().lower().startswith(CLOSED_STATUSES)

    @property
    def applies_to(self) -> str:
        return self.fields.get("applies to", "")

    def as_dict(self) -> dict:
        return {"id": self.id, "title": self.title, "source": self.source,
                "status": self.status, "live": self.live, "appliesTo": self.applies_to,
                "recommendation": self.fields.get("recommendation", ""),
                "history": list(self.history)}


def id_pattern(prefix: str) -> re.Pattern:
    """A lesson identifier: the prefix, a hyphen, digits — not part of a longer token."""
    return re.compile(r"(?<![\w-])%s-(\d+)(?![\w-])" % re.escape(prefix))


def parse(text: str, prefix: str) -> list[Lesson]:
    """Every lesson in ``text``, in first-appearance order, with its current status.

    An entry is a heading at depth 2-4 that starts with an identifier. Fenced blocks
    are examples, never entries. The first entry for an id carries the lesson; a
    later entry for the same id is a status record appended after it.
    """
    body = overlays_mod.without_fenced_blocks(text or "")
    heading_re = re.compile(r"^#{2,4}[ \t]+(%s-\d+)\b[ \t]*(?:[—–:-][ \t]*)?(.*?)[ \t]*$"
                            % re.escape(prefix))
    lessons: dict[str, Lesson] = {}
    order: list[str] = []
    current: Lesson | None = None
    first_entry = False
    for line in body.splitlines():
        line = line.rstrip("\r")
        match = heading_re.match(line)
        if match:
            lesson_id, heading = match.group(1), match.group(2)
            current = lessons.get(lesson_id)
            first_entry = current is None
            if first_entry:
                title, source = heading, ""
                split = _SOURCE_RE.match(heading)
                if split:
                    title, source = split.group("title"), split.group("source")
                current = Lesson(id=lesson_id, title=title.strip(), source=source.strip())
                lessons[lesson_id] = current
                order.append(lesson_id)
            continue
        if _HEADING_RE.match(line):
            current = None                       # any other heading ends the entry
            continue
        if current is None:
            continue
        field_match = _FIELD_RE.match(line.strip())
        if not field_match:
            continue
        name = field_match.group("name").strip().lower()
        value = field_match.group("value").strip()
        if name == "status":
            current.history.append(value or DEFAULT_STATUS)
        elif first_entry and name not in current.fields:
            current.fields[name] = value
    return [lessons[i] for i in order]


# --- checking a specification or a close-out ---------------------------------


@dataclass
class CheckResult:
    kind: str                      # "specification" | "close-out"
    passed: bool = True
    cited: list = field(default_factory=list)
    findings: list = field(default_factory=list)

    def fail(self, code: str, message: str) -> None:
        self.passed = False
        self.findings.append({"code": code, "severity": "error", "message": message})

    def note(self, code: str, severity: str, message: str) -> None:
        self.findings.append({"code": code, "severity": severity, "message": message})

    def as_dict(self) -> dict:
        return {"kind": self.kind, "passed": self.passed, "cited": list(self.cited),
                "findings": list(self.findings)}


def _headings(lines: list[str]):
    for index, line in enumerate(lines):
        match = _HEADING_RE.match(line)
        if match:
            yield index, len(match.group("hashes")), match.group("text")


def _section(lines: list[str], start: int, depth: int) -> list[str]:
    """The lines under the heading at ``start`` until the next heading at the same or
    a shallower depth."""
    out = []
    for line in lines[start + 1:]:
        match = _HEADING_RE.match(line)
        if match and len(match.group("hashes")) <= depth:
            break
        out.append(line)
    return out


def item_section(text: str, item: str) -> list[str] | None:
    """The lines of the section whose heading names ``item`` (an inline specification
    in a roadmap), or ``None`` when no heading names it."""
    lines = overlays_mod.without_fenced_blocks(text or "").splitlines()
    pattern = re.compile(r"(?<![\w-])%s(?![\w-])" % re.escape(item))
    for index, depth, heading in _headings(lines):
        if pattern.search(heading):
            return _section(lines, index, depth)
    return None


def _find_section(lines: list[str], wanted, refuse=()) -> list[str] | None:
    for index, depth, heading in _headings(lines):
        low = heading.strip().lower()
        if low.startswith(wanted) and not low.startswith(tuple(refuse)):
            return _section(lines, index, depth)
    return None


def check(text: str, lessons: list[Lesson], prefix: str, *, item: str = "",
          closeout: bool = False) -> CheckResult:
    """Readiness check U9 for a specification, or the lessons gate for a close-out.

    A **specification** carries a *Lessons applied* section that cites the live
    lessons bearing on it — each by identifier, with the change it made — or says
    that no live lesson applies. Every identifier must resolve; citing a promoted
    or retired lesson is a warning (cite the rule it became). Live lessons the
    section does not cite are listed as information, so the author confirms none
    of them applies rather than overlooking them. ``item`` locates an inline
    specification: the section whose heading names it.

    A **close-out** carries a *Lessons* section. It names the lessons the dispatch
    added — recorded with ``item`` as their source, and already in the registered
    role, which is how the check proves the append happened — or says
    "No new lesson — <reason>". Naming only older lessons (the ones the
    specification applied) is not enough: a close-out answers what *this* dispatch
    taught. ``item`` is the item being closed.
    """
    result = CheckResult(kind="close-out" if closeout else "specification")
    lines = overlays_mod.without_fenced_blocks(text or "").splitlines()
    if item and not closeout:
        section = item_section(text, item)
        if section is None:
            result.fail(ITEM_MISSING, "no heading in the document names %s" % item)
            return result
        lines = section
    if closeout:
        body = _find_section(lines, ("lessons",), refuse=("lessons applied",))
        label = "Lessons"
    else:
        body = _find_section(lines, ("lessons applied",))
        label = "Lessons applied"
    if body is None:
        result.fail(SECTION_MISSING, "no \"%s\" section%s" % (
            label, " for %s" % item if item and not closeout else ""))
        return result

    by_id = {lesson.id: lesson for lesson in lessons}
    text_body = "\n".join(body)
    cited = []
    for match in id_pattern(prefix).finditer(text_body):
        lesson_id = "%s-%s" % (prefix, match.group(1))
        if lesson_id not in cited:
            cited.append(lesson_id)
    result.cited = cited

    for lesson_id in cited:
        lesson = by_id.get(lesson_id)
        if lesson is None:
            if closeout:
                result.fail(NOT_APPENDED, "%s is named but is not in the registered lessons "
                            "role — the append did not happen" % lesson_id)
            else:
                result.fail(UNKNOWN, "%s is cited but no such lesson is recorded" % lesson_id)
        elif not lesson.live and not closeout:
            result.note(CLOSED_CITED, "warning",
                        "%s is %s; cite what it became instead" % (lesson_id, lesson.status))

    if closeout:
        # A reason must be words, not a template's "[reason]" placeholder.
        says_none = re.search(r"no new lesson[ \t]*[—–:-]+[ \t]*[^\s\[<(]", text_body,
                              re.IGNORECASE)
        item_re = re.compile(r"(?<![\w-])%s(?![\w-])" % re.escape(item)) if item else None
        added = [i for i in cited if i in by_id
                 and (item_re is None or item_re.search(by_id[i].source or ""))]
        if not added and not says_none:
            result.fail(SECTION_EMPTY, "the Lessons section names no lesson recorded from %s "
                        "and does not say \"No new lesson — <reason>\""
                        % (item or "this dispatch"))
        return result

    if not cited and "no live lesson" not in text_body.lower():
        result.fail(SECTION_EMPTY, "the Lessons applied section cites no lesson and does "
                    "not say that no live lesson applies")
    _not_cited(result, lessons, cited)
    return result


def _not_cited(result: CheckResult, lessons: list[Lesson], cited: list[str]) -> None:
    missing = [lesson for lesson in lessons if lesson.live and lesson.id not in cited]
    if missing:
        shown = ", ".join("%s (%s)" % (lesson.id, lesson.applies_to or "applies to: unstated")
                          for lesson in missing[:10])
        result.note(NOT_CITED, "info",
                    "%d live lesson(s) not cited — confirm none applies: %s%s"
                    % (len(missing), shown, "…" if len(missing) > 10 else ""))
