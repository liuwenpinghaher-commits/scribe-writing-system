---
title: "Apple Notes"
url: "https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/apple/apple-apple-notes"
source: "Hermes Agent Docs"
crawled_at: "2026-07-09T15:47:42.185037+00:00"
---

Source: https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/apple/apple-apple-notes

# Apple Notes
Manage Apple Notes via memo CLI: create, search, edit.
## Skill metadata[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/apple/apple-apple-notes#skill-metadata "Direct link to Skill metadata")  
|   |   |  
| --- | --- |  
| Source  | Bundled (installed by default)  |  
| Path  | `skills/apple/apple-notes`  |  
| Version  | `1.0.0`  |  
| Author  | Hermes Agent  |  
| License  | MIT  |  
| Platforms  | macos  |  
| Tags  |  `Notes`, `Apple`, `macOS`, `note-taking`  |  
| Related skills  | [`obsidian`](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/note-taking/note-taking-obsidian)  |  
## Reference: full SKILL.md[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/apple/apple-apple-notes#reference-full-skillmd "Direct link to Reference: full SKILL.md")
info
The following is the complete skill definition that Hermes loads when this skill is triggered. This is what the agent sees as instructions when the skill is active.
# Apple Notes
Use `memo` to manage Apple Notes directly from the terminal. Notes sync across all Apple devices via iCloud.
## Prerequisites[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/apple/apple-apple-notes#prerequisites "Direct link to Prerequisites")
  * **macOS** with Notes.app
  * Install: `brew tap antoniorodr/memo && brew install antoniorodr/memo/memo`
  * Grant Automation access to Notes.app when prompted (System Settings → Privacy → Automation)

## When to Use[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/apple/apple-apple-notes#when-to-use "Direct link to When to Use")
  * User asks to create, view, or search Apple Notes
  * Saving information to Notes.app for cross-device access
  * Organizing notes into folders
  * Exporting notes to Markdown/HTML

## When NOT to Use[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/apple/apple-apple-notes#when-not-to-use "Direct link to When NOT to Use")
  * Obsidian vault management → use the `obsidian` skill
  * Bear Notes → separate app (not supported here)
  * Quick agent-only notes → use the `memory` tool instead

## Quick Reference[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/apple/apple-apple-notes#quick-reference "Direct link to Quick Reference")
### View Notes[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/apple/apple-apple-notes#view-notes "Direct link to View Notes")

```
memo notes                        # List all notes  
memo notes -f "Folder Name"       # Filter by folder  
memo notes -s "query"             # Search notes (fuzzy)  

```

### Create Notes[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/apple/apple-apple-notes#create-notes "Direct link to Create Notes")

```
memo notes -a                     # Interactive editor  
memo notes -a "Note Title"        # Quick add with title  

```

### Edit Notes[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/apple/apple-apple-notes#edit-notes "Direct link to Edit Notes")

```
memo notes -e                     # Interactive selection to edit  

```

### Delete Notes[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/apple/apple-apple-notes#delete-notes "Direct link to Delete Notes")

```
memo notes -d                     # Interactive selection to delete  

```

### Move Notes[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/apple/apple-apple-notes#move-notes "Direct link to Move Notes")

```
memo notes -m                     # Move note to folder (interactive)  

```

### Export Notes[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/apple/apple-apple-notes#export-notes "Direct link to Export Notes")

```
memo notes -ex                    # Export to HTML/Markdown  

```

## Limitations[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/apple/apple-apple-notes#limitations "Direct link to Limitations")
  * Cannot edit notes containing images or attachments
  * Interactive prompts require terminal access (use pty=true if needed)
  * macOS only — requires Apple Notes.app

## Rules[​](https://hermes-agent.nousresearch.com/docs/user-guide/skills/bundled/apple/apple-apple-notes#rules "Direct link to Rules")
  1. Prefer Apple Notes when user wants cross-device sync (iPhone/iPad/Mac)
  2. Use the `memory` tool for agent-internal notes that don't need to sync
  3. Use the `obsidian` skill for Markdown-native knowledge management
