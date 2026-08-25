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
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .. import identifiers
from . import base, mapping as mapping_mod


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

    def as_dict(self) -> dict:
        return {
            "operation": self.operation,
            "register": self.register,
            "itemId": self.item_id,
            "fields": dict(self.fields),
            "expectedRevision": self.expected_revision,
            "idempotencyKey": self.idempotency_key,
        }


class ExternalWorkRegister(base.WorkRegisterProvider):
    name = "external"

    def __init__(self, *, source: str, mapping=None, snapshot_provider=None,
                 provider_kind: str = "external", read_only: bool = False) -> None:
        super().__init__(source=source, mapping=mapping or mapping_mod.Mapping(),
                         read_only=read_only)
        self.identifier = identifiers.parse(source)
        self.provider_kind = provider_kind
        self._snapshot_provider = snapshot_provider

    @property
    def capabilities(self) -> frozenset[str]:
        if self._snapshot_provider is None:
            return frozenset()
        return frozenset({base.LIST_ACTIVE, base.READ_SEQUENCE, base.READ_STATUS,
                          base.READ_PREREQUISITES, base.READ_EFFORT, base.NEXT_ELIGIBLE})

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
        data["hasSnapshot"] = self._snapshot_provider is not None
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

    def plan_mutation(self, operation: str, item_id: str, fields: dict, *,
                      revision: str = "", idempotency_key: str = "") -> PendingMutation:
        if self.read_only:
            raise base.CapabilityError(
                "external register %s is registered read-only" % self.source)
        return PendingMutation(
            operation=operation, register=self.source, item_id=item_id,
            fields=dict(fields), expected_revision=revision,
            idempotency_key=idempotency_key or "%s:%s:%s" % (operation, item_id,
                                                             sorted(fields.items())),
        )
