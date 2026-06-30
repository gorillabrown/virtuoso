from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CloseoutPaths:
    closeout_dir: Path
    retro_path: Path


def _manifest_paths(project_root: Path) -> CloseoutPaths | None:
    manifest = project_root / "Virtuoso" / "workspace-layout.json"
    if not manifest.exists():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        paths = data.get("paths", {})
        closeout_dir = project_root / paths["closeOuts"]
        retro_path = project_root / paths["lessons"]
    except (OSError, KeyError, TypeError, ValueError):
        return None
    closeout_dir.mkdir(parents=True, exist_ok=True)
    return CloseoutPaths(closeout_dir=closeout_dir, retro_path=retro_path)


def find_closeout_dir(project_root: Path) -> Path:
    manifest = _manifest_paths(project_root)
    if manifest:
        return manifest.closeout_dir

    docs_dir = project_root / "docs"
    candidates = [
        project_root / "Project Documentation" / "2 operational" / "Close-Outs",
        project_root / "2. Project Documentation" / "2 operational" / "Close-Outs",
        project_root / "Virtuoso" / "Project Documentation" / "2 operational" / "Close-Outs",
        project_root / "Virtuoso" / "Close-Outs",
        docs_dir / "Close-Outs",
        project_root / "Close-Outs",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    target = docs_dir / "Close-Outs"
    target.mkdir(parents=True, exist_ok=True)
    return target


def find_closeout_paths(project_root: Path) -> CloseoutPaths:
    manifest = _manifest_paths(project_root)
    if manifest:
        return manifest
    closeout_dir = find_closeout_dir(project_root)
    return CloseoutPaths(
        closeout_dir=closeout_dir,
        retro_path=closeout_dir / "SpecRetro.Lessons_Learned.md",
    )


def next_srl(retro_path: Path) -> str:
    if not retro_path.exists():
        return "SRL-001"

    matches = re.findall(r"SRL-(\d+)", retro_path.read_text(encoding="utf-8"))
    if not matches:
        return "SRL-001"
    last = max(int(value) for value in matches)
    return f"SRL-{last + 1:03d}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare close-out file paths.")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--sprint-id", required=True)
    parser.add_argument("--date", required=True)
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    paths = find_closeout_paths(project_root)
    closeout_path = paths.closeout_dir / f"CloseOut.{args.sprint_id}.{args.date}.md"

    print(f"CLOSEOUT_DIR={paths.closeout_dir}")
    print(f"CLOSEOUT_REPORT={closeout_path}")
    print(f"SPEC_RETRO={paths.retro_path}")
    print(f"NEXT_SRL={next_srl(paths.retro_path)}")


if __name__ == "__main__":
    main()
