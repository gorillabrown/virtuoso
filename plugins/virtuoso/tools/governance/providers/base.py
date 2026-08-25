"""The work-register provider interface (items 22, 28, 31, 32, 33).

A ceremony never opens a work register directly. It asks the registry which
provider serves the ``workRegister`` role, negotiates capabilities, and then uses
only the capabilities that provider actually offers. A CSV file, a markdown
table, a spreadsheet, a connector-backed task manager, an issue tracker, a
database, and a read-only cached snapshot are all equally valid registers.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import asdict, dataclass, field

from ..errors import CapabilityError, ConcurrencyError

# --- capabilities -------------------------------------------------------------

LIST_ACTIVE = "list-active"
READ_SEQUENCE = "read-sequence"
READ_STATUS = "read-status"
WRITE_STATUS = "write-status"
READ_PREREQUISITES = "read-prerequisites"
READ_EFFORT = "read-effort"
STORE_SPEC_LINK = "store-spec-link"
RECORD_COMPLETION = "record-completion"
NEXT_ELIGIBLE = "next-eligible"

ALL_CAPABILITIES = (
    LIST_ACTIVE, READ_SEQUENCE, READ_STATUS, WRITE_STATUS, READ_PREREQUISITES,
    READ_EFFORT, STORE_SPEC_LINK, RECORD_COMPLETION, NEXT_ELIGIBLE,
)

#: Capabilities that mutate the register.
MUTATIONS = frozenset({WRITE_STATUS, STORE_SPEC_LINK, RECORD_COMPLETION})

# --- canonical vocabulary -----------------------------------------------------

#: Canonical statuses. A project's own vocabulary maps onto these (item 27); the
#: literal words "Queued", "In Flight", ... are never required.
QUEUED = "queued"
IN_FLIGHT = "in-flight"
BLOCKED = "blocked"
COMPLETED = "completed"
DISSOLVED = "dissolved"
SUPERSEDED = "superseded"
UNKNOWN = "unknown"

CANONICAL_STATUSES = (QUEUED, IN_FLIGHT, BLOCKED, COMPLETED, DISSOLVED, SUPERSEDED, UNKNOWN)
#: Statuses that take an item out of the live pipeline.
TERMINAL_STATUSES = frozenset({COMPLETED, DISSOLVED, SUPERSEDED})

STUB = "stub"
FULL_SPEC = "full-spec"


@dataclass
class WorkItem:
    id: str
    title: str = ""
    sequence: int | None = None
    status: str = UNKNOWN            # canonical
    raw_status: str = ""             # exactly as the register spells it
    written_status: str = ""         # canonical: "" | stub | full-spec
    raw_written_status: str = ""
    prerequisites: list[str] = field(default_factory=list)
    effort: str = ""
    lane: str = ""
    group: str = ""
    spec_link: str = ""
    branch: str = ""
    started: str = ""
    completed: str = ""
    evidence: str = ""
    description: str = ""
    notes: str = ""
    #: Opaque token identifying the version of this item that was read.
    #: A mutation passes it back so the provider can detect a concurrent change.
    revision: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class Snapshot:
    """A point-in-time read of a register, with the provenance every derived
    metric must cite (items 29, 31)."""

    items: list[WorkItem]
    provider: str
    source: str
    taken_at: str
    fields: list[str] = field(default_factory=list)
    stale: bool = False
    stale_reason: str = ""

    def provenance(self) -> dict:
        data = {
            "provider": self.provider,
            "source": self.source,
            "takenAt": self.taken_at,
            "fields": list(self.fields),
            "stale": self.stale,
        }
        if self.stale_reason:
            data["staleReason"] = self.stale_reason
        return data


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- the interface ------------------------------------------------------------


class WorkRegisterProvider:
    """Base class. Subclasses declare ``capabilities`` and implement what they
    declare; every unimplemented capability raises :class:`CapabilityError` with a
    message naming the provider and the missing capability."""

    #: Short provider name, matching the registry's ``provider`` value.
    name = "base"

    def __init__(self, *, source: str, mapping=None, read_only: bool = False) -> None:
        self.source = source
        self.mapping = mapping
        self.read_only = read_only

    # -- negotiation ---------------------------------------------------------

    @property
    def capabilities(self) -> frozenset[str]:
        return frozenset()

    def supports(self, capability: str) -> bool:
        if capability in MUTATIONS and self.read_only:
            return False
        return capability in self.capabilities

    def require(self, *capabilities: str) -> None:
        """Capability negotiation (item 28): a ceremony calls this up front so it
        fails with a clear, actionable message instead of half-way through."""
        missing = [c for c in capabilities if not self.supports(c)]
        if missing:
            raise CapabilityError(
                "provider %r does not support: %s (available: %s)"
                % (self.name, ", ".join(sorted(missing)),
                   ", ".join(sorted(self.capabilities)) or "none"),
                detail={"provider": self.name, "missing": sorted(missing),
                        "available": sorted(self.capabilities)},
            )

    def describe(self) -> dict:
        return {
            "provider": self.name,
            "source": self.source,
            "readOnly": self.read_only,
            "capabilities": sorted(self.capabilities),
        }

    # -- reads ---------------------------------------------------------------

    def snapshot(self) -> Snapshot:
        raise CapabilityError("provider %r cannot produce a snapshot" % self.name)

    def list_active(self) -> list[WorkItem]:
        self.require(LIST_ACTIVE)
        return [i for i in self.snapshot().items if not i.is_terminal]

    def get(self, item_id: str) -> WorkItem | None:
        for item in self.snapshot().items:
            if item.id == item_id:
                return item
        return None

    def next_eligible(self) -> WorkItem | None:
        """The next item whose prerequisites are all terminal, in sequence order.

        Default implementation works for any provider that can list and sequence;
        providers with a server-side notion of "next" override it.
        """
        self.require(NEXT_ELIGIBLE)
        snap = self.snapshot()
        terminal = {i.id for i in snap.items if i.is_terminal}
        active = [i for i in snap.items if not i.is_terminal and i.status != BLOCKED]
        active.sort(key=lambda i: (i.sequence is None, i.sequence or 0, i.id))
        for item in active:
            if all(p in terminal for p in item.prerequisites if p):
                return item
        return None

    # -- mutations -----------------------------------------------------------

    def set_status(self, item_id: str, status: str, *, revision: str = "",
                   raw: str = "") -> WorkItem:
        raise CapabilityError("provider %r cannot write status" % self.name)

    def store_spec_link(self, item_id: str, link: str, *, revision: str = "") -> WorkItem:
        raise CapabilityError("provider %r cannot store specification links" % self.name)

    def record_completion(self, item_id: str, *, completed: str = "", evidence: str = "",
                          revision: str = "") -> WorkItem:
        raise CapabilityError("provider %r cannot record completion" % self.name)

    # -- concurrency ---------------------------------------------------------

    def check_revision(self, item: WorkItem, revision: str) -> None:
        """Optimistic-concurrency guard (item 32). An empty ``revision`` opts out
        explicitly — callers that never read the item first cannot claim to know
        it is unchanged, and must say so by passing ``""``."""
        if revision and item.revision and revision != item.revision:
            raise ConcurrencyError(
                "item %r changed since it was read (read %s, now %s); re-read and retry"
                % (item.id, revision[:12], item.revision[:12]),
                detail={"item": item.id, "expected": revision, "actual": item.revision},
            )
