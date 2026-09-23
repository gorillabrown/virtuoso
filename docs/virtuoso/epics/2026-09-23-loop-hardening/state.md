---
epic: loop-hardening
last_updated: 2026-09-23 19:40
updated_by: session 1
---

# State — single source of current truth

<!-- Rewrite freely; keep under ~80 lines. History belongs in journal.md; the route in
     plan.md; the contract in charter.md. Never end a work burst with this file stale. -->

## RESUME PROTOCOL — no memory of this epic? Do this first, in order

1. Read charter.md (the contract), then plan.md (the route), then all of this file, then
   the **last** entry of journal.md.
2. Distrust, then verify: these files are MEMORY; the repo/system is REALITY. Run the
   cheapest check that confirms the "Where we are" block below (usually the current
   phase's exit-gate command). On conflict: believe reality, fix this file, note the
   correction in journal.md.
3. If `done.md` exists in this directory, do not start work — re-verify its claims
   against the charter DoD and report.
4. If `last_updated` above is older than the newest journal entry, trust the journal and
   repair this file before working.
5. Append a session-start entry to journal.md, then continue from "Next actions".

## Where we are

```
phase:        P3 — Make the prose links mechanical
next_action:  lessons --hygiene / --record-status / --candidates (D22, D11), then record-completion (D9)
blockers:     BLOCKER(USER) #1 (stranded branches) — does not block P3–P6
session:      1 of ~3 budgeted
dod:          D1–D8 [met] | D9–D18 [unmet] | D19 [raised] | D20–D22 [unmet] | D23 [met]
```

## Next actions — max 5, near horizon only

1. [ ] D22 + D11: `lessons --hygiene`, `--record-status`, `--candidates`; governance-sweep and roadmap-review D.4 run them
2. [ ] D12: anchored no-lesson reason; `kpis lesson-yield`
3. [ ] D9: `record-completion`; `test_crossing.py` runs it
4. [ ] D10: standing-rules pairing; Zeus reads `policy.standingRules.source`
5. [ ] Push; gate P3

## Working set — verified facts this epic relies on

| Fact | Value | Verified how / when |
|------|-------|---------------------|
| Repository | `/home/user/virtuoso`, branch `eb/zealous-einstein-zxvy3w` | `git status`, 2026-09-23 |
| Base for this epic | `1442ccc` (v1.9.0 candidate, CI #115 green both legs) + merge of `4e00672` | `git log`, CI run 35900011114 |
| Full suite | `python -m pytest plugins/virtuoso/ -q` → 775 passed, 3 skipped (38 s) | run 2026-09-23 18:00 |
| Validator | `python plugins/virtuoso/scripts/validate.py` → All checks passed | same |
| Version sync | `python plugins/virtuoso/scripts/bump_version.py --check` → in sync at 1.8.2 (bump is release.py's job) | same |
| Push | `git push -u origin eb/zealous-einstein-zxvy3w` works from this container | 1442ccc pushed 18:04Z |
| CI | `.github/workflows/ci.yml`: validate.py, bump_version --check, pytest; ubuntu + windows, py3.12 | read 2026-09-23 |
| Machine lines today | `status:`, `writes:`, `overlays:`, `deadlines:` (no `roadmap-integrity:`) | grep, 2026-09-23 |
| U9 matcher | `lessons.py _find_section` matches markdown headings only | read, 2026-09-23 |
| Ledger append | `TerminalLedger.append` (ledger.py) reached only from `test_crossing.py` | grep, 2026-09-23 |
| `policy.standingRules` | declared in `policy.py` defaults; read by no code | grep, 2026-09-23 |
| Marketplace/manifest keys | `displayName`, `category`, `tags`, `author`, `homepage`, `repository`, `license`, `keywords` documented; unknown `plugin.json` keys ignored | Claude Code docs via the guide agent, 2026-09-23 |
| Stranded branches | see Blockers #1 | `git diff main...`, 2026-09-23 |

## Blockers

- **BLOCKER(USER) #1 — merge or retire the two stranded branches?** (raised 2026-09-23;
  unblocks D19 and nothing else; the epic proceeds on every other front)
  - `eb/gracious-mendel-juqys8` (2 commits over v1.8.2): adds an *Acceptance and evidence
    reconciliation* section to `pointer-closeout` (141 lines: failure classification,
    proportional evidence, exact integrated identity, protected-state custody, completion
    scope, population naming) with seven rule anchors registered in `skill_rules.py`, and
    an unreleased release-notes entry. Additive, no code. Would need a merge against the
    1.9.0 close-out edits (same file, different regions).
  - `eb/charming-pasteur-9rigux` (1 commit over v1.8.2): a read-only `retired-vendored-tool`
    warning at preflight for stale pre-1.4 copies under `Virtuoso/scripts/` (26 lines in
    `registry.py`, 14 in `schema.py`, a test). Additive, small, safe.
  - **Recommendation:** merge both into this branch during P5 (each is finished, tested
    where it has code, and closes a real gap the SWOT named); retire neither.
  - **Answer:** _(pending — unanswered means: not merged; recorded as retired-for-now in done.md)_

## Decision log — append; never silently re-litigate

| # | Date | Decision | Why | Charter authority |
|---|------|----------|-----|-------------------|
| 1 | 2026-09-23 | Epic lives at `docs/virtuoso/epics/2026-09-23-loop-hardening/` | this repository is not registry-governed and keeps its own governance artifacts under `docs/virtuoso/` | Assumption A6 |
| 2 | 2026-09-23 | Gap 15 closed by stating the memory boundary (not a new `agentMemory` role) | lighter closure that still closes the gap; a role would add a default every governed project must absorb | grant: lighter of two closures |
| 3 | 2026-09-23 | Gap 16's buffer figure is a new metric `dispatch-buffer-ready`, `dispatch-buffer-filled` unchanged | Constraint: existing KPI names keep their meaning | Assumption A4 |

## Evidence

- (none yet — interim gate evidence goes here as one line + pointer)
