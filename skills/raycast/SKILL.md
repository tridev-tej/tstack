---
name: raycast
description: Manage Raycast script commands - create, list, edit, run, delete scripts, open Raycast AI, search store, reload commands. Use when user asks to "create a raycast script", "list raycast commands", "add a raycast shortcut", "run a raycast script", "manage raycast", or any task involving Raycast script commands.
---

# Raycast - Script Command Manager

Manage Raycast script commands via the `raycast` CLI at `~/.local/bin/raycast`.
Scripts live in `~/raycast-scripts/` (already registered with Raycast).

## CLI Reference

```
raycast list                       # list all script commands with titles
raycast create <name> [mode]       # scaffold new script (mode: compact|silent|fullOutput)
raycast edit <name>                # open script in $EDITOR
raycast run <name> [args...]       # run a script directly
raycast cat <name>                 # print script contents
raycast delete <name>              # delete a script
raycast reload                     # reload scripts in Raycast app
raycast open [query]               # open Raycast (with optional search)
raycast ai <prompt>                # open Raycast AI chat
raycast ext <query>                # search Raycast extension store
raycast confetti                   # trigger confetti
```

## Workflow: Creating a New Script Command

1. Run `raycast create <name>` to scaffold
2. Read the created file and edit it with the user's requirements
3. Run `raycast reload` to pick it up in Raycast

## Script Command Template

Scripts must have Raycast metadata comments at the top:

```bash
#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title My Command Title
# @raycast.mode compact
# @raycast.packageName Custom

# Optional parameters:
# @raycast.icon 🔧
# @raycast.argument1 { "type": "text", "placeholder": "Input" }
# @raycast.argument2 { "type": "text", "placeholder": "Optional", "optional": true }

# Documentation:
# @raycast.description What this does
# @raycast.author the user

echo "output shown in Raycast"
```

### Mode Options
- `compact` - shows a single line of output in Raycast HUD
- `silent` - no output shown (fire and forget)
- `fullOutput` - opens a Raycast panel with full output
- `inline` - shows output in the command row itself (for menu bar style)

### Argument Types
- `text` - free text input
- `dropdown` - predefined options via `"data"` array

### Script Languages
Scripts can be bash, python, swift, applescript, ruby, or node. Set the shebang accordingly.

## Key Details

- Scripts directory: `~/raycast-scripts/`
- CLI location: `~/.local/bin/raycast`
- After creating/editing scripts, always run `raycast reload`
- Raycast deeplinks: `raycast://` URL scheme for opening specific features
- Script names use kebab-case (e.g., `my-cool-tool`)

## Existing Scripts

To see current scripts, run `raycast list`. Notable ones:
- `claude-agent` - launch Claude Code agent with a prompt in background
- `session-launcher` - launch coding sessions
- `meeting-mode` - toggle meeting mode
- `end-of-day` - end of day routine

## Common Patterns

### Background task with notification
```bash
(long-running-command > /tmp/output.txt 2>&1 && osascript -e 'display notification "Done" with title "Raycast"') &
echo "Launched"
```

### Clipboard integration
```bash
pbpaste | some-transform | pbcopy
echo "Transformed clipboard"
```

### Open URLs
```bash
open "https://example.com"
```

### AppleScript for macOS automation
```bash
osascript -e 'tell application "Finder" to ...'
```
