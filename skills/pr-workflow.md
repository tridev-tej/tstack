# PR Workflow Reference

This file is loaded on demand when creating PRs, reviewing PRs, or writing commit messages.

---

## PR Review Comments Style

When leaving PR review comments on behalf of the user:
- **ALWAYS leave inline comments on the specific line/file - NEVER general PR comments**
- Use `gh api` to post inline review comments with proper diff position
- Only leave general PR comments if explicitly requested
- No punctuation marks (no periods commas or apostrophes)
- Make occasional grammatical errors to sound natural
- All lowercase except for code/constants
- Keep it conversational and casual
- Be direct but not formal
- Include code snippets when suggesting fixes

**How to post inline PR comments:**
```bash
# First get the diff to find the position
gh pr diff <PR_NUMBER> --repo owner/repo

# Then post inline comment using the diff position (not file line number)
gh api repos/owner/repo/pulls/<PR_NUMBER>/comments \
  -X POST \
  -f body='comment text' \
  -f path='path/to/file.py' \
  -f commit_id='<HEAD_COMMIT_SHA>' \
  -F position=<DIFF_POSITION>
```

**CRITICAL: position is the line number in the DIFF output, not the file line number**

**Examples:**
- `could cap this with MAX_ENTITIES = 500 since we only display 5 anyway`
- `seeing a potential race condition here if multiple workers grab same config`
- `might want to wrap this in a transaction otherwise email goes out but audit fails`

**Anti-patterns (too formal/AI-sounding):**
- `I think we should consider adding a limit here.`
- `This could potentially cause issues with memory.`

For full review methodology, see `~/.claude/skills/pr-review-comments.md`

---

## Commit and PR Messages

- **ALWAYS show the full PR description to the user for review BEFORE creating the PR. Never create a PR without explicit approval of the description.**
- Do NOT include "Co-Authored-By: Claude" or similar attribution in commit messages
- Do NOT include "Generated with Claude Code" or similar in commit/PR descriptions
- Do NOT mention Claude, Claude Code, Codex, GPT, or any AI tools in commit messages or PR descriptions
- Keep commit messages clean and professional without AI attribution
- **If the PR involves UI changes, always remind the user to tag `ui-dev` as a reviewer**
- **CRITICAL: All PR descriptions must be written as if the user personally authored them.** Write in first person ("I fixed", "I added", "I refactored"), match the user's casual/concise communication style, no formal AI-sounding language.

---

## PR Description Template

```markdown
## Summary **(required)**
<!-- Brief description of what this PR does -->

## Type of Change **(required - check at least one)**
- [ ] Bug fix
- [ ] New feature
- [ ] UI/UX improvement
- [ ] Performance improvement
- [ ] Config/deployment
- [ ] Documentation

## What Changed? **(required)**
<!-- List the key changes made -->
-
-
-

## Why?
<!-- What problem does this solve? Link issues if applicable -->

Fixes #

## Screenshots (if UI changes checked)
<!-- Add before/after screenshots for visual changes -->

**Before:**

**After:**

## Checklist **(all mandatory)**
- [ ] Code follows project guidelines and coding standards
- [ ] Self-reviewed my code
- [ ] All tests pass locally
- [ ] Updated documentation if needed
- [ ] No sensitive information exposed (API keys, credentials, etc.)

## Deployment Notes (if applicable)
<!-- Any special deployment steps, migrations, env vars, rollback plan? -->

## Additional Context
<!-- Dependencies added/removed, breaking changes, future work, concerns? -->
```

---

## Project Documentation: FOR_DEV.md

For every project, write a detailed `FOR_DEV.md` file that explains the whole project in plain language.

### What to Include:

1. **Technical Architecture** - How the system is designed, the major components and how they talk to each other
2. **Codebase Structure** - Directory layout, where to find what, how the pieces connect
3. **Technologies Used** - The stack and why each piece was chosen
4. **Technical Decisions** - The "why" behind architectural choices, trade-offs we made
5. **Lessons Learned** - This is the gold:
   - Bugs we ran into and how we fixed them
   - Potential pitfalls and how to avoid them
   - New technologies/patterns discovered
   - How good engineers think and work
   - Best practices that emerged from the project

### Writing Style:

- **Engaging, not boring** - Write like you're explaining to a friend over coffee
- **Use analogies** - "The message queue is like a restaurant ticket system"
- **Include anecdotes** - "We spent 3 hours debugging why tests were flaky..."
- **Be opinionated** - Share what worked, what didn't, what you'd do differently
- **Make it memorable** - Stories stick better than bullet points

### When to Create/Update:

- Create when starting a new project
- Update after significant features, bug fixes, or architectural changes
- Especially update after learning something the hard way

### Location:

Place `FOR_DEV.md` in the project root directory.
