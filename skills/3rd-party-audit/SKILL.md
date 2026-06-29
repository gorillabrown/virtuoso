---
name: 3rd-party-audit
description: >
  Full lifecycle management of external 3rd-party codebase audits. Use this skill whenever
  the user says "3rd party audit", "external audit", "outside audit", or when an audit is
  required at phase close. This skill governs package creation, auditor prompts, remediation
  planning, and final decision integration. It produces 5 deliverables across 6 steps with
  structured handoffs between Cowork, the user, and the external auditor. Trigger on:
  "3rd party audit", "audit the codebase", "prepare audit package", "audit remediation",
  "process audit findings", or any phase-close audit gate. This is a Cowork skill — all
  audit steps are coordinated from the planning surface.
---

# 3rd Party Audit Process

## Preflight — workspace check (run first)

This skill operates on the project's `Virtuoso/` workspace. Before anything else, ensure it exists and is complete:

    python "$(cat ~/.virtuoso/plugin-root 2>/dev/null)/scripts/virtuoso_preflight.py" --root . --mode create

The script is idempotent — it never overwrites existing files. The bundled-script path comes from `~/.virtuoso/plugin-root`, a bridge file the plugin's session-start hook records every session (skill bodies cannot read `${CLAUDE_PLUGIN_ROOT}`, only hooks can). If that file is missing or the command fails, run `/virtuoso-init`, or create the workspace by hand: a `Virtuoso/` directory containing `roadmap-reviews/` (and `roadmap-reviews/checkins/`), `Close-Outs/`, `audits/`, `scripts/`, a `.virtuoso` marker, and seed `Roadmap.md` + `SpecRetro.Lessons_Learned.md`. If the workspace was just created, tell the user where it lives, then continue.

**Workspace paths.** Canonical files live under `Virtuoso/`: `Virtuoso/Roadmap.md`, `Virtuoso/sprint-queue.xlsx`, bundled scripts in `Virtuoso/scripts/`, review outputs in `Virtuoso/roadmap-reviews/` (check-ins in `Virtuoso/roadmap-reviews/checkins/`), close-outs in `Virtuoso/Close-Outs/`, audits in `Virtuoso/audits/`. Wherever this skill names `Roadmap.md`, `sprint-queue.xlsx`, or `roadmap-reviews/` without a directory, resolve them under `Virtuoso/` first (falling back to the project root for legacy projects).


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

The audit is a 6-step pipeline producing 5 deliverables with structured handoffs:

```
Step 1: Package Creation (Cowork)         → D1a + D1b
Step 2: Handoff to Auditor (User)         → [user action]
Step 3: Audit Report (3rd Party)          → D2
Step 4: Remediation Plan (Cowork + User)  → D3
Step 5: Auditor Review of Response (3P)   → D4
Step 6: Final Decisions (Cowork + User)   → D5
```

**Ownership:** Cowork owns Steps 1, 4, 6. User owns Step 2. 3rd party owns Steps 3, 5.

---

## Upload & File Constraints (Authoritative)

Universal upload parameters that govern how audit packages can be delivered to the auditor. All packaging decisions in Step 1 must respect these limits — they are system constraints, not preferences.

### I. Per-Session / Per-Prompt Limits

- **Max 10 discrete files per auditor session or prompt.** Every file delivered (including the outer zip) counts.
- **Max 100 MB per file** (non-video file types).
- **Alternative ingestion path:** A single code directory or GitHub repository may be ingested per session, provided it contains **≤ 5,000 files** and **total size ≤ 100 MB**. Use this path when the project exceeds what zips can carry.

### II. ZIP Archive Protocols

- **Max 10 internal entries in the outermost zip** (the one the auditor uploads directly).
- **Max 100 MB per zip** (applies to every zip — outer and nested).
- **No video or audio files inside zips.** Compressed archives are restricted to document and data formats only (.md, .py, .json, .docx, .csv, .pdf, .txt, .yaml, etc.).
- **Nesting is allowed.** A nested sub-zip counts as 1 entry in its parent zip. Sub-zip contents are not "intake load" for the outer-zip ceiling — the auditor extracts them as a separate operation. This is how large file counts (>10) get delivered without violating the outer-zip rule.

### III. Practical Packaging Math

The standard package is a **single outer zip** that bundles everything — orientation doc, manifest, and all content sub-zips. This makes the audit a **1-deliverable handoff** to the auditor (frees up 9 session slots for safety margin).

- **1 outer zip** with **≤ 10 entries**: `00_*.zip` (orientation + manifest) + up to 9 content sub-zips
- Each content sub-zip can hold the natural shape of its source data (size capped at 100 MB)
- Theoretical ceiling is dominated by total size, not file count, since nesting absorbs the file-count limit
- If total payload exceeds ~900 MB or the project needs >5,000 files of context, switch to the **GitHub repo / single-directory ingestion path** (≤ 5,000 files, ≤ 100 MB)

### IV. Media Constraints (Reference Only)

Audit packages contain code, documentation, and data — never video or audio. The full media constraints below exist only for context if a future audit ever needs supplementary media:

- **Video:** up to 2 GB per file; total duration capped at 5 min (standard) / 1 hr (premium)
- **Audio:** total length capped at 10 min (standard) / 3 hr (premium)

Media files cannot be packaged in zips and would need to be delivered as standalone files (counting against the 10-file session limit).

---

## Step 1 — Package Creation

**Deliverables:** D1a (AuditOrientation) + D1b (AuditPackage)

### Actions

1. **Confirm scope** with user:
   - Which phases or areas are in scope?
   - Full-scope audit or targeted?
   - Any specific concerns to flag to the auditor?

2. **Determine audit number:**
   - Check existing `OutsideAudit.N.*` folders in `Virtuoso/audits/`
   - Next audit = max(N) + 1

3. **Create audit folder:**
   ```
   Virtuoso/audits/OutsideAudit.N+1.YYYY-MM-DD/
   ```

4. **Generate AuditOrientation document (D1a):**
   - Format: `.docx` (use the docx skill)
   - Required sections:
     - Executive summary of the project
     - Current build status (phase completion, calibration metrics, test counts)
     - Architecture overview
     - Description of every file included in the zip
     - Forward plan summary
     - File manifest organized by tier (Tier 1 critical / Tier 2 supporting / Tier 3 reference)
     - Outer-zip layout table (entries 00–09 with what each holds)

5. **Generate MANIFEST.md** describing the outer-zip layout:
   - One row per outer-zip entry (00–09)
   - For each entry: filename, brief description, internal-file count, and tier mapping
   - Plain markdown — auditor reads this first to orient themselves before opening sub-zips

6. **Assemble the `00_*.zip` orientation bundle:**
   - Filename: `00_orientation_manifest.zip`
   - Contents: the AuditOrientation `.docx` from step 4 + the `MANIFEST.md` from step 5
   - This is always **entry 0** of the outer zip

7. **Assemble content sub-zips (entries 01–09):**
   - Apply tiered scoping (see Package Scoping below) to group source files into logical sub-zips
   - Each sub-zip ≤ 100 MB
   - Naming: `01_<descriptive_slug>.zip`, `02_<descriptive_slug>.zip`, … `09_<descriptive_slug>.zip`
   - Sub-zip internal file counts can exceed 10 — nesting absorbs the per-zip file-count limit
   - **No video or audio inside any zip** — document/data formats only

8. **Assemble the outer audit package zip (D1b):**
   - Filename: `AuditPackage.N.YYYY-MM-DD.zip` (no "Batch" suffix — single delivery)
   - Contents: exactly the `00_*.zip` plus the `01_*.zip`–`09_*.zip` content sub-zips
   - **Hard cap: 10 entries in the outer zip** (1 orientation/manifest bundle + up to 9 content sub-zips)
   - Outer zip ≤ 100 MB
   - If the natural shape of the project exceeds these limits, pivot to the GitHub repo / single-directory ingestion path

9. **Place all files** in the audit subfolder. The auditor receives a **single deliverable**: the outer zip.

10. **Provide user with the Step 1 Prompt** (see Auditor Prompts below)

### Standard Outer-Zip Layout

```
AuditPackage.N.YYYY-MM-DD.zip                     (single deliverable, ≤ 100 MB, exactly 10 entries)
├── 00_orientation_manifest.zip                   ← entry 0: orientation + manifest
│   ├── AuditOrientation.N.YYYY-MM-DD.docx
│   └── MANIFEST.md
├── 01_<slug>.zip                                 ← entry 1: content group (e.g., engine_code_tests_data)
├── 02_<slug>.zip                                 ← entry 2: content group (e.g., governance_root)
├── 03_<slug>.zip
├── 04_<slug>.zip
├── 05_<slug>.zip
├── 06_<slug>.zip
├── 07_<slug>.zip
├── 08_<slug>.zip
└── 09_<slug>.zip                                 ← entry 9: content group (e.g., tier3_reference)
```

The auditor uploads one file (`AuditPackage.N.YYYY-MM-DD.zip`), opens `00_orientation_manifest.zip` first to read the orientation .docx and manifest, then opens content sub-zips as needed. If the project doesn't need all 9 content slots, leave them unused — the layout never requires padding.

### Package Scoping

Organize materials into tiers:

| Tier | Contents | When to Include |
|------|----------|-----------------|
| **Tier 1 — Core** | Main codebase, test suites, databases, roadmap, algorithm/design specs, CLAUDE.md | Always |
| **Tier 2 — Supporting** | Design specs, lessons learned, agent findings, frameworks, calibration data | When relevant to audit scope |
| **Tier 3 — Reference** | Workbooks, data files, onboarding docs, prior audit history | Full-scope audits only |

**Sub-zip grouping rules** (applies to entries 01–09 inside the outer zip):
1. Group source files by logical role, not by raw file count — e.g., `engine_code_tests_data`, `governance_root`, `roadmap`, `agents_roster`, `closeouts`, `calibration_benchmarks`, `tier3_reference`
2. Keep each sub-zip ≤ 100 MB; sub-zip internal file count is unconstrained (nesting absorbs the per-zip 10-file limit)
3. **Hard ceiling: 9 content sub-zips** (entries 01–09) + the `00_orientation_manifest.zip` = 10 outer-zip entries
4. The `00_*.zip` is reserved for orientation + manifest — never put content sub-zips at index 00
5. If the project's natural grouping needs >9 content sub-zips, consolidate adjacent groups OR pivot to the GitHub repo / single-directory path (≤ 5,000 files, ≤ 100 MB)
6. Label every outer-zip entry in both the `MANIFEST.md` and the AuditOrientation file-manifest table

**Exclusion rules — never include:**
- `.git/`, `__pycache__/`, `.pytest_cache/`, `node_modules/`
- API keys, credentials, secrets
- Meta-archives (e.g., project-level .zip backups)
- `desktop.ini`, `.DS_Store`, OS metadata
- **Video or audio files** (.mp4, .mov, .mp3, .wav, .m4a, etc.) — system constraint, zips are restricted to document/data formats only

---

## Step 2 — Handoff to Auditor

**No deliverable — user action only.**

Provide the user with:
1. The **single outer audit zip** (`AuditPackage.N.YYYY-MM-DD.zip`) — contains everything: orientation, manifest, and all content sub-zips
2. The **Step 1 Prompt** (see below) for the auditor
3. Instructions: "Give the auditor the outer zip and the prompt in a fresh session. The auditor opens `00_orientation_manifest.zip` first to get the orientation doc and manifest, then opens content sub-zips as needed."

If for any reason the project required multiple outer zips (rare — typically only when total payload exceeded what one outer zip can carry and the GitHub repo path wasn't viable), deliver them all together — they're split for size, not sequencing.

Then **WAIT** for the user to return with D2 (the audit report).

---

## Step 3 — Audit Report (3rd Party)

**Deliverable:** D2 (AuditReport)

The auditor produces their report externally. When the user returns with it:

1. Save as `AuditReport.N.YYYY-MM-DD.md` in the audit subfolder
2. Read the full report
3. Summarize key findings for the user before proceeding to Step 4

The report should cover:
- Executive verdict (sound / partially flawed / structurally unsound)
- Codebase reality check
- Roadmap item-by-item audit with classification
- Major contradictions and false assumptions
- Sequencing and dependency analysis
- Structural/modeling review
- Testing and validation review
- Top risks ranked by severity
- Missing work identification
- Proposed revised roadmap (if needed)
- Scored assessment (1–10) across 8 review dimensions

### Review Dimensions

1. Grounding in current codebase
2. Architectural coherence
3. Correct sequencing
4. Modeling soundness
5. Extensibility
6. Testability
7. Delivery practicality
8. Overall confidence

---

## Step 4 — Remediation Plan

**Deliverable:** D3 (AuditRemediationPlan)

### Actions

1. **Read the full audit report** (D2)

2. **For every major finding, assign a disposition:**

   | Disposition | Meaning | When to Use |
   |------------|---------|-------------|
   | **Accept** | Implement as recommended | Finding is correct, actionable, and timely |
   | **Accept with narrowing** | Implement with reduced scope | Finding is valid but scope is too broad for current phase |
   | **Defer** | Valid but not now | Correct finding, wrong timing — place in roadmap at right position |
   | **Reject** | Disagree | Evidence or reasoning doesn't hold — explain why with counter-evidence |

3. **Produce `AuditRemediationPlan.N.YYYY-MM-DD.md` containing:**
   - Management summary
   - Audit feedback response matrix (finding → disposition → next step)
   - Exact roadmap rewrite actions
   - Grouped implementation packages
   - Blocking decisions requiring user input
   - Testing/validation plan
   - Corrected execution order
   - Final decision-ready conclusion

4. **For each accepted finding, identify:**
   - Calibration drift risk
   - Documentation updates required (CLAUDE.md, Roadmap, Algorithm Spec, etc.)
   - Prerequisites and dependencies

5. **Present to user for review** before proceeding

6. **Provide user with the Step 3 Prompt** for the auditor

Then **WAIT** for the user to return with D4.

---

## Step 5 — Auditor Review of Response (3rd Party)

**Deliverable:** D4 (AuditReviewResponse)

When the user returns with the auditor's response:

1. Save as `AuditReviewResponse.N.YYYY-MM-DD.md` in the audit subfolder
2. Read the full response
3. Summarize any surprises or disagreements for the user before proceeding to Step 6

The auditor provides line-by-line responses with disposition:
- Accept
- Accept with narrowing
- Defer
- Reject
- Convert into documentation-only correction
- Convert into later-phase calibration task

---

## Step 6 — Final Decisions & Implementation

**Deliverable:** D5 (AuditDecisions)

### Actions

1. **Treat the audit loop as closed** — these responses are definitive

2. **Update the project roadmap** with all accepted changes

3. **Update all affected governance documents:**
   - CLAUDE.md — system state, phase status, references
   - Roadmap — resequenced phases, new tasks, updated specs
   - Algorithm/design specs — any architecture changes
   - LESSONS_LEARNED — new entry for this audit cycle
   - Variable/constants references — if constants affected

4. **Produce `AuditDecisions.N.YYYY-MM-DD.md` summarizing:**
   - All changes made to the roadmap
   - Deferred items with placement
   - Rejected items with rationale
   - New lessons-learned entries created

5. **Print a summary** of all roadmap changes

6. **Update CLAUDE.md** §External Audit Outcomes (or equivalent section)

---

## Auditor Prompts

These are project-agnostic templates. Customize the bracketed sections for each project.

### Step 1 Prompt — Initial Audit (Given to 3rd Party)

> You are a principal systems architect, technical program auditor, and domain expert reviewer. You are being given:
>
> 1. The current [PROJECT NAME] codebase
> 2. The project roadmap
> 3. Supporting documentation that describes architecture, runtime flow, data model, logic, current state, open gaps, design intent, and context
>
> Your task is to perform a full, evidence-based vetting of the roadmap against the actual system as it exists today.
>
> Do not treat the roadmap as presumptively correct. Treat the code as the primary source of truth, then use the supporting documents to understand intended architecture, domain terminology, and planned direction. Where code and documentation differ, explicitly identify the divergence.
>
> Your review must be extensive, rigorous, and critical. The goal is to determine whether the roadmap is logically sound, technically coherent, properly sequenced, grounded in the existing implementation, and likely to produce a stable, extensible, and realistic way forward.
>
> Core instructions:
> - Read the roadmap in full
> - Inspect the codebase deeply before judging the roadmap
> - Cross-reference every major roadmap claim against actual code structures and data models
> - Be skeptical, specific, and concrete — no generic advice
> - Ground every major conclusion in direct evidence from the repository
> - Cite relevant files, modules, classes, functions, schemas, and constants by name/path
> - If a claim cannot be verified, state that clearly
> - Distinguish between: (a) what already exists, (b) what the roadmap assumes exists, (c) what is actually missing, (d) what must happen before later items can succeed
>
> Primary review question: "Given the current codebase and documentation, is this the right plan, in the right order, for the right reasons?"
>
> Review dimensions (score 1–10 each):
> 1. Grounding in current codebase
> 2. Architectural coherence
> 3. Correct sequencing
> 4. Modeling soundness
> 5. Extensibility
> 6. Testability
> 7. Delivery practicality
> 8. Overall confidence
>
> Required output format: (A) Executive verdict, (B) Current-state architecture summary, (C) Roadmap item-by-item audit, (D) Major contradictions, (E) Sequencing analysis, (F) Structural/modeling review, (G) Testing review, (H) Top risks, (I) Missing work, (J) Proposed revised roadmap, (K) Final recommendation with scores

### Step 2 Prompt — Remediation Plan (Cowork)

> You are managing remediation of an audit against the [PROJECT NAME] roadmap.
>
> Input: current codebase, roadmap and supporting docs, completed audit feedback
>
> Task: Convert the audit into a concrete management plan. Do not re-audit. Do not code yet.
>
> For every major audit finding, provide: disposition (accept / accept with narrowing / defer / reject), why, immediate next step, prerequisites, code/data/docs/tests touched, acceptance criteria, risk of calibration drift, correct placement in revised roadmap, consequence if mishandled
>
> Then produce: (1) management summary, (2) audit feedback response matrix, (3) exact roadmap rewrite actions, (4) grouped implementation packages, (5) blocking decisions, (6) testing/validation plan, (7) corrected execution order, (8) final decision-ready conclusion
>
> Constraints: preserve current calibration unless a change explicitly requires recalibration; identify where feature flags, migration shims, and invariant tests are required; specify required updates to all affected governance documents
>
> Do not be generic. Convert critique into action.

### Step 3 Prompt — Auditor Review of Response (3rd Party)

> Responses to your feedback below. Provide line-by-line responses in the following format with the intent to close the iterative feedback loop:
>
> 1. Feedback item — Utilize the item number
> 2. Disposition — Accept / Accept with narrowing / Defer / Reject / Convert into documentation-only correction / Convert into later-phase calibration task

### Step 4 Prompt — Final Decisions (Cowork)

> Here are responses to your Audit Remediation Plan. Consider this audit loop now closed with these responses as the definitive way forward.
>
> Tasks:
> 1. Adjust and implement all decisions into the roadmap and other relevant documentation
> 2. Print a summary of all changes to the roadmap based on this audit

---

## Cowork Execution Checklist

Use this checklist to track progress through the audit lifecycle:

- [ ] Confirm scope with user (phases covered, full vs. targeted)
- [ ] Determine audit number (check last `OutsideAudit.N.*` folder)
- [ ] Create `OutsideAudit.N+1.YYYY-MM-DD/` folder
- [ ] Generate AuditOrientation document (D1a) — use the docx skill
- [ ] Generate `MANIFEST.md` describing the outer-zip layout (entries 00–09)
- [ ] Bundle orientation .docx + MANIFEST.md into `00_orientation_manifest.zip`
- [ ] Assemble content sub-zips `01_*.zip` through `09_*.zip` (each ≤ 100 MB; no video/audio)
- [ ] Assemble outer audit package zip `AuditPackage.N.YYYY-MM-DD.zip`: exactly 10 entries (1 × `00_*.zip` + up to 9 content sub-zips), ≤ 100 MB total (D1b)
- [ ] Verify auditor handoff is a single deliverable (the outer zip); pivot to GitHub repo path if outer zip exceeds size limit
- [ ] Place all files in audit subfolder
- [ ] Provide user with Step 1 Prompt for the auditor
- [ ] **WAIT** — User delivers to auditor and returns with D2
- [ ] Save audit report as `AuditReport.N.YYYY-MM-DD.md` (D2)
- [ ] Summarize key findings for user
- [ ] Execute Step 4: produce remediation plan (D3)
- [ ] Present remediation plan to user for review
- [ ] Provide user with Step 3 Prompt for the auditor
- [ ] **WAIT** — User delivers D3 to auditor and returns with D4
- [ ] Save auditor review as `AuditReviewResponse.N.YYYY-MM-DD.md` (D4)
- [ ] Execute Step 6: finalize all decisions, update docs (D5)
- [ ] Update CLAUDE.md §External Audit Outcomes
- [ ] Add lessons-learned entry for this audit cycle
- [ ] Print roadmap change summary

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

| Anti-Pattern | Why It's Wrong | Do This Instead |
|-------------|---------------|-----------------|
| Skipping the orientation document | Auditor lacks context, produces surface-level review | Always generate D1a with full project context |
| Including `.git/` or caches in the package | Bloats zip, confuses auditor | Apply exclusion rules strictly |
| Rejecting findings without counter-evidence | Turns the audit into a rubber stamp | Provide specific code/data evidence for every rejection |
| Implementing fixes before Step 6 closes | Changes may conflict with auditor's final response | Wait for the full loop to close before writing code |
| Accepting everything without narrowing | Scope explosion — audit creates more work than the phase it audited | Apply "accept with narrowing" aggressively on broad findings |
| Skipping the lessons-learned entry | Audit insights get lost | Always log at least one LL entry per audit cycle |
| Sending batches sequentially to auditor | Auditor reviews are meant to be holistic | Deliver all batches together — they're split for size, not sequencing |
| Packing >10 entries into the outer zip | Violates the per-zip outer-entry limit; auditor may not be able to extract or process | Use the standard layout: `00_*.zip` + up to 9 content sub-zips = exactly 10 entries |
| Delivering the orientation .docx as a separate file alongside the outer zip | Wastes a session deliverable slot and risks the auditor missing it | Bundle orientation + manifest inside `00_orientation_manifest.zip` so the handoff is a single outer zip |
| Skipping `MANIFEST.md` | Auditor opens the outer zip with no map; has to guess what each `0N_*.zip` holds | Always generate `MANIFEST.md` and bundle it with the orientation in `00_*.zip` |
| Putting content at index 00 | Index 00 is reserved for orientation + manifest | Reserve `00_*.zip` for the orientation bundle; content groups start at `01_*.zip` |
| Sending >10 deliverables in a single auditor session | Violates the per-session file limit | Consolidate into a single outer zip; if too large, pivot to the GitHub repo / directory ingestion path |
| Embedding video or audio inside a zip | Prohibited content type for compressed archives | Strip media from the package; if media is essential, deliver as standalone files (counts against the 10-file ceiling) |
| Letting any zip exceed 100 MB | Violates the per-zip size limit | Split the content into more sub-zips — never relax the ceiling |
