from __future__ import annotations

import argparse
import re
from pathlib import Path


def find_closeout_dir(project_root: Path) -> Path:
    docs_dir = project_root / "docs"
    candidates = [
        docs_dir / "Close-Outs",
        project_root / "Close-Outs",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    target = docs_dir / "Close-Outs"
    target.mkdir(parents=True, exist_ok=True)
    return target


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
    closeout_dir = find_closeout_dir(project_root)
    closeout_path = closeout_dir / f"CloseOut.{args.sprint_id}.{args.date}.md"
    retro_path = closeout_dir / "SpecRetro.Lessons_Learned.md"

    print(f"CLOSEOUT_DIR={closeout_dir}")
    print(f"CLOSEOUT_REPORT={closeout_path}")
    print(f"SPEC_RETRO={retro_path}")
    print(f"NEXT_SRL={next_srl(retro_path)}")


if __name__ == "__main__":
    main()
