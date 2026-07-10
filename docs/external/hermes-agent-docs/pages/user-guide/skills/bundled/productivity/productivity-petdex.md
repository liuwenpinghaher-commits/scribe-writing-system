---
title: "Petdex"
url: "https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/productivity/productivity-petdex"
source: "Hermes Agent Docs"
crawled_at: "2026-07-09T15:47:42.185037+00:00"
---

Source: https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/productivity/productivity-petdex

# Petdex
Install and select animated petdex mascots for Hermes.
## Skill metadata[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/productivity/productivity-petdex#skill-metadata "Direct link to Skill metadata")  
|   |   |  
| --- | --- |  
| Source  | Bundled (installed by default)  |  
| Path  | `skills/productivity/petdex`  |  
| Version  | `1.0.0`  |  
| Author  | Hermes Agent  |  
| License  | MIT  |  
| Platforms  | linux, macos, windows  |  
| Tags  |  `petdex`, `mascot`, `display`, `cli`, `tui`, `desktop`  |  
## Reference: full SKILL.md[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/productivity/productivity-petdex#reference-full-skillmd "Direct link to Reference: full SKILL.md")
info
The following is the complete skill definition that Hermes loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
# Petdex Skill
Browse, install, and select animated "pet" mascots from the public [petdex](https://github.com/crafter-station/petdex) gallery. An installed pet reacts to agent activity (idle, running a tool, reviewing, error, done) across the Hermes CLI, TUI, and desktop app. This skill drives the `hermes pets` CLI and the `display.pet` config — it does not generate sprites.
## When to Use[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/productivity/productivity-petdex#when-to-use "Direct link to When to Use")
  * The user wants a desktop/terminal mascot or asks about "pets" / petdex.
  * The user wants to change, preview, or disable the active pet.
  * Diagnosing why a pet isn't showing (terminal graphics support, config).

## Prerequisites[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/productivity/productivity-petdex#prerequisites "Direct link to Prerequisites")
  * Network access to `petdex.dev` for the gallery/manifest (read-only, no auth).
  * Pillow (a core Hermes dependency) for sprite decoding — already installed.
  * For full-fidelity terminal rendering: a graphics-capable terminal (kitty, Ghostty, WezTerm, iTerm2, or sixel). Otherwise a truecolor Unicode half-block fallback is used automatically.

## How to Run[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/productivity/productivity-petdex#how-to-run "Direct link to How to Run")
Use the `terminal` tool to run `hermes pets <subcommand>`.
## Quick Reference[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/productivity/productivity-petdex#quick-reference "Direct link to Quick Reference")  
| Goal  | Command  |  
| --- | --- |  
| Browse the gallery  |  `hermes pets list` (add a substring to filter: `hermes pets list cat`)  |  
| List installed pets  | `hermes pets list --installed`  |  
| Install a pet  |  `hermes pets install <slug>` (add `--select` to make it active)  |  
| Set the active pet  |  `hermes pets select <slug>` (omit slug for a picker)  |  
| Resize the pet everywhere  |  `hermes pets scale <factor>` (e.g. `0.5`, clamped 0.1–3.0)  |  
| Preview/animate in terminal  | `hermes pets show [slug] [--cycle] [--state run]`  |  
| Disable the pet  | `hermes pets off`  |  
| Remove a pet  | `hermes pets remove <slug>`  |  
| Diagnose setup  | `hermes pets doctor`  |  
## Procedure[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/productivity/productivity-petdex#procedure "Direct link to Procedure")
  1. Find a pet: `hermes pets list <query>` and note its `slug`.
  2. Install + activate: `hermes pets install <slug> --select`.
  3. Preview it: `hermes pets show` (Ctrl+C to stop).
  4. Confirm setup: `hermes pets doctor` — shows the resolved pet, configured render mode, detected terminal graphics protocol, and effective mode.

Pets install into `<HERMES_HOME>/pets/<slug>/` (profile-aware). Selecting a pet writes `display.pet.slug` + `display.pet.enabled` to `config.yaml`.
## Configuration[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/productivity/productivity-petdex#configuration "Direct link to Configuration")
Under `display.pet` in `config.yaml`:
  * `enabled` (bool) — master on/off.
  * `slug` (str) — active pet; empty = first installed.
  * `render_mode` — `auto` (detect) | `kitty` | `iterm` | `sixel` | `unicode` | `off`.
  * `scale` (float) — on-screen size of the native 192×208 frames (default 0.33, clamped 0.1–3.0). One knob resizes every surface; set it with `hermes pets scale <factor>`, the `/pet scale` slash command, or the desktop Appearance slider.
  * `unicode_cols` (int) — width in columns for the Unicode fallback.

## Pitfalls[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/productivity/productivity-petdex#pitfalls "Direct link to Pitfalls")
  * A pet only shows once one is installed AND selected (`enabled: true`).
  * Inside a pipe/redirect (no TTY) terminal rendering is disabled by design.
  * The petdex npm CLI installs to `~/.codex/pets`; Hermes uses its own profile-scoped `<HERMES_HOME>/pets/` instead — install through `hermes pets`.

## Verification[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/productivity/productivity-petdex#verification "Direct link to Verification")
  * `hermes pets doctor` reports `✓ ready` when a pet is installed, selected, enabled, and Pillow is importable.
