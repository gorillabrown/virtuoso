Serves `mid-dispatch-decision` Step 3: what each of the seven decision types means.

# Decision Types

Seven types across three axes: same direction vs. new direction, continue vs. stop, and a
verification gate that defers the strategic decision entirely. The instruction block each
type carries is in [instruction-blocks.md](instruction-blocks.md) (read at Step 6a).

### Type 1a — Advance (Pre-Authorized)

The dispatch spec pre-authorized a response for this exact situation, and the implementation
agent's findings confirm the pre-authorization still applies. Confirm and go.

### Type 1b — Advance (Planner-Originated)

No pre-authorization exists, but the direction is right and the remaining scope is correct.
The planner authors the direction the implementation agent didn't have.

### Type 2 — Advance with Narrowing

Same direction, reduced scope. Budget, focus, or new information justifies doing less.

### Type 3 — Pivot Advance

The implementation agent continues but does *different work* than planned. The planner
authors a mini dispatch revision in real time, sizing new tasks with the effort-levels Task
Type Reference Table; virtuoso's execution discipline applies to the revised plan.

### Type 3a — Revise Routing / Effort (Same Plan)

The remaining work is valid and the direction is correct, but agent routing or effort
allocation is wrong (e.g. a task dispatched as bounded/medium needs cross-cutting/high).
Revise the annotations and continue.

### Type 4 — Pivot Stop and Regroup

The implementation agent stops. Completed work is preserved; remaining tasks are cancelled.
The planner runs a partial dispatch-closeout (the contract in SKILL.md §Decision Types), then
authors a new dispatch.

### Type 5 — Verify First

The implementation agent's findings are surprising, and the correct strategic decision
depends on whether the measurement is real. Instead of choosing a direction now, dispatch a
narrow verification task and defer the decision until results land.

This is distinct from Type 3: you aren't pivoting strategy, you're gating strategy on
verification. The remaining plan pauses (not cancelled) while verification runs.

**When to use:** the measurement is load-bearing for the decision AND at least one of the
valid measurement suspicions (SKILL.md Step 3) applies.

Return to SKILL.md Step 3 and walk the classification tree.
