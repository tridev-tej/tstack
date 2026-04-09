---
description: Understand and navigate large PRs systematically - file by file, function by function, line by line
allowed-tools: ["Bash", "Read", "Grep", "Glob", "Task", "WebFetch"]
---

# Understand PR - Systematic Large PR Comprehension

Help me understand a large PR by breaking it down systematically. This is NOT about reviewing/leaving comments - it's about comprehension and building mental models of changes.

## Arguments

- `$ARGUMENTS` - PR number or URL (required)

## The Multi-Pass Methodology

Based on how experienced engineers read giant PRs:

### Pass 1: Quick Scan (Bird's Eye View)
- Files changed count and categories
- Lines added/removed statistics
- Ratio: UI vs Backend vs Tests vs Config
- Where is most new code concentrated?
- What's the apparent intent/scope?

### Pass 2: Prioritized Deep Dive
- Start with **most important/complex changes first**
- Backend logic before UI
- Core changes before peripheral
- Go file → function → line level
- Jump around for context when needed

### Pass 3: Synthesis
- Build the "story" of what this PR does
- Identify patterns and design decisions
- Note areas needing clarification

## Execution Steps

### Step 1: Fetch PR Metadata

```bash
# Get PR overview
gh pr view $PR_NUMBER --json title,body,additions,deletions,changedFiles,baseRefName,headRefName

# Get file list with stats
gh pr diff $PR_NUMBER --stat

# Get full diff
gh pr diff $PR_NUMBER
```

### Step 2: Generate Statistics Report

Output a summary like:

```
## PR #{number}: {title}

**Stats:** +{additions} / -{deletions} across {changedFiles} files
**Branch:** {headRefName} → {baseRefName}

### File Breakdown

| Category | Files | Lines Changed | % of PR |
|----------|-------|---------------|---------|
| Backend (Python) | X | +Y/-Z | AA% |
| Frontend (React/TS) | X | +Y/-Z | BB% |
| Tests | X | +Y/-Z | CC% |
| Config/Other | X | +Y/-Z | DD% |

### Concentration Analysis
- Most changes: {file_with_most_changes} (+X/-Y)
- New files: {list}
- Deleted files: {list}

### Files by Priority (for detailed review)
1. {most_important_file} - {why}
2. {second_file} - {why}
...
```

### Step 3: Prioritize Files

Rank files for detailed review using this priority:

1. **Core logic changes** - New features, algorithms, business logic
2. **API/Interface changes** - Endpoints, schemas, contracts
3. **Database changes** - Models, migrations, queries
4. **Security-sensitive** - Auth, permissions, data handling
5. **Integration points** - How components connect
6. **Configuration** - Settings, environment, dependencies
7. **Tests** - What's being tested, coverage
8. **UI components** - Last priority unless logic-heavy

### Step 4: File-by-File Walkthrough

For each prioritized file, provide:

```
## {file_path} (+{additions}/-{deletions})

### Purpose
{What this file does in 1-2 sentences}

### Key Changes
- {Change 1}: {explanation}
- {Change 2}: {explanation}

### Functions/Classes Modified
- `{function_name}`: {what changed and why}
- `{class_name}`: {what changed and why}

### Notable Lines
- L{number}: {interesting code or pattern}
- L{number}: {potential concern or question}

### Dependencies
- Imports from: {list}
- Used by: {list if known}

### Questions/Clarifications Needed
- {Question 1}
- {Question 2}
```

### Step 5: Cross-File Analysis

After individual files, analyze:

```
## Cross-Cutting Concerns

### Data Flow
{How data moves through the changes}

### New Patterns Introduced
- {Pattern}: {where and why}

### Breaking Changes
- {If any}

### Migration/Deployment Considerations
- {If any}
```

### Step 6: Summary Synthesis

```
## Understanding Summary

### What This PR Does (Plain English)
{2-3 sentence summary anyone could understand}

### Technical Summary
{Detailed technical summary}

### Design Decisions
- {Decision 1}: {rationale if apparent}
- {Decision 2}: {rationale if apparent}

### Open Questions
- {Questions to ask PR author}

### Areas Needing More Context
- {What would help understanding}
```

## Interactive Mode

After initial analysis, I should be ready to:

1. **Deep dive any file**: "Let's look at {file} in detail"
2. **Trace data flow**: "How does {X} flow through the system?"
3. **Explain functions**: "What does {function} do?"
4. **Compare before/after**: "What changed in {file}?"
5. **Find related code**: "What else uses {class/function}?"

## Time Investment Guidelines

| Code Type | Time per 100 LOC | Approach |
|-----------|------------------|----------|
| Low-stakes patterns | < 1 min | Skim for consistency |
| Standard backend | 2-5 min | Line-by-line |
| Complex/critical | 5-10+ min | Deep investigation |
| Interesting 5 lines | 15+ min | Research required |
| UI code | Minimal | Brief scan |

## Output Format

Present understanding in layers:

1. **TL;DR** - One paragraph anyone can understand
2. **Stats** - Numbers and categorization
3. **Priority List** - Files ranked by importance
4. **Deep Dives** - File-by-file breakdowns
5. **Synthesis** - Cross-cutting analysis
6. **Questions** - What needs clarification

---

## Begin

Parse the PR number/URL from arguments and start with Pass 1 (Quick Scan).
