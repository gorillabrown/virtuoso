# Roadmap review — assessment detail

Serves `roadmap-review` SKILL.md Phase B: B.2 (pace) and B.3 (what the previous cycle
left, the open findings, and the board comments).

## B.2 Pace — what to report

Pace comes from the `pace` block of the same `kpis --json` call — one report per
declared deadline. Each gives the rate the date requires (remaining work ÷ weeks
left) against the trailing rate (completions over
`policy.roadmap.pace.trailingWeeks`), in items and in the effort unit the report
names (`effortUnit`: hours or points; see `policy.roadmap.effortBasis`), and a verdict:
`ahead`, `on track`, `behind`, `overdue`, or `met`, naming the unit that drove it.
Report, for each deadline:

- the verdict and its reason, and the projected finish at the trailing rate
- the scope it covers — say it, because a wrong assumption about scope is only
  visible if it is stated
- the blocked share of remaining work: blocked work cannot be delivered however
  fast the rest moves
- every figure returned as not computable, with its missing inputs named
- the effort basis of each figure (`effort.remaining`, `effort.trailing`): how many items
  each source sized, and its kind — `inferred` when size words stood in for hours

### Recording a deadline the owner sets or moves

The date has one home, `policy.roadmap.deadlines.<id>`. Before writing, ask which
finish line the date is for and which items count toward it — the answers are
`finishLine` and `scope`; without them the review reports the deadline unanchored,
which is the truth. Preview, get approval, then apply:

    "$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . --actor roadmap-review policy-set roadmap.deadlines.<id> --value-json '{"date": "YYYY-MM-DD", "owner": "<who ruled>", "finishLine": "<roadmap heading>"}'

then the same command with `--apply`. A moved date is
`policy-set roadmap.deadlines.<id>.date`; a withdrawn one is `--value-json null`.
Record the ruling in the roadmap's finish-line section as prose that points at the
policy. Do not copy the date into memory, charters, or the board — every surface
reads it from the policy, and a copy is a second authority that drifts.

Return to SKILL.md B.3.

## B.3 What the previous cycle left, open findings, and board comments

Read what the previous cycle left for this one: the previous review's
`YYYY-MM-DD-lessons-applied.md` (the lessons it applied, the candidates it left
undecided — decide them in D.4). The resolver names it:
`"$HOME/.virtuoso/bin/virtuoso" virtuoso_registry --root . review --date <YYYY-MM-DD>`
gives `previous`, latest by date, then run. When that set was interrupted and has no
lessons-applied, read `previousComplete`'s, and name the interrupted review in the
assessment.

Read too every entry in the registered `findings` role whose latest **Disposition** is
still `open`. Each open finding is carried into the plan: fixed by a planned item,
accepted with a reason, or turned into a lesson — recorded by appending a disposition
under its id. A finding left open across two reviews is named in the assessment.

Beside the open findings, read the open **board comments** — the notes people left on
the roadmap board's rows, saved or exported into the registered `boardComments` file:

    "$HOME/.virtuoso/bin/virtuoso" board_comments --root .

Address, adopt or answer each one. A comment on live work is input to that item's plan
or specification; a comment on finished work (the Completed tab) is a follow-up
candidate, proposed as a new item, never a change to the closed one. Mark each answered
comment resolved, which greys it out on the page:

    "$HOME/.virtuoso/bin/virtuoso" board_comments --root . --actor roadmap-review --resolve <ID> --answer "<what the review did>" --apply

The board never edits the register or the roadmap; its comments reach them only through
this review. Resolving changes the comments file, so preflight reads `board: stale`
until D.7 regenerates the page later in this review.

Return to SKILL.md B.4.
