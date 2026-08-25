"""Project policy — everything the plugin must stop hardcoding.

Redesign items 26, 27, 47, 49, 50, 51, 53, 64-73, 74, 76, 79.

Policy lives under ``policy`` in the manifest. Every value here has a documented
default, so an existing project keeps working, but nothing in the plugin may
*assume* a default that policy can override: branch names, the default remote,
the dispatch buffer size, the status vocabulary, the lane/phase hierarchy, the
readiness-rubric extensions, actor names, and sweep boundaries are all project
configuration.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

#: Git workflow policies (item 64). Ordered from least to most permissive.
GIT_POLICIES = (
    "read-only",            # inspect only; never mutate the repository
    "prepare-no-stage",     # write files; never `git add`
    "explicit-path-stage",  # `git add <exact paths>`; never commit
    "explicit-path-commit", # stage exact paths and commit
    "push",                 # commit and push
)

DEFAULTS: dict = {
    # --- actors (items 74, 75) ------------------------------------------------
    "actors": {
        "planner": "planner",
        "implementer": "implementation agent",
        "reviewer": "reviewer",
        "operator": "repository operator",
    },
    # --- interaction adapter (item 76) ---------------------------------------
    "interaction": {
        # "auto" uses structured questions when the host offers them and concise
        # plain-text questions otherwise.
        "mode": "auto",
        "maxOptions": 4,
    },
    # --- git (items 64-73) ----------------------------------------------------
    "git": {
        "policy": "explicit-path-commit",
        "separationOfDuties": False,
        "independentReviewer": False,
        # null/"" => detect from the repository. Never assume "main"/"origin".
        "defaultBranch": "",
        "remote": "",
        "requireRemote": False,
        "networkOperations": "ask",     # "ask" | "allow" | "deny"
        "branchNameTemplate": "{item-id}",
        "branchCleanup": "maintenance",  # never a dispatch prerequisite (item 68)
        "staleLock": "report",           # "report" | "prompt"; never "auto-delete" (item 69)
        "worktreeAware": True,
    },
    # --- work register / ceremonies (items 26, 27, 49, 50, 51) ---------------
    "workRegister": {
        "fieldMappings": {},            # canonical field -> project column name
        "statusMappings": {},           # canonical status -> project vocabulary
        "snapshot": "",                 # optional cached snapshot role name
        "staleAfterHours": 24,
    },
    "roadmap": {
        "dispatchBuffer": 5,            # item 49 — configurable, may be 0 (disabled)
        "eagerSpec": True,
        "hierarchy": ["phase", "stage"],  # item 50 — may be [] for a flat project
        "lanes": [],
        "specStorage": "inline",        # "inline" | "files" | "external"
        "specDirectory": "",
        "lengthCeilingLines": 2000,
    },
    # --- readiness rubric (items 52, 53) -------------------------------------
    "rubric": {
        "version": "1.0",
        "extensions": [],               # project-specific check ids
    },
    # --- standing rules / escalation (items 48b, 49b) -------------------------
    "standingRules": {
        "source": "roadmap",            # role name carrying the standing rules
        "ids": [],                      # project rule identifiers; none hardcoded
    },
    "issues": {
        "targets": ["local"],           # "local", "external", or both (item 49b)
        "externalRole": "",             # role name of the external tracker
        "filenameTemplate": "Issue.{item-id}.{date}.md",
    },
    # --- terminal ledger (items 47, 48) --------------------------------------
    "terminalLedger": {
        "writers": ["pointer-closeout"],
        "correctionWriters": ["pointer-closeout", "roadmap-review"],
        "format": "markdown",           # "markdown" | "csv" | "jsonl"
    },
    # --- governance sweep (items 51b, 52b, 53b, 56) --------------------------
    "sweep": {
        "include": ["**/*"],
        "exclude": [
            "Virtuoso/.backups/**",
            "Virtuoso/.quarantine/**",
            "**/node_modules/**",
            "**/.git/**",
            "**/__pycache__/**",
            "**/.venv/**",
            "**/vendor/**",
            "**/dist/**",
            "**/build/**",
        ],
        "ignoreDirectories": [".git", "node_modules", "__pycache__", ".venv", "vendor"],
        "followSymlinks": False,
        "maxFileBytes": 5 * 1024 * 1024,
        "binaryPolicy": "skip",          # "skip" | "hash-only"
        "quarantineDirectory": "Virtuoso/.quarantine",
        "deletionPolicy": "quarantine",  # "quarantine" | "permanent"
        "backupRetention": 10,
        "protectedAuthorities": ["archive", "terminal", "evidence"],
        "structuralAuthority": "registry",  # never "directory-readme" unless declared
    },
    # --- runtime dependencies (item 79) --------------------------------------
    "dependencies": {
        "openpyxl": ">=3.1",
    },
}


def _deep_merge(base: dict, overlay: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in (overlay or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


@dataclass
class Policy:
    data: dict

    def section(self, name: str) -> dict:
        value = self.data.get(name)
        return value if isinstance(value, dict) else {}

    def get(self, path: str, default=None):
        """Dotted lookup: ``policy.get("git.policy")``."""
        cursor = self.data
        for part in path.split("."):
            if not isinstance(cursor, dict) or part not in cursor:
                return default
            cursor = cursor[part]
        return cursor

    # -- convenience accessors used across ceremonies -----------------------

    @property
    def git_policy(self) -> str:
        return str(self.get("git.policy", "explicit-path-commit"))

    @property
    def may_stage(self) -> bool:
        return self.git_policy in ("explicit-path-stage", "explicit-path-commit", "push")

    @property
    def may_commit(self) -> bool:
        return self.git_policy in ("explicit-path-commit", "push")

    @property
    def may_push(self) -> bool:
        return self.git_policy == "push"

    @property
    def dispatch_buffer(self) -> int:
        try:
            return max(0, int(self.get("roadmap.dispatchBuffer", 5)))
        except (TypeError, ValueError):
            return 5

    @property
    def hierarchy(self) -> list[str]:
        value = self.get("roadmap.hierarchy", [])
        return [str(v) for v in value] if isinstance(value, list) else []

    def validate(self) -> list[str]:
        problems = []
        if self.git_policy not in GIT_POLICIES:
            problems.append("policy.git.policy=%r is not one of %s"
                            % (self.git_policy, ", ".join(GIT_POLICIES)))
        stale = self.get("git.staleLock", "report")
        if stale not in ("report", "prompt"):
            problems.append(
                "policy.git.staleLock=%r is not allowed; automatic lock-file deletion is "
                "never prescribed (use 'report' or 'prompt')" % (stale,))
        deletion = self.get("sweep.deletionPolicy", "quarantine")
        if deletion not in ("quarantine", "permanent"):
            problems.append("policy.sweep.deletionPolicy=%r is not one of quarantine, permanent"
                            % (deletion,))
        storage = self.get("roadmap.specStorage", "inline")
        if storage not in ("inline", "files", "external"):
            problems.append("policy.roadmap.specStorage=%r is not one of inline, files, external"
                            % (storage,))
        return problems


def load(raw: dict | None) -> Policy:
    """Merge a project's ``policy`` block over the documented defaults."""
    return Policy(_deep_merge(DEFAULTS, raw or {}))
