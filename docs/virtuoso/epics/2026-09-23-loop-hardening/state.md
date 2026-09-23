---
epic: loop-hardening
last_updated: 2026-09-23 23:10
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
phase:        complete — done.md written
next_action:  none; owner answers BLOCKER(USER) #1, launch Q2/Q3, then releases
blockers:     none — BLOCKER(USER) #1 answered: both branches merged
session:      1 of ~3 budgeted
dod:          D1–D23 [met] (D19 met as raised)
```

## Next actions — max 5, near horizon only

1. [ ] (owner) answer BLOCKER(USER) #1 and launch Q2/Q3

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
| Windows CI | a piped Python child writes the console code page (cp1252): a test that decodes UTF-8 must set PYTHONIOENCODING=utf-8 for the child; reproduce locally with PYTHONIOENCODING=cp1252 | runs 119/120 failed, fixed in 80047fa |
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
  - **Answer:** Merge (owner, 2026-09-23). Both merged: charming-pasteur `6734c58`, gracious-mendel in the following merge commit; its seven rule anchors hashed.

## Decision log — append; never silently re-litigate

| # | Date | Decision | Why | Charter authority |
|---|------|----------|-----|-------------------|
| 1 | 2026-09-23 | Epic lives at `docs/virtuoso/epics/2026-09-23-loop-hardening/` | this repository is not registry-governed and keeps its own governance artifacts under `docs/virtuoso/` | Assumption A6 |
| 2 | 2026-09-23 | Gap 15 closed by stating the memory boundary (not a new `agentMemory` role) | lighter closure that still closes the gap; a role would add a default every governed project must absorb | grant: lighter of two closures |
| 4 | 2026-09-23 | For local roles, `record-completion` performs crossing Steps 3 and 5 together at Step 3, so Step 4 persists ledger and register in one commit | the crossing's order exists to keep irreversible/external work last; both writes are local and reversible, and persisting them together is simpler to reconcile | grant: order of work; lighter closure |
| 5 | 2026-09-23 | D15's metrics landed in P3 with D12's `lesson-yield` | one close-out scan feeds hygiene, candidates, yield and the other five figures | grant: order of work |
| 3 | 2026-09-23 | Gap 16's buffer figure is a new metric `dispatch-buffer-ready`, `dispatch-buffer-filled` unchanged | Constraint: existing KPI names keep their meaning | Assumption A4 |

## Evidence

Fresh DoD run, 2026-09-23, one session (D2 re-run after the docstring fix: `grep -c` = 1):

```
D1: 13 passed, 244 deselected in 0.81s | All declared files in sync at 1.8.2
D2: 11 passed, 865 deselected in 2.01s | preflight roadmap-integrity occurrences: 0 | contract lists it: 1
D3: 3 passed, 873 deselected in 0.73s
D4: 18 passed, 858 deselected in 1.24s
D5: 5 Decision mentions; 1 passed, 875 deselected in 0.21s
D6: 1 ref-check OK; ghost grep: 0 files; 2 passed, 874 deselected in 0.21s
D7: conventional paths in epic skill: 0; 2 passed, 874 deselected in 0.35s
D8: 20 passed in 1.80s | registry:scripts: 0
D9: 4 passed, 872 deselected in 0.64s
D10: 7 passed, 869 deselected in 0.30s | zeus reads source: 1
D11: 3 passed, 873 deselected in 0.59s | D.4 runs it: 1
D12: 12 passed, 864 deselected in 0.54s
D13: 19 passed, 857 deselected in 0.88s
D14: 14 passed, 862 deselected in 0.97s
D15: 3 passed, 873 deselected in 0.45s
D16: All checks passed. | residue grep: 0
D17: 1 passed, 875 deselected in 0.16s | feedback.log in Plato: 0
D18: 11 passed, 865 deselected in 0.72s
D19: BLOCKER(USER) #1 raised in state.md: 3
D20: 31 passed in 0.27s | notes: 3:## v1.10.0 (2026-09-23) — loop hardening
D22: 3 passed, 873 deselected in 0.56s | sweep runs it: 2
D23: 3 passed, 873 deselected in 0.90s | closeout runs it: 2
FULL: 873 passed, 3 skipped in 49.26s | cp1252: 104 passed in 7.36s
D21: CI run #126 (35907177454) on d8ef633 — success, ubuntu + windows
```
