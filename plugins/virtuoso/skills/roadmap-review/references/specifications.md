# Roadmap review — specification detail

Serves `roadmap-review` SKILL.md Phase D: D.3 (writing the dispatch-ready
specifications), D.5.2 (the specification format, which `/write-plan`,
`references/execution-paths.md` and `references/task-rows.md` cite as roadmap-review's
D.5.2), D.5.3 (updating the live work register), and D.5.4 (regenerating exports).

## D.3 Write the dispatch-ready specifications

**D.3.0 Read the live lessons first.** Before drafting anything:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . lessons --open

Carry the list into every draft. A lesson is applied while a specification is being
written, not retrofitted after the specification has passed.

For each item in scope:

**D.3.1 Draft.** Write each specification in the D.5.2 format (below), with structural
and implementation-detail inputs sourced from close-outs, decision records, standing
rules, and archives — and a **Lessons applied** section: each live lesson that bears on
the item, by identifier, with the concrete change it made to this specification; or the
statement that no live lesson applies.

**D.3.2 Apply the shared rubric.** Open `references/readiness-rubric.md` and walk
every universal check plus the project's declared extensions. For each item:
- **PASS** → move on.
- **CLOSABLE GAP** → resolve by investigation:

  | Gap | How to close |
  |---|---|
  | Stale location reference | Read the source; correct it in place. |
  | Vague test reference | Read the test file; insert the exact name and assertion. |
  | Unverified constant | Search; record the current value and where it lives. |
  | Non-mechanical acceptance criterion | Rewrite it as a command or assertion. |
  | Missing branch plan | Apply `policy.git.branchNameTemplate`. |
  | Missing failure handling | Enumerate the known failure modes; add "if X, do Y". |
  | Missing rollback | State the revert path for this project's git policy. |
  | Missing source citation | Find it and link it, with an anchor. |
  | Missing project-extension detail | Consult the project's own precedent. |
  | Missing or empty Lessons applied | From D.3.0: name each live lesson that bears on the item and what it changed here, or that none applies. |

- **STRUCTURAL GAP** → ask the user. Do not invent decisions.

**D.3.3 Re-audit.** Walk the rubric again. Two enrichment passes maximum. A
specification still failing after two passes is NOT saved as dispatch-ready: flag
it as a buffer gap in D.6 and continue from the next item. U9 has a mechanical
half, and it must pass before the specification is saved:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . lessons --check <spec> --item <ITEM-ID>

**D.3.4 Save.** Store the specification where `policy.roadmap.specStorage` says:

- `inline` — in the roadmap document at the item's position.
- `files` — one file per item under `policy.roadmap.specDirectory`, with the link
  stored on the register item via `store-spec-link`.
- `external` — in the external system, with the link stored the same way.

If the provider lacks `store-spec-link` and storage is `files` or `external`,
say so and record the links in the roadmap instead.

Return to SKILL.md D.4.

## D.5.2 Specification format

**D.5.2** Specification format (structural fields first, then implementation
detail, then the task list U10 reads, in the row format of `references/task-rows.md`,
then the milestones U11 reads, then the lessons applied under the heading U9 reads).
Grouping headings
appear only if `policy.roadmap.hierarchy` declares them:

```
#### ITEM-ID — Item title

- **What:** …
- **Why:** …
- **Prerequisites:** …
- **Done when:**
    1. … (mechanically verifiable)
- **Effort:** … (the size word, and the hours estimate where the register carries
  hours: `M — 6 h`. An estimate above `policy.roadmap.maxItemHours` is split before it
  is sized)
- **Owners:** … (roles from policy.actors)
- **Source:** …
- **Path:** dispatch | epic — … (optional; absent means dispatch — see references/execution-paths.md)
- **Origin:** … (for absorbed ad hoc work: held plan <entry> (HB-<n>))

##### Implementation detail
- **Edit sites:** …
- **Tests:** …
- **Constants:** …
- **Branch:** … from …
- **Staging plan:** explicit paths, per policy.git
- **Failure handling:** if X, do Y; rollback: …
- **Project extensions:** … (only those policy.rubric.extensions declares)

##### Task list
| # | Task | Class | Kind | Tier | Effort | Estimate | Timebox | Group |
|---|---|---|---|---|---|---|---|---|
| 1 | … (an outcome, never a code step) | repeat | … | bounded | medium | 35m (median of 9 runs) | — | — |

**Total:** the line `timing --rows-from-spec <spec> --item ITEM-ID` prints

##### Milestones
| Milestone | Rows | Done when |
|---|---|---|
| … (a stage a reader would name) | 1-3 | … (something checkable, ending the stage) |

##### Lessons applied
- <prefix>-NNN — what it changed here: a *Done when* row, a constraint, a test
- (or) No live lesson applies — N read
```

Mid-dispatch amendments append as `##### Mid-Dispatch Amendment — YYYY-MM-DD`.

Return to SKILL.md at the step that sent you here (D.3.1 or D.5.2).

## D.5.3 Update the live work register

Through the provider, for each newly specified item: sequence, title, group, workstream,
effort, effort hours, prerequisites, status, the specification state, branch,
description — each only where the register has a column for it (a declared
`policy.workRegister.fieldMappings` names it; a plan naming any other is refused). Pass
the `revision` you read.

For an external register, every change is its own plan and its own connector call
(the external handshake in `references/registry-contract.md`). Read the item back
before every `mutation-confirm`. When only some fields landed, confirm `--partial
--written <fields>`, then plan the rest. Close a plan you will not execute with
`mutation-abandon --recovery-id <ID> --reason <why>`.

An item that is **not yet in the register** — a specification this review authored
or approved that has no row — is brought into existence through `create-item`,
never by writing a row into a file by hand and never by calling a connector's raw
create. For a local register that is one write. For an external register it is
the handshake: refresh the snapshot first (`snapshot --import <rows.json>`, or a raw
page with `--columns`; a `[DRIFT]` line naming a field you are about to write is fixed in
`fieldMappings` before planning), then `mutation-plan --operation create-item`, execute
the returned instruction with the host's connector, read the item back,
`mutation-confirm --recovery-id <RECOVERY-ID> --succeeded --provider-id <ID>
--actual-revision <REVISION>`, then refresh the canonical snapshot the same way
(`snapshot --import <rows.json>`) and verify `recovery` is empty. The
plan is refused when the snapshot is absent or stale, when the id already exists (terminal
items included), or when a creation under the same idempotency key was already
confirmed; each refusal names the fix. If `policy.workRegister.creators` does not
name this ceremony, say so and stop — creation is separately authorized.

Only write fields the provider reports it can write. Field *names* come from
`policy.workRegister.fieldMappings`; status *words* come from
`policy.workRegister.statusMappings`. Never assume a column is called
"Implementation Status" or that "Queued" is the right word for this project.

## D.5.4 Regenerate exports (optional)

If the project registers a generated report role, regenerate it through its registered
generator:

    "$HOME/.virtuoso/bin/virtuoso" build_register_report --root . --role sprintQueue

The generator refuses to write any role the project has not declared generated.
A generated export is a presentation output: never read it back as truth, and
never hand-edit it — regenerate it.

Return to SKILL.md D.5.5.
