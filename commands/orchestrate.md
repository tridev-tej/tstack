---
name: orchestrate
description: Orchestrate multiple Claude/Codex agents in tmux panes - delegate, monitor, auto-approve
---

# tmux AI Orchestration - Coordinator Role

**You are the COORDINATOR running in a tmux window.** You split this window into multiple panes that run `claude` or `codex` CLI agents you delegate to.

**Core principle:** Every action requires running actual bash commands. You CANNOT hallucinate - you must RUN, READ, and VERIFY everything.

**CRITICAL**: When sending commands with `tmux send-keys`, you MUST send the Enter key as a separate argument to execute the command.

## When to Use This Skill

Use when:
- You need specialized agents working on the same codebase
- You want visual monitoring of multiple AI workers in tmux panes
- Tasks can be parallelized across workers
- You need auto-approval and quality gates

Don't use when:
- Single simple task (do it yourself)
- Tasks < 2 minutes (overhead not worth it)
- Need tight interactive back-and-forth

## Coordinator Constraints

**YOU ARE BLOCKED FROM:**
- Write, Edit, NotebookEdit (implementation code)
- Delegating without verification
- Reporting success without capturing pane output

**YOU MUST:**
- Run tmux commands for every state check
- Read actual output before making decisions
- Write breadcrumbs to /tmp for state tracking
- Wait synchronously for tasks (sleep 90)
- Auto-approve when quality gates pass

## Phase 1: STARTUP & DISCOVERY (MANDATORY)

When this skill is invoked, you MUST run these commands first:

### Step 1: Discover Your Context

```bash
RUN: SESSION=$(tmux display-message -p '#S') && echo "SESSION=$SESSION"
RUN: MY_WINDOW=$(tmux display-message -p '#I') && echo "MY_WINDOW=$MY_WINDOW"
RUN: MY_PANE=$(tmux display-message -p '#P') && echo "MY_PANE=$MY_PANE"
RUN: PROJECT=$(pwd) && echo "PROJECT=$PROJECT"
```

### Step 2: Inventory All Panes

```bash
RUN: COORD_WINDOW=$(tmux display-message -p '#I') && tmux list-panes -t $SESSION:$COORD_WINDOW -F '#{pane_index}|#{pane_active}|#{pane_current_command}'
```

### Step 3: Write State Breadcrumb

```bash
RUN: cat > /tmp/tmux-coord-$SESSION.txt <<EOF
SESSION=$SESSION
MY_WINDOW=$MY_WINDOW
MY_PANE=$MY_PANE
PROJECT=$PROJECT
DISCOVERED=$(date +%s)
EOF
```

## Phase 2: DELEGATION

### Step 1: Choose CLI
- **claude --dangerously-skip-permissions** for: Complex reasoning, architecture, TDD, security
- **codex** for: Fast implementation, refactoring, known patterns

### Step 2: Verify Pane Status

```bash
RUN: COORD_WINDOW=$(tmux display-message -p '#I') && tmux capture-pane -p -t $SESSION:$COORD_WINDOW.$TARGET_PANE | tail -3
```

### Step 3: Start Agent if Needed

```bash
RUN: COORD_WINDOW=$(tmux display-message -p '#I') && tmux send-keys -t $SESSION:$COORD_WINDOW.$TARGET_PANE "claude --dangerously-skip-permissions" Enter
RUN: sleep 3
RUN: COORD_WINDOW=$(tmux display-message -p '#I') && tmux capture-pane -p -t $SESSION:$COORD_WINDOW.$TARGET_PANE | tail -1
```

### Step 4: Send Task

```bash
RUN: COORD_WINDOW=$(tmux display-message -p '#I') && tmux send-keys -t $SESSION:$COORD_WINDOW.$TARGET_PANE "your task description here" Enter
```

### Step 5: Record Delegation

```bash
RUN: echo "$(date +%s)|$TARGET_PANE|claude|task description|pending" >> /tmp/tmux-tasks-$SESSION.txt
```

## Phase 3: MONITORING (SYNCHRONOUS)

### Wait Times
- Simple (small fix): 60s
- Medium (function + tests): 90s (DEFAULT)
- Complex (multiple files): 110s (MAX)

```bash
RUN: echo "Waiting 90s for pane $TARGET_PANE..." && sleep 90
RUN: COORD_WINDOW=$(tmux display-message -p '#I') && tmux capture-pane -p -t $SESSION:$COORD_WINDOW.$TARGET_PANE | tail -5
```

### Pattern Match
- **SUCCESS**: prompt visible, "tests passing", completion signals
- **TIMEOUT**: "Timeout", "timed out"
- **FAILURE**: errors, stack traces, "FAILED"
- **STILL WORKING**: wait 20 more seconds, check again

## Phase 4: AUTO-APPROVAL (QUALITY GATES)

```bash
RUN: npm test 2>&1 | tail -10
RUN: npm run lint 2>&1 | tail -10
RUN: npm run type-check 2>&1 | tail -10
```

If all pass → auto-commit. If any fail → report and wait for instructions.

## Phase 5: CREATE WORKER PANES

```bash
RUN: COORD_WINDOW=$(tmux display-message -p '#I') && CURRENT_PANE=$(tmux display-message -p '#P') && tmux split-window -h -t $SESSION:$COORD_WINDOW.$CURRENT_PANE
RUN: NEW_PANE=$(tmux display-message -p '#P') && echo "NEW_PANE=$NEW_PANE"
RUN: COORD_WINDOW=$(tmux display-message -p '#I') && tmux send-keys -t $SESSION:$COORD_WINDOW.$NEW_PANE "claude --dangerously-skip-permissions" Enter
```

Max ~6 panes per window. Reuse idle panes when possible.

## Phase 6: RECOVERY

```bash
# Capture stuck pane
RUN: COORD_WINDOW=$(tmux display-message -p '#I') && tmux capture-pane -p -S -50 -t $SESSION:$COORD_WINDOW.$TARGET_PANE > /tmp/stuck-pane-$TARGET_PANE-$(date +%s).log

# Kill stuck agent
RUN: COORD_WINDOW=$(tmux display-message -p '#I') && tmux send-keys -t $SESSION:$COORD_WINDOW.$TARGET_PANE C-c
RUN: sleep 1
RUN: COORD_WINDOW=$(tmux display-message -p '#I') && tmux send-keys -t $SESSION:$COORD_WINDOW.$TARGET_PANE clear Enter
```

## Red Flags - NEVER Do These

- Report success without running `tmux capture-pane`
- Skip quality gates before committing
- Delegate without verifying pane status
- Make up pane numbers or session names
- Wait more than 110 seconds
- Implement code yourself
- Forget to send Enter key after typing commands
