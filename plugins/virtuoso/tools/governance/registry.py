"""Loading, validating, and serializing the governance registry.

The manifest is the authority; the readme is a synchronized view (item 13).
This module never writes anything — construction and validation are pure reads.
Writes live in :mod:`repair` and are always previewable and transactional
(items 7, 8).
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field

from . import identifiers, readme as readme_mod, safepath, schema, textio
from .errors import RegistryValidationError, RoleNotRegistered, SchemaVersionError

_RANGE_RE = re.compile(r">=\s*([0-9]+(?:\.[0-9]+)*)\s*<\s*([0-9]+(?:\.[0-9]+)*)")


def _version_tuple(value: str) -> tuple[int, ...]:
    parts = []
    for chunk in str(value).split("-", 1)[0].split("."):
        try:
            parts.append(int(chunk))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def version_in_range(version: str, spec: str) -> bool:
    """Whether ``version`` satisfies a ``>=A <B`` range. An unparseable range is
    treated as satisfied — a malformed compatibility hint must not brick a
    project (it is reported as a finding instead)."""
    match = _RANGE_RE.search(spec or "")
    if not match:
        return True
    low, high = _version_tuple(match.group(1)), _version_tuple(match.group(2))
    current = _version_tuple(version)
    return low <= current < high


@dataclass
class Finding:
    code: str
    severity: str          # "error" | "warning" | "info"
    message: str
    role: str = ""

    def as_dict(self) -> dict:
        data = {"code": self.code, "severity": self.severity, "message": self.message}
        if self.role:
            data["role"] = self.role
        return data


@dataclass
class Registry:
    root: str
    schema_version: int = schema.SCHEMA_VERSION
    plugin_compatibility: str = schema.PLUGIN_COMPATIBILITY
    layout: str = "plugin-only"
    adopted: bool = False
    documentation_root: str = ""
    roles: dict[str, schema.RoleSpec] = field(default_factory=dict)
    policy: dict = field(default_factory=dict)
    #: Top-level manifest keys the plugin does not own — round-tripped verbatim.
    extensions: dict = field(default_factory=dict)
    #: Everything the manifest carried, so an unrecognized key is never dropped.
    raw: dict = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    manifest_present: bool = False
    readme_present: bool = False
    readme_managed: bool = False
    readme_view: readme_mod.ReadmeView | None = None

    # -- resolution ----------------------------------------------------------

    @property
    def manifest_path(self) -> str:
        return os.path.join(self.root, *schema.MANIFEST_RELPATH.split("/"))

    @property
    def readme_path(self) -> str:
        return os.path.join(self.root, *schema.README_RELPATH.split("/"))

    def role(self, name: str) -> schema.RoleSpec | None:
        return self.roles.get(name)

    def resolve(self, name: str) -> str:
        """The absolute path (or external identifier) for ``name``.

        Raises :class:`RoleNotRegistered` when the role is absent — a ceremony must
        never fall back to a conventional path (item 87).
        """
        spec = self.roles.get(name)
        if spec is None:
            raise RoleNotRegistered(
                "role %r is not registered in %s — register it before use "
                "(the plugin does not guess conventional paths)"
                % (name, schema.MANIFEST_RELPATH), detail={"role": name}
            )
        if spec.is_external:
            return spec.external
        return spec.absolute or os.path.join(self.root, *spec.path.split("/"))

    def roles_with_authority(self, *authorities: str) -> list[schema.RoleSpec]:
        return [r for r in self.roles.values() if r.authority in authorities]

    def writable(self, name: str, actor: str) -> bool:
        spec = self.roles.get(name)
        return bool(spec and spec.writable_by(actor))

    # -- serialization -------------------------------------------------------

    def to_manifest(self) -> dict:
        """The manifest dict this registry would serialize to.

        Unrecognized top-level keys are carried through verbatim so an upgrade
        never discards project configuration (item 18).
        """
        data = dict(self.raw) if self.raw else {}
        data["schemaVersion"] = self.schema_version
        data["pluginCompatibility"] = self.plugin_compatibility
        data["layout"] = self.layout
        data["adopted"] = bool(self.adopted)
        if self.documentation_root:
            data["documentationRoot"] = self.documentation_root
        data["roles"] = {name: spec.to_manifest() for name, spec in self.roles.items()}
        if self.policy:
            data["policy"] = self.policy
        for key, value in self.extensions.items():
            data[key] = value
        # `paths` was the v1 carrier. It is not re-emitted: keeping a second
        # mapping alive is precisely the dual-authority problem item 13 removes.
        data.pop("paths", None)
        return data

    def manifest_json(self) -> str:
        return json.dumps(self.to_manifest(), indent=2, ensure_ascii=False) + "\n"

    # -- validation ----------------------------------------------------------

    def validate(self, *, plugin_version: str = "") -> list[Finding]:
        """Validate every registered role. Pure inspection: returns findings and
        never mutates ``self.findings`` (callers accumulate)."""
        found: list[Finding] = []

        if self.plugin_compatibility and plugin_version:
            if not version_in_range(plugin_version, self.plugin_compatibility):
                found.append(Finding(
                    "plugin-incompatible", "error",
                    "registry declares pluginCompatibility %r but this plugin is %s"
                    % (self.plugin_compatibility, plugin_version)))

        for name, spec in self.roles.items():
            found.extend(self._validate_role(name, spec))

        # Derived-artifact relationships must name a registered source (item 57).
        for name, spec in self.roles.items():
            if spec.generated_from and spec.generated_from not in self.roles:
                found.append(Finding(
                    "generator-source-missing", "error",
                    "role %r declares generatedFrom=%r, which is not registered"
                    % (name, spec.generated_from), role=name))

        # Exactly one live work register keeps precedence unambiguous (item 13).
        live_registers = [n for n, s in self.roles.items()
                          if s.authority == "live" and s.provider != "directory"
                          and n not in ("roadmap",)]
        if len(live_registers) > 1:
            found.append(Finding(
                "ambiguous-authority", "error",
                "more than one role claims live operational authority: %s — exactly one "
                "live work register may be registered" % ", ".join(sorted(live_registers))))

        return found

    def _validate_role(self, name: str, spec: schema.RoleSpec) -> list[Finding]:
        found: list[Finding] = []

        if spec.authority not in schema.AUTHORITIES:
            found.append(Finding("bad-authority", "error",
                                 "role %r has unknown authority %r" % (name, spec.authority),
                                 role=name))
        if spec.mutability not in schema.MUTABILITIES:
            found.append(Finding("bad-mutability", "error",
                                 "role %r has unknown mutability %r" % (name, spec.mutability),
                                 role=name))
        if spec.authority == "terminal" and spec.mutability != "append-only":
            found.append(Finding(
                "terminal-not-append-only", "error",
                "role %r claims terminal authority but has mutability %r; terminal records "
                "must be append-only" % (name, spec.mutability), role=name))
        if spec.provider not in schema.PROVIDERS:
            found.append(Finding("bad-provider", "error",
                                 "role %r has unknown provider %r" % (name, spec.provider),
                                 role=name))
        if spec.classification not in schema.CLASSIFICATIONS:
            found.append(Finding("bad-classification", "warning",
                                 "role %r has unknown classification %r"
                                 % (name, spec.classification), role=name))
        if spec.origin not in schema.ORIGINS:
            found.append(Finding("bad-origin", "warning",
                                 "role %r has unknown origin %r" % (name, spec.origin), role=name))

        if spec.path and spec.external:
            found.append(Finding("dual-target", "error",
                                 "role %r registers both a path and an external identifier"
                                 % name, role=name))
            return found
        if not spec.path and not spec.external:
            found.append(Finding("no-target", "error",
                                 "role %r registers neither a path nor an external identifier"
                                 % name, role=name))
            return found

        if spec.is_external:
            # Item 17: an external identifier is validated by shape only. No
            # filesystem call happens, and it is never reported as missing.
            if spec.provider not in schema.EXTERNAL_PROVIDERS:
                found.append(Finding(
                    "provider-mismatch", "error",
                    "role %r registers an external identifier but declares provider %r "
                    "(expected one of %s)"
                    % (name, spec.provider, ", ".join(sorted(schema.EXTERNAL_PROVIDERS))),
                    role=name))
            for problem in identifiers.validate(spec.external):
                found.append(Finding("bad-external-identifier", "error",
                                     "role %r: %s" % (name, problem), role=name))
            return found

        if spec.provider in schema.EXTERNAL_PROVIDERS:
            found.append(Finding(
                "provider-mismatch", "error",
                "role %r declares external provider %r but registers a filesystem path"
                % (name, spec.provider), role=name))

        verdict = safepath.validate_path(
            self.root, name, spec.path,
            authority=spec.authority, expect=spec.expect, provider=spec.provider,
        )
        for problem in verdict.findings:
            found.append(Finding("unsafe-path", "error", problem, role=name))
        return found

    def compute_presence(self) -> None:
        """Fill each role's ``presence`` and ``absolute``. External roles resolve
        to ``external``; a registered-but-missing path resolves to ``absent`` and
        is *reported*, never re-pointed at a lookalike file (item 20)."""
        for spec in self.roles.values():
            if spec.is_external:
                spec.presence = "external"
                spec.absolute = ""
                continue
            _rel, absolute = safepath.normalize(self.root, spec.path)
            spec.absolute = absolute
            if spec.is_directory:
                spec.presence = "present" if os.path.isdir(absolute) else "absent"
            else:
                spec.presence = "present" if os.path.isfile(absolute) else "absent"

    # -- readme divergence ---------------------------------------------------

    def divergence(self, view: readme_mod.ReadmeView) -> list[Finding]:
        """Compare the readme's machine block against the manifest.

        Divergence is a *diagnostic* (item 13). Nothing here rewrites either side.
        """
        found: list[Finding] = []
        if not view.text:
            return found
        for name, target in view.targets.items():
            spec = self.roles.get(name)
            if spec is None:
                found.append(Finding(
                    "readme-only-role", "warning",
                    "the readme registers role %r (-> %s) which the manifest does not carry; "
                    "run `--mode repair` to review adopting it" % (name, target), role=name))
                continue
            if spec.target != target:
                found.append(Finding(
                    "registry-divergence", "warning",
                    "role %r: readme says %r, manifest says %r — the manifest is the authority; "
                    "run `--mode repair` to review synchronizing the view"
                    % (name, target, spec.target), role=name))
        for name, spec in self.roles.items():
            if view.has_machine_block and name not in view.targets and spec.target:
                found.append(Finding(
                    "readme-missing-role", "info",
                    "role %r is in the manifest but not in the readme view" % name, role=name))
        return found


# --- loading -----------------------------------------------------------------


def _populate(reg: Registry, data: dict) -> None:
    """Fill ``reg`` from a parsed manifest dict. Shared by :func:`load` (disk) and
    :func:`from_dict` (an in-memory candidate a repair is validating before it is
    ever written)."""
    reg.raw = dict(data)
    declared = data.get("schemaVersion", 1 if data else schema.SCHEMA_VERSION)
    try:
        reg.schema_version = int(declared)
    except (TypeError, ValueError):
        reg.schema_version = 1
        reg.findings.append(Finding(
            "bad-schema-version", "error",
            "schemaVersion %r is not an integer" % (declared,)))

    if data and reg.schema_version not in schema.SUPPORTED_SCHEMA_VERSIONS:
        raise SchemaVersionError(
            "registry schema version %s is not supported by this plugin (supports %s)"
            % (reg.schema_version, ", ".join(str(v) for v in schema.SUPPORTED_SCHEMA_VERSIONS)),
            detail={"schemaVersion": reg.schema_version,
                    "supported": list(schema.SUPPORTED_SCHEMA_VERSIONS)},
        )

    reg.plugin_compatibility = str(data.get("pluginCompatibility") or schema.PLUGIN_COMPATIBILITY)
    reg.layout = str(data.get("layout") or "plugin-only")
    reg.adopted = bool(data.get("adopted"))
    reg.documentation_root = str(data.get("documentationRoot") or "")
    reg.policy = data.get("policy") if isinstance(data.get("policy"), dict) else {}
    reg.extensions = {k: v for k, v in data.items() if schema.is_extension_key(k)}

    roles_blob = data.get("roles")
    if isinstance(roles_blob, dict):
        for name, entry in roles_blob.items():
            reg.roles[name] = schema.RoleSpec.from_manifest(name, entry)
    elif data and reg.schema_version == 1:
        from .migrate import roles_from_v1  # local import: migration is optional
        migrated, notes = roles_from_v1(data)
        reg.roles.update(migrated)
        reg.findings.extend(notes)


def from_dict(root: str, data: dict, *, plugin_version: str = "") -> Registry:
    """Build and validate a registry from an in-memory manifest dict.

    Used by :mod:`repair` to prove a reconstructed pair is sound *before* a single
    byte reaches disk (item 8).
    """
    reg = Registry(root=os.path.abspath(root))
    _populate(reg, data)
    reg.manifest_present = bool(data)
    reg.compute_presence()
    reg.findings.extend(reg.validate(plugin_version=plugin_version))
    return reg


def load(root: str, *, plugin_version: str = "") -> Registry:
    """Read the registry for ``root``. Never writes, never heals, never guesses."""
    root = os.path.abspath(root)
    reg = Registry(root=root)

    manifest_text = textio.read_text(reg.manifest_path)
    reg.manifest_present = manifest_text is not None

    data: dict = {}
    if manifest_text is not None:
        try:
            parsed = json.loads(manifest_text)
            if isinstance(parsed, dict):
                data = parsed
            else:
                reg.findings.append(Finding(
                    "manifest-malformed", "error",
                    "%s does not contain a JSON object" % schema.MANIFEST_RELPATH))
        except ValueError as exc:
            reg.findings.append(Finding(
                "manifest-malformed", "error",
                "%s is not valid JSON: %s" % (schema.MANIFEST_RELPATH, exc)))

    _populate(reg, data)

    readme_text = textio.read_text(reg.readme_path)
    reg.readme_present = readme_text is not None
    reg.readme_view = readme_mod.parse(readme_text)
    reg.readme_managed = reg.readme_view.is_plugin_managed

    # A readme-only role is surfaced as a divergence finding, not silently merged:
    # merging is a *repair*, and repairs are previewed and approved (item 7).
    reg.compute_presence()
    reg.findings.extend(reg.validate(plugin_version=plugin_version))
    reg.findings.extend(reg.divergence(reg.readme_view))
    return reg


def require_valid(reg: Registry) -> None:
    errors = [f for f in reg.findings if f.severity == "error"]
    if errors:
        raise RegistryValidationError(
            "registry validation failed with %d error(s)" % len(errors),
            detail={"findings": [f.as_dict() for f in errors]},
        )
