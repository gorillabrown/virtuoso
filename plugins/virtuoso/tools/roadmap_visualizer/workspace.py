from __future__ import annotations

import json
from pathlib import Path

from .model import WorkspacePaths


def load_workspace(root: Path | str) -> WorkspacePaths:
    root_path = Path(root).resolve()
    manifest = root_path / "Virtuoso" / "workspace-layout.json"

    if manifest.is_file():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        paths = data.get("paths") if isinstance(data, dict) else None
        roadmap = paths.get("roadmap") if isinstance(paths, dict) else None
        sprint_queue = paths.get("sprintQueue") if isinstance(paths, dict) else None
        missing_fields = []
        if not roadmap:
            missing_fields.append("paths.roadmap")
        if not sprint_queue:
            missing_fields.append("paths.sprintQueue")
        if missing_fields:
            raise ValueError(
                f"workspace manifest missing required fields: {', '.join(missing_fields)}"
            )
        return WorkspacePaths(
            root=root_path,
            manifest=manifest,
            roadmap=_resolve(root_path, roadmap),
            sprint_queue=_resolve(root_path, sprint_queue),
            reports=root_path / "Virtuoso" / "reports",
        )

    # No manifest: fall back to the conventional plugin layout.
    conventional_roadmap = root_path / "Virtuoso" / "Roadmap.md"
    conventional_queue = root_path / "Virtuoso" / "sprint-queue.xlsx"
    if conventional_roadmap.is_file() and conventional_queue.is_file():
        return WorkspacePaths(
            root=root_path,
            manifest=manifest,
            roadmap=conventional_roadmap,
            sprint_queue=conventional_queue,
            reports=root_path / "Virtuoso" / "reports",
        )

    raise FileNotFoundError(
        "No Virtuoso/workspace-layout.json manifest, and no conventional "
        "Virtuoso/Roadmap.md + Virtuoso/sprint-queue.xlsx were found under "
        f"{root_path}. Provide a manifest or use the conventional layout."
    )


def _resolve(root: Path, rel: str) -> Path:
    path = Path(rel)
    if path.is_absolute():
        return path
    return root / path
