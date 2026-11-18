---
name: 3rd-party-audit
description: >
  Full lifecycle management of external 3rd-party codebase audits. Use this skill whenever
  the user says "3rd party audit", "external audit", "outside audit", or when an audit is
  required at phase close. This skill governs package creation, auditor prompts, remediation
  planning, and final decision integration. Every audit begins with a Q&A that establishes
  the primary question the audit must answer and the child questions that bear on it, the
  child questions offered to the user for approval. It produces 6 deliverables across 7 steps
  with structured handoffs between the planner, the user, and the external auditor. Trigger on:
  "3rd party audit", "audit the codebase", "prepare audit package", "audit remediation",
  "process audit findings", or any phase-close audit gate. This is a planner skill — all
  audit steps are coordinated from the planning surface.
---

<!-- virtuoso-shared-contract v2 -->
**Shared contract (all Virtuoso skills).** Reference block; the skill body below governs specifics.

- **Registry resolution** — `Virtuoso/workspace-layout.json` is the authority; `Virtuoso.Governance.Readme.md` is its synchronized human view. Resolve every document, work item, and permission through the registry. Never hardcode a path, never fall back to a conventional one, and never infer authority from a role's name. Full contract: the plugin's `references/registry-contract.md`.
- **Read-only preflight** — session start and any "where am I" check runs `--mode check`, which performs **zero project writes**. Adoption, creation, and repair are separate operations, each explicitly invoked.
- **Providers** — work items come from the configured work-register provider (local file, spreadsheet, connector-backed task manager, issue tracker, database, or read-only snapshot). Negotiate capabilities before planning work; never open a register file directly. The live work register, the append-only terminal ledger, and any compatibility export are three different roles.
- **Provenance** — every derived figure cites its provider, source, and snapshot time. A figure whose inputs are missing is reported as *not computable* with the missing inputs named, never approximated.
- **Git** — behaviour is `policy.git`, not a fixed rule of this plugin. See `references/git-policy.md`. Under every policy: inspect first, stage exact paths, preserve unrelated work, no destructive flags, no force-push without explicit authorization.
- **Readiness** — one shared, versioned rubric: `references/readiness-rubric.md` (its universal checks, at the version it declares, plus the project's declared extensions). No skill restates it in its own words.
- **Actors** — roles from `policy.actors`: planner, implementation agent, reviewer, repository operator. Never a product, vendor, or model name. See `references/actors-and-interaction.md`.
- **Issue contract** — any stop, hold, block, or elevation becomes an issue document, routed per `policy.issues.targets` (local file, external tracker, or both).
- **Effort levels** — low / medium / high / xhigh / max. A property of the task's difficulty, never a ranking of whoever performs it.

<!-- virtuoso-overlay-clause v2 -->
**Project overlay.** If the registry declares an `overlays` role, read the overlay mirroring
every shipped file you read beneath it — this file at its own path (`skills/<skill>/SKILL.md`,
`agents/<Agent>.md`) and any `references/<file>.md` this one sends you to — and apply each on
top of the file it mirrors. Resolve them with the registry helper's `overlays` subcommand;
never fork or edit a shipped file to carry a project's rules. An overlay is additive and
wins on conflict, with one exception: it may not loosen a shared-contract safety rule
(registry resolution, read-only preflight, write permission, git safety, provenance, the
issue contract), and `references/registry-contract.md` may not be overlaid at all. No
`overlays` role, an absent overlays directory, and no matching overlay file all mean the
same thing — proceed on the shipped file alone.

# 3rd Party Audit Process

## Preflight — read-only registry check (run first)

Resolve the plugin through its launcher, then run the **read-only** check. It performs
discovery and validation with zero project writes.

**Unix-like shell**

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_preflight --root . --mode check

**Windows PowerShell**

    & "$HOME/.virtuoso/bin/virtuoso.ps1" virtuoso_preflight --root . --mode check

Add `--json` when you want the structured result (status, writes, findings, and the full
resolved role table). Read the `virtuoso-status:` line and branch:

- `ready` — the registry is valid. Continue.
- `warning` — usable; surface the findings to the user and continue. Warnings are not blockers.
- `repair-needed` — **STOP.** Run `--mode repair` to produce the preview, show the user the
  proposed paths, semantic changes, files affected, and backup location, and apply it only
  with `--apply` after they approve.
- `adoptable` — the project has governance documents but is not registered. Offer
  `--mode adopt`: it registers what exists, in place. Nothing is moved, duplicated, or rewritten.
- `none` — no registry and nothing to adopt. Route the user to `/virtuoso-init`.
- `failed` — report the error verbatim and stop.

If neither launcher resolves, report that the plugin could not be located and stop. Do not
guess a path.

**Governance authority.** Resolve every document you need through the registry
(`references/registry-contract.md`). Never create a parallel document for a registered role;
never write to a role whose `allowedWriters` does not name this ceremony; never treat a
`mirror`, `report`, `archive`, or `unknown` role as truth.

This skill manages the full lifecycle of external codebase audits. Audits are conducted
by **legitimate independent 3rd-party auditors** — separate AI instances with no access
to the project's conversation history, prior decisions, or internal context. They receive
only the audit package and orientation brief and evaluate the project on its own merits.

**Announce at start:** "Using the 3rd-party-audit skill to manage this audit cycle."

**Authoritative reference:** this skill (the authoritative audit process).

---

## When to Trigger

- User says "3rd party audit" or "external audit"
- A major phase closes and audit is part of the governance process
- User returns with an audit report (D2) or auditor review response (D4) — resume at the appropriate step
- User asks to prepare an audit package

---

## Audit Pipeline Overview

The audit is a 7-step pipeline producing 6 deliverables with structured handoffs:

```
Step 0: Audit Questions Q&A (planner+user) → D0
Step 1: Package Creation (planner)         → D1a + D1b
Step 2: Handoff to Auditor (User)         → [user action]
Step 3: Audit Report (3rd Party)          → D2
Step 4: Remediation Plan (planner + user)  → D3
Step 5: Auditor Review of Response (3P)   → D4
Step 6: Final Decisions (planner + user)   → D5
```

**Ownership:** planner and user share Step 0; the user approves its questions. The planner
owns Steps 1, 4, 6. User owns Step 2. 3rd party owns Steps 3, 5.

**Every audit begins at Step 0.** No package is built, no auditor prompt is written, and no
scope is settled until the primary question and its child questions are approved.

---

## Step 0 — Audit Questions Q&A

**Deliverable:** D0 (AuditQuestions)

The audit answers questions; it does not survey a codebase for whatever turns up. This step
settles what those questions are before anything else happens. It is a conversation with
the user: ask **one question at a time** and wait for each answer.

### Actions

1. **Establish the primary question** through Q&A:
   - What decision will this audit inform, and who makes it?
   - What prompted the audit now (phase close, a concern, a pending commitment)?
   - What would a "yes" and a "no" each change?

   Then draft the **primary question** in one sentence, answerable from evidence, and put it
   to the user. Revise until the user confirms it. The default ("Given the current codebase
   and documentation, is this the right plan, in the right order, for the right reasons?")
   is an option to offer, never an assumption.

2. **Settle scope** in the same conversation, as it bears on the primary question:
   - Which phases or areas are in scope? Full-scope audit or targeted?
   - Any specific concerns to flag to the auditor?

3. **Propose the child questions** for approval. Present them as a numbered list, each
   with:
   - **Question**: one sentence, answerable from evidence in the package
   - **Bears on the primary question because**: one line
   - **Evidence that would answer it**: the files, data, or behaviour the auditor must examine

   Together the child questions must cover the primary question: if every one were
   answered, the primary question could be answered. Say so explicitly, or name the gap.

4. **Get approval.** The user approves, edits, drops, or adds child questions. Revise and
   re-present until the user approves the full set explicitly. Do not proceed to Step 1 on
   silence, a partial answer, or your own judgement that the set is good enough.

5. **Record D0.** Once the audit folder exists (Step 1, action 3), save the approved set as
   `AuditQuestions.N.YYYY-MM-DD.md`: the primary question, the approved child questions
   (numbered `Q1`, `Q2`, …), scope, and the date the user approved them. D0 is fixed for the
   cycle: a question changed later is recorded as a dated amendment, with the user's approval.

---

## Step 1 — Package Creation

**Deliverables:** D1a (AuditOrientation) + D1b (AuditPackage)

**Before assembling the package (action 4 on), read
[references/packaging.md](references/packaging.md)** — the authoritative upload and zip
limits, the standard outer-zip layout, tiered package scoping, the exclusion rules, and the
packaging anti-patterns. They are system constraints, not preferences.

### Actions

1. **Carry in Step 0.** Scope, the primary question, and the approved child questions come
   from D0. If Step 0 has not been completed and approved, stop and run it.

2. **Determine audit number:** check existing `OutsideAudit.N.*` folders in the manifest
   `outsideAudits` directory; next audit = max(N) + 1.

3. **Create audit folder:** `<outsideAudits>/OutsideAudit.N+1.YYYY-MM-DD/`

4. **Generate AuditOrientation document (D1a):**
   - Format: `.docx` (use the docx skill)
   - Required sections:
     - The audit questions: the primary question and the approved child questions from D0
     - Executive summary of the project
     - Current build status (phase completion, calibration metrics, test counts)
     - Architecture overview
     - Description of every file included in the zip
     - Forward plan summary
     - File manifest organized by tier (Tier 1 critical / Tier 2 supporting / Tier 3 reference)
     - Outer-zip layout table (entries 00–09 with what each holds)

5. **Generate MANIFEST.md** describing the outer-zip layout, in plain markdown: one row per
   outer-zip entry (00–09) with filename, brief description, internal-file count, and tier
   mapping. The auditor reads it first, before opening sub-zips.

6. **Assemble the orientation bundle `00_orientation_manifest.zip`** — always **entry 0** of
   the outer zip: the AuditOrientation `.docx` (action 4) + `MANIFEST.md` (action 5) +
   `AuditQuestions.N.YYYY-MM-DD.md` (D0).

7. **Assemble content sub-zips (entries 01–09):**
   - Apply tiered scoping (references/packaging.md, *Package Scoping*) to group source files into logical sub-zips; apply its exclusion rules strictly (never `.git/`, caches, secrets, meta-archives, OS metadata, or media)
   - Naming: `01_<descriptive_slug>.zip` … `09_<descriptive_slug>.zip`; each ≤ 100 MB
   - Sub-zip internal file counts can exceed 10 — nesting absorbs the per-zip file-count limit
   - **No video or audio inside any zip** — document/data formats only

8. **Assemble the outer audit package zip (D1b):**
   - Filename: `AuditPackage.N.YYYY-MM-DD.zip` (no "Batch" suffix — single delivery)
   - Contents: exactly the `00_*.zip` plus the `01_*.zip`–`09_*.zip` content sub-zips
   - **Hard cap: 10 entries in the outer zip** (1 orientation/manifest bundle + up to 9 content sub-zips); outer zip ≤ 100 MB
   - If the natural shape of the project exceeds these limits, pivot to the GitHub repo / single-directory ingestion path

9. **Place all files** in the audit subfolder. The auditor receives a **single deliverable**: the outer zip.

10. **Provide user with the Step 1 Prompt** for the auditor. **Read [references/auditor-prompts.md](references/auditor-prompts.md)** — the four prompt templates; fill the primary and child questions from D0.

---

## Step 2 — Handoff to Auditor

**No deliverable — user action only.**

Provide the user with:
1. The **single outer audit zip** (`AuditPackage.N.YYYY-MM-DD.zip`) — contains everything: orientation, manifest, and all content sub-zips
2. The **Step 1 Prompt** for the auditor ([references/auditor-prompts.md](references/auditor-prompts.md)), filled from D0
3. Instructions: "Give the auditor the outer zip and the prompt in a fresh session. The auditor opens `00_orientation_manifest.zip` first to get the orientation doc and manifest, then opens content sub-zips as needed."

If for any reason the project required multiple outer zips (rare — typically only when total payload exceeded what one outer zip can carry and the GitHub repo path wasn't viable), deliver them all together — they're split for size, not sequencing.

Then **WAIT** for the user to return with D2 (the audit report).

---

## Step 3 — Audit Report (3rd Party)

**Deliverable:** D2 (AuditReport)

The auditor produces their report externally. When the user returns with it:

1. Save as `AuditReport.N.YYYY-MM-DD.md` in the audit subfolder
2. Read the full report
3. Summarize key findings for the user before proceeding to Step 4, organized by the D0
   questions: the answer to the primary question, then each child question's answer. Name
   any question the report left unanswered or answered without evidence; that is a gap to
   raise with the auditor, not one to fill in yourself
4. Record each finding in the registered `findings` role as an `F-NNN` entry (this skill is
   one of its writers; see `references/registry-contract.md`, *Findings*), with
   `**Source:** 3rd-party-audit`. A finding that prices something adds its **Tier**,
   **Confidence**, **Kind** and **Figure** lines, in the one finding format.

The report should cover: a direct answer to the primary question and to each approved child
question, with evidence; executive verdict (sound / partially flawed / structurally
unsound); codebase reality check; roadmap item-by-item audit with classification; major
contradictions and false assumptions; sequencing and dependency analysis;
structural/modeling review; testing and validation review; top risks ranked by severity;
missing work identification; proposed revised roadmap (if needed); scored assessment (1–10)
across 8 review dimensions.

### Review Dimensions

(1) Grounding in current codebase, (2) Architectural coherence, (3) Correct sequencing,
(4) Modeling soundness, (5) Extensibility, (6) Testability, (7) Delivery practicality,
(8) Overall confidence.

---

## Step 4 — Remediation Plan

**Deliverable:** D3 (AuditRemediationPlan)

### Actions

1. **Read the full audit report** (D2)

   An external report arrives with borrowed authority — it was commissioned and paid for, so
   its findings read as settled. Before assigning dispositions, consider `/adversarial-review`
   over the report itself, particularly where a finding would drive expensive remediation or a
   roadmap rewrite. The **Reject** disposition below is only credible if the reasoning was
   actually tested: an adversarial pass is what makes "we disagree" defensible rather than
   merely defensive.

2. **For every major finding, assign a disposition:**

   | Disposition | Meaning | When to Use |
   |------------|---------|-------------|
   | **Accept** | Implement as recommended | Finding is correct, actionable, and timely |
   | **Accept with narrowing** | Implement with reduced scope | Finding is valid but scope is too broad for current phase |
   | **Defer** | Valid but not now | Correct finding, wrong timing — place in roadmap at right position |
   | **Reject** | Disagree | Evidence or reasoning doesn't hold — explain why with counter-evidence |

3. **Produce `AuditRemediationPlan.N.YYYY-MM-DD.md` containing:** management summary,
   including the audit's answer to the primary question; audit feedback response matrix
   (finding → disposition → next step); exact roadmap rewrite actions; grouped implementation
   packages; blocking decisions requiring user input; testing/validation plan; corrected
   execution order; final decision-ready conclusion.

4. **For each accepted finding, identify:** calibration drift risk; documentation updates
   required (CLAUDE.md, Roadmap, Algorithm Spec, etc.); prerequisites and dependencies.

5. **Present to user for review** before proceeding

6. **Provide user with the Step 3 Prompt** for the auditor
   ([references/auditor-prompts.md](references/auditor-prompts.md); its Step 2 Prompt frames
   this step's plan)

Then **WAIT** for the user to return with D4.

---

## Step 5 — Auditor Review of Response (3rd Party)

**Deliverable:** D4 (AuditReviewResponse)

When the user returns with the auditor's response:

1. Save as `AuditReviewResponse.N.YYYY-MM-DD.md` in the audit subfolder
2. Read the full response
3. Summarize any surprises or disagreements for the user before proceeding to Step 6

The auditor provides line-by-line responses, each with a disposition: Accept / Accept with
narrowing / Defer / Reject / Convert into documentation-only correction / Convert into
later-phase calibration task.

---

## Step 6 — Final Decisions & Implementation

**Deliverable:** D5 (AuditDecisions)

### Actions

1. **Treat the audit loop as closed** — these responses are definitive (the Step 4 Prompt in
   [references/auditor-prompts.md](references/auditor-prompts.md) frames this step)

2. **Update the project roadmap** with all accepted changes

3. **Update all affected governance documents:**
   - CLAUDE.md — system state, phase status, references
   - Roadmap — resequenced phases, new tasks, updated specs
   - Algorithm/design specs — any architecture changes
   - The registered `lessons` role — a new entry for this audit cycle, in the
     standard shape (dispatch-closeout's `references/spec-retro-format.md`)
   - Variable/constants references — if constants affected

4. **Produce `AuditDecisions.N.YYYY-MM-DD.md` summarizing:**
   - The final answer to the primary question and to each child question
   - All changes made to the roadmap
   - Deferred items with placement
   - Rejected items with rationale
   - New lessons-learned entries created

5. **Print a summary** of all roadmap changes

6. **Update CLAUDE.md** §External Audit Outcomes (or equivalent section)

---

## Planner Execution Checklist

Use this checklist to track progress through the audit lifecycle:

- [ ] Step 0: primary question (one question at a time), scope, child questions — the user approves the full set
- [ ] Determine audit number; create `OutsideAudit.N+1.YYYY-MM-DD/`; save D0 (`AuditQuestions.N.YYYY-MM-DD.md`)
- [ ] Generate AuditOrientation (D1a, the docx skill) and `MANIFEST.md` (entries 00–09); bundle both + D0 into `00_orientation_manifest.zip`
- [ ] Assemble content sub-zips `01_*.zip`–`09_*.zip` (each ≤ 100 MB; no video/audio)
- [ ] Assemble `AuditPackage.N.YYYY-MM-DD.zip` (D1b): ≤ 10 entries, ≤ 100 MB; a single deliverable, or pivot to the GitHub repo path
- [ ] Place all files in the audit subfolder; provide the user with the Step 1 Prompt
- [ ] **WAIT** — the user returns with D2; save `AuditReport.N.YYYY-MM-DD.md`; summarize by question, flagging any left unanswered; record findings
- [ ] Step 4: produce the remediation plan (D3); present it for review; provide the Step 3 Prompt
- [ ] **WAIT** — the user returns with D4; save `AuditReviewResponse.N.YYYY-MM-DD.md`
- [ ] Step 6: finalize all decisions, update docs (D5); update CLAUDE.md §External Audit Outcomes; add the lessons-learned entry; print the roadmap change summary

---

## Audit History Tracking

Maintain an audit history table in the project's audit procedure document or CLAUDE.md:

```markdown
| # | Date | Scope | Auditor | Verdict | Key Outcome |
|---|------|-------|---------|---------|-------------|
| 1 | YYYY-MM-DD | [Full/Targeted: area] | [Auditor ID] | [Verdict] | [1-line summary] |
```

---

## Anti-Patterns

Packaging anti-patterns (zip limits, layout, exclusions, batching) are in
[references/packaging.md](references/packaging.md), *Packaging Anti-Patterns*.

| Anti-Pattern | Why It's Wrong | Do This Instead |
|-------------|---------------|-----------------|
| Building the package before the questions are approved | The audit answers no one's question; findings sprawl and can't be judged complete | Always run Step 0 first; proceed only on the user's explicit approval of the child questions |
| Choosing the child questions without the user | The planner's framing replaces the user's; the audit tests what the planner wanted tested | Offer the child questions for approval; the user edits, drops, and adds |
| Skipping the orientation document | Auditor lacks context, produces surface-level review | Always generate D1a with full project context |
| Rejecting findings without counter-evidence | Turns the audit into a rubber stamp | Provide specific code/data evidence for every rejection |
| Implementing fixes before Step 6 closes | Changes may conflict with auditor's final response | Wait for the full loop to close before writing code |
| Accepting everything without narrowing | Scope explosion — audit creates more work than the phase it audited | Apply "accept with narrowing" aggressively on broad findings |
| Skipping the lessons-learned entry | Audit insights get lost | Always log at least one LL entry per audit cycle |
