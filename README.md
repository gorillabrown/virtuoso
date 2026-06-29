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

Governance state lives in a `Virtuoso/` directory at your project root. It is created and
healed automatically; it is **never overwritten**.

```
Virtuoso/
├── .virtuoso                      # marker — tags this as a Virtuoso project
├── Roadmap.md                     # canonical roadmap
├── sprint-queue.xlsx              # Dashboard + Catalog (KPIs)
├── SpecRetro.Lessons_Learned.md   # running lessons catalog
├── WORKFLOW_REFERENCE.md          # index → skills
├── roadmap-reviews/  └── checkins/
├── Close-Outs/
├── audits/
└── scripts/                       # plugin-managed: recalc.py, build_sprint_queue.py, prepare_closeout_files.py
```

Three ways the workspace stays healthy:

1. **`/virtuoso-init`** — explicit setup/repair.
2. **Inline preflight** — every governance skill checks/creates it before running.
3. **SessionStart hook** — auto-heals an *existing* Virtuoso project (a no-op in unrelated
   folders, so it never litters directories you open by chance).

The hook also records the plugin's install path to `~/.virtuoso/plugin-root`, and preflight
vendors its scripts into `Virtuoso/scripts/`. This lets skills locate bundled scripts
*without* relying on `${CLAUDE_PLUGIN_ROOT}` — which resolves only inside hooks/MCP, never in
skill or command bodies.

## Skills & commands

| Skill | Command | Purpose |
|-------|---------|---------|
| `virtuoso` | — | Multi-step execution discipline for sprints |
| `roadmap-review` | `/roadmap-review` | Heavyweight roadmap recalibration |
| `roadmap-status` | `/roadmap-status` | Lightweight roadmap pulse check |
| `next-pointer` | `/next-pointer` | Finalize + dispatch the next sprint |
| `pointer-closeout` | `/pointer-closeout` | Close-out report + retrospective |
| `mid-dispatch-decision` | `/mid-dispatch-decision` | Decide when a dispatch pauses mid-run |
| `governance-sweep` | `/governance-sweep` | 3-phase doc-hygiene sweep: discover → approve → fix |
| `3rd-party-audit` | `/3rd-party-audit` | External codebase audit lifecycle |
| `ultrathink` | `/ultrathink` | Deep first-principles reasoning |
| `effort-levels` | — | Effort/cost sizing framework (modifier) |
| `adversarial-review` | — | Structured red-team review (modifier) |
| `git-handoff` | — | Legacy git handoff packet (manual only) |
| `delayed-start` | `/delayed-start` | Defer execution to a clock time / delay |
| `virtuoso-init` | `/virtuoso-init` | Create/repair the `Virtuoso/` workspace |

(The three modifiers and `virtuoso` itself are model-invoked — they layer onto other work
rather than being entry points, so they ship without a slash command.)

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
  mechanics). The roadmap spreadsheet still works without `xlsx`, because Virtuoso bundles
  `build_sprint_queue.py` (template generator) and `recalc.py` (Dashboard KPI recalc).
- **`product-management`** — `write-spec` and `roadmap-update`, used by `roadmap-review`.

## Project conventions

- **`zeus.md` / lead-agent reference** — several skills can read a project-supplied
  behavioral reference (routing, escalation, coordination rules). Provide your own per
  project; Virtuoso ships none.
- **Git Workflow** — `next-pointer` and `pointer-closeout` follow your project's Git Workflow
  (typically defined in the project's `CLAUDE.md`) for how — and whether — read-only git
  inspection runs and who commits. Cowork never runs mutating git itself.

## Requirements

- Python 3 with `openpyxl` for the bundled spreadsheet scripts (`build_sprint_queue.py`,
  `recalc.py`, `virtuoso_preflight.py`).

## License

MIT
