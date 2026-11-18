# Roadmap review — the roadmap document, the work register, and the board

Serves `roadmap-review` SKILL.md wherever it writes the roadmap (A.4, C.2, C.6, D.5),
reads or writes the work register, or regenerates the board (D.7), and defines the
terms the skill uses.

## Glossary

- **Work item** — a discrete unit of work with clear acceptance criteria. The
  atomic dispatch unit. Identified by whatever id the project's register uses.
- **Group / workstream** — optional grouping levels, named by `policy.roadmap.hierarchy`
  and `policy.roadmap.workstreams`. A project may use neither.
- **Stub** — a placeholder item: id, title, and optionally a one-line gist.
- **Specification** — an item card with full structural fields plus implementation
  detail. It lives wherever `policy.roadmap.specStorage` says.
- **Dispatch-ready** — a specification that passes the shared readiness rubric.
- **Dispatch** — sending an item to the implementation agent.
- **Dispatch buffer** — the number of dispatch-ready specifications carried ahead
  of the head of the conveyor belt. Size is `policy.roadmap.dispatchBuffer`.

The progression of an item's content density:

```
Stub  →  Specification  →  Dispatch-ready  →  Close-out
(gist)   (drafted)         (rubric passed)    (terminal record)
                           ▲                  │
                           │                  ▼
                   roadmap-review        One record appended to the
                   Phase D.3 applies     terminal ledger; the full
                   the shared rubric     specification migrates to a
                                         dated archive
```

## Roadmap document template

Headings the plugin's parser recognizes are shown; a project may rename sections
and register the change. Grouping headings appear only if the project uses them.

```markdown
# [Project] — Roadmap

**Last updated:** [YYYY-MM-DD] — [one-line state]

## How This Document Is Maintained
[Archive-forward policy; dispatch buffer size; where specifications live]

## Finish Line — Target
[Description, graduated tiers if applicable]

## Completed Work Summary
| Item | Session | Result | Close-Out |
|------|---------|--------|-----------|

**Disposition of superseded work:**
- `[ITEM-ID]` — [reason]. [Where the work is preserved.]

## Active & Remaining Work

### Standing Rules All Items Inherit
- **[id from policy.standingRules.ids — short title].** [Rule.]

### [Workstream name]    *(only after an approved structure, C.2)*
[Its one-line purpose.]

#### [Deliverable name]
[Its one-line purpose.]

#### ITEM-ID — Title    *(position 1 — dispatch-ready)*
[structural fields + implementation detail, per D.5.2]

#### ITEM-ID — Title    *(beyond the buffer — stub)*
[One-line gist.]

## Non-Blocking Follow-Up Queue
## Notes
```

## The work register

The register's shape is the project's, not the plugin's. The canonical fields the
plugin reasons in are:

`id`, `title`, `sequence`, `status`, `written_status`, `prerequisites`, `effort`,
`effort_hours`, `workstream`, `deliverable`, `group`, `spec_link`, `branch`, `started`, `completed`,
`evidence`, `description`, `notes`.

Map them to the project's own column names in
`policy.workRegister.fieldMappings`, and the project's own status words in
`policy.workRegister.statusMappings`. Canonical statuses: `queued`, `in-flight`,
`blocked`, `completed`, `dissolved`, `superseded`. Canonical specification
states: `stub`, `full-spec`.

All metrics are computed from the register at read time, through the provider,
with provenance. There is no cache to refresh and nothing to recalculate.

## The roadmap board

The **roadmap board** is the project's one interactive page: a Dashboard (KPI tiles,
charts, slicers built from the data), a Roadmap tab (live work as a board, grouped by
pipeline state, with a comment box and a copy button on every row) and a Completed
tab (the register's terminal items joined with the terminal ledger, mismatches marked
*unreconciled*). `generate_board --create` makes D.7 the first review's step that brings
it into being: it registers the `board` and `boardComments` roles when they are missing
(default paths `roadmap-board.html` and `roadmap-board.comments.json` in the project
root), generates a missing page and reports `board created`, and adds the page's path
to `.gitignore` once — skipped when it is already ignored or the project is not a git
repository. The page is a build output: never commit it. The comments file is written
by people: commit it. A later review regenerates the page and reports `board
regenerated`.

The board reads the configured authoritative work register through its provider and
the roadmap through its registered role. It never modifies a source document; it
surfaces drift on the Dashboard instead. Every figure carries its provenance, and a
snapshot-backed read is labelled with its age. A `planning-cockpit.html` left by an
earlier version is not read or written; delete it when you like.

Return to SKILL.md at the step that sent you here.
