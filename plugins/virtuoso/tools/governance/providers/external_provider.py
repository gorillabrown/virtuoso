"""Connector-backed, issue-tracker, and database registers (items 17, 23, 28, 31, 34).

The plugin cannot call a host's connectors from Python, and pretending otherwise
would be the same class of dishonesty this redesign removes. So an external
register is modelled explicitly:

* **reads** come from a registered snapshot role, always timestamped and marked
  stale when it ages out (item 31). Without a snapshot the provider withdraws its
  read capabilities and says exactly what to register.
* **mutations** are *planned*, not performed: :meth:`plan_mutation` returns a
  structured instruction the ceremony carries out with the host's own tools, and
  :meth:`confirm` records the outcome. An unconfirmed mutation leaves a recovery
  record (item 34) so nothing is silently half-done.
* **creation** is the one mutation with no item to read first. Its concurrency
  guard is proof of *absence* against a fresh snapshot, and its idempotency is
  held by the recovery trail: a confirmed creation is never planned twice, even
  in the window before the snapshot shows the new item.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .. import identifiers
from ..errors import DuplicateItemError
from . import base, mapping as mapping_mod, recovery


_OPERATION_CAPABILITIES = {
    "set-status": base.WRITE_STATUS,
    "store-spec-link": base.STORE_SPEC_LINK,
    "record-completion": base.RECORD_COMPLETION,
    "create-item": base.CREATE_ITEM,
}
CREATE_OPERATION = "create-item"


@dataclass
class PendingMutation:
    """An instruction for the ceremony to execute against the external system."""

    operation: str                 # set-status | store-spec-link | record-completion
    register: str                  # the external identifier
    item_id: str
    fields: dict = field(default_factory=dict)
    #: The revision the item carried when it was read, for the ceremony to
    #: re-verify before it writes (item 32).
    expected_revision: str = ""
    idempotency_key: str = ""
    recovery_id: str = ""
    # -- creation only: the evidence that the item did not exist when planned ---
    expected_absent: bool = False
    snapshot_taken_at: str = ""
    id_field: str = ""
    project_fields: dict = field(default_factory=dict)
    defaults_applied: dict = field(default_factory=dict)
    preconditions: list = field(default_factory=list)
    postconditions: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def as_dict(self) -> dict:
        data = {
            "operation": self.operation,
            "register": self.register,
            "itemId": self.item_id,
            "fields": dict(self.fields),
            "expectedRevision": self.expected_revision,
            "idempotencyKey": self.idempotency_key,
            "recoveryId": self.recovery_id,
        }
        if self.operation == CREATE_OPERATION:
            data.update({
                "expectedAbsent": self.expected_absent,
                "snapshotTakenAt": self.snapshot_taken_at,
                "idField": self.id_field,
                "projectFields": dict(self.project_fields),
                "defaultsApplied": dict(self.defaults_applied),
                "preconditions": list(self.preconditions),
                "postconditions": list(self.postconditions),
                "warnings": list(self.warnings),
            })
        return data


class ExternalWorkRegister(base.WorkRegisterProvider):
    name = "external"

    def __init__(self, *, source: str, mapping=None, snapshot_provider=None,
                 provider_kind: str = "external", read_only: bool = False,
                 recovery_root: str = "", may_create: bool = True,
                 create_denied_reason: str = "") -> None:
        super().__init__(source=source, mapping=mapping or mapping_mod.Mapping(),
                         read_only=read_only, may_create=may_create,
                         create_denied_reason=create_denied_reason)
        self.identifier = identifiers.parse(source)
        self.provider_kind = provider_kind
        self._snapshot_provider = snapshot_provider
        self._recovery_root = recovery_root

    @property
    def capabilities(self) -> frozenset[str]:
        available: set[str] = set()
        if self._snapshot_provider is not None:
            available.update({
                base.LIST_ACTIVE, base.READ_SEQUENCE, base.READ_STATUS,
                base.READ_PREREQUISITES, base.READ_EFFORT, base.NEXT_ELIGIBLE,
            })
        # These capabilities are fulfilled through a host-executed mutation plan,
        # never by pretending Python can call the connector directly.
        if not self.read_only:
            available.update(base.MUTATIONS)
        return frozenset(available)

    def require(self, *capabilities: str) -> None:
        if self._snapshot_provider is None and any(c not in base.MUTATIONS for c in capabilities):
            raise base.CapabilityError(
                "external register %s has no snapshot to read from. Register a `snapshot` "
                "role and name it in policy.workRegister.snapshot, or refresh it with the "
                "host's connector before running read ceremonies." % self.source,
                detail={"register": self.source})
        super().require(*capabilities)

    def describe(self) -> dict:
        data = super().describe()
        data["providerKind"] = self.provider_kind
        data["externalIdentifier"] = self.source
        data["scheme"] = self.identifier.scheme
        data["mutationMode"] = "planned"
        data["plannedOperations"] = sorted(_OPERATION_CAPABILITIES)
        data["hasSnapshot"] = self._snapshot_provider is not None
        data["durableRecovery"] = bool(self._recovery_root)
        return data

    def snapshot(self) -> base.Snapshot:
        self.require(base.LIST_ACTIVE)
        snap = self._snapshot_provider.snapshot()
        # The snapshot's *source* is the external register, not the cache file.
        return base.Snapshot(items=snap.items, provider="%s+snapshot" % self.provider_kind,
                             source=self.source, taken_at=snap.taken_at, fields=snap.fields,
                             stale=snap.stale, stale_reason=snap.stale_reason)

    # -- planned mutations ---------------------------------------------------

    def _reject(self, operation: str):
        raise base.CapabilityError(
            "external register %s cannot be mutated from the plugin. Call "
            "plan_mutation(%r, ...) and execute the returned instruction with the host's "
            "connector, then confirm() the result." % (self.source, operation),
            detail={"register": self.source, "operation": operation, "mode": "planned"})

    def set_status(self, item_id, status, *, revision="", raw=""):
        self._reject("set-status")

    def store_spec_link(self, item_id, link, *, revision=""):
        self._reject("store-spec-link")

    def record_completion(self, item_id, *, completed="", evidence="", revision=""):
        self._reject("record-completion")

    def create_item(self, fields):
        self._reject(CREATE_OPERATION)

    def plan_mutation(self, operation: str, item_id: str, fields: dict, *,
                      revision: str = "", idempotency_key: str = "") -> PendingMutation:
        capability = _OPERATION_CAPABILITIES.get(operation)
        if capability is None:
            raise base.CapabilityError(
                "external register %s received unsupported planned mutation %r; "
                "supported operations are %s"
                % (self.source, operation, ", ".join(sorted(_OPERATION_CAPABILITIES))))
        self.require(capability)
        if not item_id:
            raise base.CapabilityError("external mutation item id must not be empty")
        if not isinstance(fields, dict):
            raise base.CapabilityError("external mutation fields must be a dictionary")

        if operation == CREATE_OPERATION:
            return self._plan_creation(item_id, fields, revision=revision,
                                       idempotency_key=idempotency_key)

        if self._snapshot_provider is not None:
            current = self.get(item_id)
            if current is not None:
                self.check_revision(current, revision)

        key = idempotency_key or "%s:%s:%s" % (operation, item_id, sorted(fields.items()))
        plan = PendingMutation(
            operation=operation, register=self.source, item_id=item_id,
            fields=dict(fields), expected_revision=revision,
            idempotency_key=key,
        )
        if self._recovery_root:
            record = recovery.open_record(
                self._recovery_root, operation="external-%s" % operation, item_id=item_id,
                completed_steps=["planned external mutation"],
                remaining_steps=["execute the host connector instruction",
                                 "confirm the external mutation result"],
                detail={
                    "register": self.source,
                    "operation": operation,
                    "fields": dict(fields),
                    "expectedRevision": revision,
                    "idempotencyKey": key,
                },
            )
            plan.recovery_id = record.id
        return plan

    # -- creation ------------------------------------------------------------

    def _plan_creation(self, item_id: str, fields: dict, *, revision: str,
                       idempotency_key: str) -> PendingMutation:
        """Plan bringing a new item into the external register.

        The guard rails, in order: no revision (there is nothing to compare); a
        snapshot must exist and be fresh (absence can only be proven against a
        read the plan can cite); the fields validate exactly as a local creation
        would; the id must be absent from the snapshot, terminal items included;
        and the recovery trail must not already hold a confirmed creation under
        the same idempotency key.
        """
        if revision:
            raise base.CapabilityError(
                "a creation carries no revision to check — the item must not exist yet. "
                "Pass an empty revision.", detail={"operation": CREATE_OPERATION})
        if self._snapshot_provider is None:
            raise base.CapabilityError(
                "external register %s has no snapshot, so a creation cannot prove that item %r "
                "is absent. Register a `snapshot` role, name it in policy.workRegister.snapshot, "
                "and refresh it with the host's connector before planning a creation."
                % (self.source, item_id), detail={"register": self.source, "item": item_id})
        snap = self.snapshot()
        if snap.stale:
            raise base.CapabilityError(
                "the snapshot of %s is stale (%s); a creation must prove absence against a "
                "fresh read. Refresh it with the host's connector, then plan again."
                % (self.source, snap.stale_reason or "no timestamp"),
                detail={"register": self.source, "staleReason": snap.stale_reason})

        requested = dict(fields)
        requested.setdefault("id", item_id)
        if str(requested.get("id") or "").strip() != item_id:
            raise base.CapabilityError(
                "the planned item id %r and fields.id %r disagree" % (item_id, requested.get("id")))
        prepared, defaults = base.prepare_creation(requested, self.mapping.statuses)

        existing = next((i for i in snap.items if i.id == item_id), None)
        if existing is not None:
            raise DuplicateItemError(
                "item %r already exists in %s (status %s, revision %s); creation is not an "
                "update. Change it through set-status / store-spec-link, or refresh the "
                "snapshot if you believe this is stale."
                % (item_id, self.source, existing.status, existing.revision[:12] or "unknown"),
                detail={"item": item_id, "register": self.source,
                        "status": existing.status, "revision": existing.revision})

        key = idempotency_key or "%s:%s:%s" % (CREATE_OPERATION, self.source, item_id)
        id_field = self.mapping.fields.column_for("id")
        preconditions = [
            "no item whose %r equals %r exists in %s — search before creating; the host's "
            "own duplicate handling is not relied on" % (id_field, item_id, self.source),
        ]
        postconditions = [
            "read the created item back and pass its provider identifier and revision to "
            "mutation-confirm (--provider-id, --actual-revision)",
            "refresh the canonical snapshot so the new item is readable through the provider",
            "verify `recovery` reports nothing outstanding",
        ]
        known = {i.id for i in snap.items}
        warnings = [
            "prerequisite %r is not in the register snapshot taken %s" % (p, snap.taken_at)
            for p in prepared["prerequisites"] if p not in known
        ]

        superseded: list[str] = []
        if self._recovery_root:
            prior = recovery.find(self._recovery_root,
                                  operation="external-%s" % CREATE_OPERATION,
                                  idempotency_key=key)
            for record in prior:
                detail_blob = record.get("detail") if isinstance(record.get("detail"), dict) else {}
                last = detail_blob.get("lastConfirmation") or {}
                if record.get("resolved"):
                    if detail_blob.get("supersededBy"):
                        continue                    # a failed attempt, already replaced
                    raise DuplicateItemError(
                        "a creation of %r in %s was already confirmed under idempotency key %r "
                        "(recovery record %s, provider item %s); it is not repeated. Refresh the "
                        "snapshot so the item becomes readable."
                        % (item_id, self.source, key, record.get("id"),
                           last.get("providerItemId") or "unrecorded"),
                        detail={"item": item_id, "recoveryId": record.get("id"),
                                "idempotencyKey": key})
                if not last:
                    raise base.CapabilityError(
                        "a creation plan for %r is still outstanding (recovery record %s) and "
                        "has not been confirmed; confirm it with --succeeded or --failed before "
                        "planning again" % (item_id, record.get("id")),
                        detail={"item": item_id, "recoveryId": record.get("id")})
                # An attempt the host reported as failed: re-planning is a retry, but
                # a timeout can fail *after* creating, so the host must look first.
                preconditions.insert(0, (
                    "a previous attempt (%s) was confirmed failed; verify with the host that it "
                    "created nothing before executing" % record.get("id")))
                superseded.append(str(record.get("id")))

        plan = PendingMutation(
            operation=CREATE_OPERATION, register=self.source, item_id=item_id,
            fields=dict(prepared), expected_revision="", idempotency_key=key,
            expected_absent=True, snapshot_taken_at=snap.taken_at, id_field=id_field,
            project_fields=self._project_fields(prepared), defaults_applied=defaults,
            preconditions=preconditions, postconditions=postconditions, warnings=warnings,
        )
        if self._recovery_root:
            record = recovery.open_record(
                self._recovery_root, operation="external-%s" % CREATE_OPERATION,
                item_id=item_id,
                completed_steps=["planned external creation"],
                remaining_steps=["execute the host connector instruction",
                                 "confirm the external mutation result"],
                detail={
                    "register": self.source,
                    "operation": CREATE_OPERATION,
                    "fields": dict(prepared),
                    "expectedRevision": "",
                    "expectedAbsent": True,
                    "snapshotTakenAt": snap.taken_at,
                    "idempotencyKey": key,
                },
            )
            plan.recovery_id = record.id
            for old_id in superseded:
                recovery.note(self._recovery_root, old_id, {"supersededBy": record.id})
                recovery.resolve(self._recovery_root, old_id)
        return plan

    def _project_fields(self, prepared: dict) -> dict:
        """The same values keyed by the project's own column names — what the
        ceremony hands to the host connector."""
        out = {}
        for key, value in prepared.items():
            column = (self.mapping.fields.column_for(key)
                      if key in base.CREATABLE_FIELDS else key)
            out[column] = value if isinstance(value, int) else base.cell_text(key, value)
        return out

    def confirm(self, plan: PendingMutation, *, succeeded: bool,
                actual_revision: str = "", detail: dict | None = None,
                provider_item_id: str = "") -> dict:
        """Record the host connector's result and resolve recovery only on success."""
        if plan.register != self.source:
            raise base.CapabilityError(
                "mutation plan targets %s, not this external register %s"
                % (plan.register, self.source))
        if plan.recovery_id and self._recovery_root:
            record = recovery.get_record(self._recovery_root, plan.recovery_id)
            if record is None:
                raise base.CapabilityError(
                    "external mutation recovery record %r is missing or unsafe"
                    % plan.recovery_id)
            expected = {
                "register": self.source,
                "operation": plan.operation,
                "item": plan.item_id,
                "idempotency": plan.idempotency_key,
            }
            detail_blob = record.get("detail") if isinstance(record.get("detail"), dict) else {}
            actual = {
                "register": detail_blob.get("register"),
                "operation": detail_blob.get("operation"),
                "item": record.get("item_id"),
                "idempotency": detail_blob.get("idempotencyKey"),
            }
            if actual != expected:
                raise base.CapabilityError("external mutation confirmation does not match recovery record")
        outcome = {
            "succeeded": bool(succeeded),
            "operation": plan.operation,
            "itemId": plan.item_id,
            "idempotencyKey": plan.idempotency_key,
            "actualRevision": actual_revision,
            "recoveryId": plan.recovery_id,
            "detail": dict(detail or {}),
        }
        if provider_item_id or plan.operation == CREATE_OPERATION:
            outcome["providerItemId"] = provider_item_id
        if plan.operation == CREATE_OPERATION and succeeded:
            outcome["nextStep"] = ("refresh the canonical snapshot so the new item is "
                                   "readable through the provider")
        if plan.recovery_id and self._recovery_root:
            recovery.note(self._recovery_root, plan.recovery_id,
                          {"lastConfirmation": outcome})
            if succeeded:
                recovery.resolve(self._recovery_root, plan.recovery_id)
        return outcome
