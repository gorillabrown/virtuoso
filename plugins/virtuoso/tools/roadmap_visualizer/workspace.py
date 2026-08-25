"""Resolve the cockpit's inputs through the governance registry (items 82, 84, 87).

The cockpit used to require a generated spreadsheet and fell back to a
conventional layout when no manifest existed. It now reads the *declared*
authoritative work register through its provider, and a project with no registry
gets an actionable error instead of a guess.
"""
from __future__ import annotations

from pathlib import Path

from tools.governance import providers, registry as registry_mod
from tools.governance.errors import RoleNotRegistered

from .model import WorkspaceContext


def load_workspace(root: Path | str, *, actor: str = "") -> tuple[WorkspaceContext, object]:
    """Return ``(context, provider_selection)`` for ``root``."""
    root_path = Path(root).resolve()
    reg = registry_mod.load(str(root_path))
    if not reg.manifest_present:
        raise FileNotFoundError(
            "no governance registry at %s. Run virtuoso_preflight.py --mode check to see "
            "what is here, then --mode adopt (established project) or --mode create "
            "--authorize (new workspace)." % (root_path / "Virtuoso" / "workspace-layout.json")
        )

    selection = providers.work_register(reg, actor=actor)
    try:
        roadmap = Path(reg.resolve("roadmap"))
    except RoleNotRegistered:
        roadmap = None

    context = WorkspaceContext(
        root=root_path,
        manifest=Path(reg.manifest_path),
        roadmap=roadmap,
        reports=root_path / "Virtuoso" / "reports",
        work_register_role=selection.role_name,
        work_register_authority=selection.authority,
        provider=selection.provider.describe(),
        compatibility_adapter=selection.compatibility,
        notes=list(selection.notes),
    )
    return context, selection
