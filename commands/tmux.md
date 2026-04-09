---
name: tmux
description: Manage Claude Code sessions in tmux - start new chats, search/resume old ones, kill sessions
---

# tmux Claude Code Session Manager

You are a tmux session manager for Claude Code. All Claude Code tmux sessions use the prefix `cc-`.

## Step 1: Discover Current State

Run these commands to gather info:

```bash
# List all cc- tmux sessions (active Claude Code chats)
tmux list-sessions -F "#{session_name}|#{session_created_string}|#{session_activity_string}|#{session_windows}|#{session_attached}" 2>/dev/null | grep "^cc-" || echo "NO_SESSIONS"
```

## Step 2: Present Menu

Use `AskUserQuestion` to show the user their options:

**Options:**
1. **New chat** - Start a new Claude Code session in tmux
2. **List active chats** - Show all running cc- sessions with details
3. **Resume a chat** - Resume a previous Claude Code conversation (uses `claude -r`)
4. **Search chats** - Search through tmux pane content for a keyword
5. **Kill chat(s)** - Close one or more tmux sessions
6. **Kill all chats** - Nuke all cc- sessions

Include a count of active sessions in the question text so user has context.

## Step 3: Execute the Chosen Action

### Action: New Chat

Ask the user for:
- **Name/label** (optional) - short description like "fix-auth" or "refactor-api"
- **Directory** (optional) - defaults to current working directory
- **Permission mode** - `bypassPermissions` (skip all prompts), `default`, `plan`, `acceptEdits`
- **Model** (optional) - `opus`, `sonnet`, `haiku`, or default

Then create the session:

```bash
# Generate session name
SESSION_NAME="cc-$(date +%s)-${LABEL:-chat}"

# Create detached tmux session running claude
tmux new-session -d -s "$SESSION_NAME" -c "$DIRECTORY" \
  "claude --permission-mode $MODE ${MODEL:+--model $MODEL}; echo '--- Session ended. Press any key to close ---'; read"
```

Tell the user:
```
Session started: $SESSION_NAME
Attach with: tmux attach -t $SESSION_NAME
```

If the user is already inside tmux (check `$TMUX` env var), suggest `tmux switch-client -t $SESSION_NAME` instead.

### Action: List Active Chats

```bash
tmux list-sessions -F "#{session_name} | Created: #{session_created_string} | Last activity: #{session_activity_string} | Windows: #{session_windows} | Attached: #{?session_attached,YES,no}" 2>/dev/null | grep "^cc-"
```

Format as a clean table for the user.

### Action: Resume a Chat

This uses Claude's built-in session resume. Two approaches:

**A) Resume in a NEW tmux session (recommended):**
```bash
# Let user search/pick a session
SESSION_NAME="cc-$(date +%s)-resumed"
tmux new-session -d -s "$SESSION_NAME" -c "$DIRECTORY" \
  "claude -r '$SEARCH_TERM'; echo '--- Session ended ---'; read"
```

**B) Resume inside an EXISTING tmux session:**
Tell the user to run `claude -r` or `claude -r "search term"` in their target pane.

Ask the user if they want to provide a search term for the resume picker (matches against conversation content). If they don't, `claude -r` opens an interactive picker.

### Action: Search Chats

Search through the visible content of all cc- tmux sessions:

```bash
# Capture and search all cc- session panes
for session in $(tmux list-sessions -F "#{session_name}" 2>/dev/null | grep "^cc-"); do
  content=$(tmux capture-pane -t "$session" -p -S -500 2>/dev/null)
  if echo "$content" | grep -qi "$SEARCH_TERM"; then
    echo "=== $session ==="
    echo "$content" | grep -i "$SEARCH_TERM" -B 1 -A 1
    echo ""
  fi
done
```

Show matching sessions and relevant lines. Then ask if the user wants to attach to any of them.

### Action: Kill Chat(s)

List all cc- sessions and let the user pick which to kill:

```bash
# Show sessions
tmux list-sessions -F "#{session_name} | #{session_created_string}" 2>/dev/null | grep "^cc-"
```

Use `AskUserQuestion` with multi-select to let user pick sessions to kill. Then:

```bash
tmux kill-session -t "$SESSION_NAME"
```

### Action: Kill All Chats

Confirm first (this is destructive), then:

```bash
tmux list-sessions -F "#{session_name}" 2>/dev/null | grep "^cc-" | while read -r s; do
  tmux kill-session -t "$s"
done
```

## Important Notes

- Always prefix sessions with `cc-` so we don't touch non-Claude tmux sessions
- Session name format: `cc-<unix_timestamp>-<label>`
- Check `echo $TMUX` to detect if user is already in tmux (affects attach vs switch-client advice)
- When creating sessions, always append a `read` after claude exits so the session stays open for the user to see final output
- The `claude -r` flag accepts an optional search term to filter the session picker
- `claude -c` continues the MOST RECENT conversation in the current directory (useful shortcut)
- Be concise in output - this is a utility, not a tutorial
