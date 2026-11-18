# Governance Sweep — Default Sweep Policy

Serves the `governance-sweep` skill, *Before Phase 1 — read the registry and the sweep
policy*: the `policy.sweep` fields that govern the traversal, with their shipped
defaults (respect every field), and the meaning of each `structuralAuthority` value.

```jsonc
"sweep": {
  "include": ["**/*"],
  "exclude": ["Virtuoso/.backups/**", "Virtuoso/.quarantine/**",
              "**/node_modules/**", "**/.git/**", "**/__pycache__/**",
              "**/.venv/**", "**/vendor/**", "**/dist/**", "**/build/**"],
  "ignoreDirectories": [".git", "node_modules", "__pycache__", ".venv", "vendor"],
  "followSymlinks": false,
  "maxFileBytes": 5242880,
  "binaryPolicy": "skip",
  "quarantineDirectory": "Virtuoso/.quarantine",
  "deletionPolicy": "quarantine",
  "backupRetention": 10,
  "protectedAuthorities": ["archive", "terminal", "evidence"],
  "structuralAuthority": "registry"
}
```

## `structuralAuthority` values

Serves *Structural authority comes from the registry*.

| Value | Meaning |
|---|---|
| `registry` *(default)* | The registry's role table defines what belongs where. A directory readme is documentation, and inconsistency with it is a *finding*, not a mandate. |
| `directory-readme` | Each directory's readme defines what belongs in it, as in earlier versions of this skill. |
| `both` | Registry wins on conflict; readme governs anything the registry does not cover. |

Return to SKILL.md, *Before Phase 1*.
