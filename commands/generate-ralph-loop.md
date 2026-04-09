# Generate Ralph Loop Command

Analyzes the current conversation and generates an optimized Ralph Loop command for autonomous task continuation.

## Trigger

- `/generate-ralph-loop`
- "create ralph command"
- "generate loop command"

## How It Works

This skill analyzes:
1. **Current task context** - What work is being done
2. **Completion criteria** - How to know when done
3. **Stop conditions** - When to halt the loop
4. **Iteration limits** - Maximum cycles to prevent runaway

## Output Format

Generates a command in this format:

```
/ralph-loop iterations=N stop="COMPLETION_SIGNAL" task="TASK_DESCRIPTION"
```

## Analysis Steps

### Step 1: Identify Task Type

| Task Type | Iterations | Stop Signal |
|-----------|------------|-------------|
| Testing | 10-20 | `ALL_TESTS_PASS` |
| Bug Fix | 5-10 | `BUG_FIXED` |
| Feature Implementation | 15-25 | `FEATURE_COMPLETE` |
| Code Review | 5-10 | `REVIEW_COMPLETE` |
| Documentation | 5-10 | `DOCS_COMPLETE` |
| Research | 10-15 | `RESEARCH_COMPLETE` |

### Step 2: Define Stop Conditions

Include these in the generated command:
- Primary completion signal (promise tag)
- Error threshold (max consecutive failures)
- Time-based limit (via iterations)
- Manual intervention triggers

### Step 3: Generate Command

Based on current conversation context, output:

```markdown
## Generated Ralph Loop Command

Copy and paste this command:

\`\`\`
/ralph-loop iterations=X stop="<promise>SIGNAL</promise>" task="DESCRIPTION"
\`\`\`

### What This Will Do:
- [List of actions]

### Stop Conditions:
- Output `<promise>SIGNAL</promise>` when complete
- Max X iterations
- Stop on critical errors

### Resume If Needed:
If interrupted, run: `/ralph-loop resume`
```

## Example Generations

### For MSSP Testing (Current Context)

```
/ralph-loop iterations=15 stop="<promise>MSSP_TESTING_COMPLETE</promise>" task="Continue MSSP functional testing: run all test suites, capture unique UI screenshots, output results to CSV, fix any failing tests, verify permission boundaries work correctly. Output the promise when all 118+ tests pass."
```

### For Bug Fix

```
/ralph-loop iterations=10 stop="<promise>BUG_FIXED</promise>" task="Fix the reported bug: investigate root cause, implement fix, write tests, verify fix works. Output the promise when the bug is resolved and tests pass."
```

### For Feature Implementation

```
/ralph-loop iterations=20 stop="<promise>FEATURE_COMPLETE</promise>" task="Implement the requested feature: design approach, write code, add tests, update documentation. Output the promise when feature is fully implemented and tested."
```
