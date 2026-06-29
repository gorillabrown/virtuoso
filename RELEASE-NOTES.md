# Virtuoso Release Notes

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
