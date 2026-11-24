# Dispatching an Epic

Serves next-dispatch Phase 1.2, *Epic at head*: the head is an epic run. Either `next`
names its packet (`inEpicPacket`, with the launch file in `epicLaunch`), because the head
is a combination's **epic row** or an item an active charter names, or the head declares
`Path: epic` and a charter for it exists. An epic is dispatched like any item: one gate,
five findings, one kickoff to paste into the session that runs it. Only what the gate
reads changes. The packet is the specification, and its launch file's prompt is the
kickoff.

A head that declares `Path: epic` with **no** charter is not chartered yet: halt and route
to `/epic [ITEM-ID]` (*Epic at head* in [edge-cases.md](edge-cases.md)). A packet whose
`done.md` exists is finished: route to `/dispatch-closeout [PACKET-ID]`, and print no
kickoff.

## The five findings, for an epic

| Finding | PASS when |
|---|---|
| **Specification** | The charter's Definition of Done rows each name a command or a concrete procedure; `progress --check-milestones <charter> --charter` exits 0; `lessons --check <charter> --item <PACKET-ID>` passes; and charter.md and launch.md carry no unfilled `[BRACKET]`. A gap here goes back to `/epic`: this gate never rewrites a charter. |
| **Prerequisites** | Every prerequisite of the head's row (a combination's epic row carries what its members wait on outside the set) is terminal through the provider. |
| **Repository** | The packet is on the default branch: `git log -1 --format=%H <default> -- <packet dir>/charter.md` prints a commit. Otherwise BLOCKED, for the reason Phase 3.5's *Gate consequence* gives: the run branch would start from a base without its own packet. Land it as Phase 3.5 lands an enrichment edit, under `policy.git`. Then read state.md's Working set: the run branch not yet created means a first session; created means a resume, and the same prompt resumes it. |
| **External register** | As for any dispatch. For a combination, every member also reads nested under the epic row (`member_of` in `items --json`). A member still on the belt alone, or no epic row at all, is AUTO-COMPLETABLE: preview `epic-row --actor next-dispatch --packet <packet>`, and apply it once the preview shows only that run's rows. A refusal there (no column to nest in, no write permission) is a GAP with the refusal's own fix. |
| **Execution environment** | Re-run the launch file's walk-away preflight rows that can change since scaffold: credentials, the permission mode or allowlist, reachable remotes. Any that fails is a GAP. |

A BLOCKER(USER) waiting in state.md does not fail a finding. Name it in *What's next*:
the session that resumes adopts its answer, so answer it first (`/mid-dispatch-decision`).

## The print

The three sections of [kickoff-format.md](kickoff-format.md), with these changes:

- **What's next** leads with the charter's title and outcome. For a combination, list its
  members by descriptive name, in serial order.
- **The Kickoff block** carries this header, then the launch file's *Kickoff / resume
  prompt* verbatim. Its `GIT WORK` block is the reconciliation recipe, so no second
  recipe is added:

      [Charter title]  ([PACKET-ID])
      Session: [PACKET-ID]-S<n> — [phase state.md names as current] · Remote Control: [state]
      Origin: epic packet — [packet dir] ([PACKET-ID]: [ITEM-ID], [ITEM-ID], ...)
      Branch: [run branch] from [default] @ [base]  ([first session | resume, S<n>])
      Specification: [packet dir]/charter.md
      Readiness: specification ✓ · prerequisites ✓ · repository ✓ · register ✓ · environment ✓

  `n` is the next session number in journal.md.
- **Goal line.** Straight after the kickoff, print the launch file's goal line in its own
  fenced block, for the CLI's `/goal`.
- **Pre-flight** adds `[resolved] Packet on the default branch` and, for a combination,
  `[resolved] Members nested under the epic row`.

§4.3 applies with check 7 read as "the `GIT WORK` block is filled, with no placeholder",
and check 10 as "the Session line names `[PACKET-ID]-S<n>`".

Return to SKILL.md Phase 4 and print.
