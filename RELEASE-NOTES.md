# Virtuoso Release Notes

## v1.4.0 (2026-08-25) — source-of-truth redesign

**Breaking changes, despite the minor version number.** Plugin 1.3.6 → 1.4.0; the
**registry schema moves 1 → 2**; several bundled scripts are removed. Migration itself is
non-destructive and previewed — see [`docs/MIGRATION-1.4.md`](docs/MIGRATION-1.4.md) for the
full removed-and-changed tables.

### Release-blocking safety

- **A genuinely read-only preflight.** `--mode check` performs discovery and validation with
  **zero project writes**, in every project state. The SessionStart hook now runs it, so
  starting, clearing, or compacting a session can no longer create, heal, vendor, or rewrite
  a project file.
- **Four separate operations.** `check` (validate), `adopt` (register in place), `create`
  (initialize, requires `--authorize`), `repair` (preview, then `--apply`). Adoption against
  an already-registered project behaves exactly like `check` — it never silently heals.
- **The human registry is never regenerated from a template.** Only the plugin's own
  generated region is refreshed; user prose, tables, labels, comments, ordering, line
  endings, and extension sections are preserved byte-for-byte. A registry with no generated
  region is user-authored: the plugin reads it, reports divergence, and offers only an
  additive append behind an approved repair.
- **Repair is previewable and transactional.** The preview names the proposed paths, semantic
  changes, files affected, and backup location, and writes nothing. The apply validates the
  reconstruction before any write, backs every existing target into a hash-verified set, and
  restores on any failure — leaving the original registry and manifest intact.
- **Verifiable backups.** Each entry records source, destination, byte count, SHA-256,
  timestamp, and operation, with a manifest that restores and verifies independently.
- **One complete status contract**, documented and tested: `ready`, `warning`,
  `repair-needed`, `repair-preview`, `repaired`, `adoptable`, `adopted`, `created`, `none`,
  `failed` — plus `--json` for the full structured result.
- **No global unversioned plugin pointer.** `~/.virtuoso/installs.json` is keyed by plugin
  version, and version-agnostic launchers (`virtuoso`, `virtuoso.ps1`) resolve the newest
  valid install. Two installed versions can no longer overwrite each other's discovery state.

### Governance registry redesign

- **One authority.** `Virtuoso/workspace-layout.json` holds the structured configuration;
  `Virtuoso.Governance.Readme.md` is a synchronized view with protected user sections.
  Divergence produces a diagnostic, never an overwrite.
- **A versioned schema** with a declared plugin-compatibility range.
- **Full role metadata**: path or external identifier, provider type, authority level,
  mutability, owning ceremony, allowed writers, validation method, presence, active/historical
  classification, and authored/generated origin.
- **Seven authority classifications**: live, terminal, mirror, report, evidence, archive,
  reference — plus `unknown` for conservative migration.
- **Authority is never inferred from a role name.** A role called `sprintCatalog` is
  authoritative only when the project says so.
- **External identifiers are valid registrations.** A board, project, database, or service id
  is validated by shape and never reported as a missing filesystem path.
- **Protected `x-` extension namespaces** survive plugin upgrades verbatim.
- **Registered paths are validated before use**: root escapes, unsafe absolute paths, archive
  paths claiming live authority, malformed external identifiers, and role/type mismatches are
  all rejected.
- **A registered-but-absent target is reported**, never repointed at a lookalike.
- **Conservative migration.** Unknown legacy roles stay unknown; the legacy local catalog
  migrates as a read-only compatibility mirror, not as the live register.

### Work-register provider architecture

- **A provider interface** with negotiated capabilities: list active, read sequence, read and
  write status, read prerequisites, read effort, store specification links, record
  completion, find the next eligible item.
- **Implementations** for local CSV, local Markdown, spreadsheet, read-only snapshot, and
  external registers (connector-backed task manager, issue tracker, database).
- **Three distinct roles**: the live work register, the append-only terminal ledger, and any
  optional compatibility export. The local CSV catalog is now optional.
- **Configurable field and status mappings.** Nothing requires the literal vocabulary
  *Queued*, *In Flight*, *Blocked*, *Completed*, *Stub*, or *Full Spec*.
- **Provenance on every derived metric**, and **"not computable"** with the missing inputs
  named rather than a fabricated figure.
- **Offline operation** through timestamped snapshots that are marked stale past a
  configurable window.
- **Optimistic concurrency**, **idempotent cross-system updates**, and **recovery records**
  that name exactly what remains after a partial failure.

### Ceremonies

- Roadmap Review works through the configured provider and touches a compatibility export
  only when it is registered, generated, and writable.
- Roadmap Status is **read-only by default**; corrections require an explicitly approved
  phase and a role this ceremony is registered to write.
- Next Pointer determines the next item through the provider — the absence of any particular
  file is no longer a hard stop — leads with descriptive names, and reports readiness as five
  separate findings: specification, prerequisite, repository, external-register, and
  execution-environment.
- Pointer Close-Out performs an ordered transactional crossing: verify evidence, create the
  artifact, append the terminal record, persist locally, close the item in the live register,
  verify every result — with a recovery record on any partial failure.
- The terminal ledger is **append-only** with configurable writers; corrections are new
  records referencing prior ones, and history is never reordered, rewritten, or deleted.
- The dispatch buffer, the phase/stage/lane hierarchy, and where specifications are stored
  are all project policy. Standing-rule identifiers and branch conventions come from policy;
  none are hardcoded. Issue escalation is provider-aware.
- **One shared, versioned readiness rubric** (`references/readiness-rubric.md`, v1.0), split
  into eight universal checks plus project-declared extensions. The two ceremonies that used
  to carry divergent copies now read the same file.

### Governance sweep

- Structural authority resolves through the registry; a directory readme is authoritative
  only when the project declares it so.
- Configurable scan boundaries (include/exclude, ignored directories, symlinks, file-size
  ceilings, binary policy) and protected path classes that can never enter a mutation plan.
- **Quarantine before deletion** by default, with irreversible actions moved to the end.
- Backup manifests that restore and verify; retention policy; backup and quarantine
  directories excluded from future sweeps.
- Source-and-derived artifact relationships, regeneration instead of hand-editing,
  document-type verification adapters, registered generation and validation commands,
  tested-before-documented command repair, immutable-hash verification, and exact repository
  scope in the completion report.

### Git and portability

- The universal "the planner never mutates git" rule is replaced by a configurable policy
  ladder: read-only, prepare-no-stage, explicit-path-stage, explicit-path-commit, push.
- Separation of duties is an optional project policy, tied to no product.
- The default branch and remote are **detected**; a repository with **no remote** is
  supported; branch cleanup is maintenance, not a dispatch prerequisite; a stale lock is
  reported, never deleted; network operations are explicit; and the plugin is worktree-aware.
- Product-, vendor-, and model-specific names are gone from shipped content. Actors are
  configurable roles; routing uses vendor-neutral task tiers; readiness never rests on a
  claim that one host or model is superior.
- A host-neutral launcher in both POSIX-shell and PowerShell forms; package resources resolve
  relative to the installed plugin; runtime dependencies are declared and checked; fixtures
  and comments carry no project's names, thresholds, or directory assumptions.

### Tooling

- The planning cockpit reads the configured authoritative provider instead of requiring a
  generated spreadsheet.
- The retired recalculation script is removed — bundled copy, tests, vendoring, and the
  visualizer's recommendation.
- Generated workbooks are presentation outputs; nothing reads one as operational truth.
- Close-out path resolution fails loudly on a malformed registry instead of falling back to a
  conventional directory, and is read-only unless `--prepare` is passed.

### Validation

216 tests and an expanded structural validator now cover byte-for-byte preservation, registry
round-tripping, authority precedence, external identifiers, read-only hooks, repair previews,
transactional failure, idempotency, cross-platform launchers, repository states, the provider
contract, documentation-to-code agreement, and migration fixtures for the older schema.

## v1.2.1 (2026-07-02)

### Added

- **Governance registry — `Virtuoso.Governance.Readme.md`.** A new project-root authority
  that maps every required governance role (roadmap, sprint catalog, lessons, close-outs,
  issues, reviews, outside audits) to its *actual* path in whatever layout the project uses,
  marking each present or absent. The preflight engine generates it idempotently on
  create/adopt/heal, and `Virtuoso/workspace-layout.json` is its machine-readable mirror.

### Changed

- **All six governance gate skills now read the registry first.** `/roadmap-status`,
  `/next-pointer`, `/roadmap-review`, `/pointer-closeout`, `/mid-dispatch-decision`, and
  `/3rd-party-audit` resolve every document through `Virtuoso.Governance.Readme.md`, defer to
  the paths it lists, and **never create a parallel or competing document for a role already
  registered.** On registry/disk divergence the rule is to repoint the registry, not fork a
  rival. A contract test enforces that every gate skill references the registry.

### Fixed

- **Established projects are no longer seeded over with an empty roadmap.** Preflight
  discovery previously recognized only `Project Documentation/` trees, so a project whose
  governance lives elsewhere (a root `ROADMAP.md`, a `docs/governance/` tree) was treated as
  bare and given a fresh empty template — which the skills then tried to reconcile against the
  real roadmap, improvising parallel plumbing. Discovery now finds the live roadmap across
  root, `docs/`, and `docs/governance/` layouts, adopts the project in place, and anchors
  every registry role to the real governance home instead of a phantom default path.

## v1.2.0 (2026-07-02)

### Changed

- **`sprint-catalog.csv` is now the source of truth for sprint/KPI data**, replacing
  `sprint-queue.xlsx`'s Dashboard + Catalog tabs across `/roadmap-status`,
  `/next-pointer`, `/roadmap-review`, and `/virtuoso-init`. All KPIs (totals, %
  complete, buffer health, phase progress) are computed catalog-direct from the CSV
  at read time — there is no cache to go stale, and no `recalc.py` step to run.
  Root cause: a companion xlsx's Dashboard tab is fed by Power Query, which only
  recomputes when a human opens the workbook in Excel; force-writing it headlessly
  via openpyxl (the old `recalc.py` path) fights that refresh and produces
  internally-contradictory cached values.
- `sprint-queue.xlsx` is now optional and, where a project keeps one, strictly a
  generated, human-facing report — written from the CSV via `build_sprint_queue.py`,
  never read back by any skill.
- `/virtuoso-init` seeds new workspaces with `sprint-catalog.csv` (header row only)
  instead of the `sprint-queue.xlsx` template.
- `pointer-closeout` documents the CSV as the authoritative catalog location, with
  `sprint-queue.xlsx` / `sprint-queue.md` named only as legacy/optional companions.

### Known gap

- `tools/roadmap_visualizer/workbook.py` (feeding the planning-cockpit generator)
  still reads `sprint-queue.xlsx` via openpyxl rather than `sprint-catalog.csv`;
  migrating it is tracked as follow-up work. Until then, treat the cockpit's
  sprint-level figures as secondary to the CSV-computed figures reported directly
  by `/roadmap-status` and `/next-pointer`.

## v1.1.7 (2026-06-30)

### Added

- **cwd-independent cockpit launcher.** `scripts/generate_cockpit.py` pins its own import
  root so the roadmap planning cockpit runs from any working directory (and for an installed
  plugin), fixing the previous `python -m tools.roadmap_visualizer.generate` command that
  only worked from `plugins/virtuoso/`. `/roadmap-review` now regenerates the cockpit as its
  final step (D.7) via the `~/.virtuoso/plugin-root` bridge; there is no standalone command.
- **`conftest.py`** pins the test import root so `tools.roadmap_visualizer` resolves
  regardless of the directory pytest is invoked from.

### Changed

- **CI runs the full test suite.** The `Tests` step now runs `pytest plugins/virtuoso/`
  instead of two hand-picked files, so the roadmap-visualizer suite (and every other
  previously-ungated test) actually gates merges. The green check is now honest.
- Removed the standalone "Roadmap planning cockpit" command/section from the README — the
  visualizer is invoked only from within `/roadmap-review`.

### Fixed

- `.gitignore` now excludes the `skills.zip` build artifact so it cannot be committed by
  accident.

## v1.1.6 (2026-06-30)

### Added

- **Adopt an established project in place.** The preflight gained `--mode adopt`: when a
  project already maintains its own documentation tree (`Project Documentation/` or
  `2. Project Documentation/` with a `1 governance` / `2 operational` subtree) but has no
  `Virtuoso/` marker, `adopt` lays down only a thin `Virtuoso/` control dir whose
  `workspace-layout.json` **points at the existing roadmap** (under any name, e.g.
  `GoG_Roadmap.md`). Nothing is moved or duplicated, and no parallel `Roadmap.md` is
  seeded. It prints a parseable `virtuoso-status: ready|adopted|none` line.
- **Roadmap discovery.** Both `adopt` and `create` now discover an existing roadmap and
  sprint-queue anywhere under the documentation root (preferring the live, non-archived
  copy with roadmap structural markers) and record those real paths in the manifest,
  instead of assuming `1 governance/Roadmap.md`.
- **Roadmap integrity guard.** `--check-roadmap PATH` sanity-checks a roadmap before a
  heavyweight rewrite and exits `0` ok / `2` warn (empty or unusually large) / `3` fail
  (null bytes, non-UTF-8, or missing). `/roadmap-review` runs it as a pre-rewrite gate and
  stops on a corrupt roadmap rather than rewriting it.

### Changed

- **Governance gate skills now adopt instead of bailing.** `roadmap-review`,
  `roadmap-status`, `next-pointer`, `pointer-closeout`, `mid-dispatch-decision`, and
  `3rd-party-audit` call `--mode adopt` and branch on the printed status, so an
  established project is brought under management in place rather than reporting "no
  workspace" and routing to `/virtuoso-init` (which would have scaffolded a parallel tree).
- `virtuoso-init` documents adoption and its `create` flow is now adoption-aware (points
  at an existing roadmap rather than seeding a new one).

### Fixed

- **No more parallel roadmap.** An established roadmap kept under a non-default name or in
  `2 operational/` is no longer shadowed by a freshly seeded `1 governance/Roadmap.md`.

## v1.1.5 (2026-06-30)

### Added

- **Roadmap visualizer** (`tools/roadmap_visualizer/`) — renders the roadmap +
  sprint-queue Dashboard to HTML, with manifest-aware workspace discovery and a
  staleness check that flags a drifted Excel Dashboard cache and routes it to
  `/roadmap-review`.
- **Workspace layout manifest.** `virtuoso-init` now offers a layout choice
  (plugin-only vs. canonical `Virtuoso/Project Documentation/`) and the preflight
  writes `Virtuoso/workspace-layout.json`. Skills resolve workspace paths from that
  manifest (`roadmap`, `sprintQueue`, `closeOuts`, `issues`, `outsideAudits`,
  `reference`, `scripts`) instead of hard-coded flat paths, falling back to the
  legacy layout for older projects.

### Changed

- **Preflight** gained `--mode detect|create` and `--layout plugin-only|canonical`,
  generating and respecting the workspace manifest (idempotent, non-destructive).
- Skills (`roadmap-review`, `roadmap-status`, `next-pointer`, `pointer-closeout`,
  `mid-dispatch-decision`, `3rd-party-audit`, `virtuoso`, `virtuoso-init`) now read
  the manifest as the source of truth for workspace paths.

### Fixed

- **Removed duplicate slash-menu entries.** The 10 `commands/*.md` wrappers each only
  re-invoked their matching skill, so every name appeared twice — once bare
  (`/roadmap-review`) and once namespaced (`/virtuoso:roadmap-review`). Skills are
  invoked directly via the `virtuoso:` namespace, so the wrappers were removed; the
  structural validator now treats `commands/` as optional.

## v1.1.4 (2026-06-30)

### Fixed

- **Relaxed the git posture in `next-pointer` (and clarified `git-handoff`).** The
  skills were conflating "Cowork doesn't *commit*" with "no git at all, even reads,"
  and quarantining the dispatch's git reconciliation into a read-only handoff packet.
  Now:
  - **Read-only git (`status`/`log`/`diff`/`show`) is always available** in every
    project — no project gates reads. Legacy mutating-handoff conventions (e.g.
    `git-handoff`) govern only *state-changing* commands; "no commits" never means
    "no git at all."
  - **The enrichment commit rides with the sprint.** The dispatch pointer's git
    reconciliation recipe lands the finalized spec as step 0 of the sprint (per the
    project's Git Workflow), instead of a separate pre-dispatch hand-off that could
    deadlock. Cowork still authors-but-doesn't-certify its own commit (separation of
    duties); the sprint's implementer (or the user) commits it.
  - `git-handoff` now states explicitly that even when the legacy packet is
    requested, read-only git stays available for verification.

## v1.1.3 (2026-06-29)

### Fixed

- **Eliminated duplicate skill registration.** The plugin now lives in a subdirectory
  (`plugins/virtuoso/`) with `marketplace.json` at the repo root pointing to it
  (`"source": "./plugins/virtuoso"`), matching the documented marketplace layout. Previously
  the plugin sat at the repo root (`"source": "."`), so the cloned marketplace directory was
  itself a plugin directory and Claude Code loaded every skill twice — once namespaced
  (`virtuoso:roadmap-review`) and once unprefixed (`roadmap-review`). Internal
  `${CLAUDE_PLUGIN_ROOT}` / vendored-script paths are unaffected (they resolve relative to the
  plugin directory, which moved as one unit). **Install commands are unchanged.**

### Upgrade note

- To clear the duplicate locally, fully reset the marketplace rather than a plain update:
  `/plugin marketplace remove virtuoso-marketplace`, then `/plugin marketplace add gorillabrown/virtuoso`
  and `/plugin install virtuoso@virtuoso-marketplace`. A plain `/plugin update` may leave the old
  root-plugin clone in place.

## v1.1.2 (2026-06-29)

Integration-correctness pass — **Phase 1 of the v1.2.0 integration design**
([docs/virtuoso/specs/2026-06-29-v1.2.0-integration-design.md](docs/virtuoso/specs/2026-06-29-v1.2.0-integration-design.md)).
Closes the lifecycle loop, reconciles conflicting load-bearing rules, and adds a structured
issue-handoff contract.

### Fixed

- **Git ownership reconciled; legacy `git-handoff` no longer mandated.** `pointer-closeout`
  now persists per the project's Git Workflow (Cowork never mutates git; the user or a
  dispatched executor commits; Cowork verifies read-only) instead of invoking the
  LEGACY/MANUAL-ONLY `git-handoff` skill, which disclaimed sprint-closeout use. (BC-1/BC-2)
- **Orchestrator naming unified to `Zeus`.** `zeus.md` no longer calls the orchestrator
  "CLI" (which contradicted the skill body and the README). It is rewritten as a lean,
  project-agnostic protocol — GoG-specific calibration bands, worktree scripts, absolute
  paths, and SRL/memo references removed; two clearly-marked illustrative blocks retained —
  with a Cowork/CLI ↔ Zeus vocabulary bridge. (BC-3/F17)

### Added

- **Closed the planning loop.** `pointer-closeout` runs a mandatory buffer-depletion check
  after elevating the conveyor belt — if fewer than 5 dispatch-ready specs remain (or the new
  head is a stub), it recommends `/roadmap-review`. The executor (`virtuoso`) is now
  bookended: its close-out names `/pointer-closeout`, and its spec source is `/next-pointer`.
  (BC-4/BC-5)
- **Structured issue-handoff contract (`virtuoso` → `mid-dispatch-decision`).** Every
  stop/hold/block/elevation is rendered in a fixed 7-field format (tl;dr, executive summary,
  evidence, possible causes, likely solutions, confidence 1–10, exported path) and saved as
  `Virtuoso/Issues/Issue.<id>.<date>.md`; `mid-dispatch-decision` now expects that path as
  its primary input. New `Virtuoso/Issues/` workspace directory.

### Notes

Phases 2–4 of the integration design (authoring-modifier wiring, the Ideas + `/reconcile`
skills, governance-sweep roadmap/queue hygiene, and shared-reference de-duplication) ship in
v1.2.0.

## v1.1.1 (2026-06-29)

### Fixed

- **Orchestrator renamed `codex-parent` → `Zeus`** in the `virtuoso` skill, matching the
  `zeus.md` orchestration protocol and the capitalized deity worker roster. The orchestrator
  (the parent agent that owns the plan, integration, decisions, and close-out) now shows as
  `Zeus` in task plans, the routing tree, narration, and the worker-utilization summary.

## v1.1.0 (2026-06-29)

Sprint-queue **v2** workbook support. The roadmap workbook was restructured; Virtuoso's
data engine, skills, and bundled template now match it.

### Changed

- **`sprint-queue.xlsx` v2 structure** — three sheets (`Dashboard`, `DATA.sprint-catalog`,
  `Variables`). The Catalog is a 20-column Excel table (`sprint_catalog`) with five
  formula-driven computed columns (Priority, Done?, PhaseRank, SizeRank, SortKey) that
  auto-rank the conveyor belt; the Dashboard carries a Status-Distribution doughnut chart and
  an auto-ranked "Next Up" queue.
- **`recalc.py` rewritten** — reads the Catalog by **header name** (column-order independent)
  and auto-detects the data sheet, so it is robust to the rename and the added `Notes` column.
  New Dashboard cell map (`B11–B18` pipeline incl. `Superseded`, `B21–B26` effort); LOE points
  span eight sizes (XS 0.5 … XL 20); status vocabulary adds `Superseded`/`Pivot` and matches
  `Completed*`. Validated against real data (reproduces every cached KPI); preserves the chart
  and tables on save.
- **Skills remapped to v2** — `roadmap-status`, `next-pointer`, and `roadmap-review` use the
  new Dashboard cells and the `DATA.sprint-catalog` layout. Buffer health, full-specs-queued,
  and phase progress (no longer Dashboard cells) are computed from the Catalog.
- **Bundled template refreshed** — `sprint-queue.template.xlsx` is the clean v2 workbook
  (chart, tables, and live formulas intact).

### Removed

- **`build_sprint_queue.py`** — the bundled `.xlsx` is the single source of truth for the
  template; the generator and its preflight/test/doc wiring are gone.

### Migration

- `/virtuoso-init` never overwrites an existing `sprint-queue.xlsx`. A project still on the
  old two-sheet workbook keeps it and will mismatch the v2 cell map — recreate it from the new
  template (or re-point your data) to adopt v2. New projects get v2 automatically.

## v1.0.0 (2026-06-29)

First public release. Virtuoso packages a complete Cowork-style governance & dispatch
system — roadmap planning, sprint execution discipline, close-outs, mid-run decisions,
external audits, and documentation hygiene — as a single installable Claude Code plugin,
backed by a self-healing per-project workspace.

### What's included

- **14 skills**, **10 commands**, and a **SessionStart hook**.
  - Execution & planning: `virtuoso`, `roadmap-review`, `roadmap-status`, `next-pointer`.
  - Close-out & decisions: `pointer-closeout`, `mid-dispatch-decision`.
  - Governance & audits: `governance-sweep`, `3rd-party-audit`.
  - Reasoning modifiers: `ultrathink`, `effort-levels`, `adversarial-review`.
  - Utilities: `delayed-start`, `git-handoff` (legacy/manual), `virtuoso-init`.
- **Self-healing `Virtuoso/` workspace** — `Roadmap.md`, `sprint-queue.xlsx`, lessons
  catalog, workflow-reference index, and review/close-out/audit folders, created and healed
  idempotently and never overwritten.
- **Bundled, dependency-light scripts** — `recalc.py` (pure-Python Dashboard KPI recalc,
  no Excel/LibreOffice required) and `virtuoso_preflight.py`.
- **Agent roster** — a dispatchable `agents/` roster (`Aristotle`, `Hercules`, `Hermes`,
  `Hippocrates`, `Plato`, `MarcusAurelius`, `Socrates`, `Pythagoras`, `Archimedes`, `Hesiod`)
  with the shared `AGENT_MEMORY_GUIDE.md`, plus the `zeus` orchestration protocol at
  `skills/virtuoso/references/zeus.md` (read by the virtuoso skill, not dispatched). The
  legacy single-dimension analysis agents were folded into `Plato` / `Hippocrates` /
  `MarcusAurelius` / `Aristotle`; superseded older agents were archived. All agent
  absolute paths were de-hardcoded to `<project-root>/…`.

### Robustness (incorporating learnings from obra/superpowers)

- **Skill bodies no longer depend on `${CLAUDE_PLUGIN_ROOT}`.** That variable resolves only
  inside hooks/MCP, never in skill or command markdown. The SessionStart hook now records
  the plugin's path to `~/.virtuoso/plugin-root`, and preflight vendors the bundled scripts
  into `Virtuoso/scripts/`, so every in-skill script call is workspace-relative and robust.
- **SessionStart hook scoped** to `startup|clear|compact` (was `*`), `async: false`.
- **Authoring fixes from the build:** the `3rd Party Audit SKILL.md` filename normalized;
  `delayed-start` frontmatter added; `pointer-closeout` absolute paths removed; dangling
  `WORKFLOW_REFERENCE.md §` citations repointed to the `effort-levels` / `3rd-party-audit`
  skills (with a generated index in the workspace).
- **Description hygiene:** `next-pointer` and `adversarial-review` descriptions trimmed under
  the 1024-char frontmatter limit, preserving all trigger phrases and manual-invocation
  gating.

### Tooling

- `scripts/validate.py` — structural validator (frontmatter, manifests, no absolute paths,
  no dangling refs, no `${CLAUDE_PLUGIN_ROOT}/` in skill bodies, command↔skill mapping).
- `scripts/bump_version.py` — version sync across manifests (`--check` / `--audit` / bump),
  driven by `.version-bump.json`.
- **GitHub Actions CI** runs the validator, version check, and the Python test suites
  (`recalc`, `virtuoso_preflight`) on every push and PR.

### Install

```
/plugin marketplace add gorillabrown/virtuoso
/plugin install virtuoso@virtuoso-marketplace
/virtuoso-init
```

### Known follow-ups (post-1.0)

- Split the largest skills' heavy reference detail into `references/` for token efficiency.
- Add behavioral/triggering evals (in the spirit of superpowers' eval harness).
- Optional Windows polyglot hook dispatcher for graceful no-op when Python/bash is absent.
- Reassess the Cowork/CLI vocabulary vs. true multi-harness support.
