# Governance Sweep — Formats

Serves the `governance-sweep` skill: the work list presented at Phase 2 (*Present the work
list*), the completion report written at Phase 3, Step 4, and the human-review questions
asked at the end of Phase 1 (*Flagging for human review*).

## Work list

```
## Governance Sweep — Work List ([project], [date])

- Findings: [N]   Actions: [N]   Files affected: [N]   Deferred: [N]
- Structural authority: [registry | directory-readme | both]
- Boundaries: [N] path(s) excluded by policy — [summary]
- Protected and untouchable: [N] path(s) — [roles/classes]
- Deletion policy: quarantine → [quarantine dir]   (or: permanent, as required)

[Groups A–G, each action enumerated with source, target, and rationale]

### Deferred (left for you to handle manually)
[items too ambiguous to act on, with why]
```

Return to SKILL.md Phase 2, *Approval gate*.

## Completion report

```
## Governance Sweep — Complete

- Actions executed: [N]  (A:[n] B:[n] C:[n] D:[n] E:[n] F:[n] G:[n])
- Files created / moved / quarantined / deleted / edited: [counts]
- Backup set: [path]   manifest verified: [yes]
- Protected-file hashes: [N] checked, [N] unchanged
- Verification: [all checks passed | anomalies: …]
- Deferred (manual): [N] — [list]
- Disk footprint: [removed: paths and sizes | none]; [kept for the user: unique,
  evidence, in-flight paths]; free space [before] → [after]
- Findings recorded: [F-NNN … in the registered `findings` role, or "none"]

### Repository scope
- Changed paths:            [explicit list]
- Staged paths:             [explicit list, or "none — policy.git is <policy>"]
- Cached diff (name-only):  [explicit list]
- Commit:                   [sha, or "not committed — policy.git is <policy>"]
- Uncommitted unrelated work present: [explicit list, untouched]
```

Return to SKILL.md Phase 3, Step 4: *Record what outlives the sweep*.

## Human-review questions

Each is a bounded question, batched, naming the specific file with its viable
dispositions and consequences.

- **Ambiguous orphan** — Absorb into [doc] / Archive / Promote / Quarantine.
- **Absorption target unclear** — [best guess] / Promote standalone / Archive.
- **Large orphan** (>500 lines) — Absorb whole / Absorb summary + link / Promote.
- **Stale reference, no obvious fix** — [best guess] / Remove the reference / Defer.
- **Duplicate conflict** — which copy is authoritative, or defer to a manual merge.
- **Archival rotation** (multi-select) — which of these oldest records rotate?
- **Unclear version currency** — which variant is current?
- **Binary of unknown purpose** — document / archive / quarantine.
- **Protected path implicated** — a registry change, previewed, never a sweep action.
- **Broken documented command with no tested replacement** — leave and flag / the
  user supplies the correct invocation / remove the instruction.

Return to SKILL.md, *Flagging for human review*: answers become `[user-confirmed]`
actions; declined items become **Deferred (manual)**.
