"""The guided move of a project's work register to another tool.

``preview`` reads the current register through its provider and says what a move
would do: the open items that would be created in the new register, and how many
finished items stay in the terminal ledger only. It writes nothing.

``plan`` writes one move record — a recovery record whose ``detail.items`` carries
each open item's state, ``pending`` or ``created`` — and either prints one create
instruction per item (an external target, for the session's connector) or writes the
rows itself (a local target). ``confirm`` marks one item ``created`` after the
session read it back. ``finish`` compares the new register, as read back, with the
record, and only on a match repoints the registry and resolves the record.
"""
from __future__ import annotations

import dataclasses
import json
import os

from . import (identifiers, policy as policy_mod, providers, registry as registry_mod,
               repair as repair_mod, schema, textio, workspace)
from .errors import CapabilityError, GovernanceError
from .providers import base, mapping as mapping_mod, recovery, snapshot_provider
from .providers.external_provider import CREATE_OPERATION, ExternalWorkRegister, PendingMutation

#: The canonical fields the new register's mappings must name a column for.
REQUIRED_FIELDS = ("id", "title", "status")

#: The recovery record's operation, and the states of each open item it copies.
OPERATION = "move-register"
PENDING, CREATED = "pending", "created"

_LOCAL_EXTENSIONS = {ext: kind for kind, (_, _, ext) in workspace.LOCAL_REGISTER_KINDS.items()}


def read_mappings(root: str, path: str) -> dict:
    """The mappings file: ``{"fieldMappings": {...}, "statusMappings": {...}}``."""
    full = path if os.path.isabs(path) else os.path.join(root, path)
    text = textio.read_text(full)
    if text is None:
        raise GovernanceError("%s cannot be read as text" % path)
    try:
        mappings = json.loads(text)
    except ValueError as exc:
        raise GovernanceError("%s must be valid JSON: %s" % (path, exc)) from exc
    if not isinstance(mappings, dict):
        raise GovernanceError("%s must be a JSON object" % path)
    for key in ("fieldMappings", "statusMappings"):
        if not isinstance(mappings.get(key) or {}, dict):
            raise GovernanceError("%s: %s must be a JSON object" % (path, key))
    if mappings.get("fieldMappings"):
        # An old field name (lane) is read as its new one before anything is planned.
        mappings["fieldMappings"] = mapping_mod.canonical_field_mappings(
            mappings["fieldMappings"])
    return mappings


def resolve_target(reg, to: str) -> dict:
    """``{"target", "provider", "external"}`` for ``--to``: an external
    ``<scheme>:<id>``, a local kind (the layout ``create`` uses), or a local path."""
    if to in workspace.LOCAL_REGISTER_KINDS:
        provider, _, ext = workspace.LOCAL_REGISTER_KINDS[to]
        docs = reg.documentation_root or workspace.DEFAULT_DOC_ROOT
        path = "/".join((docs, workspace.DOC_SUBDIRS["operational"], "work-register" + ext))
        return {"target": path, "provider": provider, "external": False}
    if identifiers.looks_external(to):
        return {"target": identifiers.parse(to).raw, "provider": "connector", "external": True}
    kind = _LOCAL_EXTENSIONS.get(os.path.splitext(to)[1].lower())
    if kind is None:
        raise GovernanceError(
            "--to %r is neither a tool identifier (<scheme>:<id>, e.g. notion:database/abc or "
            "linear:team/ENG) "
            "nor a local register (csv, markdown, xlsx, or a .csv, .md or .xlsx path)" % to)
    full = os.path.abspath(to if os.path.isabs(to) else os.path.join(reg.root, to))
    rel = os.path.relpath(full, reg.root)
    if rel.startswith(".."):
        raise GovernanceError("--to %s is outside the project root %s" % (to, reg.root))
    return {"target": rel.replace(os.sep, "/"), "provider": workspace.LOCAL_REGISTER_KINDS[kind][0],
            "external": False}


def _same_register(reg, spec, target: dict) -> bool:
    if spec.is_external or target["external"]:
        return spec.is_external and target["external"] and spec.external == target["target"]
    here = os.path.normcase(os.path.abspath(os.path.join(reg.root, spec.path)))
    there = os.path.normcase(os.path.abspath(os.path.join(reg.root, target["target"])))
    return here == there


def _has_word(spellings) -> bool:
    if isinstance(spellings, str):
        spellings = [spellings]
    return isinstance(spellings, list) and any(str(s).strip() for s in spellings)


def preview(reg, to: str, mappings: dict) -> dict:
    """What a move to ``to`` would do. Raises :class:`GovernanceError` on a target
    equal to the current register, a local target file that already exists, mappings
    that miss a required field, or an open item whose status the new
    ``statusMappings`` has no word for."""
    return _read(reg, to, mappings)[0]


def _read(reg, to: str, mappings: dict) -> tuple[dict, list]:
    """``(preview payload, the open items as read)``."""
    target = resolve_target(reg, to)
    selection = providers.work_register(reg)
    spec = reg.role(selection.role_name)
    current = spec.external if spec.is_external else spec.path
    if _same_register(reg, spec, target):
        raise GovernanceError("--to %s is the current work register; there is nothing to move"
                              % target["target"])
    if not target["external"]:
        path = os.path.join(reg.root, target["target"])
        if os.path.exists(path):
            raise GovernanceError("--to %s already exists; a move creates a new register and "
                                  "never writes into an existing file" % target["target"])
        if not os.path.isdir(os.path.dirname(path)):
            raise GovernanceError("--to %s: its folder does not exist; a move creates no "
                                  "folders" % target["target"])
    fields = mappings.get("fieldMappings") or {}
    missing = [f for f in REQUIRED_FIELDS if not str(fields.get(f) or "").strip()]
    if missing:
        raise GovernanceError("the new mappings' fieldMappings name no column for %s; every "
                              "move needs %s" % (", ".join(missing), ", ".join(REQUIRED_FIELDS)))

    snap = selection.provider.snapshot()
    open_items = [i for i in snap.items if not i.is_terminal]
    statuses = mappings.get("statusMappings") or {}
    unmapped: dict[str, list[str]] = {}
    for item in open_items:
        if not _has_word(statuses.get(item.status)):
            label = "%s (%r)" % (item.status, item.raw_status) if item.raw_status else item.status
            unmapped.setdefault(label, []).append(item.id)
    if unmapped:
        raise GovernanceError(
            "the new mappings' statusMappings have no word for status %s; add one so the "
            "open items can be created. Nothing was written."
            % "; ".join("%s, held by %s" % (status, ", ".join(ids))
                        for status, ids in sorted(unmapped.items())))

    return {
        "from": current, "to": target["target"], "toProvider": target["provider"],
        "external": target["external"],
        "open": [{"id": i.id, "title": i.title, "status": i.status} for i in open_items],
        "finished": len(snap.items) - len(open_items),
        "mappings": {k: mappings.get(k) or {} for k in ("fieldMappings", "statusMappings")},
        "source": snap.source, "takenAt": snap.taken_at, "stale": snap.stale,
        "applied": False,
    }, open_items


# -- the plan and the per-item confirmations ----------------------------------------


def outstanding_move(root: str) -> dict | None:
    """The unresolved move record, if one is open."""
    return next((r for r in recovery.outstanding(root) if r.get("operation") == OPERATION),
                None)


def _creation_fields(item, declared: set, external: bool) -> dict:
    """The canonical fields copied for one open item. An external register has columns
    only for the fields its mappings name; a local one is seeded with every column."""
    names = [f for f in base.CREATABLE_FIELDS
             if not external or f in declared or f in REQUIRED_FIELDS]
    values = {f: getattr(item, f) for f in names}
    return {k: v for k, v in values.items() if v not in (None, "", [])}


def _instruction(target: str, mapping, declared: set, prepared: dict, defaults: dict) -> dict:
    """One create instruction in the create-item handshake's shape."""
    landing = {k: v for k, v in prepared.items() if k in declared or k == "id"}
    id_field = mapping.fields.column_for("id")
    # The handshake's own column mapping, so a moved item lands as a planned creation would.
    columns = ExternalWorkRegister(source=target, mapping=mapping)._project_fields(landing)
    return PendingMutation(
        operation=CREATE_OPERATION, register=target, item_id=prepared["id"],
        fields=landing, idempotency_key="%s:%s:%s" % (CREATE_OPERATION, target, prepared["id"]),
        expected_absent=True, id_field=id_field, project_fields=columns,
        defaults_applied={k: v for k, v in defaults.items() if k in landing},
        preconditions=["no item whose %r equals %r exists in %s — search before creating"
                       % (id_field, prepared["id"], target)],
        postconditions=["read the created item back, then record it: move-register --confirm "
                        "%s --provider-id <its identifier> --recovery-id <this record>"
                        % prepared["id"]],
    ).as_dict()


def _steps(items: list) -> tuple[list, list]:
    """``(completed, remaining)`` steps, derived from the per-item states."""
    done = ["previewed and approved"] + ["created %s (%s)" % (i["id"], i["providerId"])
                                         for i in items if i["state"] == CREATED]
    remaining = ["create %s" % i["id"] for i in items if i["state"] == PENDING]
    return done, remaining + ["finish: compare a fresh snapshot of the new register, then "
                              "repoint (move-register --finish)"]


def _save(root: str, payload: dict) -> None:
    payload["completed_steps"], payload["remaining_steps"] = _steps(payload["detail"]["items"])
    recovery.write(root, recovery.RecoveryRecord(**payload))


def _seed_local(path: str, provider: str, columns: list) -> None:
    """A new local register holding only its header row, in the columns ``create`` lays
    down, each named as the new mappings name it."""
    if provider == "xlsx":
        import openpyxl
        book = openpyxl.Workbook()
        book.active.append(columns)
        book.save(path)
    elif provider == "markdown":
        textio.write_if_changed(path, "# Work Register\n\n| %s |\n|%s\n"
                                % (" | ".join(columns), "---|" * len(columns)))
    else:
        textio.write_if_changed(path, ",".join(columns) + "\n")


def plan(reg, to: str, mappings: dict, *, apply: bool, actor: str = "") -> dict:
    """The move record and, for an external target, one create instruction per open
    item. Without ``apply`` it writes nothing. With it, it writes the record (every
    item ``pending``, ``approvedAt`` now); a local target's rows are then written here
    and each item marked ``created`` as it lands."""
    if apply and not actor:
        raise CapabilityError("an explicit ceremony actor is required to apply a move, for "
                              "example --actor virtuoso-init")
    open_move = outstanding_move(reg.root)
    if open_move is not None:
        raise GovernanceError(
            "move %s to %s is still outstanding; finish it, or resolve it, before planning "
            "another" % (open_move.get("id"), open_move.get("item_id")))
    view, open_items = _read(reg, to, mappings)
    mapping = mapping_mod.Mapping.from_policy(view["mappings"])
    declared = set(view["mappings"]["fieldMappings"])
    items = []
    for item in open_items:
        prepared, defaults = base.prepare_creation(
            _creation_fields(item, declared, view["external"]), mapping.statuses)
        entry = {"id": item.id, "title": item.title, "status": item.status,
                 "sequence": item.sequence, "state": PENDING, "providerId": "",
                 "fields": prepared}
        if view["external"]:
            entry["instruction"] = _instruction(view["to"], mapping, declared, prepared, defaults)
        items.append(entry)
    detail = {"kind": OPERATION, "from": view["from"], "to": view["to"],
              "toProvider": view["toProvider"], "external": view["external"],
              "mappings": view["mappings"], "finished": view["finished"],
              "readFrom": view["source"], "readAt": view["takenAt"],
              "approvedAt": "", "actor": actor, "items": items}
    if not apply:
        return dict(view, record=detail, recoveryId="", applied=False)

    detail["approvedAt"] = base.utc_now()
    record = recovery.open_record(reg.root, operation=OPERATION, item_id=view["to"],
                                  completed_steps=[], remaining_steps=[], detail=detail)
    payload = record.as_dict()             # a copy: the record's own items from here on
    for entry in payload["detail"]["items"]:
        if "instruction" in entry:
            entry["instruction"]["recoveryId"] = record.id
    _save(reg.root, payload)
    if not view["external"]:
        _create_locally(reg.root, payload, mapping)
    return dict(view, record=payload["detail"], recoveryId=record.id, applied=True)


def _create_locally(root: str, payload: dict, mapping) -> None:
    """Write each pending item into the new local register through its provider's
    create path, marking it ``created`` as it lands; a failure leaves the rest pending."""
    detail = payload["detail"]
    path = os.path.join(root, *detail["to"].split("/"))
    _seed_local(path, detail["toProvider"],
                [mapping.fields.column_for(f) for f in workspace.WORK_REGISTER_SEED.strip()
                 .split(",")])
    register = providers._LOCAL_PROVIDERS[detail["toProvider"]](source=path, mapping=mapping)
    for entry in detail["items"]:
        if entry["state"] == PENDING:
            created = register.create_item(entry["fields"])
            entry.update(state=CREATED, providerId=created.id, createdAt=base.utc_now())
            _save(root, payload)


def confirm(root: str, recovery_id: str, item_id: str, provider_id: str) -> dict:
    """Mark one item ``created`` after the session read it back. Idempotent: the same
    confirmation again changes nothing; a different provider identifier is refused."""
    if not str(provider_id or "").strip():
        raise GovernanceError("--provider-id names the identifier the new register gave %s"
                              % item_id)
    payload = _open_move(root, recovery_id)
    entry = next((i for i in payload["detail"]["items"] if i["id"] == item_id), None)
    if entry is None:
        raise GovernanceError("%s is not one of the open items move %s copies"
                              % (item_id, recovery_id))
    if entry["state"] == CREATED:
        if entry["providerId"] != provider_id:
            raise GovernanceError("%s was already confirmed as %s, not %s"
                                  % (item_id, entry["providerId"], provider_id))
        return {"recoveryId": recovery_id, "item": item_id, "providerId": provider_id,
                "changed": False, "pending": _pending(payload)}
    entry.update(state=CREATED, providerId=provider_id, createdAt=base.utc_now())
    _save(root, payload)
    return {"recoveryId": recovery_id, "item": item_id, "providerId": provider_id,
            "changed": True, "pending": _pending(payload)}


def abandon(root: str, recovery_id: str, reason: str) -> dict:
    """Close a move that will not finish, saying why. The register stays where it was;
    rows a local move already wrote are the owner's to remove."""
    if not str(reason or "").strip():
        raise GovernanceError("an abandoned move says why (--reason)")
    payload = _open_move(root, recovery_id)
    created = [i["id"] for i in payload["detail"]["items"] if i["state"] == CREATED]
    recovery.resolve(root, recovery_id, outcome="abandoned", reason=reason)
    return {"recoveryId": recovery_id, "outcome": "abandoned", "reason": reason,
            "created": created, "to": payload["detail"].get("to")}


def _open_move(root: str, recovery_id: str) -> dict:
    payload = recovery.get_record(root, recovery_id)
    if payload is None or payload.get("operation") != OPERATION:
        raise GovernanceError("%r is not a move record (see `virtuoso_registry recovery`)"
                              % recovery_id)
    if payload.get("resolved"):
        raise GovernanceError("move %s is already resolved (%s)"
                              % (recovery_id, recovery.outcome_of(payload)))
    return payload


def _pending(payload: dict) -> list:
    return [i["id"] for i in payload["detail"]["items"] if i["state"] == PENDING]


# -- the finish: compare, then repoint ----------------------------------------------


def _new_snapshot(root: str, detail: dict, mapping, rows_path: str):
    """The new register as read now: the rows the session read back, imported through
    the new mappings, or — for a local target with no rows given — the file itself."""
    if not rows_path:
        if detail["external"]:
            raise GovernanceError("--snapshot <rows.json> is required: the rows the session "
                                  "read back from %s" % detail["to"])
        source = os.path.join(root, *detail["to"].split("/"))
        return providers._LOCAL_PROVIDERS[detail["toProvider"]](
            source=source, mapping=mapping, read_only=True).snapshot()
    full = rows_path if os.path.isabs(rows_path) else os.path.join(root, rows_path)
    text = textio.read_text(full)
    if text is None:
        raise GovernanceError("%s cannot be read as text" % rows_path)
    try:
        rows, read_at, is_page = snapshot_provider.parse_rows(text)
        if is_page:
            raise ValueError("this is a raw items page; turn it into rows with "
                             "`snapshot --import ... --columns ... --out <scratch>` first")
        taken_at = snapshot_provider.parse_taken_at(read_at) if read_at else base.utc_now()
        return snapshot_provider.from_rows(rows, mapping, source=detail["to"],
                                           taken_at=taken_at)[0]
    except ValueError as exc:
        raise GovernanceError("%s: %s" % (rows_path, exc)) from exc


def _differences(detail: dict, snap) -> list[str]:
    """Every way the new register differs from the move record: ids, then each item's
    canonical status and sequence (sequence only where the new register has a column)."""
    found = {i.id: i for i in snap.items}
    expected = {i["id"]: i for i in detail["items"]}
    ordered = not detail["external"] or "sequence" in detail["mappings"]["fieldMappings"]
    out = ["%s is missing from the new register" % i for i in expected if i not in found]
    out += ["%s is in the new register but not in the move" % i for i in found
            if i not in expected]
    for item_id, want in expected.items():
        got = found.get(item_id)
        if got is None:
            continue
        if got.status != want["status"]:
            out.append("%s: status %s, the move record says %s"
                       % (item_id, got.status, want["status"]))
        if ordered and got.sequence != want["sequence"]:
            out.append("%s: sequence %s, the move record says %s"
                       % (item_id, got.sequence, want["sequence"]))
    return out


def _repoint(reg, detail: dict) -> str:
    """Point ``reg`` (in memory) at the new register: the work-register role, its
    mappings and, for a tool, a snapshot role. Returns the snapshot role's path, or ""."""
    external, to = detail["external"], detail["to"]
    # The role shape ``create --register`` writes, keeping this project's authority and writers.
    fresh = workspace.create_registry(reg.root, doc_root=reg.documentation_root,
                                      register=to if external else detail["toProvider"],
                                      mappings=detail["mappings"] if external else None)
    shaped = fresh.roles[providers.WORK_REGISTER_ROLE]
    current = reg.roles.get(providers.WORK_REGISTER_ROLE) or shaped
    reg.roles[providers.WORK_REGISTER_ROLE] = dataclasses.replace(
        current, path="" if external else to, external=to if external else "",
        provider=shaped.provider, validation=shaped.validation, label=shaped.label)
    candidate = reg.policy
    for key in ("fieldMappings", "statusMappings"):
        candidate = policy_mod.assign(candidate, "workRegister." + key, detail["mappings"][key])
    snapshot_path = ""
    if external:
        name = str(policy_mod.load(reg.policy).get("workRegister.snapshot", "") or "")
        if not name or name not in reg.roles or reg.roles[name].is_external:
            name = "workRegisterSnapshot"
            reg.roles.setdefault(name, fresh.roles[name])
        candidate = policy_mod.assign(candidate, "workRegister.snapshot", name)
        snapshot_path = reg.roles[name].path
    problems = policy_mod.load(candidate).validate()
    if problems:
        raise GovernanceError("the repointed policy is not valid; nothing was written:\n  %s"
                              % "\n  ".join(problems))
    reg.policy = candidate
    return snapshot_path


def finish(reg, recovery_id: str, *, rows_path: str = "", apply: bool = False,
           actor: str = "") -> dict:
    """Compare the new register with the move record; on a match, repoint.

    Refuses while any item is pending, and on any difference, writing nothing. Applied,
    it writes the new snapshot (a tool), then the manifest — backed up and validated as
    ``policy-set`` writes it — and only after the repoint has landed resolves the record,
    so any failure leaves the move outstanding and the old register in place."""
    if apply and not actor:
        raise CapabilityError("an explicit ceremony actor is required to finish a move, for "
                              "example --actor virtuoso-init")
    payload = _open_move(reg.root, recovery_id)
    detail = payload["detail"]
    pending = _pending(payload)
    if pending:
        raise GovernanceError("move %s still has pending item(s) %s; create and confirm each "
                              "before finishing. Nothing was written."
                              % (recovery_id, ", ".join(pending)))
    snap = _new_snapshot(reg.root, detail, mapping_mod.Mapping.from_policy(detail["mappings"]),
                         rows_path)
    differences = _differences(detail, snap)
    if differences:
        raise GovernanceError("the new register does not match move %s; nothing was written:"
                              "\n  %s" % (recovery_id, "\n  ".join(differences)))
    found = {i.id: i for i in snap.items}
    table = [{"id": i["id"], "before": {"status": i["status"], "sequence": i["sequence"]},
              "after": {"status": found[i["id"]].status, "sequence": found[i["id"]].sequence}}
             for i in detail["items"]]
    if [f for f in reg.findings if f.severity == "error"]:
        raise GovernanceError("this registry reports errors; run `virtuoso_preflight.py --mode "
                              "repair` first. Nothing was written.")
    snapshot_path = _repoint(reg, detail)
    result = {"recoveryId": recovery_id, "from": detail["from"], "to": detail["to"],
              "table": table, "snapshot": snapshot_path, "manifest": schema.MANIFEST_RELPATH,
              "applied": False}
    if not apply:
        return result

    target = os.path.join(reg.root, *snapshot_path.split("/")) if snapshot_path else ""
    previous = textio.read_bytes(target) if target else None
    if target:
        snapshot_provider.write_snapshot(target, snap)
    plan = repair_mod.RepairPlan(
        root=reg.root, files_affected=[schema.MANIFEST_RELPATH], manifest_text=reg.manifest_json(),
        actions=[repair_mod.RepairAction(
            kind="repoint-work-register", role=providers.WORK_REGISTER_ROLE,
            detail="repoint the work register (move %s)" % recovery_id,
            current=detail["from"], proposed=detail["to"])])
    try:
        written, backup_set = repair_mod.apply_plan(reg, plan, label=OPERATION, actor=actor)
    except Exception:
        if target and previous is None:
            os.remove(target)               # the snapshot this finish created
        elif target:
            with open(target, "wb") as handle:
                handle.write(previous)
        raise
    recovery.note(reg.root, recovery_id, {"finishedAt": base.utc_now(),
                                          "backup": backup_set.relative_directory})
    recovery.resolve(reg.root, recovery_id)
    reloaded = registry_mod.load(reg.root)
    result.update(applied=True, filesWritten=written + ([snapshot_path] if target else []),
                  backup=backup_set.relative_directory,
                  notes=[f.message for f in reloaded.findings if f.code == "registry-divergence"])
    return result


def item_states(record: dict) -> tuple[list, list]:
    """``(created ids, pending ids)`` of a move record."""
    items = (record.get("detail") or {}).get("items") or []
    return ([i["id"] for i in items if i.get("state") == CREATED],
            [i["id"] for i in items if i.get("state") == PENDING])
