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

from ..errors import CapabilityError, ConcurrencyError, DuplicateItemError

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
#: Bring a new item into existence. The one mutation that has no item to read
#: first: its concurrency guard is proof of *absence*, not a revision.
CREATE_ITEM = "create-item"

ALL_CAPABILITIES = (
    LIST_ACTIVE, READ_SEQUENCE, READ_STATUS, WRITE_STATUS, READ_PREREQUISITES,
    READ_EFFORT, STORE_SPEC_LINK, RECORD_COMPLETION, NEXT_ELIGIBLE, CREATE_ITEM,
)

#: Capabilities that mutate the register.
MUTATIONS = frozenset({WRITE_STATUS, STORE_SPEC_LINK, RECORD_COMPLETION, CREATE_ITEM})

#: Canonical fields a creation may set. ``revision`` and the ``raw_*`` spellings
#: are computed by the provider from what it wrote, never supplied.
CREATABLE_FIELDS = (
    "id", "title", "sequence", "status", "written_status", "prerequisites", "effort",
    "lane", "group", "spec_link", "branch", "started", "completed", "evidence",
    "description", "notes",
)

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


# --- creation ------------------------------------------------------------------


def supplied_fields(fields) -> set[str]:
    """The keys a creation request actually carries a value for. A field the
    caller left out is filled by a default or skipped; a field the caller *gave*
    must land somewhere, or the creation is refused naming the missing column."""
    if not isinstance(fields, dict):
        return set()
    return {str(k) for k, v in fields.items() if v not in (None, "", [], ())}


def prepare_creation(fields, statuses) -> tuple[dict, dict]:
    """Validate and normalize a creation request. Shared by every provider so a
    new item means the same thing in a CSV, a spreadsheet, and a connector plan.

    * ``fields`` must be a dictionary naming a non-empty ``id`` and ``title``.
    * ``status`` and ``written_status`` default to the project's own spelling of
      ``queued`` and ``stub`` when absent: an item enters the pipeline, it is never
      born in flight or terminal by omission.
    * A canonical status token is translated to the project's spelling; a project
      spelling is kept verbatim; a word in neither vocabulary is refused, because
      an item whose status no ceremony can read is invisible to all of them.
    * ``prerequisites`` may be a list or a delimited string and comes back a list;
      ``sequence`` must be numeric.

    Returns ``(normalized fields, defaults applied)``.
    """
    if not isinstance(fields, dict):
        raise CapabilityError("creation fields must be a dictionary")
    out = {str(k): v for k, v in fields.items() if v is not None}
    item_id = str(out.get("id", "") or "").strip()
    title = str(out.get("title", "") or "").strip()
    if not item_id:
        raise CapabilityError("a new work item needs a non-empty `id`")
    if not title:
        raise CapabilityError("a new work item needs a non-empty `title`")
    out["id"], out["title"] = item_id, title

    defaults: dict = {}
    if not str(out.get("status", "") or "").strip():
        out["status"] = statuses.to_project(QUEUED)
        defaults["status"] = out["status"]
    if not str(out.get("written_status", "") or "").strip():
        out["written_status"] = statuses.written_to_project(STUB)
        defaults["written_status"] = out["written_status"]

    status = str(out["status"]).strip()
    if status in CANONICAL_STATUSES:
        status = statuses.to_project(status)
    if statuses.to_canonical(status) == UNKNOWN:
        raise CapabilityError(
            "status %r is not in the project's vocabulary "
            "(policy.workRegister.statusMappings); a new item with an unreadable status is "
            "invisible to every ceremony" % status,
            detail={"field": "status", "value": status})
    out["status"] = status

    written = str(out["written_status"]).strip()
    if written in (STUB, FULL_SPEC):
        written = statuses.written_to_project(written)
    if statuses.written_to_canonical(written) not in (STUB, FULL_SPEC):
        raise CapabilityError(
            "specification state %r is not in the project's vocabulary "
            "(policy.workRegister.statusMappings.written)" % written,
            detail={"field": "written_status", "value": written})
    out["written_status"] = written

    prerequisites = out.get("prerequisites", [])
    if isinstance(prerequisites, str):
        prerequisites = [p.strip() for p in prerequisites.replace(";", ",").split(",")
                         if p.strip()]
    elif isinstance(prerequisites, (list, tuple)):
        prerequisites = [str(p).strip() for p in prerequisites if str(p).strip()]
    else:
        raise CapabilityError("prerequisites must be a list or a delimited string")
    out["prerequisites"] = prerequisites

    if "sequence" in out and str(out["sequence"]).strip() != "":
        try:
            out["sequence"] = int(float(out["sequence"]))
        except (TypeError, ValueError):
            raise CapabilityError("sequence %r is not a number" % (out["sequence"],))
    elif "sequence" in out:
        del out["sequence"]
    return out, defaults


def cell_text(field_name: str, value) -> str:
    """The textual form a row-based register stores a creation value in."""
    if field_name == "prerequisites" and isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    if value is None:
        return ""
    return str(value)


def check_duplicate(existing: "WorkItem", prepared: dict, supplied: set, statuses,
                    source: str) -> None:
    """The idempotency rule for creation (item 33). Re-issuing the *same* creation
    is a no-op that returns the existing item; a creation whose supplied fields
    disagree with the existing item is a conflict, refused by name, because a
    creation must never turn into a silent overwrite."""
    differing = []
    for key in sorted(supplied):
        if key not in CREATABLE_FIELDS or key == "id":
            continue
        wanted = prepared.get(key)
        current = getattr(existing, key)
        if key == "status":
            same = statuses.to_canonical(existing.raw_status) == statuses.to_canonical(wanted)
        elif key == "written_status":
            same = (statuses.written_to_canonical(existing.raw_written_status)
                    == statuses.written_to_canonical(wanted))
        elif key == "prerequisites":
            same = list(current or []) == list(wanted or [])
        elif key == "sequence":
            same = current == wanted
        else:
            same = str(current or "").strip() == str(wanted or "").strip()
        if not same:
            differing.append(key)
    if differing:
        raise DuplicateItemError(
            "item %r already exists in %s and differs in %s; creation is not an update. "
            "Change the existing item through set-status / store-spec-link instead."
            % (existing.id, source, ", ".join(differing)),
            detail={"item": existing.id, "differing": differing, "register": source})


# --- the interface ------------------------------------------------------------


class WorkRegisterProvider:
    """Base class. Subclasses declare ``capabilities`` and implement what they
    declare; every unimplemented capability raises :class:`CapabilityError` with a
    message naming the provider and the missing capability."""

    #: Short provider name, matching the registry's ``provider`` value.
    name = "base"

    def __init__(self, *, source: str, mapping=None, read_only: bool = False,
                 may_create: bool = True, create_denied_reason: str = "") -> None:
        self.source = source
        self.mapping = mapping
        self.read_only = read_only
        #: Creation is a separately authorized act (``policy.workRegister.creators``).
        #: A writer that may change items is not thereby entitled to bring new
        #: ones into existence.
        self.may_create = may_create
        self.create_denied_reason = create_denied_reason

    # -- negotiation ---------------------------------------------------------

    @property
    def capabilities(self) -> frozenset[str]:
        return frozenset()

    def supports(self, capability: str) -> bool:
        if capability in MUTATIONS and self.read_only:
            return False
        if capability == CREATE_ITEM and not self.may_create:
            return False
        return capability in self.capabilities

    def require(self, *capabilities: str) -> None:
        """Capability negotiation (item 28): a ceremony calls this up front so it
        fails with a clear, actionable message instead of half-way through."""
        missing = [c for c in capabilities if not self.supports(c)]
        if missing:
            why = ""
            if (CREATE_ITEM in missing and CREATE_ITEM in self.capabilities
                    and not self.read_only and not self.may_create):
                why = "; " + (self.create_denied_reason
                              or "this actor is not authorized to create work items")
            raise CapabilityError(
                "provider %r does not support: %s (available: %s)%s"
                % (self.name, ", ".join(sorted(missing)),
                   ", ".join(sorted(self.capabilities)) or "none", why),
                detail={"provider": self.name, "missing": sorted(missing),
                        "available": sorted(self.capabilities)},
            )

    def describe(self) -> dict:
        data = {
            "provider": self.name,
            "source": self.source,
            "readOnly": self.read_only,
            "capabilities": sorted(self.capabilities),
            "mayCreate": self.supports(CREATE_ITEM),
        }
        if CREATE_ITEM in self.capabilities and not self.read_only and not self.may_create:
            data["createDenied"] = self.create_denied_reason
        return data

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

    def create_item(self, fields: dict) -> WorkItem:
        """Bring a new item into the register (capability ``create-item``).

        ``fields`` uses canonical names (see :data:`CREATABLE_FIELDS`); extra keys
        are project columns. Re-issuing an identical creation returns the existing
        item unchanged; a conflicting one raises :class:`DuplicateItemError`.
        """
        raise CapabilityError("provider %r cannot create work items" % self.name)

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
