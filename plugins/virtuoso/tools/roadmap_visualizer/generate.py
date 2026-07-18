from __future__ import annotations

import argparse
from pathlib import Path

from .health import summarize_health
from .model import PlanningModel
from .render import render_html
from .roadmap import parse_roadmap
from .workbook import read_catalog
from .workspace import load_workspace


def build_model(root: Path | str) -> PlanningModel:
    workspace = load_workspace(root)
    roadmap = parse_roadmap(workspace.roadmap)
    rows, dashboard = read_catalog(workspace.sprint_queue)
    health = summarize_health(roadmap, rows, dashboard)
    return PlanningModel(
        workspace=workspace,
        roadmap=roadmap,
        sprints=rows,
        dashboard=dashboard,
        health=health,
    )


def generate(root: Path | str, output: Path | str | None = None) -> Path:
    model = build_model(root)
    output_path = _output_path(model, output)
    _refuse_protected_output(model, output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_html(model), encoding="utf-8")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the Virtuoso planning cockpit.")
    parser.add_argument("--root", default=".", help="Workspace root containing Virtuoso/workspace-layout.json")
    parser.add_argument("--output", default="", help="Output HTML path; relative paths resolve under --root")
    args = parser.parse_args(argv)

    output = generate(args.root, args.output or None)
    print(f"planning cockpit written: {output}")
    return 0


def _output_path(model: PlanningModel, output: Path | str | None) -> Path:
    if output is None:
        return model.workspace.reports / "planning-cockpit.html"

    output_path = Path(output)
    if output_path.is_absolute():
        return output_path
    return model.workspace.root / output_path


def _refuse_protected_output(model: PlanningModel, output_path: Path) -> None:
    protected_paths = {
        model.workspace.manifest.resolve(),
        model.workspace.roadmap.resolve(),
        model.workspace.sprint_queue.resolve(),
    }
    if output_path.resolve() in protected_paths:
        raise ValueError(
            f"Refusing to overwrite workspace source file: {output_path}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
