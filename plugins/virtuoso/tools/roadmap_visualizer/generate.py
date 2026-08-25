from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.governance import policy as policy_mod, registry as registry_mod  # noqa: E402
from tools.governance.providers import kpi  # noqa: E402

from .health import summarize_health  # noqa: E402
from .model import PlanningModel, RoadmapSnapshot  # noqa: E402
from .render import render_html  # noqa: E402
from .roadmap import parse_roadmap  # noqa: E402
from .workspace import load_workspace  # noqa: E402


def build_model(root: Path | str) -> PlanningModel:
    context, selection = load_workspace(root)
    reg = registry_mod.load(str(context.root))
    project_policy = policy_mod.load(reg.policy)

    snapshot = selection.provider.snapshot()
    roadmap = (parse_roadmap(context.roadmap) if context.roadmap and context.roadmap.is_file()
               else RoadmapSnapshot(path=None, active_codes=[], completed_codes=[],
                                    full_spec_codes=[], headings={}, frontmatter={}))
    metrics = kpi.compute(
        snapshot,
        effort_scale=project_policy.get("roadmap.effortScale"),
        dispatch_buffer=project_policy.dispatch_buffer,
    )
    health = summarize_health(roadmap, snapshot, buffer_target=project_policy.dispatch_buffer)
    return PlanningModel(
        workspace=context,
        roadmap=roadmap,
        items=[item.as_dict() for item in snapshot.items],
        metrics=metrics.as_dict(),
        health=health,
        provenance=snapshot.provenance(),
    )


def generate(root: Path | str, output: Path | str | None = None) -> Path:
    model = build_model(root)
    output_path = _output_path(model, output)
    _refuse_protected_output(model, output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_html(model), encoding="utf-8", newline="\n")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the Virtuoso planning cockpit.")
    parser.add_argument("--root", default=".",
                        help="project root carrying Virtuoso/workspace-layout.json")
    parser.add_argument("--output", default="",
                        help="output HTML path; relative paths resolve under --root")
    args = parser.parse_args(argv)

    output = generate(args.root, args.output or None)
    print("planning cockpit written: %s" % output)
    return 0


def _output_path(model: PlanningModel, output: Path | str | None) -> Path:
    if output is None:
        return model.workspace.reports / "planning-cockpit.html"
    output_path = Path(output)
    if output_path.is_absolute():
        return output_path
    return model.workspace.root / output_path


def _refuse_protected_output(model: PlanningModel, output_path: Path) -> None:
    """The cockpit is a generated report; it may never be written over a source."""
    protected = {model.workspace.manifest.resolve()}
    if model.workspace.roadmap is not None:
        protected.add(model.workspace.roadmap.resolve())
    source = model.workspace.provider.get("source", "")
    if source and os.path.isabs(source):
        protected.add(Path(source).resolve())
    if output_path.resolve() in protected:
        raise ValueError("refusing to overwrite a registered governance document: %s"
                         % output_path)


if __name__ == "__main__":
    raise SystemExit(main())
