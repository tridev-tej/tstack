---
name: git-pr-bug-attribution
description: |
  Determine whether a bug was introduced by a specific PR or commit. Use when:
  (1) a bug appears on a feature branch and you suspect a recent PR caused it,
  (2) you need to find which commit first introduced a failing line of code,
  (3) you want to rule out your own PR as the source before filing a bug.
  Uses git log --follow, git show on each commit, and line-number comparison
  across historical versions of the file.
author: Claude Code
version: 1.0.0
date: 2026-03-17
---

# Git PR Bug Attribution

## Problem

A bug surfaces when running code from a feature branch. It's unclear whether:
- The current PR introduced it, or
- It was pre-existing and just triggered by the new deployment

## Context / Trigger Conditions

- An error traceback points to a specific file and line number
- You have a list of recent PRs/commits that touched the file
- You want to definitively say "this was/wasn't introduced by PR #N"

## Solution

### Step 1 — Get full commit history for the file

```bash
git log --oneline --follow -- <path/to/file.py>
```

This shows all commits that touched the file, with PR numbers in commit messages.

### Step 2 — Check the file at each suspect commit

```bash
git show <commit_sha>:path/to/file.py > /tmp/file_version.py
```

Then inspect the specific line number from the traceback:

```bash
python3 -c "
with open('/tmp/file_version.py') as f:
    lines = f.readlines()
# Print lines around the failing line
for i, l in enumerate(lines[line_num-5:line_num+5], line_num-4):
    print(f'{i}: {l}', end='')
"
```

### Step 3 — Check if the failing line existed before the suspect PR

If the exact line (e.g., `raw_data.get("log_sources", [])`) is present in the version
**before** the suspect PR was merged, the bug is **pre-existing** and NOT caused by that PR.

### Step 4 — Find the actual introducing commit

Use `git log -p` filtered to the function/line:

```bash
git log --oneline -p -- path/to/file.py | grep -B5 -A5 "failing_code_fragment"
```

Or check each historical version systematically to find when the line first appeared.

## Verification

Compare `git show <commit_before_pr>:file.py` vs `git show <commit_after_pr>:file.py` at
the failing line number. If the line is identical in both versions, the PR didn't introduce it.

## Example

**Scenario**: Bug at `investigation_report.py:785` — `raw_data.get("log_sources", [])`.
Suspect: PR #4090 (timestamp format fix).

```bash
# 1. Get history
git log --oneline --follow -- apps/reporting/.../investigation_report.py
# Output: 04abc5a91 PR #4090, 72df28d3e PR #4068, 2ba60c8b2 PR #4050 ...

# 2. Check line 785 in version before PR #4090 (commit 72df28d3e)
git show 72df28d3e:path/to/investigation_report.py > /tmp/before_4090.py
# Line 785: log_sources = raw_data.get("log_sources", [])  ← SAME LINE EXISTS

# 3. Conclusion: bug predates PR #4090 — introduced by an earlier PR
```

## Notes

- The line number in the traceback refers to the **current** file. When checking older
  versions, the line number may shift slightly due to insertions/deletions — look for
  the code pattern, not just the line number.
- Docker image tags often encode the commit: `fix-report-issues.9d6ed54` → commit `9d6ed54`.
  Cross-reference this with `git log` to know exactly what's deployed.
- `gh pr list --author "@me" --limit 5` quickly shows your recent PRs and their branches
  to confirm which branch is deployed on staging.
