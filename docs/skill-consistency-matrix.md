# Skill Consistency Matrix

Sprint SK-09. Establishes what the 15 Virtuoso skills share, proves the shared contract is
present and identical in all of them, and records the deliberate cross-invocation call-outs
between skills.

Scope: `plugins/virtuoso/skills/*/SKILL.md` (15 files). All commands below are run from the
repository root and their pasted output is real.

---

## 1. The shared contract preamble

Every `SKILL.md` carries an identical block immediately after its YAML frontmatter, opening
with the stable marker line:

```
<!-- virtuoso-shared-contract v1 -->
```

The block is 9 lines: the marker, a one-line framing sentence, a blank line, and six bullets —
one per shared concept. It is a reference block; the skill body below it governs specifics.

### Why these six concepts

They are the cross-cutting rules that more than one skill depends on and that a skill author
could plausibly get wrong in isolation. Concepts owned end-to-end by a single skill (e.g. the
Dispatch-Readiness Rubric, which lives in `next-pointer` and `roadmap-review`) are deliberately
*not* in the shared block — duplicating them would create two sources of truth.

### A note on what the block does NOT say

The block deliberately avoids the literal strings `Virtuoso.Governance.Readme.md` and
`--mode adopt`, referring instead to "the project-root governance readme" and describing
adoption behaviourally.

This is not stylistic. `plugins/virtuoso/scripts/test_skill_preflight_contract.py` asserts that
each of the six **gate skills** contains those exact tokens
(`test_gate_skills_reference_governance_registry_first`, `test_gate_skills_adopt_rather_than_detect`).
Had the shared block contained them, those two tests would have been satisfied *by the preamble
alone* in all 15 files and would no longer discriminate — a gate skill could lose its real
governance-authority block and the suite would stay green. Keeping the tokens out preserves the
tests' power. The block likewise contains neither `--mode detect` nor `virtuoso_preflight.py`,
so it cannot trip `test_no_skill_uses_superseded_detect_mode` or
`test_only_virtuoso_init_can_create_workspace_directly`.

---

## 2. Skill × shared-concept matrix

Legend:

| Mark | Meaning |
|---|---|
| ● | **Load-bearing** — the skill's own workflow is built around this concept; remove it and the skill is wrong or broken. |
| ○ | **Applicable but incidental** — the rule binds the skill in some runs, but the skill's workflow is not organised around it. |
| — | **Not applicable** — the concept does not reach this skill's behaviour. |

Columns: **REG** registry resolution · **ADO** workspace adopt · **GIT** git ownership ·
**EFF** effort levels · **ISS** issue contract · **STG** governance staging.

| # | Skill | REG | ADO | GIT | EFF | ISS | STG |
|---|---|:--:|:--:|:--:|:--:|:--:|:--:|
| 1 | 3rd-party-audit | ● | ● | ○ | — | ○ | ○ |
| 2 | adversarial-review | ○ | — | — | ○ | — | — |
| 3 | delayed-start | — | — | — | — | — | — |
| 4 | effort-levels | — | — | ○ | ● | — | — |
| 5 | epic | ● | — | ○ | — | ○ | — |
| 6 | git-handoff | — | — | ● | — | — | — |
| 7 | governance-sweep | ○ | — | ○ | — | ○ | ○ |
| 8 | mid-dispatch-decision | ● | ● | ○ | ● | ● | ● |
| 9 | next-pointer | ● | ● | ● | ○ | ○ | ● |
| 10 | pointer-closeout | ● | ● | ● | ○ | ○ | ● |
| 11 | roadmap-review | ● | ● | ● | ○ | ○ | ○ |
| 12 | roadmap-status | ● | ● | ○ | — | ○ | ○ |
| 13 | ultrathink | — | — | — | ● | — | — |
| 14 | virtuoso | ● | — | ● | ● | ● | ● |
| 15 | virtuoso-init | ● | ● | — | — | ○ | — |

### Cell evidence (non-obvious cells only)

- **3rd-party-audit / ADO ●** — gate skill; its Preflight brings the project under management.
  Same for rows 8–12.
- **3rd-party-audit / STG ○** — Step 4 produces "exact roadmap rewrite actions", so the
  staging rule binds when the run is worktree-resident, but the skill has no staging machinery.
- **adversarial-review / GIT —** — its `git`/`branch` matches are false positives: "**Branch
  points**" at line ~279 means *decision* branches, not VCS branches.
- **effort-levels / GIT ○** — two incidental mentions; the skill does no git work.
- **epic / REG ●** — resolves an `epics` path from `Virtuoso/workspace-layout.json` and, when
  absent, offers once to register the directory. Registry resolution is genuinely load-bearing.
- **epic / ADO —** — epic registers a directory; it never runs the adopt flow.
- **epic / ISS ○** — routes `BLOCKER(USER)` to `mid-dispatch-decision`, but its blocker lives in
  `state.md` in epic's own format, not as the 7-field `Issue.<SPRINT-ID>.<YYYY-MM-DD>.md`.
- **governance-sweep / REG ○** — the skill is self-contained "for any project" and treats each
  directory's `readme.md` as structural authority; it does not resolve the Virtuoso registry.
  The *concept* is load-bearing, the *Virtuoso registry* is not wired in. See ambiguity note A2.
- **roadmap-review / STG ○** — roadmap-review is the document staging writes *into*; it is the
  fold-in target, not a stager.
- **roadmap-status / ISS ○** — its `Issue:` matches are a plain-language field in the briefing
  format, not the 7-field contract.
- **virtuoso / REG ●** — resolves the `issues` directory from `Virtuoso/workspace-layout.json`
  (manifest side only, never the readme); the issue contract depends on it.
- **virtuoso / ADO —** — virtuoso assumes a managed workspace; adoption is a gate-skill job.
- **virtuoso-init / REG ●** — it *creates* the registry (both carriers).

### Genuinely ambiguous cells

**A1 — `delayed-start`, entire row.** It is a pure wait wrapper: it sleeps, then hands control
to whatever task follows. That following task may do git work, route an issue, or resolve the
registry. Scored `—` throughout on the rule that a cell describes *the skill's own behaviour*,
not what it defers to. Under a "wrapped task inherits" reading the row would be `○` across the
board. Flagged rather than silently decided.

**A2 — `governance-sweep` / REG.** Split verdict. Readme-as-structural-authority is the skill's
core mechanic (`●`), but it is the *directory* `readme.md`, not the Virtuoso governance
registry, and the skill resolves no registry path. Scored `○`. If governance-sweep is ever meant
to defer to the registry for the documents it sweeps, this cell becomes `●` and the skill needs
a real edit — a question for the owner, not something this sprint decided.

**A3 — `adversarial-review` / EFF.** Its "Effort to Close" column is remediation-cost
estimation, a different sense of "effort" from the low/medium/high/max tier system. It does
document an ULTRATHINK pairing that bears on depth. Scored `○` on the pairing, not the column.

**A4 — `adversarial-review` / REG.** The skill produces review artifacts, and "review artifacts"
is a registered role, but the skill itself never resolves where to save them. Scored `○` as an
obligation it inherits from the shared contract rather than one it implements.

---

## 3. Verify commands

Every command below was run at sprint close; the output shown is real.

### V1 — preamble present in all 15

```bash
grep -l "virtuoso-shared-contract v1" plugins/virtuoso/skills/*/SKILL.md | wc -l
```
```
15
```

### V2 — the extracted block is 9 lines in every file

```bash
for f in plugins/virtuoso/skills/*/SKILL.md; do
  sed -n '/virtuoso-shared-contract v1/,+8p' "$f" | wc -l
done | sort -u
```
```
9
```
A single value `9` proves no file's block was truncated or padded.

### V3 — the block is identical in all 15 (content identity)

```bash
for f in plugins/virtuoso/skills/*/SKILL.md; do
  sed -n '/virtuoso-shared-contract v1/,+8p' "$f" | tr -d '\r' | sha256sum
done | sort -u
```
```
ff37035364e2b50aa4a7f79667567183c88213f4854d2fa049af9cc6909d24fe *-
```
Exactly one hash across 15 files.

### V4 — raw-byte reality (why V3 normalizes)

The skill set has mixed line endings by design: 14 files are pure CRLF, `epic/SKILL.md` is pure
LF, and SK-09 preserved each file's convention. So the block is byte-identical *within* a
newline family and identical *across* all 15 only after normalization. V3 states that honestly
via `tr -d '\r'`. This command shows the underlying split:

```bash
python3 -c "
import hashlib;from pathlib import Path
M=b'<!-- virtuoso-shared-contract v1 -->';d={}
for p in sorted(Path('plugins/virtuoso/skills').glob('*/SKILL.md')):
    b=p.read_bytes();i=b.index(M);nl=b'\r\n' if b.count(b'\r\n') else b'\n'
    d.setdefault(hashlib.sha256(nl.join(b[i:].split(nl)[:9])).hexdigest(),[]).append(p.parent.name)
for h,f in sorted(d.items(),key=lambda x:-len(x[1])): print(h[:16],len(f),'CRLF' if len(f)>1 else f[0])
"
```
```
7fa8152ad16d3106 14 CRLF
61e11b04bcf237dc 1 epic
```

> **Portability caveat.** Under MSYS/Git-Bash the `sed` in V3 already strips CR on read, so V3
> returns one hash even without `tr -d '\r'`. That is an accident of this environment, not a
> guarantee — the explicit `tr -d '\r'` keeps V3 correct on GNU/Linux too. V4 is the
> authoritative byte-level check because it never goes through `sed`.

### V5–V9 — cross-invocation call-outs

See the greps in the Cross-invocation table (§4); each returns `1`.

### V10 — full script suite

```bash
python3 -m pytest plugins/virtuoso/scripts/ -q
```
```
68 passed
```

### V11 — skill preflight contract (never edited by this sprint)

```bash
python3 -m pytest plugins/virtuoso/scripts/test_skill_preflight_contract.py -q
```
```
6 passed
```

### V12 — project-agnosticism not regressed

```bash
grep -ric "gog\|gloves\|blurby\|archetype\|fighter\|kokoro\|fight-sim\|KO rate" \
  plugins/virtuoso/skills | grep -cv ":0$"
```
```
0
```
Zero files carry a nonzero count, i.e. every count is `:0`.

---

## 4. Cross-invocation

Call-outs are written as natural sentences in the host skill's own voice and each names a
**trigger condition** and **what to do with the output** — the idiom set by `roadmap-review`'s
`write-spec` / `next-pointer` bookends (it invokes `write-spec` at D.3.1 to draft, then hands
off to `/next-pointer` for dispatch) and by `mid-dispatch-decision`'s existing
"Integration with Other Skills" section.

### Added or strengthened by SK-09

| Source | Target | Trigger condition | Proving grep |
|---|---|---|---|
| pointer-closeout | adversarial-review | Close-out carries something the project would inherit unexamined: a lesson being promoted to a standing rule, a sprint declared complete on partial evidence, or a roadmap edit that retires scope. Explicitly *not* offered for routine close-outs. | `grep -c "adversarial-review" plugins/virtuoso/skills/pointer-closeout/SKILL.md` → `1` |
| mid-dispatch-decision | ultrathink | Decision is genuinely *hard*, not merely consequential: type classification keeps flipping on re-reading, options trade off on incommensurable axes, or the recommendation rests on an unstated assumption. | ``grep -c "Escalate to \`/ultrathink\`" plugins/virtuoso/skills/mid-dispatch-decision/SKILL.md`` → `1` |
| 3rd-party-audit | adversarial-review | Before assigning dispositions, where a finding would drive expensive remediation or a roadmap rewrite — makes the **Reject** disposition defensible rather than defensive. | `grep -c "adversarial-review" plugins/virtuoso/skills/3rd-party-audit/SKILL.md` → `1` |
| governance-sweep | virtuoso | Approved Phase 3 work list runs past a handful of actions; the failure mode is silent partial completion (a group skipped or its verification never performed). | ``grep -c "\`/virtuoso\`'s task-plan discipline" plugins/virtuoso/skills/governance-sweep/SKILL.md`` → `1` |
| effort-levels | ultrathink | Max effort selected for an analytical problem. Max buys budget; ultrathink is the method that spends it. Closes a one-way link — ultrathink already drove `/effort-levels max`, but not the reverse. | ``grep -c "pair it with \`/ultrathink\`" plugins/virtuoso/skills/effort-levels/SKILL.md`` → `1` |

The `mid-dispatch-decision → ultrathink` row strengthens a pre-existing `### + ULTRATHINK`
subsection that described *what* ultrathink changes but never said *when* to reach for it. The
other four are new.

### Pre-existing call-outs (verified, not added)

| Source | Target | Note |
|---|---|---|
| roadmap-review | write-spec, next-pointer | The bookend pattern this sprint imitated. |
| virtuoso | mid-dispatch-decision | Issue-contract routing; the 7-field document's consumer. |
| mid-dispatch-decision | adversarial-review, effort-levels, virtuoso, pointer-closeout | Existing integration section. |
| epic | virtuoso, mid-dispatch-decision, adversarial-review | Existing optional-integration list. |
| ultrathink | pointer-closeout, effort-levels, 3rd-party-audit, adversarial-review | Existing combination list. |
| adversarial-review | ultrathink, pointer-closeout, 3rd-party-audit | Existing "Combining with Other Skills". |

### Considered and rejected

Recorded so a later sprint does not re-litigate them.

- **next-pointer → adversarial-review.** Rejected: next-pointer already runs a
  Dispatch-Readiness Rubric (R1–R10) over the spec. A second skeptical pass duplicates the
  rubric rather than adding to it.
- **adversarial-review → ultrathink.** Rejected as redundant: already documented in
  `adversarial-review`'s own "Combining with Other Skills".
- **roadmap-review → ultrathink.** Rejected: roadmap-review is a heavily-specified checkpointed
  ceremony; ultrathink's value there is diffuse and would not name a crisp trigger.
- **delayed-start → anything.** Rejected: it governs only the wait.
- **git-handoff → anything.** Rejected: legacy, explicitly "do not auto-trigger".
- **pointer-closeout → roadmap-status.** Rejected: close-out already owns its roadmap updates.

---

## 5. Maintenance

- The marker is versioned. A substantive change to the shared contract should become
  `virtuoso-shared-contract v2` and be applied to all 15 files in one pass, with V1–V4 re-run.
- Adding a skill means adding a matrix row and the preamble; V1 turns `15` into `16`.
- Do not add the tokens `Virtuoso.Governance.Readme.md`, `--mode adopt`, `--mode detect`, or
  `virtuoso_preflight.py` to the shared block — see §1.
