# Code Review Skill: Senior Reviewer's Guidelines

Use this skill when reviewing code (PRs, diffs, code changes). These are general senior-reviewer patterns for backend and infrastructure code.

## Core Philosophy

The senior reviewer's reviews focus on:
1. **Questioning assumptions** - Does this code path actually happen?
2. **Correctness over defensiveness** - Don't hide errors, let them surface
3. **Minimal complexity** - Remove unused code, avoid unnecessary abstractions
4. **Precision** - Use correct types, status codes, and framework conventions

## Review Checklist

### 1. Question Necessity & Logic (HIGH PRIORITY)

Ask these questions for every change:

- **"When would this happen?"** - If a condition checks for an "impossible" state, question it
- **"Does this change do anything?"** - Verify the code actually has impact
- **"Is this being called anywhere?"** - Check for dead code
- **"Do we expect this to happen?"** - Question defensive type checks

**Examples from the senior reviewer:**
```
"When would we want `schema_name` to be different from account `name`?"
"Does this change do anything?" (pointing to redundant condition)
"When would this return false? This code only runs after a successful materialization."
"Do we expect this to happen?" (on a type guard like `if not isinstance(x, dict)`)
```

### 2. Error Handling Philosophy (STRONG OPINION)

**Key principle: Let errors surface, don't swallow them.**

**DO NOT:**
- Wrap DB queries in try/except blocks that swallow errors
- Return empty results on failure (hiding the error)
- Catch `Exception` broadly and log-then-continue

**DO:**
- Let jobs/tasks fail when they should fail
- Use appropriate HTTP status codes (5xx for server errors, 4xx for client errors)
- Add explicit validation BEFORE code would throw exceptions

**The senior reviewer's exact words:**
```
"I don't think this should be in a `try` block. If these DB queries fail, the job should fail."
"In general, I don't think it is a good idea to suppressing errors indiscriminately."
"Proper behavior is all/most exceptions to fail the job (no try/except)."
"If it should never happen, I think an internal server error (5xx status code) should
be raised rather than a DoesNotExist error (4xx status code)."
"get_alerts should raise an exception if there was an error fetching alerts."
```

**Bad pattern:**
```python
try:
    result = db.query()
except Exception as e:
    logger.error(f"Error: {e}")
    return []  # Swallowing the error!
```

**Good pattern:**
```python
# Let exceptions propagate - the caller/job should handle failure
result = db.query()
```

### 3. Unused Code & Simplification

**Remove aggressively:**
- Unused variables (don't prefix with `_`, just delete)
- Dead imports
- `.format()` calls with no arguments
- Optional parameters that are always empty
- Redundant `_res = x.delete()` - just call `x.delete()`

**Senior reviewer's examples:**
```
"Unused as of multi-tenancy changes, can remove."
"Result doesn't need to be used, can remove FIXME and have X.delete()"
"`.format()` can be removed"
"`value` is optional, so I believe we can remove it in these cases."
```

### 4. Nits & Style (CONSISTENT)

**Always flag:**
- Missing trailing newlines (VERY common)
- `print()` instead of `logger.error()`
- Unrelated formatting changes (should be separate PR)
- Leading/trailing whitespace issues

**Senior reviewer's pattern:**
```
"nit: keep trailing newline"
"nit: logger.error instead of print"
"nit: unrelated formatting changes"
"Ideally independent formatting changes would be separate PR."
```

### 5. Correctness Issues

**Watch for:**
- Incomplete guards: `if x and x.is_active` when `x` can't be None
- Missing returns in functions
- Type mismatches: `data.get("id")` returns `Optional[str]` but field expects `str`
- Function name vs action name: `func.__name__` != `func._function_info.ActionName`
- Logic that always evaluates to the same result

**Examples:**
```
"This check is not sufficient. If `not organization`, we'll take the else
branch and evaluate `organization.name` there."
"These functions need `return`s."
"`data.get('id')` can return `None`, but the dataclass expects not optional `id: str`."
"I believe `func.__name__` isn't necessarily `func._function_info.ActionName`."
```

### 6. Architecture & Design

**Questions to ask:**
- Could we consolidate models/tables?
- Should this code live elsewhere?
- Is this abstraction justified?
- Should parameters be explicit instead of `**kwargs`?

**Examples:**
```
"Could we move `Organization` state into `Account` and remove `Organization` altogether?"
"I think these should go in the context-lake client."
"Is there a reason to use `**kwargs` here instead of explicitly declaring the parameters?"
"The point of this class was to share code... I don't see any shared code between implementations."
```

### 7. Naming

**Suggest clearer names when:**
- Class/variable name doesn't match its purpose
- Name is ambiguous

**Example:**
```
"Perhaps `UserInAccount` would be a clearer name.
The rows of this table represent relationships between users (emails) and accounts."
```

### 8. Framework & API Knowledge

**Flag when code violates:**
- Framework conventions (Dagster, Django, etc.)
- API contracts (OCSF, JSON-path syntax)
- Library best practices

**Examples:**
```
"There will never be `.` in OCSF fields. We should follow OCSF and JSON-path syntax and use ."
"JSON doesn't expect duplicate keys."
"Correction: Dagster runs `asset_sensor`s every tick interval, like ordinary `sensor`s."
```

### 9. Historical Context

**When reviewing, check:**
- Does this fix a regression? Note the original PR
- Is this version replacing another? Link both
- Is the migration safe to remove?

**Examples:**
```
"This fixes a regression introduced in #1057."
"This version was added in #1165. The version it replaces was added in #1124."
"I don't think we want to remove this migration."
```

### 10. Deferring Work

**It's OK to defer when:**
- The fix is correct but could be cleaner
- Refactoring would expand scope significantly

**Examples:**
```
"Can refactor later."
"Probably `get_integration_configuration_for_type` should raise a clearer exception
and this code can stay the same (so not needed in this PR)."
```

## Comment Format Guide

### Asking Questions (Preferred Style)
```
"When would [scenario]?"
"Is this needed to [purpose]?"
"Is there a reason to [action]?"
"Do we need [thing]? I am thinking that [alternative]."
```

### Pointing Out Issues
```
"I don't think [assumption]. [Reasoning]."
"I believe [observation]."
"This [code] is not sufficient. [Explanation of failure case]."
```

### Making Suggestions
```
"Perhaps [suggestion] would be clearer."
"Could we [alternative approach]?"
"I think we want to [recommendation] here."
```

### Nits
```
"nit: [brief description]"
```

### Acknowledgments (After Discussion)
```
"Got it, thanks."
"I see, thanks."
```

## Red Flags to Always Flag

1. **Try/except swallowing errors** - Especially around DB/API calls
2. **Missing trailing newlines** - Every file should end with newline
3. **print() for logging** - Use logger
4. **Unused variables** - Delete, don't underscore-prefix
5. **Type mismatches** - `.get()` returning Optional when non-optional expected
6. **Dead code** - Especially after refactors like multi-tenancy
7. **Defensive checks for impossible states** - Question them
8. **Format-only changes mixed with logic** - Should be separate PRs

---

## How to Review Large PRs

*Wisdom from the senior reviewer on approaching giant PRs effectively.*

### The Multi-Pass Approach

**Pass 1: Quick Scan (Get the Lay of the Land)**
- Look at files changed and "statistics" (lines added/removed)
- Identify ratio of UI vs backend code
- Note where most of the new code is concentrated
- Build mental model of PR scope and structure

**Pass 2: Detailed Review (Line-by-Line or Function-by-Function)**
- Go slower through the code
- Jump around the PR (or navigate code locally) for context
- Focus more on backend/logic, less on UI code
- Cross-reference with existing codebase when needed

**Pass 3: Fresh Eyes (If Needed)**
- Come back after some time away
- By now you'll have an idea of what to focus on
- Catch things you missed on first passes

### Time Investment Guidelines

| Code Type | Time per 100 LOC | Notes |
|-----------|------------------|-------|
| Low-stakes repeated patterns | < 1 minute | Skim for consistency |
| Standard backend logic | 2-5 minutes | Normal detailed review |
| Complex/security-critical | 5-10+ minutes | May need research |
| Interesting edge cases | 15+ minutes for 5 lines | Deep investigation |
| UI/frontend code | Minimal | Brief scan unless complex logic |

*Note: Time varies heavily based on code clarity, type safety, and reviewer familiarity with the domain.*

### When to Check Out Locally

**Stay in GitHub browser when:**
- PR is navigable (not too large)
- Context switches between files are manageable
- No need to run/test the code

**Check out locally when:**
- GitHub navigation becomes untenable
- Need to search across codebase for context
- Want to use AI tools (Claude Code, Cursor, etc.) to ask questions
- Need to actually run/test the changes

### Using AI for Reviews

- Can ask questions and paste code snippets to ChatGPT/Claude
- Checking out branch locally + using Claude Code to search for issues is effective
- AI reviewers can help with systematic checks but human judgment still needed

### What Makes PRs Hard to Review

**Harder:**
- Large scope (not necessarily LOC)
- Unfamiliarity with relevant preexisting code
- Unclear intent/design space
- Code that lacks clarity, correctness, or type safety

**Easier:**
- Clear, correct, concise code
- Good type safety
- Familiar domain/codebase area
- Well-structured commits with clear intent

### What Makes Your PR Easy to Review

1. **Clarity** - Code is self-explanatory, good naming
2. **Correctness** - Logic is sound, edge cases handled
3. **Conciseness** - No unnecessary code, minimal scope
4. **Type Safety** - Proper types, no `Any` escape hatches
5. **Context** - Good PR description, link to prior discussions
6. **Scope Control** - Don't mix unrelated changes
