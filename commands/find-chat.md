---
name: find-chat
description: Search Claude Code chat history by keyword and open matching session in a new terminal tab
---

# Find & Open Claude Code Chat

Search across ALL Claude Code session history (every project) by keyword, show matches, and open the selected one in a new terminal tab.

## Input

The user's message is the search query. If empty, ask what they're looking for.

## Step 1: Search All Session Indexes

Run this script to find matching sessions across all projects:

```bash
python3 << 'PYEOF'
import json, os, glob, sys

query = sys.argv[1].lower() if len(sys.argv) > 1 else ""
if not query:
    print("NO_QUERY")
    sys.exit(0)

base = os.path.expanduser("~/.claude/projects")
results = []

for idx_file in glob.glob(os.path.join(base, "*/sessions-index.json")):
    project = os.path.basename(os.path.dirname(idx_file))
    try:
        with open(idx_file) as f:
            data = json.load(f)
        for entry in data.get("entries", []):
            summary = entry.get("summary", "") or ""
            first = entry.get("firstPrompt", "") or ""
            branch = entry.get("gitBranch", "") or ""
            sid = entry.get("sessionId", "")
            modified = entry.get("modified", "") or ""
            project_path = entry.get("projectPath", "") or ""
            msgs = entry.get("messageCount", 0)
            combined = f"{summary} {first} {branch}".lower()
            if query in combined:
                results.append({
                    "id": sid,
                    "summary": summary,
                    "first": first[:200],
                    "branch": branch,
                    "modified": modified,
                    "project": project_path or project,
                    "msgs": msgs
                })
    except Exception:
        continue

# Sort by modified date descending
results.sort(key=lambda x: x["modified"], reverse=True)

if not results:
    print("NO_RESULTS")
else:
    for i, r in enumerate(results[:15]):
        date = r["modified"][:10] if r["modified"] else "unknown"
        print(f"[{i+1}] {r['summary']}")
        print(f"    ID: {r['id']}")
        print(f"    Date: {date} | Branch: {r['branch']} | Messages: {r['msgs']}")
        print(f"    Project: {r['project']}")
        print(f"    First: {r['first'][:120]}")
        print()

# Also dump as JSON for parsing
print("---JSON---")
print(json.dumps(results[:15]))
PYEOF
```

Pass the user's search query as the argument to the script.

## Step 2: Present Results

If `NO_QUERY` - ask the user what they want to search for using `AskUserQuestion`.

If `NO_RESULTS` - tell the user no matching sessions found. Suggest trying different keywords.

If results found, present them as a numbered list with:
- Summary
- Date modified
- Git branch
- Message count
- First prompt preview

Use `AskUserQuestion` to let the user pick which session to open. Options should be the top matches (up to 4).

## Step 3: Open in New Terminal Tab

Once the user picks a session, open it using the correct project directory:

```bash
# Check if inside tmux
if [ -n "$TMUX" ]; then
    # Create new tmux window and resume there
    tmux new-window -n "cc-resumed" "cd '$PROJECT_PATH' && claude --resume '$SESSION_ID'; echo '--- Session ended ---'; read"
else
    # Open in a new macOS Terminal tab using osascript
    osascript -e "
    tell application \"Terminal\"
        activate
        do script \"cd '$PROJECT_PATH' && claude --resume '$SESSION_ID'\"
    end tell
    "
fi
```

Replace `$SESSION_ID` with the chosen session ID and `$PROJECT_PATH` with the project path from the search results.

**iTerm2 alternative** (detect and prefer if available):
```bash
if [ -d "/Applications/iTerm.app" ] && [ -z "$TMUX" ]; then
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
fi
```

## Step 4: Confirm

Tell the user which session was opened and in what context (tmux window / terminal tab).

## Important Notes

- Always search ALL project directories under `~/.claude/projects/`
- Sort results by most recently modified first
- Cap results at 15 to avoid overwhelming output
- The search is case-insensitive and matches against summary, first prompt, and git branch
- If the user provides multiple words, search for the full phrase
- Prefer iTerm2 over Terminal.app if available
- If in tmux, create a new window instead of a terminal tab
