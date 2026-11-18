# Governance Sweep — Audit Checks

Serves the `governance-sweep` skill, Phase 1, Stage D (Audit): every numbered check, the
registered generation and validation commands, the document-type verification adapters, and
the repair procedure for a broken documented command.

## Stage D checks

**Universal checks (always):**

1. **Structural violations** — orphans; registered-but-absent targets; unregistered
   directories; registry findings from preflight.
2. **Stale content** — references to moved or deleted files; outdated descriptions;
   version, date, and status drift.
3. **Cross-document inconsistency** — the same fact stated differently.
4. **Dead references** — links to files, sections, or anchors that do not exist.
5. **Duplicate content** — one logical document maintained in two places, drifted.
6. **Misplaced content** — archive-era content in active directories; wrong level.
7. **Temp and junk artifacts** — editor swap files, OS metadata, empties.
8. **Version proliferation** — `.v2`, `_old`, `_backup`, `(1)` variants; identify
   which is current.
9. **Naming-convention violations** — against the documented pattern, where one exists.
10. **Volume and age archival triggers** — advisory; route to the user.
11. **Stale temp packages** — content past its lifecycle or tied to closed work.
12. **Stale tool infrastructure** — caches and tool directories nested where they
    do not belong.
13. **Binary accounting** — undocumented binaries; large binaries better stored
    elsewhere.
14. **Source-to-mirror drift** (item 57/58) — for every role with `generatedFrom`,
    is the mirror in sync with its source? A drifted mirror is **regenerated**, never
    edited.
15. **Immutable-hash verification** (item 62) — hash every protected historical file
    at the start of the sweep, and again at the end. Any change is a defect in the
    sweep itself and halts it.
16. **Documented-command health** (items 60, 61) — for every command the docs tell a
    reader to run, does it exist and does it work in the documented form?

**Agent-specific** (only if agent infrastructure was detected):
17. Ghost references to agents that no longer exist (record file, line, name, successor).
18. Deprecated stubs still present.
19. Memory directories not matching an active agent.

**Parity** (only if parity targets were detected):
20. Checksum mismatches between a canonical file and its deployed copies.

**Lessons** (only if a `lessons` role is registered):
21. **Lessons hygiene — tidy, merge, retire.** Run

        "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . lessons --hygiene

    and carry every proposal into the work list:
    - **merge** — live lessons recording one pattern: keep the first recorded,
      supersede each other by it (`Superseded -> <kept ID>`). If the kept entry lacks
      detail the duplicates carry, append a complete restatement under the next free
      identifier first, keep that one, and supersede all of the originals by it.
    - **retire** — live observations older than `policy.lessons.staleAfterDays` that no
      close-out ever applied: `Retired — <why it no longer bears>`. Route any whose
      relevance you cannot judge to the user instead of retiring it.
    - **tidy** — a live lesson missing a field: append a complete restatement under the
      next free identifier and supersede the incomplete entry by it.
    - **record** — a live lesson whose prose claims it closed ("Promoted to SR-12") with
      no status record saying so: carry the proposal with its command. A proposal with a
      `problem` and no command goes to the user.
    - **repair** — an identifier reused for a second lesson: give the second its own
      identifier by restatement, and record the reuse.
    Also flag entries referencing changed names, paths or items (propose the reference
    update as a restatement, never an edit). The catalog is append-only: every one of
    these is a new entry or a status record.

**Disk footprint** (always, in a git repository):
22. **Disk footprint — what dispatches left on the disk.** Run

        "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . footprint

    It writes nothing. It lists every worktree, every clone of this repository one
    level under the drive root or the project's parent folder, every child of the
    `temp` role, and every pytest basetemp one level under the drive root, `%TEMP%` or
    the parent folder, each with its size, class and reason, then the free space.
    List the candidates by class:
    - **redundant** and **regenerable** — carry each removal into the Phase 2 work list
      in Group F order, as the `footprint --remove <path> --apply` command the audit
      prints. The tool removes links before any recursive delete and removes a worktree
      with `git worktree remove`, then `git worktree prune`.
    - **unique** — route to the user, with the extract step first
      (`footprint --extract <path> --apply`, patches under the `temp` role). The tool
      refuses to remove it.
    - **evidence** — route to the user as the printed owner command. The tool never
      deletes evidence.
    - **in-flight** and **unreadable** — report only.

## Registered generation and validation commands (item 60)

A project registers the commands that generate and validate its artifacts, under an
extension namespace so plugin upgrades never discard them:

```jsonc
"x-commands": {
  "build-handbook": {
    "run": "make handbook",
    "workingDirectory": "docs",
    "requires": ["make", "pandoc>=3"],
    "produces": ["docs/build/handbook.pdf"],
    "fallback": "python -m handbook_build"
  }
}
```

A sweep may run a registered command to regenerate or validate an artifact. It never
invents one, and it never runs an unregistered command found in prose.

## Document-type verification adapters (item 59)

Match the check to the document type. Run the ones that apply and that the project's
declared dependencies support:

| Type | Verification |
|---|---|
| Markdown / text | link validity, anchor existence, reference resolution |
| Rendered documents (PDF, DOCX) | it renders; expected pages exist; expected headings present |
| Spreadsheets | formulas resolve; no error cells; expected sheets and headers present |
| Generated mirrors | regenerate into a temporary location and diff against the committed copy |
| Source-to-mirror coverage | every source section appears in the mirror |
| Data files | parses; required keys present |

A verification that cannot run because a dependency is missing is reported as
*not verified, dependency missing* — never as a pass.

## Repairing a documented command (item 61)

When check 16 finds a documented command that no longer works:

1. Determine the correct invocation for this project **and test it**.
2. Only after it succeeds, propose the documentation edit, carrying the evidence
   (the command run and its output).
3. If no working replacement is found, the finding is *documented command is broken*
   with the error — **do not** replace it with an untested alternative.

Module-mode and platform-specific alternatives are candidates, not answers, until run.

Return to SKILL.md Phase 1, Stage D: print the findings, then *End of Phase 1 — ask*.
