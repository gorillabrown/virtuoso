# Execution Paths — Three Ways In, One Destination

Work reaches implementation through one of three paths. The paths differ in **where the
work comes from and when it may start**. They do not differ in **what arrives at
execution**. Every path delivers the same thing: a specification that is robust, well
organized, and aware of the project and codebase around it. That specification is
executed under the `virtuoso` skill, closed out by `/pointer-closeout`, and recorded on
the master roadmap by `/roadmap-review`.

This file is the one home for that contract. The ceremonies that open a path —
`storyboard`, `write-plan`, `next-pointer`, `epic` — and the one that executes every
path, `virtuoso`, point here. None of them restates the contract in its own words.

## The three paths

| Path | Opened by | Draws from | May start | Who specifies it | The gate before execution |
|---|---|---|---|---|---|
| **Ad hoc** | `/storyboard`, then `/write-plan` | an idea the user brings now | any time | `storyboard` aligns it; `write-plan` specifies it | `write-plan`'s readiness gate |
| **Roadmap dispatch** | `/next-pointer` | the head of the master roadmap | only after a roadmap review has put the item there | `roadmap-review` (section D.3) | `next-pointer`'s readiness gate |
| **Roadmap epic** | `/epic` | an item on the master roadmap marked `Path: epic` | only after a roadmap review has put the item there | `roadmap-review` places it; `epic` charters it | `epic`'s walk-away preflight |

**The one asymmetry is timing.** The ad hoc path can open at any moment, because work
really does arrive between reviews. The two roadmap paths open only on items a roadmap
review has already placed on the master roadmap. Everything that follows from that:

- `next-pointer` and `epic` never start from an idea. An idea goes to `/storyboard`.
- `storyboard` and `write-plan` never write the roadmap or the live work register. They
  write one entry in the registered `holdingBay` role, and the next `/roadmap-review`
  reconciles it (see *The holding bay* in `registry-contract.md`).
- An epic-scale idea is storyboarded ad hoc, because alignment cannot wait. It is then
  held, absorbed by the next review as a `Path: epic` item, and chartered by `/epic`.
  `write-plan` never plans it.

## The destination contract

Every path meets every row below before execution starts. The rows are the standard;
the columns are how each path meets it.

| # | The destination requires | Ad hoc (`storyboard` → `write-plan`) | Roadmap dispatch (`next-pointer`) | Roadmap epic (`epic`) |
|---|---|---|---|---|
| D1 | **Alignment.** The user and the agent agree on the outcome, the scope, and what done looks like, and that agreement is written down. | The storyboard's alignment record and its *Aligned* verdict | The roadmap review's phase checkpoints; the item's *What*, *Why*, and *Done when* | The charter, sharpened with the user before launch; the absorbed storyboard where there is one |
| D2 | **A specification in the shared format.** | Roadmap-review's D.5.2 format, one per item, in the held plan | D.5.2, where `policy.roadmap.specStorage` puts it | The five-file epic packet; the charter's Definition of Done rows are verifiable |
| D3 | **Readiness by the shared rubric.** | `references/readiness-rubric.md`, walked in full | The same rubric, walked in full | Definition-of-Done rows that each name the command or procedure that verifies them, as U4 requires. The route is the executor's, so a discovery phase does the work U2 and U3 do for a dispatch |
| D4 | **Awareness of the project and codebase.** Edit sites verified against the code. Effects on other work named. Live lessons applied. Standing rules honoured. | The impact map, verified edit sites, U9 (`lessons --check`), and standing rules | U2 and U9, the standing rules, and the prerequisites checked through the provider | The charter's *Lessons applied* and constraints; a discovery phase whenever an assumption is unverified |
| D5 | **Readiness reported as five separate findings.** | Specification, prerequisites, repository, external register, execution environment | The same five | The same five, in the launch file's preflight |
| D6 | **A repository-reconciliation recipe matched to `policy.git`.** | Filled into the held plan's pointer | Filled into the dispatch pointer | In the launch file's preflight and constraints |
| D7 | **Execution under the `virtuoso` skill**, with the specification as its dispatch spec. | The held plan's pointer and specification | The dispatch pointer and specification | Every session of the run, with the packet as its dispatch spec |
| D8 | **Close-out through `/pointer-closeout`**: evidence verified, a close-out report, and lessons recorded. | Held-plan mode: evidence and lessons now; the register and the ledger at absorption | The full crossing | The full crossing, once `done.md` exists |
| D9 | **Reconciliation into the master roadmap.** | The next `/roadmap-review` absorbs the held entry, executed or not | The close-out crossing retires the item | The close-out crossing retires the item |

A path that cannot meet a row does not start execution. It says which row is missing and
what closes it.

## The origin line

Every pointer and every packet names where its work came from, so the executor and the
close-out know which path they are on:

```
Origin: roadmap — [ITEM-ID]
Origin: held plan — [entry] ([HB-n]), not yet on the roadmap
Origin: epic packet — [packet directory] ([ITEM-ID])
```

The close-out reads this line. A roadmap origin runs the full crossing against the
register. A held-plan origin runs held-plan mode: the close-out report and the lessons
are written now, the held entry moves to `executed`, and the register and the terminal
ledger wait for the review that absorbs it.

## The Path field

An item on the master roadmap carries its path in its roadmap entry's structural fields
(the D.5.2 format; a stub carries the field too):

```
- **Path:** dispatch
- **Path:** epic — [why it cannot be one dispatch]
```

A missing field means `dispatch`. `roadmap-review` sets `epic` when it places an
epic-scale item, including when it absorbs an epic-scale held storyboard. When
`next-pointer` finds `Path: epic` at the head of the belt, it routes the item to
`/epic` instead of the dispatch rubric.

## Routing

| The situation | Where it goes |
|---|---|
| A new idea, request, or bug the user wants handled now | `/storyboard` |
| The idea is already an item on the roadmap | That item: `/next-pointer` when it is the head, otherwise `/roadmap-review` |
| The idea is already a held plan | Resume that entry with `/write-plan <entry>` |
| The storyboard is epic-scale | Hold it; the next `/roadmap-review` places it as `Path: epic`; then `/epic` |
| A held plan is not executed now | It stays in the holding bay; the next `/roadmap-review` absorbs it into the roadmap, where `/next-pointer` dispatches it |
| The head of the belt says `Path: epic` | `/epic` |
| Execution stops on a decision | `/mid-dispatch-decision` |
| Execution is done | `/pointer-closeout` |
