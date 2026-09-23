# Journal — Loop hardening

<!-- Append only. Never edit or delete an old entry — corrections get their own entry.
     One entry per session or work burst, newest last. -->

## S0 — 2026-09-23 18:30 — scaffold

- **Did:** epic packet created ([charter](charter.md), [plan](plan.md), [state](state.md),
  [launch](launch.md)). Source material: the SWOT and gap analysis (18 gaps, 21 hand-offs)
  and the white paper written earlier the same day. No project work performed yet beyond
  the merge of `4e00672` (metadata), which P1 verifies.
- **Learned:** the repository keeps no lessons role, so the charter's Lessons applied
  reads the SWOT and the release notes instead (0 read from a role; six applied). The two
  stranded branches are finished, additive work; whether they merge is the owner's call
  (state.md → Blockers #1). Preflight baseline: 775 passed, validator clean, version sync
  at 1.8.2, push and CI reachable.
- **Next:** P1 per plan.md — parity of the Claude manifest and marketplace entry with the
  Codex `interface` block, pinned by a test.

## S1 — 2026-09-23 18:45

- **Did:** merged `4e00672` (alternate-host `interface` block, icon assets, pinning test)
  as `b06ec0d`; brought the Claude manifest and the marketplace entry to parity with it
  (one description that names the learning loop, `displayName`, author with URL, one
  keyword list; marketplace gains `category` and `tags`); a third prompt chip for the
  close-out; `longDescription` says "prepare outside audits" instead of "audit
  third-party code", which the skill never did. Parity test added.
- **Learned:** A2 verified from the Claude Code docs (plugin-marketplaces, plugins-reference):
  `displayName`, `category`, `tags` are documented; `plugin.json` ignores unknown keys.
  The marketplace description had drifted ("16 skills") with nothing to notice it.
- **Decisions:** charter amended by the owner mid-session — D22, `governance-sweep`
  tidies, merges and retires lessons. Scheduled into P3 beside gap 3 (candidates),
  which reads the same close-out outcomes.
- **Gate/DoD movement:** D1 met (`pytest -k "manifest or marketplace"` 13 passed;
  version sync in sync at 1.8.2).
- **Next:** P2 — `roadmap-integrity:` line (one read), policy findings at preflight.

## S1 (cont.) — 2026-09-23 19:40 — P2 gate

- **Did:** `roadmap-integrity:` printed from one roadmap read shared with the deadline
  check (64216e8); `policy-invalid` warnings at every load (64216e8); default writers
  aligned, step 6d writes the `## Decision` block and the close-out reads it, ghost
  skills/agents/cases removed with a validator check, `epics` an opt-in role (f17a22f);
  sprint guards read v2 `roles` and run through the launcher; `created-files` (D23)
  wired into close-out Wave 1, Step 4 and Step 6, with a *Files Created* template
  section; sprint guards documented in the contract.
- **Learned:** the integrity check had to decode before looking for null bytes —
  `read_text` accepts UTF-16 on purpose, and a raw-byte check would have failed every
  PowerShell-written roadmap at session start. The ghost-name check found two real
  names it had to allow (`Zeus`, the orchestrator persona; `unassigned`).
- **Decisions:** none new.
- **Gate/DoD movement:** D2–D8 and D23 met; P2 gate passed (820 passed, validator clean).
- **Next:** P3 — lessons hygiene and candidates first (D22, D11), then D12, D9, D10.

## S1 (P3) — 2026-09-23 21:10 — P3 gate

- **Did:** `lessons --hygiene` / `--candidates` / `--record-status` and the `learning`
  metric group (7eae11a); governance-sweep check 21 tidies, merges and retires through
  them; roadmap-review D.4.2 computes candidates; the "No new lesson" reason is anchored
  (`lesson-reason-unanchored`); `record-completion` performs the ledger crossing with a
  recovery record on partial failure (cb81cc4); standing rules paired at preflight from
  the same roadmap read, and Zeus reads them from the registered source.
- **Learned:** recovery records serialize snake_case (`completed_steps`) — the CLI's
  JSON is camelCase elsewhere; a test caught the assumption. The close-out skill's own
  example reason ("a routine change with no surprise") would have failed the new
  anchored-reason gate — rewritten before it shipped, per the charter's lesson about
  templates failing their own gates.
- **Decisions:** #4 (record-completion covers Steps 3 and 5), #5 (D15 landed early).
- **Gate/DoD movement:** D9–D12, D15, D22 met; P3 gate passed.
- **Next:** P4 — the findings role (D13), effort calibration (D14).

## S1 (P4) — 2026-09-23 22:20 — P4 gate

- **Did:** CI runs 119 and 120 were red on Windows — the new CLI tests decoded child
  output as UTF-8 while a piped child writes cp1252 (em dash = 0x97). Reproduced by
  forcing cp1252, fixed in the helpers (80047fa). `findings` role with writers, a
  `create` seed, and the roadmap review reading open findings and its previous
  lessons-applied (f7bd2fd). Effort calibration: optional `effortEstimate` /
  `effortActual` in the ledger (by header; markdown only when its own header has the
  columns), `record-completion --estimate --actual`, `kpis effort-calibration`,
  `effort-levels` sizes by the project's figure; new workspaces' ledgers carry the
  columns.
- **Learned:** the Windows leg is the one that finds encoding assumptions — any new
  test helper that pins an encoding must pin the child's too. An existing test pinned a
  new CSV ledger's six-column header; the effort columns are added only when a record
  carries them, so that meaning is kept.
- **Decisions:** none new.
- **Gate/DoD movement:** D13, D14 met; P4 gate passed (866 passed).
- **Next:** P5 — D16, D17, D18; D19 stays with the owner.

## S1 (P5–P6) — 2026-09-23 23:10 — complete

- **Did:** agent residue removed and the validator scan extended; memory boundary stated
  once; promoted rules hashed; `dispatch-buffer-ready` (2970be9). v1.10.0 notes (d8ef633).
  Fresh DoD run of every row in one session.
- **Learned:** the fresh run found D2's literal check failing — the preflight's docstring
  still listed four machine lines. Fixed and pinned by a test rather than argued away.
- **Gate/DoD movement:** all rows met; D19 met as raised (owner decision pending); CI #126
  green on both legs. done.md written; charter status complete.
- **Next:** none for the executor. Owner: BLOCKER(USER) #1, launch Q2/Q3, release.
