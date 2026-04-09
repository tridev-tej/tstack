# Generate Ralph Loop Command Skill

This skill analyzes the current conversation context and generates an optimized Ralph Loop command for autonomous task continuation.

## When to Use

Invoke this skill when the user wants to:
- Continue a complex task autonomously
- Generate a Ralph Loop command
- Create an iterative work loop
- Resume interrupted work

## Instructions

When this skill is invoked, analyze the current conversation to extract:

### 1. Task Identification

Identify the primary task from the conversation:
- What is the user trying to accomplish?
- What files/systems are involved?
- What is the expected output?

### 2. Completion Criteria

Determine how to know when the task is complete:
- What signals success? (tests pass, feature works, bug fixed)
- What artifacts should exist? (files, screenshots, reports)
- What promise tag should be used?

### 3. Iteration Estimate

Based on task complexity:
| Task Type | Suggested Iterations |
|-----------|---------------------|
| Simple bug fix | 5-8 |
| Testing suite | 15-20 |
| Feature implementation | 15-25 |
| Code review/refactor | 8-12 |
| Research/exploration | 10-15 |
| Documentation | 5-10 |

### 4. Generate Command

Output a formatted Ralph Loop command:

```
## Generated Ralph Loop Command

Based on our conversation about [TASK_SUMMARY], here's your command:

\`\`\`
/ralph-wiggum:ralph-loop
\`\`\`

When prompted for the mission, paste this:

\`\`\`
<mission>
## [TASK_TITLE]

### Context
[Brief context from conversation]

### Goals
1. [Goal 1]
2. [Goal 2]
3. [Goal 3]

### Steps
1. [Step 1 with details]
2. [Step 2 with details]
3. [Step 3 with details]

### Success Criteria
- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] [Criterion 3]

### Output
Only output when genuinely complete:
<promise>[PROMISE_TAG]</promise>
</mission>
\`\`\`

### Settings
- **Iterations:** [N]
- **Stop Signal:** `<promise>[PROMISE_TAG]</promise>`

### To Resume If Interrupted
\`\`\`
/ralph-wiggum:ralph-loop
\`\`\`
Then provide context about where you left off.
```

## Example Output

For an MSSP testing conversation:

```
## Generated Ralph Loop Command

Based on our conversation about MSSP functional testing, here's your command:

\`\`\`
/ralph-wiggum:ralph-loop
\`\`\`

When prompted for the mission, paste this:

\`\`\`
<mission>
## MSSP Functional Testing Mission

### Context
Testing MSSP feature on branch user/mssp-session-based-child-tenant-access with browser-based UI verification.

### Goals
1. Run 70+ functional tests across 6 categories
2. Capture unique UI screenshots for each test
3. Output results to CSV file
4. Fix any bugs discovered

### Steps
1. Seed test data to child tenants using Django command
2. Create custom MSSP roles with different permissions
3. Run browser-based tests with visible browser
4. Verify each screenshot shows actual MSSP UI content
5. Write all results to ~/Downloads/mssp_test_results.csv
6. Fix failing tests and re-run

### Success Criteria
- [ ] All 70+ tests pass
- [ ] 140+ unique screenshots saved
- [ ] CSV has complete test results
- [ ] No permission boundary violations

### Output
Only output when genuinely complete:
<promise>MSSP_FUNCTIONAL_TESTING_COMPLETE</promise>
</mission>
\`\`\`

### Settings
- **Iterations:** 20
- **Stop Signal:** `<promise>MSSP_FUNCTIONAL_TESTING_COMPLETE</promise>`
```

## Key Principles

1. **Be Specific** - Include exact file paths, commands, and expected outputs
2. **Define Clear Stop Conditions** - The promise tag should only be output when truly complete
3. **Include Verification Steps** - How to verify the work is actually done
4. **Allow for Fixes** - Include steps for handling failures
5. **No Ambiguity** - The mission should be self-contained and unambiguous

## IMPORTANT: Save and Provide Command

After generating the mission, **ALWAYS**:

1. **Write the mission to file**:
   ```bash
   Write the <mission>...</mission> content to ~/ralph-mission.txt
   ```

2. **Provide this ready-to-copy command**:
   ```
   ✅ Mission saved to ~/ralph-mission.txt

   Copy this command for new conversation:
   ───────────────────────────────────────
   Read ~/ralph-mission.txt and execute the mission using Ralph Loop. Follow ALL steps, take screenshots, output to CSV, and only output the promise tag when genuinely complete.
   ───────────────────────────────────────
   ```

This way the user just copies one line and pastes it in a new conversation.
