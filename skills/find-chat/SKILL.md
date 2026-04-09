---
name: find-chat
description: Search Claude Code chat history by keyword and open matching session in a new terminal tab
---

# Find & Open Claude Code Chat

Search across ALL Claude Code session history using `claude-history` CLI (fuzzy search, cross-project). Falls back to manual index search if CLI unavailable.

## Input

The user's message is the search query. If empty, ask what they're looking for.

## Method 1: Interactive TUI (preferred)

If the user wants to browse/search interactively, launch `claude-history` directly:

```bash
claude-history
```

This opens a fuzzy-search TUI across all conversations. User can type to search, select, and view transcripts.

For local-only (current project):
```bash
claude-history --local
```

## Method 2: Non-interactive search + resume

When the user wants you to find and open a specific chat:

### Step 1: Search using session indexes

```bash
python3 -c "
import json, os, glob, sys
query = sys.argv[1].lower()
base = os.path.expanduser('~/.claude/projects')
results = []
for idx_file in glob.glob(os.path.join(base, '*/sessions-index.json')):
    project = os.path.basename(os.path.dirname(idx_file))
    try:
        with open(idx_file) as f:
            data = json.load(f)
        for entry in data.get('entries', []):
            summary = entry.get('summary', '') or ''
            first = entry.get('firstPrompt', '') or ''
            branch = entry.get('gitBranch', '') or ''
            sid = entry.get('sessionId', '')
            modified = entry.get('modified', '') or ''
            project_path = entry.get('projectPath', '') or project
            msgs = entry.get('messageCount', 0)
            combined = f'{summary} {first} {branch}'.lower()
            if query in combined:
                results.append({'id': sid, 'summary': summary, 'first': first[:200], 'branch': branch, 'modified': modified, 'project': project_path, 'msgs': msgs})
    except Exception:
        continue
results.sort(key=lambda x: x['modified'], reverse=True)
if not results:
    print('NO_RESULTS')
else:
    for i, r in enumerate(results[:15]):
        date = r['modified'][:10] if r['modified'] else 'unknown'
        print(f\"[{i+1}] {r['summary']}\")
        print(f\"    ID: {r['id']}\")
        print(f\"    Date: {date} | Branch: {r['branch']} | Msgs: {r['msgs']}\")
        print(f\"    Project: {r['project']}\")
        print()
    print('---JSON---')
    print(json.dumps(results[:15]))
" "SEARCH_QUERY"
```

### Step 2: Present results and let user pick

Show numbered list. Use `AskUserQuestion` for selection.

### Step 3: Open selected session

```bash
if [ -n "$TMUX" ]; then
    tmux new-window -n "cc-resumed" "cd '$PROJECT_PATH' && claude --resume '$SESSION_ID'; echo '--- Session ended ---'; read"
elif [ -d "/Applications/iTerm.app" ]; then
    osascript -e "
    tell application \"iTerm\"
        activate
        tell current window
            create tab with default profile
            tell current session
                write text \"cd '$PROJECT_PATH' && claude --resume '$SESSION_ID'\"
            end tell
        end tell
    end tell
    "
else
    osascript -e "
    tell application \"Terminal\"
        activate
        do script \"cd '$PROJECT_PATH' && claude --resume '$SESSION_ID'\"
    end tell
    "
fi
```

## Useful claude-history flags

- `claude-history` - interactive TUI with fuzzy search
- `claude-history --local` - only current project
- `claude-history -c` - resume selected conversation
- `claude-history --fork-session` - fork instead of resume
- `claude-history -t` - show tool calls
- `claude-history --show-thinking` - show thinking blocks
- `claude-history --pager` - pipe to less
- `claude-history -p` - print file path of selected conversation
- `claude-history -i` - print session ID of selected conversation

## Notes

- Always search ALL project directories under `~/.claude/projects/`
- Sort by most recently modified first
- Prefer iTerm2 > Terminal.app; tmux window if in tmux
- Search is case-insensitive, matches summary + first prompt + git branch
