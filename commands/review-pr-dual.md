---
description: "Review PR with dual-model validation (Codex GPT 5.4 + Opus 4.6) - parallel agents, cross-validated findings"
allowed-tools: ["Bash", "Read", "Grep", "Glob", "Task", "AskUserQuestion", "Skill"]
---

# Dual-Model PR Review Protocol

Review a GitHub PR using both Codex CLI (GPT 5.4) and Opus 4.6 in parallel, cross-validate every finding, and present final comments in the user's style.

### CRITICAL RULES (NON-NEGOTIABLE)
- **NEVER post comments to GitHub without explicit user approval.** Always show the full comment text and API call first, then wait for "yes"/"post"/"go ahead" before executing.
- **Before posting new comments, clean up stale/outdated comments** from previous reviews on the same PR. Check `gh api repos/{REPO}/pulls/{PR_NUMBER}/comments` for existing comments by your-username and delete any that are no longer relevant (resolved, outdated by new commits, or superseded by new findings).
- **Present comments one by one** for approval - never batch post multiple comments at once.

## Input

The user provides a PR URL or PR number + repo. Extract:
- `PR_NUMBER`: the pull request number
- `REPO`: owner/repo (e.g., `your-org/your-repo`)

If only a URL is given, parse both from it.

---

## Senior Reviewer Checklist (MANDATORY)

These are the senior-reviewer patterns both review agents MUST check for on every PR. See `skills/code-review-senior-guidelines.md` for the full reference.

### 1. Don't Suppress Exceptions (HIGHEST PRIORITY)
- **NEVER** wrap DB queries or API calls in try/except that swallows errors
- If a DB query fails, the job should fail - don't return None/empty and silently continue
- Don't catch `Exception` broadly and log-then-continue
- Let exceptions bubble up to the caller
- Only catch specific, anticipated validation errors

### 2. Use Bracket Access, Not .get() for Required Keys
- If a key MUST exist, use `dict["key"]` not `dict.get("key", "")`
- `.get("key", "")` with empty string default hides missing data - it will silently pass bad data downstream
- If the key might not exist, handle it explicitly (skip or raise), don't default to ""

### 3. Correct Status Codes
- Don't assume all errors are 500
- If something "should never happen" -> assert (5xx), don't raise DoesNotExist (4xx)
- Use the actual status_code from responses, don't hardcode assumptions

### 4. Question Assumptions & Defensive Code
- Challenge EVERY defensive check: "When would this happen?"
- If a condition is impossible, use assert not if/else
- Don't add code for hypothetical scenarios that can't occur

### 5. Type Safety
- Fix pyright errors, don't add `# type: ignore` to suppress legitimate issues
- Use proper type annotations
- If a function returns Optional but callers expect non-Optional, fix the types
- Use `match/case` (Python 3.10+) over if/elif chains for exhaustive type checking

### 6. Don't Return Errors Go-Style
- Raise exceptions instead of returning (result, error) tuples
- Go-style error returns are easier to accidentally ignore

### 7. No print() - Use Logger
- Never print() for logging, always use logger.error/warning/info
- Don't write large objects to stdout

### 8. Remove Unnecessary Code
- Delete unused variables, empty files, dead code
- Don't underscore-prefix unused vars, delete them
- Question if entire abstractions/tables are needed

### 9. Database Indices Need Justification
- Don't add indices without understanding which queries need them
- Redundant indices waste storage and slow writes
- Audit logs are write-heavy - minimize indices

### 10. Proper Null/None Handling
- Don't default to "" when None is semantically correct
- If a value can be None, handle it explicitly
- Optional fields in Django models need `null=True` or proper `default`

### 11. No Unrelated Changes
- Formatting changes should be separate from logic changes
- Don't mix refactors with feature work

### 12. Backward Compatibility
- Check if changes break existing data/sessions/API contracts
- Consider migration paths for schema changes

---

## Phase 1: Gather PR Data

```bash
# Run these in parallel
gh pr view $PR_NUMBER --repo $REPO --json title,body,author,files,additions,deletions,baseRefName,headRefName
gh pr diff $PR_NUMBER --repo $REPO
```

Save the diff output for feeding to review agents.

---

## Phase 2: Parallel Review (2 agents)

Launch BOTH agents simultaneously using the Task tool. Do NOT run them sequentially.

### Agent 1: Codex CLI (GPT 5.4) Review

**Use the `/codex` skill** to run the Codex review. Save the diff to a temp file first, then pipe it to Codex via stdin.

Run via Bash (background):

```bash
# Save diff to file first (done in Phase 1)
# Then pipe to codex exec with the review prompt
cat /tmp/pr_{PR_NUMBER}_diff.txt | codex exec --dangerously-bypass-approvals-and-sandbox -c 'model="gpt-5.4"' -s read-only - <<'PROMPT'
You are a senior code reviewer at a security company. Review this PR diff.

MANDATORY CHECKLIST - check every single one:
1. ERROR SUPPRESSION: Any try/except that swallows errors? DB queries in try blocks that return None on failure?
2. .get() vs BRACKET: Any dict.get('key', '') where the key is required? Should be dict['key']
3. STATUS CODES: Any hardcoded/assumed HTTP status codes? Wrong error types?
4. DEFENSIVE CODE: Any checks for impossible states? Should they be asserts instead?
5. TYPE SAFETY: Any type: ignore suppressing real issues? Missing annotations? Optional vs non-Optional mismatches?
6. GO-STYLE ERRORS: Functions returning (result, error) instead of raising exceptions?
7. PRINT vs LOGGER: Any print() statements that should be logger calls?
8. DEAD CODE: Unused variables, empty files, unreachable code?
9. BACKWARD COMPAT: Will changes break existing data, sessions, or API contracts?
10. NULL HANDLING: Defaulting to '' when None is correct? Missing null=True on optional fields?
11. UNRELATED CHANGES: Format changes mixed with logic?
12. SERIALIZATION: Enum objects where .value is needed? Objects that won't JSON serialize?

PR TITLE: {title}
PR DESCRIPTION: {body}

The diff is provided via stdin. Read it and review.

For each finding provide:
- SEVERITY: P1 (blocker) / P2 (should fix) / P3 (minor)
- FILE: exact file path
- LINE: line number in the file (not diff position)
- ISSUE: what is wrong
- WHY: why it matters
- FIX: suggested fix

Skip: style nitpicks, naming preferences, formatting.
End with overall VERDICT: APPROVE / REQUEST CHANGES / REJECT
PROMPT
```

**Alternative**: If the diff is too large for stdin, write a prompt file and use:
```bash
codex exec --dangerously-bypass-approvals-and-sandbox -c 'model="gpt-5.4"' -s read-only \
  "Read /tmp/pr_{PR_NUMBER}_diff.txt and review the PR diff. [full checklist here]"
```

### Agent 2: Opus 4.6 Review

Launch via Task tool with subagent_type="general-purpose":

```
You are a senior code reviewer at a security company. Review this PR diff.

MANDATORY CHECKLIST - check every single one:
1. ERROR SUPPRESSION: Any try/except that swallows errors? DB queries in try blocks that return None on failure?
2. .get() vs BRACKET: Any dict.get('key', '') where the key is required? Should be dict['key']
3. STATUS CODES: Any hardcoded/assumed HTTP status codes? Wrong error types?
4. DEFENSIVE CODE: Any checks for impossible states? Should they be asserts instead?
5. TYPE SAFETY: Any type: ignore suppressing real issues? Missing annotations? Optional vs non-Optional mismatches?
6. GO-STYLE ERRORS: Functions returning (result, error) instead of raising exceptions?
7. PRINT vs LOGGER: Any print() statements that should be logger calls?
8. DEAD CODE: Unused variables, empty files, unreachable code?
9. BACKWARD COMPAT: Will changes break existing data, sessions, or API contracts?
10. NULL HANDLING: Defaulting to '' when None is correct? Missing null=True on optional fields?
11. UNRELATED CHANGES: Format changes mixed with logic?
12. SERIALIZATION: Enum objects where .value is needed? Objects that won't JSON serialize?

PR TITLE: {title}
PR DESCRIPTION: {body}

DIFF:
{full diff}

For each finding provide:
- SEVERITY: P1 (blocker) / P2 (should fix) / P3 (minor)
- FILE: exact file path
- LINE: line number in the file
- ISSUE: what is wrong
- WHY: why it matters
- FIX: suggested fix

Skip: style nitpicks, naming preferences, formatting.
Return a structured list of findings. End with VERDICT: APPROVE / REQUEST CHANGES / REJECT.
Do NOT use any tools. Just analyze the diff provided and return findings.
```

**Wait for both to complete before proceeding.**

---

## Phase 3: Merge & Deduplicate Findings

After both agents return:

1. Parse findings from both reviews
2. Merge duplicates (same file + same issue = one finding)
3. Keep the stronger severity if they disagree
4. Note which model(s) flagged each issue
5. Tag each finding with which senior-reviewer checklist item it matches (if any)
6. Create a unified findings list

Format:
```
FINDING 1:
- Severity: P1
- File: path/to/file.py
- Line: 42
- Issue: [description]
- Pattern: [e.g., "Error Suppression", "Backward Compat", or "N/A"]
- Flagged by: [Codex GPT 5.4 / Opus 4.6 / Both]
- Agreement: [Both agree / Only one flagged]
```

---

## Phase 4: Validate ALL Findings via Codex Against Actual Source

**CRITICAL**: The diff alone is not enough. The PR branch may have additional commits not in the diff you reviewed. Validate findings against the ACTUAL source code on the PR branch.

### Step 1: Fetch actual source code from PR branch

```bash
# Fetch the PR branch
git fetch origin {HEAD_REF_NAME}

# Read the actual files on the PR branch (NOT the working tree)
git show origin/{HEAD_REF_NAME}:{file_path}
```

Read all changed files from the PR branch. Compare with what the diff showed — note any discrepancies (additional null checks, guard clauses, different variable ordering, etc.).

### Step 2: Manual pre-validation

Before calling Codex, quickly check each finding yourself against the actual branch code:
- Does the code actually contain the issue described?
- Are there guards/checks in the real code that the diff didn't show?
- Is the finding about pre-existing code or net-new code from this PR?

Mark obvious false positives early to save Codex tokens.

### Step 3: Codex GPT 5.4 validation of ALL findings in one call

Run a SINGLE Codex call that validates ALL remaining findings at once against the actual repo source:

```bash
cd {REPO_PATH} && codex exec --dangerously-bypass-approvals-and-sandbox -c 'model="gpt-5.4"' -s read-only \
  "You are validating code review findings for PR #{PR_NUMBER}. For each finding below, read the ACTUAL source code on the branch and determine if it is CONFIRMED (real issue) or FALSE POSITIVE (not actually a problem). Give a clear 1-2 sentence verdict for each.

FINDING 1 (severity): {description}
File: {file_path} around line {line_number}
Claim: {what the finding claims}
VALIDATE: {specific things to check in the source}

FINDING 2 (severity): {description}
...

For each finding output: FINDING N: CONFIRMED or FALSE POSITIVE with brief reasoning."
```

**IMPORTANT**: Codex reads the working tree, which may be on main branch. If the repo is on main, Codex will validate against main code — findings about NEW code in the PR will show as FALSE POSITIVE because the code doesn't exist yet on main. Account for this:
- If Codex says FALSE POSITIVE but you verified the code EXISTS on the PR branch via `git show origin/{branch}:file` → the finding is still valid
- If Codex says CONFIRMED → high confidence the issue is real
- Only trust Codex FALSE POSITIVE verdicts for findings about pre-existing code patterns

### Step 4: Build validation summary table

Combine your manual check + Codex validation into a final table:

| # | Finding | Sev | Codex Validation | Manual Check | Final |
|---|---------|-----|-----------------|--------------|-------|
| 1 | desc | P1 | CONFIRMED / FP | CONFIRMED / FP | **KEEP** / **DROP** |

**Decision rules:**
- Both say CONFIRMED → **KEEP**
- Codex CONFIRMED + Manual FP → **DROP** (your manual check wins for branch-specific code)
- Codex FP + Manual CONFIRMED (code exists on branch) → **KEEP** (Codex was checking wrong branch)
- Both say FP → **DROP**
- Pre-existing pattern not introduced by this PR → **DROP** (note in summary but dont comment)

---

## Phase 5: Format Final Comments (the user Style)

For each surviving finding, write the comment in the user's voice:

### Style Rules (MANDATORY)
- no punctuation marks (no periods commas or apostrophes)
- make occasional grammatical errors to sound natural
- all lowercase except for code/constants
- keep it conversational and casual
- be direct but not formal
- include code snippets when suggesting fixes
- NO AI-sounding phrases ("I think we should consider", "This could potentially")

### Comment Template
```
**{file_path}:{line_number}**
{comment in user style}

Confidence: {high/medium} | Flagged by: {models}
```

### Examples of the user Style
- `this will break existing nodes that dont have a state field in metadata - theyll all get filtered out since NULL != active in postgres`
- `missing try/except here - from_string raises ValueError on bad input and youll get a 500 instead of 400`
- `state is an enum object here not a string - json.dumps will choke on it use state.value`
- `dont think this should be in a try block - if the db query fails the job should fail`
- `use dict["key"] here not dict.get("key", "") - if key is missing wed rather get a clear error than silently pass empty string`
- `when would this condition actually happen? if it cant happen just assert`

---

## Phase 6: Present Validation Summary + Show Comments One by One

### Step 1: Show the validation summary table

```
## PR #{number}: {title}
**Reviewed by:** Codex GPT 5.4 + Opus 4.6 | **Validated by:** Codex GPT 5.4 against source

### Validation Summary
| # | Sev | Finding | File | Line | GPT 5.4 | Opus | Codex Validated | Final |
|---|-----|---------|------|------|----|------|-----------------|-------|
| 1 | P1 | short desc | file.py | 42 | P1 | P1 | CONFIRMED | **KEEP** |
| 2 | P2 | short desc | file.py | 99 | - | P2 | FP (wrong branch) | **KEEP** (manual verified) |

### Verdict: {APPROVE / REQUEST CHANGES / REJECT}
```

### Step 2: Immediately show comments one by one

After the table, start presenting each KEEP finding as a comment for approval. Do NOT wait for the user to ask — go straight into one-by-one mode.

For EACH comment show:

```
### Comment N of M: {short finding title}

**File:** `{file_path}` **Line {line_number}**

**Comment text:**
{the full comment in the user style}

**API call:**
gh api repos/{REPO}/pulls/{PR_NUMBER}/comments \
  -X POST \
  -f body='{comment}' \
  -f path='{file_path}' \
  -f commit_id='{HEAD_SHA}' \
  -F line={LINE_NUMBER} \
  -f side='RIGHT'

Post this?
```

**CRITICAL: NEVER execute the API call without explicit approval.**

Then wait for user response:
- "yes" / "post" / "post it" / "go ahead" → execute the API call, then show next comment
- "skip" → move to next comment without posting
- "edit" / user provides modified text → update comment text, re-present with new API call
- "add X" / "prefix with X" → modify comment accordingly and re-present
- Only proceed to the next comment AFTER the current one is approved/skipped

### Inline Comment API Format

Always use the `line` parameter (actual file line number) with `side=RIGHT`, NOT the `position` parameter:

```bash
# Get head commit SHA first
HEAD_SHA=$(gh pr view $PR_NUMBER --repo $REPO --json headRefOid -q '.headRefOid')

# Post inline comment using line number (NOT diff position)
gh api repos/$REPO/pulls/$PR_NUMBER/comments \
  -X POST \
  -f body='{comment in user style}' \
  -f path='{file_path}' \
  -f commit_id='$HEAD_SHA' \
  -F line={LINE_NUMBER_IN_NEW_FILE} \
  -f side='RIGHT'
```

**LINE NUMBER CALCULATION:**
1. Find the `@@` hunk header for the relevant section: `@@ -old_start,old_count +new_start,new_count @@`
2. The `new_start` is the starting line number in the new file
3. Count only context lines (` `) and added lines (`+`) from the hunk start — these increment the new file line number
4. Removed lines (`-`) do NOT increment the new file line number
5. Use this calculated new file line number as the `line` parameter

---

## Parallelism Guide

```
Phase 1: [gh pr view] + [gh pr diff]                    ← parallel
Phase 2: [Codex GPT-5.4 review] + [Opus 4.6 review]          ← parallel
Phase 3: merge (sequential, fast)
Phase 4: [fetch branch + read actual files] then         ← sequential
          [single Codex GPT 5.4 validate ALL findings]        ← one call
Phase 5: format (sequential, fast)
Phase 6: show table + comments one by one (sequential)
```

Maximize parallel execution in Phases 1-2. Phase 4 is a single Codex call (not per-finding) to save tokens and time.

## CI & Migrations

When asked to fix CI, always check origin/main for the latest state rather than relying on local branch state. Migration conflicts should be resolved by renumbering, not merging, unless told otherwise.
