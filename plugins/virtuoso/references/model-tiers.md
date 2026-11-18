# Model tiers

The one place the plugin names model aliases. Every other shipped file speaks in task
tiers and effort levels (`validate.py` exempts this file from its host-term scan, as it
exempts host adapters). An agent's frontmatter carries `model: inherit`, which every
supported host accepts, and its `effort`. This table puts each agent in a tier (the
Agents column), names the alias a host may use for that tier, and says which effort the
tier defaults to.

| Tier | Model alias | Current model id | Default effort | Agents |
|---|---|---|---|---|
| mechanical | `haiku` | `claude-haiku-5-5` | `low` | Hermes, Hippocrates |
| bounded | `sonnet` | `claude-sonnet-5-5` | `medium` | Archimedes, Hercules, MarcusAurelius, Plato, Pythagoras, Socrates |
| cross-cutting | `opus` | `claude-opus-5-5` | `high` | Aristotle, Hesiod |

The effort scale is `low`, `medium`, `high`, `xhigh`, `max`. No tier defaults to `xhigh`
or `max`: a task gets either only by its own annotation (the `effort-levels` skill). The
model id an alias resolves to moves with the host's releases, so update that column,
never the agents. An agent never names an alias in its own frontmatter: a host that does
not know the alias skips the agent.

**A host that does not read `model` or `effort`.** The agent runs at whatever the host
gives it, and the run is still sized: the plan names each row's tier and effort, so the
planner's intent is on the page and a reviewer can see a mismatch. Nothing in the plugin
depends on the host honouring either field.

**Plan lines.** The virtuoso skill prints `[tier] {effort} ‹model›` on every row, the model
being the alias this table gives the owner agent's tier. A row with no owner agent shows
its tier's alias.
