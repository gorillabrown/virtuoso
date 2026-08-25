"""The published status contract (items 10, 11).

Every preflight invocation resolves to exactly one of the statuses below, in
every mode. The set is closed and each member is documented here and covered by
``scripts/test_status_contract.py``.

============== ===================================================== =======
status         meaning                                               writes
============== ===================================================== =======
ready          registered, valid, nothing to do                      0
warning        usable, but non-blocking findings exist               0
repair-needed  registered with error-severity findings; a repair     0
               plan is available
repair-preview a repair plan was produced but not applied            0
repaired       an approved repair was applied successfully           >=0
adoptable      unregistered project with discoverable governance     0
adopted        adopt registered the project in place                 >=1
created        create initialized a new workspace                    >=1
none           no workspace and nothing to adopt                     0
failed         the operation could not complete; nothing partial     0
               was written
============== ===================================================== =======

Two output forms are always available: the legacy human/agent lines
(``virtuoso-status: <status>`` and ``writes: N``) and, with ``--json``, the full
structured result. ``writes`` counts files under the project root whose bytes
were created or changed; the machine-global install record is never a project
write.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

READY = "ready"
WARNING = "warning"
REPAIR_NEEDED = "repair-needed"
REPAIR_PREVIEW = "repair-preview"
REPAIRED = "repaired"
ADOPTABLE = "adoptable"
ADOPTED = "adopted"
CREATED = "created"
NONE = "none"
FAILED = "failed"

#: The complete contract. Documented above; tested in test_status_contract.py.
STATUSES = (
    READY, WARNING, REPAIR_NEEDED, REPAIR_PREVIEW, REPAIRED,
    ADOPTABLE, ADOPTED, CREATED, NONE, FAILED,
)

#: Statuses that must never be reported by a run that wrote to the project.
ZERO_WRITE_STATUSES = frozenset(
    {READY, WARNING, REPAIR_NEEDED, REPAIR_PREVIEW, ADOPTABLE, NONE, FAILED}
)

#: Modes. ``detect`` is retained as a read-only alias of ``check`` so existing
#: hooks keep working; it performs no writes (item 2).
MODES = ("check", "detect", "adopt", "create", "repair")

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_REPAIR_NEEDED = 2


@dataclass
class Result:
    status: str
    mode: str
    root: str
    message: str = ""
    writes: int = 0
    files_written: list[str] = field(default_factory=list)
    findings: list[dict] = field(default_factory=list)
    roles: list[dict] = field(default_factory=list)
    plan: dict | None = None
    backup: dict | None = None
    schema_version: int | None = None
    plugin_version: str = ""
    error: dict | None = None

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError("unknown status %r (contract: %s)" % (self.status, ", ".join(STATUSES)))

    def assert_contract(self) -> None:
        """Enforce the invariants the contract promises. Raises AssertionError on
        a violation so a bug surfaces here rather than as a quiet lie to the user."""
        if self.status in ZERO_WRITE_STATUSES and self.writes:
            raise AssertionError(
                "status %r promises zero project writes but %d file(s) were written: %s"
                % (self.status, self.writes, self.files_written))
        if self.writes != len(self.files_written):
            raise AssertionError(
                "writes=%d disagrees with files_written=%d" % (self.writes, len(self.files_written)))

    @property
    def exit_code(self) -> int:
        if self.status == FAILED:
            return EXIT_FAILED
        return EXIT_OK

    def strict_exit_code(self) -> int:
        if self.status == FAILED:
            return EXIT_FAILED
        if self.status == REPAIR_NEEDED:
            return EXIT_REPAIR_NEEDED
        return EXIT_OK

    def as_dict(self) -> dict:
        data = {
            "status": self.status,
            "mode": self.mode,
            "root": self.root,
            "writes": self.writes,
            "filesWritten": list(self.files_written),
            "findings": list(self.findings),
            "roles": list(self.roles),
        }
        if self.message:
            data["message"] = self.message
        if self.plan is not None:
            data["plan"] = self.plan
        if self.backup is not None:
            data["backup"] = self.backup
        if self.schema_version is not None:
            data["schemaVersion"] = self.schema_version
        if self.plugin_version:
            data["pluginVersion"] = self.plugin_version
        if self.error is not None:
            data["error"] = self.error
        return data

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), indent=2, ensure_ascii=False)

    def contract_lines(self) -> list[str]:
        """The two lines every caller may parse, in every mode, quiet or not."""
        return ["virtuoso-status: %s" % self.status, "writes: %d" % self.writes]
