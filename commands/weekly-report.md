---
name: weekly-report
description: Generate weekly report from GitHub activity in team format
---

# Weekly Report Generator

Generate a weekly report based on GitHub activity AND Claude Code session history, ordered by commit activity.

## Step 1: Determine Date Range

```bash
# Get date 7 days ago
START_DATE=$(date -v-7d +%Y-%m-%d)
START_TS=$(($(date +%s) - 604800))000  # 7 days ago in milliseconds
```

## Step 2: Fetch GitHub Activity with Commit Counts

```bash
# Get all branches with commits this week and count commits per branch
gh api repos/your-org/your-repo/commits --paginate -q '.[].sha' --jq '.[] | select(.commit.author.date >= "'$START_DATE'")'

# Get PRs authored this week with their branches
gh pr list --author=@me --state=all --repo your-org/your-repo --json number,title,state,headRefName,commits --limit 50

# Count commits per branch to determine ordering
git log --since="$START_DATE" --author="user" --pretty=format:"%H %s" --all
```

## Step 3: Analyze Claude Code Sessions

```bash
# Get session prompts from the past week
cat ~/.claude/history.jsonl | jq -r '
  select(.timestamp > ('$START_TS') and
         (.display | length) > 20 and
         (.display | startswith("[Pasted") | not) and
         (.display | startswith("/") | not)) |
  "\(.timestamp | . / 1000 | strftime("%Y-%m-%d")) | \(.project | split("/") | .[-1]) | \(.display | .[0:150])"
'
```

### Session Analysis - Extract Work Items

Look for:
- **Feature work**: "implement", "add", "create", feature names
- **Bug fixes**: "fix", "debug", error investigations
- **Testing**: "puppeteer", "test", "verify"
- **DevOps**: "deploy", "n8n", "workflow", "cron"
- **Customer work**: "customer", "call", "oncall", "ad hoc"

## Step 4: Order by Commit Activity

**IMPORTANT**: Rank work items by number of commits in that branch/feature:
1. Count commits per branch from the past week
2. Map PRs/features to their branches
3. Sort descending by commit count
4. Most commits = top of list, least commits = bottom

## Step 5: Generate Report

Format:
```
This week:

- [High commit work item 1]
- [High commit work item 2]
- [Medium commit work item]
- [Low commit work item]
- Bug fixes
- Customer calls to fix ad hoc issues

Next week:

- [Carry-over items]
- [Planned items from user]
```

## Output Rules

1. **Bullet points**: Use "- " prefix for each item
2. **No PR numbers**: Never include PR numbers or status
3. **No lowercase enforcement**: Use natural capitalization
4. **Order by commits**: Most active work first, least active last
5. **Group small fixes**: Combine minor fixes into "Bug fixes"
6. **Always include**: "Customer calls to fix ad hoc issues" if any oncall/customer work detected
7. **Concise**: One line per major work item
8. **Copy to clipboard**: Always copy final output to clipboard using pbcopy

## Final Step: Copy to Clipboard

After generating the report, automatically copy to clipboard:
```bash
echo '[generated report]' | pbcopy
```

Then confirm: "Copied."

## Example Output

```
This week:

- MSSP delegated access feature: roles tab, account switching, nested tenant support
- Per-tenant SMTP config feature + UI
- Implemented inference profiles toggle + smart fallback for on-prem
- Set up n8n workflow for opensearch alerts monitoring
- Bug fixes
- Customer calls to fix ad hoc issues

Next week:

- Implement MSSP workspaces
- Ship delegated access + workspaces
```

## Interactive

After generating draft, ask:
1. Any items to add/remove?
2. What's planned for next week?

After user confirms, copy final version to clipboard.
