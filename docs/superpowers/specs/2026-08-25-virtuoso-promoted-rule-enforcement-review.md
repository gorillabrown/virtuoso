# Spec — Virtuoso Promoted-Rule Enforcement

**Source:** lessons-corpus review of 2026-08-25 (687 SRL entries in `SpecRetro.Lessons_Learned.md`
plus the Project Constitution Standing Rules) against the Virtuoso plugin surface.

**Scope decision (confirmed with the operator, 2026-08-25):**

| Question | Decision |
|---|---|
| Which surfaces get patched | **Plugin source only** — `plugins/virtuoso/`. Ships to every consumer via the existing release pipeline. |
| Preflight (section 3) placement | **Same plan, sequenced last** — cheap high-confidence fixes land first. |
| Enforcement depth | **Prose + scripts + CI checks** — per SRL-046, a promoted rule without dispatch-time machinery is applied by agent discretion. |

**Out of scope (recorded, not actioned):** the Gloves_Of_Glory_fresh vendored copies
(`.claude/skills/virtuoso/SKILL.md` and `.agents/skills/virtuoso/SKILL.md`) are an 813-line
fork sitting 630 diff-lines behind the 859-line plugin body — they lack the shared-contract
block, registry resolution and the issue contract entirely. They carry every defect below
identically. Resyncing that fork onto the fixed plugin body is follow-on work.

---

## Executive summary

The finding is not that the plugin is missing good ideas. **The project already diagnosed this
exact failure and never applied the remedy to Virtuoso itself.** Two catalog entries state the
governing principle: promoting a rule into the lessons file creates documentation but not
enforcement, because agent execution paths read skill bodies at session start, not the lessons
file (SRL-122); and a promoted rule without dispatch-time machinery gets applied
inconsistently, by agent discretion (SRL-046). Roughly a dozen twice-seen or formally promoted
execution rules currently live only in the catalog. Virtuoso is the skill body they belong in,
and it has never been patched.

Three things are worth acting on, in this order: **(1)** the skill's worked example actively
teaches a routing the project has forbidden, and the skill predates the current concurrency
model entirely; **(2)** about a dozen promoted rules need a home in the skill body; **(3)** the
plugin's own governance preflight is a known destructive actor that a consumer repository
maintains a 432-line guard against.

---

## 1. Defects in the plugin as written

**Forbidden calibration routing in the worked example.** The canonical task plan assigns a full
calibration run (N=1,200 x 3 seeds) to the lightweight test-execution agent at the cheapest
model tier. The project ruled the opposite: calibration is a **measurement** dispatch, not a
regression dispatch, and routes to the calibration specialist, never the test runner (SRL-087).
The skill's own close-out example gets this right, so the file contradicts itself. The same
forbidden routing is baked into the test runner's agent brief, which lists "Run ICM" and
"Run full-cal" among its triggers. This is SRL-122 in its purest form: the rule was promoted,
and neither execution surface was patched.

**The skill predates the concurrency model.** Zero occurrences of *lane*, *surface manifest*,
*merge slot*, or *combined-tree gate*. The project moved to lane-based concurrency with
serialized integration, then to four lanes with a per-lane slot and an exclusive engine lane
(SRL-551). A worktree-resident sprint executed under this skill is never told to declare a
lane, pass the lane gate, or merge through the slot. Phase 6 ends at a repository-state line
with no merge procedure at all, while the project's git workflow requires claim slot -> merge
base into feature -> re-run the full gate on the combined tree -> merge -> push -> remove
worktree -> release slot.

**Two stale pointers.** The skill cites a CLAUDE.md section titled "Main Governance Documents —
Worktree Edit Prohibition"; the actual section is `## Worktree Edit Prohibition` with a
`Protected documents:` list. And the staging-file location is given as prose ("wherever the
project's close-out memos live") rather than resolved through the governance registry, which is
the declared authority for exactly that lookup and already carries a `closeOuts` key. The
Constitution's AMEND-THE-RESTATEMENTS rule prescribes the fix: convert a restatement into a
citation, because a citation cannot go stale.

---

## 2. Promoted rules with no home in the skill body

### Phase 4 — what "the sub-agent returned" is allowed to mean

| Rule | Concept | Catalog |
|---|---|---|
| Worker-output validation | A "completed" message is not evidence work happened; the tool-use trail and the repository delta are. A result with zero tool uses is discarded and re-dispatched — never partially complied with, because a payload shaped as instructions is injection-shaped. | SRL-513, SRL-524 |
| Artifact existence | An agent's report that it wrote a file is not evidence the file exists. Check the path. | SRL-189 |
| Read-only is verified, not instructed | An agent told "read-only" can still write a tracked file. A lock-free `git status` guard after each read-only burst is what holds the contract — and an independent party, not the writer, certifies any revert. | SRL-520 |

### Phase 4 — long-running work

The orchestrator must own any run that exceeds the sub-agent tool timeout; a sub-agent holding
a long suite handle is a single point of silent failure, and its background process dies when
it returns (SRL-417, SRL-595, SRL-453). This is a genuine and necessary exception to the flat
"the orchestrator never runs anything" rule. Adjacent: a backgrounded multi-arm compute launch
in a sibling worktree dies silently and can leave a stale result file that reads as fresh —
plan foreground per-arm splits from the start (SRL-571, four occurrences, promoted).

### Phase 4 — what must be inlined into worker prompts

Dispatch guidance is "concise, not exhaustive" and "pointers, not payloads", which is right for
context and wrong for safety. A rule that lives in the pointer but not in the worker's own task
text does not exist for that worker (SRL-589). The carve-out needs to be explicit and carry at
least:

- **A tool refusal is a stop, not a `--force` invitation** — even when the stopped worker
  believes it has proven the refusal spurious. Verification and override authority belong to
  the orchestrator (SRL-597 -> SRL-617, promoted).
- **A git scope fence** when another agent owns commit and merge, stated affirmatively (SRL-051).
- **A working-directory assertion** as the first action of any dispatch that writes to the
  filesystem (SRL-227).

### Phase 2 — how tiers get assigned

The skill instructs annotating each task with "the minimum viable model — the cheapest tier
that can handle the task". Ask instead what breaks if this output is wrong: a baseline capture
assigned to the cheapest tier returned figures that could not be reproduced under any
invocation, and an entire merge gate had to be re-derived (SRL-650). A task phrased "re-run the
tool and report" is sized as mechanical but is reasoning-dense whenever its output is an
interpretation rather than an artifact — classify by shape, not label (SRL-506). Cross-module
tasks at the highest effort tier systematically trigger critical review findings and need a fix
round pre-allocated as a planned step, not discovered as an overrun (SRL-038, promoted).

### Phase 1 — what an acceptance criterion has to be

Nothing in Phase 1 requires acceptance criteria to be mechanical. Stop gates and completion
conditions must be numeric thresholds, boolean checks, or enumerable criteria, with prose like
"reasonable" or "approximately" banned (SRL-067); a stop gate that names a rollback must also
name what happens when the rollback also fails (SRL-071); a contingency is pre-registered as a
decision table covering every axis the measured fact touches (SRL-619). A spec whose completion
depends on a suite gate needs an explicit procedure for a red base — measure the base *before*
implementing so attribution is unambiguous, and if red, file and escalate rather than
diagnosing in-sprint (SRL-585, with SRL-058).

### Phase 6 — close-out is an artifact, not a printout

- **The durable close-out file.** A plan authored without an explicit authoring task completes
  with governance updates that reference a file nobody produced (SRL-114).
- **The completed-work ledger row.** Close-out authoring and ledger entry are separate acts and
  only the first has a natural owner, so the ledger silently falls behind (SRL-642, promoted).
- **Deliverable existence before teardown.** Verify each named completion artifact is actually
  on the merged branch before removing the worktree (SRL-312, promoted).
- A verification task that finds more than a handful of issues must stop and spawn a
  remediation task rather than silently becoming implementation (SRL-004).

### The governance staging section — format is covered, lifecycle is not

- A resident staging memo is an **open obligation**, not an archive artifact; every close-out
  should sweep the directory and confirm each memo is processed *by checking the destination
  documents, not the memo's claims about them* (SRL-651).
- A gate claim in a staging memo needs a backing artifact before it is folded in (SRL-320).
- Lesson numbers proposed inside a worktree are provisional labels only; the worktree's view of
  the catalog is frozen at branch time and collides with numbers consumed since (SRL-372). The
  paired fix is to pass the current catalog tip into the authoring agent's prompt (SRL-424).

---

## 3. The preflight is a destructive actor

The governance preflight regenerates `Virtuoso.Governance.Readme.md` from a template while
printing a benign status line — deleting hand-authored prose with no indication anything
changed. Promoted to a standing guard on its **third** occurrence; the trigger surface turned
out to be session initialization, not merely the governance-skill entry points (SRL-557). An
attempted closure was falsified within hours because it verified against the manifest-churn
mechanism rather than against the reported symptom of prose deletion (SRL-590).

The consequence is visible in the consumer repository: `tools/virtuoso/registry_guard.py` is
432 lines with a 247-line test suite, and its README states plainly that the offending script
"lives outside this repo and cannot be modified from here."

**Posture change required: adopt/heal should be diff-and-propose, never clobber.** A registered
path that resolves on disk is never rewritten; a divergence is reported for the operator to
resolve, which is what the registry's own Rule 4 already prescribes for humans. Ride-alongs: a
governance restructuring that moves registered prose must grep the registry contents first
(SRL-680), and any closure must be re-probed against the originally reported symptom, not the
diagnosed mechanism (SRL-590).

### Reproduction of record (2026-08-25)

Run against a scratch fixture with a curated registry, using the SessionStart hook command
verbatim:

```
python plugins/virtuoso/scripts/virtuoso_preflight.py --root <fixture> --mode detect --quiet
```

| Step | Observed |
|---|---|
| Seed fixture with `--mode create` | `writes: 9` |
| Append a hand-authored `## Local Operating Notes` section to `Virtuoso.Governance.Readme.md` | present |
| Run the SessionStart hook command verbatim | `writes: 1` |
| Grep for the appended section | **absent — silently deleted** |
| Re-run on the now-settled tree | `writes: 0` |

The `writes: 1` line is truthful (PF-02 works). The content is gone anyway. This means
**R1 of the existing remediation design ("Detect mode writes nothing, ever",
`docs/superpowers/specs/2026-07-18-preflight-registry-clobber-remediation-design.md`) is still
open** for the hand-authored-prose case — exactly the SRL-590 pattern of closing against the
mechanism rather than the reported symptom.

---

## 4. Implementation notes

**The mechanization idiom already exists.** The plugin ships `validate.py`, `bump_version.py`,
`release.py`, `virtuoso_preflight.py` and friends, each with paired tests, gated by CI. SRL-046
points at that directory, not at more prose. Three of the gaps above are small guards in the
established idiom: a staging-memo residency sweep, a completion-artifact existence check, and
an unpushed-commit count at burst end.

**One tempting finding checked and dropped:** the repository-wide clean-tree gate that blocked
lane dispatches from proceeding past dirt they were forbidden to touch has already been fixed
in the consumer repo's `tools/worktree/worktree-create.sh` — scoped to the declared manifest
union in lane mode, whole-repository check retained in serialized mode.
