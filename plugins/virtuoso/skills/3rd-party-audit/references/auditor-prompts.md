# Auditor Prompts

Serves the `3rd-party-audit` skill: the prompt templates for its steps. Prompt numbers are
their own sequence, not step numbers. The two auditor prompts are handed to the user: the
Step 1 Prompt at Step 1 (action 10) and Step 2, the Step 3 Prompt at Step 4 (action 6). The
two planner prompts frame the planner's own work: the Step 2 Prompt for Step 4 (the
remediation plan), the Step 4 Prompt for Step 6 (final decisions).

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
> Primary review question: "[PRIMARY QUESTION — from D0]"
>
> Child questions (answer each, with evidence):
> - Q1. [CHILD QUESTION 1 — from D0]
> - Q2. [CHILD QUESTION 2 — from D0]
> - …
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
> Required output format: (0) Answers to the primary question and to each child question, each grounded in cited evidence or marked unverifiable, (A) Executive verdict, (B) Current-state architecture summary, (C) Roadmap item-by-item audit, (D) Major contradictions, (E) Sequencing analysis, (F) Structural/modeling review, (G) Testing review, (H) Top risks, (I) Missing work, (J) Proposed revised roadmap, (K) Final recommendation with scores

### Step 2 Prompt — Remediation Plan (planner)

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

### Step 4 Prompt — Final Decisions (planner)

> Here are responses to your Audit Remediation Plan. Consider this audit loop now closed with these responses as the definitive way forward.
>
> Tasks:
> 1. Adjust and implement all decisions into the roadmap and other relevant documentation
> 2. Print a summary of all changes to the roadmap based on this audit

Return to the SKILL.md step that sent you here.
