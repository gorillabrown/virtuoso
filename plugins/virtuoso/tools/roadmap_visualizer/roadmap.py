from __future__ import annotations

import re
from pathlib import Path

from .model import RoadmapSnapshot


SPRINT_CODE_RE = r"\b[A-Z][A-Z0-9]+(?:-[A-Z0-9]+)+\b"

_SPRINT_CODE_PATTERN = re.compile(SPRINT_CODE_RE)
_HEADING_PATTERN = re.compile(r"^(#{2,6})\s+(.+?)\s*$", re.MULTILINE)
_FRONTMATTER_PATTERN = re.compile(r"<!--\s*Frontmatter:\s*(.*?)-->", re.DOTALL | re.IGNORECASE)
_FULL_SPEC_PATTERN = re.compile(r"\b(full spec|acceptance criteria|implementation plan)\b", re.IGNORECASE)


def parse_roadmap(path: Path | str) -> RoadmapSnapshot:
    roadmap_path = Path(path)
    text = roadmap_path.read_text(encoding="utf-8")

    return RoadmapSnapshot(
        path=roadmap_path,
        active_codes=_active_codes(text),
        completed_codes=_completed_codes(text),
        full_spec_codes=_full_spec_codes(text),
        headings=_headings(text),
        frontmatter=_frontmatter(text),
    )


def _completed_codes(text: str) -> list[str]:
    section = _section_body(text, "Completed Work Summary")
    codes: list[str] = []
    for line in section.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        for code in _SPRINT_CODE_PATTERN.findall(line):
            _append_unique(codes, code)
    return codes


def _active_codes(text: str) -> list[str]:
    codes: list[str] = []
    for _, heading, _ in _active_sprint_blocks(text):
        match = _SPRINT_CODE_PATTERN.search(heading)
        if match:
            _append_unique(codes, match.group(0))
    return codes


def _full_spec_codes(text: str) -> list[str]:
    codes: list[str] = []
    for _, heading, body in _active_sprint_blocks(text):
        match = _SPRINT_CODE_PATTERN.search(heading)
        if match and _FULL_SPEC_PATTERN.search(body):
            _append_unique(codes, match.group(0))
    return codes


def _headings(text: str) -> dict[str, str]:
    headings: dict[str, str] = {}
    for _, heading, _ in _active_sprint_blocks(text):
        match = _SPRINT_CODE_PATTERN.search(heading)
        if not match:
            continue
        title = heading[: match.start()] + heading[match.end() :]
        title = re.sub(r"^[\s\W_]+", "", title).strip()
        headings[match.group(0)] = title
    return headings


def _frontmatter(text: str) -> dict[str, str]:
    match = _FRONTMATTER_PATTERN.search(text)
    if not match:
        return {}

    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if not key:
            continue
        values[key] = value.strip().strip("\"'")
    return values


def _active_sprint_blocks(text: str) -> list[tuple[int, str, str]]:
    section = _section_body(text, "Active & Remaining Sprint Skeletons")
    headings = list(_HEADING_PATTERN.finditer(section))
    blocks: list[tuple[int, str, str]] = []

    for index, match in enumerate(headings):
        heading = match.group(2)
        if not _SPRINT_CODE_PATTERN.search(heading):
            continue
        body_start = match.end()
        body_end = headings[index + 1].start() if index + 1 < len(headings) else len(section)
        blocks.append((len(match.group(1)), heading, section[body_start:body_end]))

    return blocks


def _section_body(text: str, title: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(title)}\s*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""

    next_heading = re.search(r"^##\s+", text[match.end() :], re.MULTILINE)
    if not next_heading:
        return text[match.end() :]
    return text[match.end() : match.end() + next_heading.start()]


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)
