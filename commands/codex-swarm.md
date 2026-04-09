---
name: codex-swarm
description: Spawn a swarm of parallel Codex agents - break any task into subtasks, each agent runs codex exec independently
allowed-tools: ["Bash", "Read", "Grep", "Glob", "Task", "Write", "Edit", "AskUserQuestion"]
---

# Codex Swarm - Parallel Agent Orchestration

Spawn 2-6 Codex CLI agents in parallel, each tackling a subtask of a larger goal. You are the **orchestrator** - you decompose, delegate, collect, and synthesize.

## Input

User provides:
- A task description (what to accomplish)
- Optional: project path (defaults to cwd)
- Optional: mode override (analyze / implement)
- Optional: model override (default: gpt-5.3-codex)
- Optional: max agents (default: auto, 2-6)

## Phase 1: Task Decomposition

**THINK before spawning.** Read relevant files to understand scope, then break the task into independent subtasks.

Rules for decomposition:
- Each subtask MUST be independently executable (no dependencies between agents)
- Each subtask should target different files/areas when possible
- Prefer 3-4 agents for most tasks, 5-6 only for very large scope
- 2 agents minimum (otherwise just do it yourself, no swarm needed)

Output a task table before spawning:

```
## Swarm Plan: {task summary}
| Agent | Subtask | Mode | Target Files/Area |
|-------|---------|------|-------------------|
| codex-1 | {description} | {analyze/implement} | {files or area} |
| codex-2 | {description} | {analyze/implement} | {files or area} |
| codex-3 | {description} | {analyze/implement} | {files or area} |
```

## Phase 2: Spawn Agents

Launch ALL agents simultaneously using the Task tool with `run_in_background: true`.

Each agent is a `Bash` subagent that runs codex exec. Use this template for each:

### Agent Prompt Template

```
Run the following codex command and return the FULL output:

cd {PROJECT_PATH} && codex exec {FLAGS} "{PROMPT}"

If the command fails, retry once with --dangerously-bypass-approvals-and-sandbox flag.
Return the complete output including any file changes made.
```

### Codex Flags by Mode

**Analyze mode** (read-only, safe):
```bash
codex exec --dangerously-bypass-approvals-and-sandbox -s read-only "{prompt}"
```

**Implement mode** (can write files):
```bash
codex exec --full-auto "{prompt}"
```

**Implement mode (unsafe, for complex changes):**
```bash
codex exec --dangerously-bypass-approvals-and-sandbox "{prompt}"
```

### Model Selection

- Default: `gpt-5.3-codex` (already set in config, no flag needed)
- For heavy reasoning: add `-c 'model="o3"'`
- For max context: add `-c 'model="gpt-5.1-codex-max"'`
- For speed: add `-c 'model="gpt-5.3-codex-spark"'`

### Prompt Engineering for Each Agent

Each agent prompt MUST include:
1. **TASK**: One clear sentence of what to do
2. **SCOPE**: Which files/directories to focus on
3. **CONSTRAINTS**: What NOT to touch, patterns to follow
4. **OUTPUT**: What to return (findings, code changes, analysis)

Example agent prompt:
```
TASK: Review all error handling in the authentication module for exception suppression.
SCOPE: apps/accounts/ and apps/users/ directories only.
CONSTRAINTS: Do not modify any files. Report only - no fixes.
OUTPUT: For each issue found, report: file path, line number, the problem, and suggested fix. Format as a numbered list.
```

## Phase 3: Collect Results

Wait for ALL background agents to complete. Use TaskOutput to read each agent's result.

If an agent fails:
- Check the error output
- Retry ONCE with adjusted flags (e.g., add --dangerously-bypass-approvals-and-sandbox)
- If still failing, note the failure and continue with other results

## Phase 4: Synthesize

Merge all agent outputs into a single coherent response:

### For Analysis Tasks
```
## Swarm Results: {task}

### Agent Summary
| Agent | Status | Findings |
|-------|--------|----------|
| codex-1 | done | {count} findings |
| codex-2 | done | {count} findings |

### Combined Findings
{deduplicated, merged findings from all agents}

### Cross-Agent Insights
{patterns that appear across multiple agents' results}
```

### For Implementation Tasks
```
## Swarm Results: {task}

### Agent Summary
| Agent | Status | Files Changed |
|-------|--------|---------------|
| codex-1 | done | file1.py, file2.py |
| codex-2 | done | file3.ts |

### Changes Made
{list of all changes by file}

### Verification Needed
{any conflicts between agents, files touched by multiple agents}
```

**CRITICAL for implementation:** If two agents modified the same file, flag the CONFLICT immediately. Do NOT silently overwrite. Show both versions and ask the user to resolve.

## Phase 5: Verify (Implementation Mode Only)

After all agents complete implementation:

1. Run `git diff` to see all changes
2. Run project linter/formatter if available
3. Run tests if available
4. Report any issues

## Common Swarm Patterns

### Codebase Review Swarm
Break by module/directory - each agent reviews a different area:
```
codex-1: Review apps/accounts/ for security issues
codex-2: Review apps/threat_intel/ for error handling
codex-3: Review apps/integration/ for API safety
codex-4: Review apps/commons/ for shared utility bugs
```

### Feature Implementation Swarm
Break by layer - each agent handles a different concern:
```
codex-1: Write the database models and migrations
codex-2: Write the API views and serializers
codex-3: Write the React components
codex-4: Write the tests
```

### Bug Investigation Swarm
Break by hypothesis - each agent tests a different theory:
```
codex-1: Check if the bug is in data serialization
codex-2: Check if the bug is in async task handling
codex-3: Check if the bug is in database queries
```

### Refactoring Swarm
Break by file/module - each agent refactors independently:
```
codex-1: Refactor file_a.py to use new pattern
codex-2: Refactor file_b.py to use new pattern
codex-3: Update all tests for new pattern
```

## Constraints

- Max 6 agents (diminishing returns beyond this)
- Min 2 agents (otherwise no swarm needed)
- Each codex exec has a ~10 min timeout
- codex exec MUST run inside a git repo
- For Docker projects: agents run codex on host, NOT inside containers
- NEVER spawn agents that depend on each other's output

## Error Handling

| Error | Recovery |
|-------|----------|
| codex not found | Tell user to install: `npm i -g @openai/codex` |
| Not a git repo | Tell user to cd into a git repo or use `-C path` |
| Agent timeout | Kill and report partial results |
| Rate limit | Stagger remaining agents with 10s delays |
| Conflicting changes | Flag and present both versions to user |
