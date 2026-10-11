# Model tiers

The one place the plugin names model aliases. Every other shipped file speaks in task
tiers and effort levels (`validate.py` exempts this file from its host-term scan, as it
exempts host adapters). An agent's frontmatter carries its `model` alias and its
`effort`; this table says what each alias means and which effort a tier defaults to.

| Tier | Model alias | Current model id | Default effort | Agents |
|---|---|---|---|---|
| mechanical | `haiku` | `claude-haiku-5-5` | `low` | Hermes, Hippocrates |
| bounded | `sonnet` | `claude-sonnet-5-5` | `medium` | Archimedes, Hercules, MarcusAurelius, Plato, Pythagoras, Socrates |
| cross-cutting | `opus` | `claude-opus-5-5` | `high` | Aristotle, Hesiod |

The effort scale is `low`, `medium`, `high`, `xhigh`, `max`. No tier defaults to `xhigh`
or `max`: a task gets either only by its own annotation (the `effort-levels` skill). The
alias is what an agent declares; the model id it resolves to moves with the host's
releases, so update that column, never the agents.

**A host that does not read `model` or `effort`.** The agent runs at whatever the host
gives it, and the run is still sized: the plan names each row's tier and effort, so the
planner's intent is on the page and a reviewer can see a mismatch. Nothing in the plugin
depends on the host honouring either field.

**Plan lines.** The virtuoso skill prints `[tier] {effort} ‹model›` on every row, the model
being the owner agent's alias from this table. A row with no owner agent shows its tier's
alias.
