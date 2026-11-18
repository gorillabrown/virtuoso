# Acceptance and Evidence Reconciliation — Detail

Serves dispatch-closeout SKILL.md, Wave 2 Step 1 and *Acceptance and evidence
reconciliation*. The rules stay in SKILL.md, each under its anchor; this file gives what
each one requires, under the rule's own heading.

## Failure classification

Every non-pass result is exactly one of:

1. **In-scope regression** — the candidate fails behavior within its changed
   dependency surface. Completion is blocked.
2. **Inherited baseline failure** — the same deterministic failure occurs at the
   accepted baseline and at the candidate, with the relevant implementation
   unchanged. Preserve the failure, link or create a separate bounded issue through
   the issue contract, and apply only an authorized acceptance amendment.
3. **Admission or custody failure** — repository identity, import isolation,
   protected inputs, or evidence collection cannot be trusted. Completion is blocked
   even if test assertions passed.
4. **Infrastructure failure** — the test produced no valid behavioral result because
   of environment, runner, storage, permission, or provider failure. Repair or rerun
   the affected operation; do not classify it as a product failure.
5. **Authorized exclusion** — an owner-approved, published exclusion exists. Report
   it explicitly and never describe the excluded population as passed.

An inherited failure requires evidence, not inference: reproduce it at the accepted
baseline when practical, compare the candidate's relevant dependency surface, and
verify that protected inputs remained unchanged.

## Proportional evidence

- Commit and tree identities prove tracked-content identity.
- Exact-path diffs prove implementation scope.
- Clean index and working-tree checks detect checkout drift; `virtuoso_registry repo`
  reports both, read-only.
- Hash protected inputs and configuration surfaces directly.
- Use multiple independent repositories only when the proof depends on distinct
  repository identities.
- Use one fresh isolated runner for ordinary regression unless the governing
  contract requires more.
- Do not repeatedly hash complete repositories when version-control identities and a
  targeted protected-file inventory establish the same property.
- Do not rerun an accepted final test merely to produce another summary. Read and
  verify its raw evidence unless the contract explicitly requires a fresh close-out
  execution.

Evidence reduction is never invented during close-out. Any change to a binding gate
goes through the project's amendment and review process first.

## Exact integrated identity

Before publication, verify:

- the complete candidate diff matches the authorized manifest;
- the tested tree equals the tree selected for publication;
- the published local, tracking, and authoritative remote references agree;
- no unreviewed change landed between final acceptance and publication.

A later governance-only commit does not retroactively invalidate a properly recorded
implementation acceptance, but the close-out distinguishes the tested implementation
commit from any subsequent documentation commit.

## Protected-state custody

Record the integrity properties the project declares for its protected inputs
immediately before and after the accepted test session:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . protected --json

## Completion scope

Record remaining dependencies, inherited defects, authorized exclusions, and
unresolved owner decisions without converting them into completion claims.

## Close-out language

The report distinguishes:

- what passed;
- what failed;
- what was excluded under authority;
- what remained unchanged;
- what was published;
- what remains open.

## Resource and provider completion

After publication, verify every registered terminal operation through its source:

- item retirement or terminal status;
- terminal-ledger entry;
- worktree completion;
- workstream, lock, or merge-slot release;
- authoritative remote publication;
- recovery state.

Use the exact recorded holder, branch, item, and revision identities. A partial
crossing remains incomplete and receives a recovery record describing what succeeded
and what remains (SKILL.md, *On partial failure*).

## Epic packets — the record merge

Step 1's done.md check, in full:

    "$HOME/.virtuoso/bin/virtuoso" dispatch_guards artifacts-exist --ref <default branch> <packet directory>/done.md

must exit 0. Exit 1 means the record sits only on the run branch: the
crossing waits for a merge into the default branch — the run branch's, or, where its code
is already merged, its docs-only completion commit's, with `--no-ff` — made as far as
`policy.git` permits, or handed with the exact command to whoever it names. For the
docs-only merge, check that it touches only the packet directory (`git diff --name-only
<merge>^1 <merge>` lists nothing outside it), then run the guard again. The close-out
runs the record merge's scope check itself (`git diff --name-only <record merge>^1
<record merge> -- . ":(exclude)<packet directory>"` prints nothing) and reports it in
the close-out: the run cannot record a check of its own last merge.

Return to SKILL.md, *Acceptance and evidence reconciliation*, then Step 2.
