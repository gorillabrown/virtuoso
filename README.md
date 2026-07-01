# Virtuoso

A Claude Code plugin that packages a complete **Cowork-style governance & dispatch
system**: a planning surface that specs and sequences work, hands dispatch-ready specs to
an implementer, and closes the loop with retrospectives, audits, and documentation
hygiene — backed by a self-healing per-project workspace.

## What it is

Virtuoso models a two-role workflow:

- **Cowork (planning)** — the high-capability model that plans the roadmap, writes
  dispatch-ready specs, makes decisions, and closes out sprints.
- **CLI (implementer)** — a lower-capability agent that executes a fully-specified sprint
  without judgment calls.

The skills enforce the discipline that makes that hand-off reliable: rigorous specs,
execution narration, progress tracking, mid-run decision protocols, close-out
retrospectives, and read-only governance audits.

**Reading the vocabulary.** The skills speak in terms of *Cowork* and *CLI* (their origin
in a Codex/Cowork setup). Read these as roles, not products: *Cowork* = your main planning
agent (on Claude Code, your interactive session); *CLI* / *the implementer* = whatever
executes a fully-specified sprint — a subagent, a separate lower-tier session, or a CLI
runner. The discipline is platform-neutral; only the names are historical.

## Install

```
/plugin marketplace add gorillabrown/virtuoso
/plugin install virtuoso@virtuoso-marketplace
```

Then initialize a project workspace:

```
/virtuoso-init
```

## The `Virtuoso/` workspace

Virtuoso supports two bootstrap layouts. Both are created and healed automatically, and
neither overwrites existing user files.

### Option 1: plugin-only `Virtuoso/` folder

Project documentation lives in the project root under `Project Documentation/`; `Virtuoso/`
holds plugin-managed files only. This is the default.

```
Project Documentation/
├── 1 governance/
│   ├── Roadmap.md
│   └── SpecRetro.Lessons_Learned.md
├── 2 operational/
│   ├── sprint-queue.xlsx
│   ├── roadmap-reviews/  └── checkins/
│   ├── Close-Outs/
│   └── Issues/
├── 3 temp/
├── 4 Outside Audits/
└── 5 Reference/
    └── WORKFLOW_REFERENCE.md

Virtuoso/
├── .virtuoso
├── workspace-layout.json
└── scripts/                       # plugin-managed: recalc.py, prepare_closeout_files.py
```

### Option 2: canonical Virtuoso layout

Project documentation lives under `Virtuoso/Project Documentation/`. When selected,
preflight migrates existing documentation into the new tree only when the destination path
is free; conflicts are left in place for human review.

```
Virtuoso/
├── .virtuoso                      # marker — tags this as a Virtuoso project
├── workspace-layout.json          # selected layout + path map
├── Project Documentation/
│   ├── 1 governance/
│   │   ├── Roadmap.md
│   │   └── SpecRetro.Lessons_Learned.md
│   ├── 2 operational/
│   │   ├── sprint-queue.xlsx
│   │   ├── roadmap-reviews/  └── checkins/
│   │   ├── Close-Outs/
│   │   └── Issues/
│   ├── 3 temp/
│   ├── 4 Outside Audits/
│   └── 5 Reference/
│       └── WORKFLOW_REFERENCE.md
└── scripts/                       # plugin-managed: recalc.py, prepare_closeout_files.py
```

`Virtuoso/workspace-layout.json` is the source of truth for skill path resolution. The
SessionStart hook runs preflight in `auto` mode, so it preserves whichever layout was
selected during `/virtuoso-init`.

### Adopting an existing project

If a project already maintains its own documentation tree — a `Project Documentation/` or
`2. Project Documentation/` directory with a `1 governance` / `2 operational` subtree and
its own roadmap under any name (e.g. `GoG_Roadmap.md`) — the governance skills **adopt it in
place** rather than scaffolding a parallel structure. On first run they invoke preflight
`--mode adopt`, which:

- discovers the project's existing roadmap and sprint-queue (preferring the live file over a
  fresh `/virtuoso-init` seed, a backup/snapshot copy, or an archived review), and
- writes only a thin `Virtuoso/` control dir (`.virtuoso`, `workspace-layout.json`, vendored
  `scripts/`) whose manifest **points at those existing files**.

Nothing is moved or duplicated and no parallel `Roadmap.md` is seeded. A project with no
discoverable roadmap is routed to `/virtuoso-init` instead, which seeds one. Before its
destructive rewrite, `/roadmap-review` also runs a `--check-roadmap` integrity gate and
stops on a corrupt roadmap (null bytes, non-UTF-8) rather than rewriting it.

Three ways the workspace stays healthy:

1. **`/virtuoso-init`** — explicit setup/repair.
2. **Inline preflight** — every governance skill runs `--mode adopt` before starting: it
   heals an existing workspace, adopts an established project in place, or routes a bare
   project to `/virtuoso-init`.
3. **SessionStart hook** — auto-heals an *existing* Virtuoso project (a no-op in unrelated
   folders, so it never litters directories you open by chance; it never adopts unattended).

The hook also records the plugin's install path to `~/.virtuoso/plugin-root`, and preflight
vendors its scripts into `Virtuoso/scripts/`. This lets skills locate bundled scripts
*without* relying on `${CLAUDE_PLUGIN_ROOT}` — which resolves only inside hooks/MCP, never in
skill or command bodies.

## Skills

All skills are invoked through the plugin namespace, e.g. `/virtuoso:roadmap-review`.
(The standalone `commands/` wrappers were removed — each only re-invoked its matching skill,
so it produced a duplicate slash entry alongside `/virtuoso:<name>`.)

| Skill | Slash | Purpose |
|-------|-------|---------|
| `virtuoso` | — | Multi-step execution discipline for sprints |
| `roadmap-review` | `/virtuoso:roadmap-review` | Heavyweight roadmap recalibration |
| `roadmap-status` | `/virtuoso:roadmap-status` | Lightweight roadmap pulse check |
| `next-pointer` | `/virtuoso:next-pointer` | Finalize + dispatch the next sprint |
| `pointer-closeout` | `/virtuoso:pointer-closeout` | Close-out report + retrospective |
| `mid-dispatch-decision` | `/virtuoso:mid-dispatch-decision` | Decide when a dispatch pauses mid-run |
| `governance-sweep` | `/virtuoso:governance-sweep` | 3-phase doc-hygiene sweep: discover → approve → fix |
| `3rd-party-audit` | `/virtuoso:3rd-party-audit` | External codebase audit lifecycle |
| `ultrathink` | `/virtuoso:ultrathink` | Deep first-principles reasoning |
| `effort-levels` | — | Effort/cost sizing framework (modifier) |
| `adversarial-review` | — | Structured red-team review (modifier) |
| `git-handoff` | — | Legacy git handoff packet (manual only) |
| `delayed-start` | `/virtuoso:delayed-start` | Defer execution to a clock time / delay |
| `virtuoso-init` | `/virtuoso:virtuoso-init` | Create/repair the `Virtuoso/` workspace |

(The three modifiers and `virtuoso` itself are model-invoked — they layer onto other work
rather than being entry points.)

## Agents

Virtuoso bundles a dispatchable agent roster in `agents/` (the virtuoso skill scans it when
delegating worker tasks):

| Agent | Model | Role |
|-------|-------|------|
| `Aristotle` | opus | Lead — investigation, cross-system, root-cause, cross-finding synthesis |
| `Hercules` | sonnet | Single-domain implementation |
| `Hermes` | haiku | Mechanical execution (config, renames, git) |
| `Hippocrates` | haiku | Test execution + coverage-gap reporting |
| `Plato` | sonnet | Code-quality review (complexity, coupling, dead code, duplication, churn, TODOs) |
| `MarcusAurelius` | sonnet | Docs, compliance, archiving + doc/spec drift detection |
| `Socrates` | sonnet | Calibration specialist |
| `Pythagoras` | sonnet | SQLite / data-integrity auditing |
| `Archimedes` | sonnet | Display / stats / scorecard auditing |
| `Hesiod` | opus | Archetype behavioral-KPI evaluation |

- **`skills/virtuoso/references/zeus.md`** is the orchestration protocol (routing tree, agent
  hierarchy, escalation rules) the `virtuoso` skill *reads* at Phase 1 — it is not a
  dispatchable subagent.
- **`agents/AGENT_MEMORY_GUIDE.md`** documents the shared agent-memory convention.
- `Socrates`, `Pythagoras`, `Archimedes`, and `Hesiod` are domain-flavored templates — adapt
  their project-specific paths and targets per project.

## External prerequisites (recommended)

Some skills reference skills from other plugins. They are **not** bundled:

- **`anthropic-skills`** — `docx` (audit orientation documents) and `xlsx` (spreadsheet
  mechanics). The bundled `sprint-queue.template.xlsx` is the canonical roadmap workbook (a
  hand-built Excel file with live formulas + chart); `recalc.py` refreshes its Dashboard KPIs
  headlessly when a skill edits the Catalog without opening Excel.
- **`product-management`** — `write-spec` and `roadmap-update`, used by `roadmap-review`.

## Project conventions

- **`zeus.md` / lead-agent reference** — several skills can read a project-supplied
  behavioral reference (routing, escalation, coordination rules). Provide your own per
  project; Virtuoso ships none.
- **Git Workflow** — `next-pointer` and `pointer-closeout` follow your project's Git Workflow
  (typically defined in the project's `CLAUDE.md`) for how — and whether — read-only git
  inspection runs and who commits. Cowork never runs mutating git itself.

## Requirements

- Python 3 with `openpyxl` for the parts that read/write the sprint-queue workbook:
  `recalc.py` (Dashboard KPI refresh) and the roadmap visualizer
  (`tools/roadmap_visualizer/`, incl. `scripts/generate_cockpit.py`). The preflight
  (`virtuoso_preflight.py`) and the rest of the scripts need only the standard library.

## License

MIT
