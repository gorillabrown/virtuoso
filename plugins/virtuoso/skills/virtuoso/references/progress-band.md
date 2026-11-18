Serves `virtuoso` Phases 1, 4, 5 and 6: opening, feeding, and ending the progress band's run.

# The Progress Band

The plugin draws a progress band above the prompt of every session running a dispatch or an
epic, in any project (format in `references/registry-contract.md`, *The progress band*):

    <bar over this milestone's steps> Step X/Y      ( P% complete; milestone ETA) <step>
    <bar over the run's milestones>   Milestone X/Y ( Q% complete; dispatch ETA) <milestone>

This skill is the band's only writer: it opens the run, feeds it, and ends it. Nothing else
does, not `/next-dispatch`, `/epic` or `/dispatch-closeout`. Every change goes through one
command, never a hand edit; the command stamps the time, and each ETA is measured from those
stamps. Its files live in your own state folder, never in the project, and it never touches
the registry. The plugin's hook points the session that runs a feeding command at that run,
so each session shows only its own, even when two share one folder.

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor virtuoso progress --run <ID> <change>

- **Phase 1 — milestones.** The milestones are the plan's phases: a specification's
  `##### Milestones` table grouping its task rows (rubric U11; check it with
  `progress --check-milestones <spec> --item <ITEM-ID>`), an epic charter's `## Milestones`.
  A ready specification with no milestones is not refused: derive them from its task rows
  and *Done when* (two to five, each a group of consecutive rows ending in something
  checkable; one milestone where the plan has no phases), write them to a scratch JSON file
  outside the project as `[{"id": "M1", "label", "steps": [{"id": "<row #>", "label"}]}]`,
  and say they were derived. Show the milestones, with their steps, before Phase 2.
- **Phase 1 — open.** `progress --run <DISPATCH-ID> --from-spec <spec> --item <ITEM-ID>
  --title "<short title>"`, or `--plan <file>` for derived milestones. Phase 2's task list
  follows the milestones. If the plan changes mid-run, open it again the same way: the
  milestone list follows the plan, and every stamp already made stays.
- **Phase 4 — steps.** A step is a task row, its id the row number, so the band moves with
  the time log: beside `timing --start <n>` run `progress --run <DISPATCH-ID> --step <n>
  --state active`, and beside `timing --end <n>` run `--state done` (or `blocked`, or
  `cancelled`: a cancelled step or milestone drops out of X/Y). Mark a
  milestone `done` with `--milestone <M#> --state done` when its *Done when* holds; the next
  milestone's steps then take over line one. A row added mid-run is added to the band with
  `--step <n> --label "<task>"`.
- **Phase 5.** A pause to wait on a decision is not an end: mark the active step `blocked`,
  and `active` again when the decision releases it. The band stays live throughout.
- **Phase 6 — end.** `progress --run <DISPATCH-ID> --complete --evidence "<the check>"`
  only once this skill's own completion check has passed and every milestone is done; the
  band then shows `✓ COMPLETE`. Any other end (failed, aborted, halted) is
  `--stop <one-word reason>`, shown as `■ STOPPED`, never COMPLETE and never hidden. The run
  is archived either way, and its end line stays until the session's next run starts or the
  user runs `progress --clear`.
- **An epic.** The run id is the epic's id, carried in its launch and state. Its first
  session opens it with `--from-charter <charter>`; each step is a charter checkpoint
  (`1.1`, `1.2`, …). After context loss or in a later session, open it again the same way:
  that re-attaches to the same run and continues its milestones and stamps; never start a
  second run for one epic. End it only when the epic ends.

A run with no feed for 30 minutes (longer where its steps run long) is drawn dim with when
it last moved. Work with no
dispatch or epic id is not tracked. The band never blocks work: a refusal from the command
is reported as it stands, never worked around by editing a file.

Return to the SKILL.md phase that sent you here.
