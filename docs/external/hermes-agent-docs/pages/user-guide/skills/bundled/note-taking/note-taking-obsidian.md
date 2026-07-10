---
title: "Obsidian"
url: "https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/note-taking/note-taking-obsidian"
source: "Hermes Agent Docs"
crawled_at: "2026-07-09T15:47:42.185037+00:00"
---

Source: https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/note-taking/note-taking-obsidian

# Obsidian
Read, search, create, and edit notes in the Obsidian vault.
## Skill metadata[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/note-taking/note-taking-obsidian#skill-metadata "Direct link to Skill metadata")  
|   |   |  
| --- | --- |  
| Source  | Bundled (installed by default)  |  
| Path  | `skills/note-taking/obsidian`  |  
| Platforms  | linux, macos, windows  |  
## Reference: full SKILL.md[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/note-taking/note-taking-obsidian#reference-full-skillmd "Direct link to Reference: full SKILL.md")
info
The following is the complete skill definition that Hermes loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
# Obsidian Vault
Use this skill for filesystem-first Obsidian vault work: reading notes, listing notes, searching note files, creating notes, appending content, and adding wikilinks.
## Vault path[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/note-taking/note-taking-obsidian#vault-path "Direct link to Vault path")
Use a known or resolved vault path before calling file tools.
The documented vault-path convention is the `OBSIDIAN_VAULT_PATH` environment variable, for example from `${HERMES_HOME:-~/.hermes}/.env`. If it is unset, use `~/Documents/Obsidian Vault`.
File tools do not expand shell variables. Do not pass paths containing `$OBSIDIAN_VAULT_PATH` to `read_file`, `write_file`, `patch`, or `search_files`; resolve the vault path first and pass a concrete absolute path. Vault paths may contain spaces, which is another reason to prefer file tools over shell commands.
If the vault path is unknown, `terminal` is acceptable for resolving `OBSIDIAN_VAULT_PATH` or checking whether the fallback path exists. Once the path is known, switch back to file tools.
## Read a note[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/note-taking/note-taking-obsidian#read-a-note "Direct link to Read a note")
Use `read_file` with the resolved absolute path to the note. Prefer this over `cat` because it provides line numbers and pagination.
## List notes[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/note-taking/note-taking-obsidian#list-notes "Direct link to List notes")
Use `search_files` with `target: "files"` and the resolved vault path. Prefer this over `find` or `ls`.
  * To list all markdown notes, use `pattern: "*.md"` under the vault path.
  * To list a subfolder, search under that subfolder's absolute path.

## Search[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/note-taking/note-taking-obsidian#search "Direct link to Search")
Use `search_files` for both filename and content searches. Prefer this over `grep`, `find`, or `ls`.
  * For filenames, use `search_files` with `target: "files"` and a filename `pattern`.
  * For note contents, use `search_files` with `target: "content"`, the content regex as `pattern`, and `file_glob: "*.md"` when you want to restrict matches to markdown notes.

## Create a note[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/note-taking/note-taking-obsidian#create-a-note "Direct link to Create a note")
Use `write_file` with the resolved absolute path and the full markdown content. Prefer this over shell heredocs or `echo` because it avoids shell quoting issues and returns structured results.
## Append to a note[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/note-taking/note-taking-obsidian#append-to-a-note "Direct link to Append to a note")
Prefer a native file-tool workflow when it is not awkward:
  * Read the target note with `read_file`.
  * Use `patch` for an anchored append when there is stable context, such as adding a section after an existing heading or appending before a known trailing block.
  * Use `write_file` when rewriting the whole note is clearer than constructing a fragile patch.

For an anchored append with `patch`, replace the anchor with the anchor plus the new content.
For a simple append with no stable context, `terminal` is acceptable if it is the clearest safe option.
## Targeted edits[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/note-taking/note-taking-obsidian#targeted-edits "Direct link to Targeted edits")
Use `patch` for focused note changes when the current content gives you stable context. Prefer this over shell text rewriting.
## Wikilinks[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/note-taking/note-taking-obsidian#wikilinks "Direct link to Wikilinks")
Obsidian links notes with `[[Note Name]]` syntax. When creating notes, use these to link related content.
