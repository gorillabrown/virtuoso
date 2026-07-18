from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

from .model import SprintRow


# sprint-catalog.csv is the single source of truth for sprint data (see the
# roadmap-review, roadmap-status, and next-pointer skills). sprint-queue.xlsx is an
# optional, human-facing report whose Dashboard tab is driven by Power Query / formulas
# that only refresh when a human opens the workbook in Excel — a workbook left unopened
# can silently disagree with the CSV, so it is never read back here.
CATALOG_FILENAME = "sprint-catalog.csv"

CATALOG_HEADERS = [
    "Seq",
    "Sprint Code",
    "Phase",
    "Stage",
    "Title",
    "LOE",
    "Dependencies",
    "Implementation Status",
    "Written Status",
    "Branch",
    "Date Started",
    "Date Completed",
    "Close-Out File",
    "Description",
    "Notes",
]


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_int(value: Any) -> int | None:
    text = _clean(value)
    if not text:
        return None
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


def _dependencies(value: Any) -> list[str]:
    text = _clean(value)
    if not text:
        return []
    return [part.strip() for part in re.split(r"[,;\n]+", text) if part.strip()]


def _resolve_catalog_path(path: Path) -> Path:
    """Resolve the sprint-catalog.csv path to read.

    Accepts either the CSV path directly, or a sprint-queue.xlsx path (in which case
    the sibling CSV in the same directory is used) — callers that only know the
    workspace's sprint_queue path do not need to change.
    """
    if path.suffix.lower() == ".csv":
        return path
    return path.with_name(CATALOG_FILENAME)


def read_catalog(path: Path | str) -> tuple[list[SprintRow], dict[str, Any]]:
    csv_path = _resolve_catalog_path(Path(path))

    rows: list[SprintRow] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for record in reader:
            code = _clean(record.get("Sprint Code"))
            if not code:
                continue
            rows.append(
                SprintRow(
                    seq=_as_int(record.get("Seq")),
                    code=code,
                    phase=_clean(record.get("Phase")),
                    stage=_clean(record.get("Stage")),
                    title=_clean(record.get("Title")),
                    loe=_clean(record.get("LOE")),
                    dependencies=_dependencies(record.get("Dependencies")),
                    implementation_status=_clean(record.get("Implementation Status")),
                    written_status=_clean(record.get("Written Status")),
                    branch=_clean(record.get("Branch")),
                    date_started=_clean(record.get("Date Started")),
                    date_completed=_clean(record.get("Date Completed")),
                    close_out_file=_clean(record.get("Close-Out File")),
                    description=_clean(record.get("Description")),
                    notes=_clean(record.get("Notes")),
                )
            )

    # No dashboard: the CSV carries no cached KPIs, so callers compute health/staleness
    # findings from the catalog rows directly rather than comparing against a cache.
    return rows, {}
