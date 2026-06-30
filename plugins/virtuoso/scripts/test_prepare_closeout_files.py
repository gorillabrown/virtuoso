import importlib.util
import json
import sys
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "pointer-closeout"
    / "scripts"
    / "prepare_closeout_files.py"
)


def _module():
    spec = importlib.util.spec_from_file_location("prepare_closeout_files", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_find_closeout_paths_from_workspace_manifest(tmp_path):
    module = _module()
    closeouts = tmp_path / "Virtuoso" / "Project Documentation" / "2 operational" / "Close-Outs"
    lessons = (
        tmp_path
        / "Virtuoso"
        / "Project Documentation"
        / "1 governance"
        / "SpecRetro.Lessons_Learned.md"
    )
    manifest = tmp_path / "Virtuoso" / "workspace-layout.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "layout": "canonical",
                "paths": {
                    "closeOuts": "Virtuoso/Project Documentation/2 operational/Close-Outs",
                    "lessons": "Virtuoso/Project Documentation/1 governance/SpecRetro.Lessons_Learned.md",
                },
            }
        ),
        encoding="utf-8",
    )

    result = module.find_closeout_paths(tmp_path)

    assert result.closeout_dir == closeouts
    assert result.retro_path == lessons
    assert closeouts.is_dir()
