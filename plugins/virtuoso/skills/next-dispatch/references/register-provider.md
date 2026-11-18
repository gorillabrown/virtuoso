# The Register's Provider

Serves next-dispatch *Resolve the register before anything else*: the capabilities to negotiate, the compatibility adapter, and refreshing a stale snapshot.

The register may be a CSV, a Markdown table, a spreadsheet, a connector-backed
task manager, an issue tracker, a database, or a read-only snapshot. What matters
is what the provider can do:

| To do this | Capability required |
|---|---|
| find the next eligible item | `next-eligible` (or `list-active` + `read-sequence`) |
| verify prerequisites | `read-prerequisites` |
| report effort-based figures | `read-effort` |
| record a status change during pre-flight | `write-status` |
| store a specification link | `store-spec-link` |

Negotiate these **before** planning the run. If the provider cannot serve one you
need, say so up front, and adjust: a read-only snapshot still supports the whole
read path and produces a complete kickoff; it simply cannot record a pre-flight
status correction, which you then hand to the user instead.

If the register is served through the **compatibility adapter** (a legacy
`sprintCatalog` with no `workRegister` role), say so in the output: reads work,
writes do not, and registering a `workRegister` role is the fix.

## Refreshing a stale snapshot

If the snapshot is **stale**, refresh it before naming the head. `next` prints
`[STALE]` with its age. For a connector-backed register, read every item with the
session's connector, write the rows keyed by the register's own column names, and
import them: `virtuoso_registry snapshot --import <rows.json>` — or, where the connector
returns an items page with `column_values`, the page and its column list:
`snapshot --import <page> --columns <columns>` (the plugin's `references/registry-contract.md`,
*Refreshing a connector-backed register's snapshot*). Report each `[DRIFT]` line as a finding. The import keeps a card's
subitems, such as owner decisions, out of the work list, so none is named as the head
card. Then run `next` again. When the snapshot
cannot be refreshed, print its age. External-register readiness is then a GAP, and the
verdict is "Not ready" until the head is confirmed against the live register.

Return to SKILL.md and continue at Phase 1.
