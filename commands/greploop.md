---
description: Loop Greptile review → fix comments → re-review until zero comments
allowed-tools: Bash(gh:*) Bash(git:*) Read Edit Write Glob Grep
---

# Greploop

Read and follow the full skill instructions at `~/.claude/skills/greptile/greploop/SKILL.md`.

**Input**: PR number or URL (optional — auto-detects from current branch if omitted).

If given a PR URL like `https://github.com/owner/repo/pull/123`, extract owner, repo, and PR number from it.

Execute the greploop skill end-to-end. Do not ask for confirmation between iterations.
