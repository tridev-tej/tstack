# Review PR with Codex

Review the current PR using Codex CLI for substantive code review feedback.

## Default Settings

- **Model:** `gpt-5.3-codex` (highest quality review)
- **Approval:** Required for each comment before posting
- **Validation:** Comments validated by Opus 4.5 before posting

## What Makes a Good PR Comment

Focus on issues that matter - not style nitpicks. Good comments:

### 1. Architectural Improvements
- Suggest dataclasses for stronger type safety instead of dicts
- Identify opportunities for better abstractions
- Point out where existing patterns/signals/utilities can be reused

### 2. Code Simplification
- Unnecessary function definitions that can be inlined
- Nested try blocks that can be flattened
- Redundant code paths that always succeed/fail

### 3. Import Organization
- Imports inside functions that can be at top of file
- Circular import concerns

### 4. Bug Identification
- Variables used before definition (NameError risks)
- Timezone handling issues (naive vs aware datetimes)
- Type mismatches between docstrings and actual returns
- Exception handlers that shadow the real error

### 5. Redundancy Removal
- Python version-specific: `.replace("Z", "+00:00")` unnecessary since Python 3.11
- Duplicate validation that already happens elsewhere
- Dead code paths

### 6. DRY Violations
- Existing signals/utilities that should be reused instead of creating new ones
- Repeated patterns that could be extracted

### 7. Separation of Concerns
- Business logic that should be in managers/services not views/consumers
- Signals called from wrong layer

### 8. Type Safety
- Unused `**kwargs` that reduces type safety
- `dict[str, Any]` that could be a typed dataclass
- Missing Optional[] annotations

## Steps

### 1. Run Codex Review

```bash
# Default: gpt-5.3-codex model
codex review --base main -c model="gpt-5.3-codex"
```

Or for a specific PR (clone and checkout first):
```bash
cd /tmp && rm -rf repo-review && gh repo clone {owner}/{repo} repo-review && cd repo-review && gh pr checkout {pr_number}
codex review --base main -c model="gpt-5.3-codex"
```

Or with custom focus:

```bash
echo "Focus on: architectural improvements, code simplification, bug identification, DRY violations, type safety issues. Look for imports that can be at top of file, unnecessary nested try blocks, variables used before definition, existing utilities that should be reused instead of creating new ones, timezone handling bugs. Skip style nitpicks." | codex review --base main -c model="gpt-5.3-codex" -
```

### 2. Manual Fallback (if Codex unavailable)

If Codex CLI fails, use Claude to review with this checklist:

**For each changed file, check:**

1. **Imports** - any inside functions that should be at top?
2. **Try blocks** - any unnecessarily nested?
3. **Function definitions** - any inline lambdas/funcs that arent needed?
4. **Type hints** - any `dict` that should be dataclass? any missing Optional?
5. **Existing utilities** - any new code that duplicates existing signals/helpers?
6. **Variable scope** - any used before defined in exception paths?
7. **Timezone** - any naive datetime issues? unnecessary .replace() calls?
8. **Dead code** - any paths that always fail or are unreachable?
9. **kwargs** - any unused **kwargs reducing type safety?
10. **Layer violations** - signals from wrong layer? business logic in views?

### 3. Validate Comments with Opus 4.5

Before presenting to user, validate each comment:
- Is the issue real? (not a false positive)
- Is the comment in the user style? (lowercase, no punctuation, casual)
- Is it actionable? (clear what to fix)
- Is it worth mentioning? (not a trivial nitpick)

### 4. Present Issues for User Approval

**CRITICAL: NEVER post comments without explicit user approval.**

For each issue found, present using AskUserQuestion tool:

```
**Comment {N} of {total}** | Priority: P{1-3}

**File:** `path/to/file.py:123`

**Draft comment (the user style):**
```
{comment text in lowercase, no punctuation, casual tone}
```

**Codex reasoning:** {why this is an issue}
```

Use AskUserQuestion with options:
- "Approve and post" - Post this comment to GitHub
- "Edit first" - User will provide edited text
- "Skip" - Dont post this comment
- "Skip all remaining" - Stop processing comments

### 5. Post Approved Comments

Only after user approves each comment:

```bash
# Get latest commit SHA for the PR
COMMIT_SHA=$(gh pr view {pr_number} --json headRefOid -q '.headRefOid')

# Post inline comment
gh api repos/{owner}/{repo}/pulls/{pr_number}/comments \
  -f body="{approved_comment_text}" \
  -f path="{file_path}" \
  -f commit_id="$COMMIT_SHA" \
  -F line={line_number} \
  -f side="RIGHT"
```

### 6. Summary

After processing all comments, show:
- Total comments found
- Comments posted
- Comments skipped
- Comments edited

## Example Good Comments

**Architectural improvement:**
```
Suggested future refactoring: use a dataclass for variables like

@dataclass
class InvestigationReportVariables:
    investigation_id: str = field(metadata={"description": "Investigation UUID"})

Then dataclasses.fields(InvestigationReportVariables) gives Fields which have name and metadata.description. Stronger type safety than dict[str, str].
```

**Code simplification:**
```
Do you need to define and then execute this function? I believe it is the same as just

    with schema_context(schema_name):
        with connection.cursor() as cursor:
            cursor.execute(query, [start_date, end_date])
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
```

**Import organization:**
```
I believe import can be at top of file.
```

**Bug identification:**
```
If this raises an exception, then next_execution_time wont get defined and if next_execution_time <= now: will raise a NameError. I dont think you need try/except here.
```

**Redundancy removal:**
```
.replace("Z", "+00:00") is no longer needed with fromisoformat since Python 3.11. fromisoformat behaves the same with Z suffix as with +00:00 suffix.
```

**DRY violation:**
```
There is already a signal investigation_updated that can be reused. No need to create new signals. That signal is extensive and you can pass any attribute of an investigation.
```

**Separation of concerns:**
```
Is it really necessary to trigger signal from this file? Ideally the status is marked as completed from managers file. Reuse the investigation_updated signal. If it needs to be modified to fit your use case, do it.
```

**Type safety:**
```
I would remove **kwargs - not being used and reduces type safety.
```

**Nested try simplification:**
```
I dont think nested try is needed here, will be the same if you remove nested try and move except json.JSONDecodeError to outer try.
```

## the user Comment Style

### Formatting Rules
- **No punctuation** - skip periods at end of sentences
- **No apostrophes** in contractions: "youre" "theres" "doesnt" "its" "dont" "wont" "cant"
- **Lowercase** throughout (except code/technical terms)
- **Line breaks** between separate thoughts (short paragraphs)

### Tone
- Casual and conversational, like talking to a colleague
- Direct but not harsh
- Use hedging phrases: "i think" "i believe" "might want to" "could be worth"

### Structure for Initial Comments
1. State the concern directly
2. Explain why its a problem (optional, if not obvious)
3. Suggest a fix with code example if applicable

### Structure for Reply Comments
1. **Acknowledge first** - "fair enough" "yeah" "good point" "makes sense" "true"
2. **Add nuance** - additional context or edge case
3. **Conclude** - "not a blocker" "not worth over-engineering" "just mentioning"

### Example Initial Comments
```
seeing a potential race condition here. if multiple workers, the same report config could trigger multiple report generation
```

```
schedule.day used directly here without validation so day=0 or day=32 would cause weird behavior

might want to clamp it in the Schedule dataclass or add a quick check like day = max(1, min(schedule.day, 28)) for safety
```

```
i believe import can be at top of file
```

### Example Reply Comments
```
yeah the lock handles most cases

looked at the implementation though and theres a comment in get_lock acknowledging a small gap - no select_for_update so two pods at exact same millisecond could both acquire. but as the comment says its very rare and theres deduplication downstream

not worth over-engineering for this edge case imo
```

```
fair enough its preexisting and the llm-generated entities should be limited in size. not a blocker for this pr
```

```
true transaction alone doesnt help since email is external

proper fix would be to record actions_results first (commit), then send email. but thats a bigger refactor and the current flow is probably fine for now
```

```
yeah its a bit unusual to select_for_update without updating same row but the lock semantics would still work

not essential given the job lock already exists, just an extra layer if we wanted it
```

### What NOT to Do
- Formal punctuation (periods, commas everywhere)
- Proper apostrophes (you're, there's, it's)
- Title case or sentence case
- Long paragraphs without breaks
- Defensive or apologetic tone
- Over-explaining obvious things
- Saying "youre right" (too agreeable, use "yeah" "fair enough" "true" instead)
