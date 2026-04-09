---
name: swarm-review
description: Orchestrate 6 parallel agents - Docker logs, frontend build, Codex CLI, Playwright UI testing, Opus 4.6 deep review, and live code validation
---

# Swarm Review: 6-Agent Parallel PR Review

Launch 6 specialized agents in parallel for maximum review coverage, then synthesize into one actionable report.

$ARGUMENTS

## Architecture

```
                         Swarm Orchestrator (you)
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │       INFRA (Phase 0.5) │                         │
        ▼                         ▼                         │
  ┌────────────┐           ┌────────────┐                   │
  │ Agent 0a   │           │ Agent 0b   │                   │
  │ Docker Logs│           │ npm-watch  │                   │
  │ make start │           │ Frontend   │                   │
  │            │           │ Build      │                   │
  │ Streams    │           │ Watches &  │                   │
  │ container  │           │ rebuilds   │                   │
  │ logs       │           │ JS/CSS     │                   │
  └────────────┘           └────────────┘                   │
        │                         │                         │
        └────────┬────────────────┘                         │
                 │ (wait ~15s for services to be ready)     │
                 ▼                                          ▼
  ┌──────────────────────────────────────────────────────────────┐
  │                    REVIEW (Phase 1)                          │
  │                                                              │
  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐
  │  │ Agent 1    │  │ Agent 2    │  │ Agent 3    │  │ Agent 4    │
  │  │ Codex CLI  │  │ Playwright │  │ Deep Review│  │ Validation │
  │  │ (GPT)      │  │ (UI Test)  │  │ (Opus 4.6) │  │ (Container)│
  │  │            │  │            │  │            │  │            │
  │  │ P1/P2/P3   │  │ Screenshots│  │ Logic/Sec  │  │ ruff/tests │
  │  │ findings   │  │ Console    │  │ Perf/Maint │  │ pyright    │
  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘
  └──────────────────────────────────────────────────────────────┘
                              │
                     Unified Review Report
                              │
                   (ask) Post to GitHub PR?
```

---

## Phase 0: Detect What to Review

Parse `$ARGUMENTS` to determine review target:

| Input | Action |
|-------|--------|
| PR number (e.g. `3721`) | `gh pr diff 3721`, `gh pr view 3721 --json title,body,headRefName,headRefOid,files` |
| Commit range (e.g. `HEAD~3..HEAD`) | `git diff HEAD~3..HEAD`, `git log --oneline HEAD~3..HEAD` |
| Nothing | Auto-detect: check `gh pr view` on current branch, fall back to `git diff HEAD` |

### Gather context (run these via Bash):

```bash
# Determine PR or commits
CURRENT_BRANCH=$(git branch --show-current)
PR_NUMBER=$(gh pr view --json number -q '.number' 2>/dev/null || echo "")

# Get changed files
CHANGED_FILES=$(gh pr diff $PR_NUMBER --name-only 2>/dev/null || git diff --name-only HEAD)

# Get full diff
DIFF_CONTENT=$(gh pr diff $PR_NUMBER 2>/dev/null || git diff HEAD)

# Separate backend vs frontend
BACKEND_FILES=$(echo "$CHANGED_FILES" | grep -E '\.py$' || true)
FRONTEND_FILES=$(echo "$CHANGED_FILES" | grep -E '\.(tsx?|jsx?|css)$' || true)

# PR metadata
COMMIT_SHA=$(gh pr view $PR_NUMBER --json headRefOid -q '.headRefOid' 2>/dev/null || git rev-parse HEAD)
PR_TITLE=$(gh pr view $PR_NUMBER --json title -q '.title' 2>/dev/null || echo "")

# Tenant name for local testing (default: app)
TENANT_NAME="app"
# Override from $ARGUMENTS if provided (e.g. "3721 --tenant qa")
```

---

## Phase 0.5: Launch Infra Agents

**Launch BEFORE review agents.** These start Docker and build frontend so the app is ready for Playwright and validation agents.

**CRITICAL: Send BOTH infra agent Task calls in a SINGLE message. Use `run_in_background: true` for each.**

### Agent 0a: Docker Logs

**subagent_type:** `Bash`
**run_in_background:** true

Starts the Docker containers and streams logs. Stays running throughout the review.

Prompt:

```
Start the Docker containers for the project and stream logs.

cd $PROJECT_DIR && make start

This is a long-running process - it will keep streaming docker logs.
Do NOT exit or ctrl-c. Let it run until killed.

If make start fails, try:
cd $PROJECT_DIR && docker compose up

If that also fails, output the error and exit.
```

---

### Agent 0b: Frontend Build (npm-watch)

**subagent_type:** `Bash`
**run_in_background:** true

Watches and rebuilds frontend assets. Stays running throughout the review.

Prompt:

```
Build and watch frontend assets for the project.

cd $PROJECT_DIR && make npm-watch

This is a long-running process - it watches for file changes and rebuilds JS/CSS.
Do NOT exit or ctrl-c. Let it run until killed.

If make npm-watch fails, try:
cd $PROJECT_DIR && cd react && npm run watch

If that also fails, output the error and exit.
```

---

### Wait for services

After launching infra agents, **sleep 15 seconds** to let Docker containers start and frontend build complete initial compilation:

```bash
sleep 15
```

Then proceed to Phase 1.

---

## Phase 1: Launch 4 Review Agents in Parallel

**CRITICAL: Send ALL 4 review agent Task calls in a SINGLE message. Use `run_in_background: true` for each.**

### Conditional logic BEFORE launching:

- **Skip Agent 2** if `$FRONTEND_FILES` is empty (no UI changes)
- **Skip Agent 1** if codex binary not found

---

### Agent 1: Codex CLI Review

**subagent_type:** `Bash`
**run_in_background:** true

Prompt:

```
Run the Codex CLI to review code changes in $PROJECT_DIR

Command:
cd $PROJECT_DIR && codex review --base main -c model="gpt-5.3-codex"

If that fails, try:
cd $PROJECT_DIR && codex review --commit {COMMIT_SHA}~{N}..{COMMIT_SHA}

Capture the FULL output. If codex is not installed or auth fails, output: "CODEX_UNAVAILABLE: {error message}"
```

---

### Agent 2: Playwright UI Testing

**subagent_type:** `general-purpose`
**run_in_background:** true

**SKIP if no frontend files changed.**

Prompt:

```
You are a UI testing agent. Test the application at http://{TENANT_NAME}.localhost:8000 using Playwright MCP tools.

IMPORTANT: Always launch in incognito mode using launchOptions: {"args": ["--incognito"]}

## Credentials:
- Email: <YOUR_TEST_EMAIL>
- Password: <YOUR_TEST_PASSWORD>

## Steps:

1. Navigate to http://{TENANT_NAME}.localhost:8000 using mcp__puppeteer__puppeteer_navigate (pass launchOptions: {"args": ["--incognito"]})
2. Take a screenshot with mcp__puppeteer__puppeteer_screenshot to see the login page
3. Fill in email field with: <YOUR_TEST_EMAIL> using mcp__puppeteer__puppeteer_fill
4. Fill in password field with: <YOUR_TEST_PASSWORD> using mcp__puppeteer__puppeteer_fill
5. Click the login/submit button using mcp__puppeteer__puppeteer_click
6. Wait for dashboard to load (take another screenshot to confirm)
7. Navigate to the pages affected by these file changes:

FRONTEND FILES CHANGED:
{$FRONTEND_FILES}

Page routing guide: map changed files to the relevant URL paths in your app. If unclear, test the main dashboard.

8. On each affected page:
   a. Take a screenshot (mcp__puppeteer__puppeteer_screenshot)
   b. Check for console errors (mcp__puppeteer__puppeteer_evaluate with script: "JSON.stringify(window.__console_errors || [])")
   c. Verify key elements render (no blank pages, no error screens)
   d. Click primary interactive elements to check they respond

9. If app is not running (connection refused), report SKIP - dont fail

## Output Format:

```
## UI Test Results

### Pages Tested
- {url}: PASS / FAIL / SKIP

### Console Errors
- {error} on {page}
(or "None")

### Visual Issues
- {description}
(or "None")

### Verdict: PASS / FAIL / SKIP
```
```

---

### Agent 3: Deep Code Review (Opus 4.6)

**subagent_type:** `general-purpose`
**model:** `opus`
**run_in_background:** true

Prompt:

```
You are a principal engineer performing a deep code review. Read every changed file IN FULL using the Read tool - not just the diff.

## Review Priorities (in order):

### 1. Correctness
- Logic errors, off-by-one, race conditions
- Null/None handling, missing error paths
- Variables used before definition in exception paths
- Type mismatches (.get() returning Optional used as concrete)

### 2. Security
- SQL injection, XSS, CSRF
- Auth/authz bypasses, IDOR
- Tenant isolation issues (django-tenants - schema isolation)
- Secrets in code, insecure defaults
- Input validation gaps at API boundaries

### 3. Performance
- N+1 queries (missing select_related/prefetch_related)
- Unbounded loops or querysets without limits
- Missing pagination on list endpoints
- Blocking calls in async paths

### 4. Error Handling Philosophy
- CRITICAL: Let errors surface. Do NOT swallow them
- Catch-all try/except = bug. Be specific about exceptions
- Returning empty results on failure instead of raising = bug
- print() should be logger

### 5. Patterns
- Dead code, unused imports
- DRY violations against existing codebase
- Missing type hints on new code
- Django: proper on_delete, proper manager usage

## Changed Files:
{$CHANGED_FILES}

## Diff:
{$DIFF_CONTENT}

## Instructions:
- Read each changed file FULLY with the Read tool to understand surrounding context
- Cross-reference with imports and callers when checking for issues
- Dont flag style nitpicks (formatting, naming conventions) - let linters handle that

## Output Format:

### Critical (Block Merge)
1. **{file}:{line}** [{category}] - {description}
   Fix: {suggestion}

### Important (Should Fix)
1. **{file}:{line}** [{category}] - {description}
   Fix: {suggestion}

### Minor (Nice to Fix)
1. **{file}:{line}** [{category}] - {description}

### Positive
- {1-2 things done well}

### Verdict: APPROVE / REQUEST CHANGES / NEEDS DISCUSSION
```

---

### Agent 4: Live Code Validation

**subagent_type:** `Bash`
**run_in_background:** true

Prompt:

```
You are a code validation agent. Run real checks against the actual codebase in the Docker container to catch issues that static review misses.

Working directory: $PROJECT_DIR

## Run these checks in order:

### 1. Django System Check
docker compose exec web python manage.py check --deploy 2>&1 || true

### 2. Migration Check (are there unapplied/missing migrations?)
docker compose exec web python manage.py makemigrations --check --dry-run 2>&1 || true

### 3. Linting on changed files
cd $PROJECT_DIR && make ruff 2>&1 || true

### 4. Type checking
cd $PROJECT_DIR && make pyright 2>&1 || true

### 5. Import validation - try importing each changed Python module
For each changed .py file, run:
docker compose exec web python -c "import {module_path}" 2>&1 || true

Convert file paths to module paths: apps/threat_intel/views.py → apps.threat_intel.views

### 6. Run relevant tests
Figure out which test files correspond to the changed files and run them:
- apps/threat_intel/* → docker compose exec web python -m pytest tests/test_alerts.py tests/test_investigations.py -x -v 2>&1 || true
- apps/users/* → docker compose exec web python -m pytest tests/test_users.py tests/test_rbac.py -x -v 2>&1 || true
- apps/integration/* → docker compose exec web python -m pytest tests/test_integrations.py -x -v 2>&1 || true
- apps/questionnaire/* → docker compose exec web python -m pytest tests/test_questionnaire.py -x -v 2>&1 || true
- If no specific test mapping, run: docker compose exec web python -m pytest tests/ -x --timeout=120 -v 2>&1 | head -100

### 7. Check for common issues
docker compose exec web python -c "
import django; django.setup()
# Check for broken foreign keys or model issues
from django.core.management import call_command
call_command('check', '--tag', 'models')
" 2>&1 || true

CHANGED FILES:
{$CHANGED_FILES}

CHANGED PYTHON FILES:
{$BACKEND_FILES}

## Important:
- If docker is not running, try: cd $PROJECT_DIR && docker compose up -d web
- If a check fails to RUN (not fails with findings), note it as SKIPPED
- Capture ALL output - truncate nothing
- Each check should run independently - dont stop on first failure

## Output Format:

```
## Live Validation Results

### Django System Check
{output or PASS}

### Migration Check
{output or PASS - no missing migrations}

### Linting (ruff)
{errors found or PASS}

### Type Checking (pyright)
{errors found or PASS}

### Import Validation
{failed imports or ALL PASS}

### Test Results
{test output - pass/fail counts}
Tests run: {N}, Passed: {N}, Failed: {N}, Errors: {N}

### Model Check
{output or PASS}

### Summary
- Checks passed: {N}/7
- Checks failed: {N}/7
- Checks skipped: {N}/7
- Blocking issues: {list or None}
```
```

---

## Phase 2: Collect Results

Read the output from all 6 background agents using the Read tool on their output files, or TaskOutput.

Wait for all 4 review agents to complete before synthesizing. The 2 infra agents (Docker logs, npm-watch) are long-running - **stop them** after review agents finish using TaskStop.

```
# After review agents complete:
TaskStop(task_id="agent_0a_docker_task_id")
TaskStop(task_id="agent_0b_npm_task_id")
```

---

## Phase 3: Synthesize Unified Report

### Dedup Rules
- Same file + same/nearby line + same issue from multiple agents = keep best explanation
- Note cross-validation: "[Found by: Codex + Opus]" = higher confidence
- Codex P1 + Opus Critical = P1. Codex P2 + Opus Critical = escalate to P1

### Output this report:

```
## Swarm Review: PR #{number} - {title}

### Agents
| Agent | Status | Findings |
|-------|--------|----------|
| Docker Logs (make start) | {RUNNING/FAIL} | {startup errors if any} |
| Frontend Build (npm-watch) | {RUNNING/FAIL} | {build errors if any} |
| Codex CLI (GPT) | {OK/FAIL/SKIP} | {count} |
| UI Testing (Playwright) | {PASS/FAIL/SKIP} | {count} |
| Deep Review (Opus 4.6) | {OK/FAIL} | {count} |
| Live Validation | {OK/FAIL} | {count checks failed} |

---

### P1: Critical (Must Fix)
1. **{file}:{line}** [{category}] [Found by: {agents}]
   {description}
   Fix: `{suggestion}`

### P2: Important (Should Fix)
1. **{file}:{line}** [{category}] [Found by: {agents}]
   {description}

### P3: Minor
1. **{file}:{line}** [{category}]
   {description}

### UI Test Results
{from Agent 2 - or "Skipped (no frontend changes)"}

### Validation Results
{from Agent 4 - summary of checks}

---

| Metric | Count |
|--------|-------|
| Files reviewed | {N} |
| P1 | {N} |
| P2 | {N} |
| P3 | {N} |
| Cross-validated | {N} |
| Tests passing | {N/N} |

### Verdict: {APPROVE / REQUEST CHANGES / NEEDS DISCUSSION}
```

---

## Phase 4: Ask About Posting to GitHub

After showing the report, ask:

"want me to post these as inline PR comments?"

Options:
- Post P1 + P2 as inline comments
- Post all findings
- Skip

### Comment Style (the user voice)
- all lowercase, no punctuation
- casual and direct
- include code snippets for fixes

### Posting method:
```bash
gh api repos/{owner}/{repo}/pulls/$PR_NUMBER/comments \
  -X POST \
  -f body='{comment}' \
  -f path='{file}' \
  -f commit_id="$COMMIT_SHA" \
  -F line={line_number} \
  -f side="RIGHT"
```

---

## Error Recovery

| Agent | If it fails | Action |
|-------|-------------|--------|
| Docker Logs | make start fails | Try `docker compose up` directly, if still fails note in report |
| npm-watch | make npm-watch fails | Try `cd react && npm run watch`, if still fails note in report |
| Codex CLI | Auth expired, binary missing | Skip, note in report |
| Playwright | App not running | Skip, note in report (infra agents should prevent this) |
| Opus Review | Context too large | Split by directory, review backend only |
| Validation | Docker not running | Skip - infra agent should have started it |

The review is still valuable even if 1-2 agents fail. Always produce a report with whatever agents succeeded.

**Infra agent failures are non-blocking for Codex and Opus review** - those agents only need the code, not a running app. Only Playwright and Validation depend on running containers.
