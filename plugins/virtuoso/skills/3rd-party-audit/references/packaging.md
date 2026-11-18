# Audit Package Constraints and Layout

Serves the `3rd-party-audit` skill, Step 1 (Package Creation) and Step 2 (Handoff): the
upload limits every package must respect, the standard outer-zip layout, tiered scoping,
exclusions, and the packaging anti-patterns.

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

## Standard Outer-Zip Layout

```
AuditPackage.N.YYYY-MM-DD.zip                     (single deliverable, ≤ 100 MB, exactly 10 entries)
├── 00_orientation_manifest.zip                   ← entry 0: orientation + manifest + questions
│   ├── AuditOrientation.N.YYYY-MM-DD.docx
│   ├── AuditQuestions.N.YYYY-MM-DD.md
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

## Package Scoping

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

## Packaging Anti-Patterns

| Anti-Pattern | Why It's Wrong | Do This Instead |
|-------------|---------------|-----------------|
| Including `.git/` or caches in the package | Bloats zip, confuses auditor | Apply exclusion rules strictly |
| Sending batches sequentially to auditor | Auditor reviews are meant to be holistic | Deliver all batches together — they're split for size, not sequencing |
| Packing >10 entries into the outer zip | Violates the per-zip outer-entry limit; auditor may not be able to extract or process | Use the standard layout: `00_*.zip` + up to 9 content sub-zips = exactly 10 entries |
| Delivering the orientation .docx as a separate file alongside the outer zip | Wastes a session deliverable slot and risks the auditor missing it | Bundle orientation + manifest inside `00_orientation_manifest.zip` so the handoff is a single outer zip |
| Skipping `MANIFEST.md` | Auditor opens the outer zip with no map; has to guess what each `0N_*.zip` holds | Always generate `MANIFEST.md` and bundle it with the orientation in `00_*.zip` |
| Putting content at index 00 | Index 00 is reserved for orientation + manifest | Reserve `00_*.zip` for the orientation bundle; content groups start at `01_*.zip` |
| Sending >10 deliverables in a single auditor session | Violates the per-session file limit | Consolidate into a single outer zip; if too large, pivot to the GitHub repo / directory ingestion path |
| Embedding video or audio inside a zip | Prohibited content type for compressed archives | Strip media from the package; if media is essential, deliver as standalone files (counts against the 10-file ceiling) |
| Letting any zip exceed 100 MB | Violates the per-zip size limit | Split the content into more sub-zips — never relax the ceiling |

Return to SKILL.md Step 1, action 4 (or to Step 2 if you came here for the handoff).
