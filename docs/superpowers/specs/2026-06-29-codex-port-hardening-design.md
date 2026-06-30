# Codex Port Hardening Design

## Context

Virtuoso is being ported from a Claude-first plugin into a Codex-compatible plugin while preserving its core governance and dispatch behavior. Recent work added `.codex-plugin/plugin.json`, introduced selectable workspace layouts, and changed non-init skills so first-time workspace setup routes through `virtuoso-init` instead of silently creating project documentation.

The Superpowers `porting-to-a-new-harness.md` guide adds a stricter portability frame: a harness port is complete only when startup behavior, install delivery, version tracking, tests, and live acceptance behavior are all explicit and verified.

## Goals

- Make the Codex plugin manifest a first-class install surface for Virtuoso.
- Ensure Codex startup behavior is explicit, testable, and safe.
- Preserve the rule that only `virtuoso-init` can create a first-time workspace.
- Keep Codex-specific adaptation out of general skill bodies where possible.
- Add tests that prevent harness-port regressions.
- Document the manual Codex acceptance flow needed before release.

## Non-Goals

- Do not change Virtuoso skill semantics beyond harness-port requirements.
- Do not edit user-level Codex configuration, shell profiles, or global instruction files.
- Do not create project documentation during plugin install or session startup.
- Do not implement a full marketplace publishing pipeline in this pass.
- Do not require a live Codex UI test to run in automated CI.

## Proposed Architecture

Use a small Codex harness layer alongside the existing Claude plugin layer:

- `.codex-plugin/plugin.json` is the Codex manifest and points at the shared `skills/` directory.
- The Codex manifest points at `./hooks/hooks-codex.json`.
- `hooks/hooks-codex.json` uses the Codex hook schema and calls an installed hook command.
- The hook command runs `virtuoso_preflight.py --mode detect --quiet`, which heals only existing Virtuoso workspaces and skips unrelated or first-time projects.
- `virtuoso-init` remains the only direct first-time creation path and owns the layout choice.
- `Virtuoso/workspace-layout.json` remains the source of truth for project workspace paths after initialization.

This keeps install-time and session-start behavior safe: Codex can load the plugin and optionally heal existing Virtuoso projects, but it cannot silently create a documentation tree in a plugin repo or arbitrary project.

## Components

### Codex Manifest

Update `.codex-plugin/plugin.json` to match the Codex reference shape from Superpowers:

- Keep `name`, `version`, metadata, `skills`, and `interface`.
- Add `hooks` with value `./hooks/hooks-codex.json`.
- Avoid unsupported fields.
- Keep referenced paths relative to the plugin root.

### Version Tracking

Update `.version-bump.json` so version bump tooling tracks `.codex-plugin/plugin.json` alongside the Claude manifest and marketplace entry. This prevents release drift where Claude and Codex install surfaces advertise different versions.

### Codex Hook Layer

Add a Codex hook configuration for full hook parity:

- `hooks/hooks-codex.json` registers a `SessionStart` hook using Codex's expected JSON shape.
- The hook command must be quoted safely for plugin paths with spaces.
- The hook must use `detect`, not `create`.
- The hook must be safe when no workspace exists.

Add or adapt a wrapper in the same style as Superpowers' `run-hook.cmd` so Windows and Unix paths both work.

### Skill Instructions

Keep the current manifest-first path rule:

- Skills read `Virtuoso/workspace-layout.json`.
- Skills route missing first-time workspaces to `virtuoso-init`.
- Only `virtuoso-init` uses `--mode create`.

Avoid Codex tool-name rewrites inside skill bodies. If a Codex-specific action mapping is needed later, add a reference file rather than editing every skill for Codex.

### Tests

Add automated tests for the harness contract:

- Codex manifest is valid JSON and includes required fields.
- Codex manifest version matches Claude plugin version.
- `.version-bump.json` tracks the Codex manifest version path.
- `.codex-plugin/plugin.json` references `hooks/hooks-codex.json`.
- Codex hook config uses `SessionStart` and runs `detect`, not `create`.
- Existing guard remains: only `virtuoso-init` can call `--mode create`.
- Preflight layout tests continue to prove plugin-only and canonical layouts are non-destructive.

### Manual Acceptance Documentation

Add a short Codex acceptance section to docs or README describing:

1. Install Virtuoso from the local plugin checkout.
2. Start a clean Codex session in a disposable project.
3. Confirm Virtuoso skills are discoverable.
4. Invoke a first-time workflow such as roadmap status.
5. Verify it routes to `virtuoso-init` for the layout choice before creating folders.
6. Run `virtuoso-init`, choose a layout, and confirm `workspace-layout.json` plus expected directories are created.
7. Restart or resume the session and confirm detect-mode preflight heals the existing workspace without asking again.

This manual transcript is release evidence, not an automated unit test.

## Error Handling

- If the Codex hook cannot find the plugin root, it should exit cleanly and avoid modifying files.
- If the project has no Virtuoso workspace, detect mode reports no workspace and exits without creating one.
- If `.codex-plugin/plugin.json` references a missing hook file, tests fail.
- If version fields drift across manifests, tests fail.
- If a non-init skill reintroduces `--mode create`, the existing guard test fails.

## Testing Strategy

Use fast repository tests for static and behavioral guarantees:

- `python -m pytest -q`
- `python scripts/validate.py`
- Codex plugin manifest validation through the plugin creator validator.

The live Codex acceptance run is performed manually because it depends on the installed desktop or CLI harness state.

## Risks

- Codex hook schema may differ from the Superpowers reference in the current installed Codex version. Mitigation: copy the live reference shape, add tests for the expected JSON, and verify manually in Codex.
- A hook command may behave differently on Windows paths with spaces. Mitigation: quote paths and test from this repo path.
- Adding a hook before proving Codex needs it may introduce extra moving parts. Mitigation: keep the hook detect-only and non-destructive.
- Manual acceptance can be skipped during release pressure. Mitigation: document it as a release gate and keep the checklist short.

## Recommendation

Implement the full Codex hook parity path, but keep the hook strictly detect-only. This gives Virtuoso an explicit and testable Codex startup surface while preserving the safety rule that first-time project setup always goes through `virtuoso-init` and its layout choice.
