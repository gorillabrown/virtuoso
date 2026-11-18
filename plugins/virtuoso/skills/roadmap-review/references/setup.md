# Roadmap review — capabilities and policy

Serves `roadmap-review` SKILL.md, *Resolve the work register and the policy before
Phase 0*, and Phase 0.3 (§ Register kinds).

## Capabilities to negotiate up front

Read the provider description and negotiate before starting:

| To do this | You need |
|---|---|
| read the pipeline at all | `list-active`, `read-status` |
| re-sequence the conveyor belt | `read-sequence` **and** `write-status` on a sequence field |
| replenish the dispatch buffer | `store-spec-link` (or inline specs — see policy) |
| record completion in Phase A (by `/dispatch-closeout`, A.4) | `record-completion` |
| register a newly specified item that has no row yet | `create-item` |
| absorb a held ad hoc plan (Phase A.4b, C.3) | `create-item`, plus `record-completion` for one that already ran |

If a capability you need is missing, say so plainly and adjust the plan before
starting. Example: a project whose register is a read-only snapshot can still get
Phases A–C as a *report*, but Phase D cannot write status back — offer the report
and stop, rather than starting and failing halfway.

## The three roles

The live work register (`workRegister`), the append-only terminal ledger
(`terminalLedger`), and any compatibility export (`sprintCatalog`, `sprintQueue`) are
separate. This ceremony writes to the live register when its `allowedWriters` names
`roadmap-review`. It appends a correction to the terminal ledger only when
`policy.terminalLedger.correctionWriters` permits it, and an ordinary record, such as a
retirement, only when `policy.terminalLedger.writers` names it. By default that never
happens, so it routes those records to `/dispatch-closeout` (A.4). It regenerates
exports only through their registered generator.

If the project has no `workRegister` role, the provider layer serves a registered
legacy `sprintCatalog` **read-only** through the compatibility adapter and says so. In
that state, run Phases A–C as analysis and offer to register a `workRegister` role
before doing anything that mutates.

## The policy keys this ceremony reads

The manifest's `policy` block governs the shape of the plan. Nothing below is a
fixed number or a required structure:

| Policy | What it controls | Default |
|---|---|---|
| `roadmap.dispatchBuffer` | how many dispatch-ready specifications to carry | 5 (0 disables eager specification) |
| `roadmap.eagerSpec` | whether to specify ahead at all | true |
| `roadmap.hierarchy` | grouping levels, e.g. `["phase","stage"]`, `["milestone"]`, or `[]` | `["phase","stage"]` |
| `roadmap.workstreams` | parallel workstreams, if the project uses them | none |
| `roadmap.specStorage` | `inline` (in the roadmap), `files` (one per item), or `external` | inline |
| `roadmap.lengthCeilingLines` | when to snapshot and trim | 2000 |
| `roadmap.effortScale` | size → points for effort-weighted metrics | generic t-shirt scale |
| `roadmap.effortBasis` | which effort governs the figures: `hours`, `size`, or `auto` (hours when the register maps `effort_hours`) | `auto` |
| `roadmap.maxItemHours` | items estimated above this many hours are flagged to split before sizing; 0 is off | 0 |
| `roadmap.deadlines` | dated finish lines, by id: `date`, `owner`, and optionally `label`, `finishLine`, `scope` | none |
| `roadmap.pace.trailingWeeks` | the window the trailing delivery rate is measured over | 4 |
| `roadmap.pace.tolerance` | how far from the required rate still reads "on track" | 0.1 |
| `standingRules.ids` | the project's inheritable rule identifiers | none — never hardcode one |
| `issues.targets` | where a blocker is written: `local`, `external`, or both | `["local"]` |

A project with a flat backlog and no phases is fully supported: `hierarchy: []`
means do not invent a phase layer to hang items from.

Return to SKILL.md where you left it; Phase 0 follows the policy read.

## Register kinds

Used at Phase 0.3, when no `workRegister` role is registered. Ask which of these the
project wants, and register it (the answer is a registry edit, previewed and approved —
this ceremony does not decide authority on its own):

- a local file the project already maintains (CSV or Markdown table),
- a spreadsheet,
- a connector-backed task manager, issue tracker, or database (registered as an
  external identifier such as `notion:database/<id>`, `linear:team/<key>` or
  `monday:board/1234567890`),
- a read-only snapshot, for reporting only.

If a legacy `sprintCatalog` is being read through the compatibility adapter, say
so explicitly in your report: it is a mirror, not the authority, and it cannot be
written until a `workRegister` role exists.

Return to SKILL.md 0.4.
