---
description: Create, update, and manage Jira tickets in the user's format
arguments:
  - name: action
    description: "Action: create, update, status, close, backlog, assign, list"
    required: true
  - name: title
    description: "Ticket title (for create) or ticket key (for update/status/close)"
    required: true
  - name: release
    description: "Release date: 'this-week', 'next-week', 'YYYY-MM-DD', or 'R2026-02-23' format"
    required: false
  - name: status
    description: "Target status: todo, inprogress, done"
    required: false
  - name: description
    description: "Ticket description"
    required: false
  - name: pr
    description: "PR number(s) to link in description"
    required: false
---

# Jira Ticket Manager

Manage Jira tickets following the user's conventions.

## Mandatory Fields (EVERY ticket, NO exceptions)

| Field | Value | Notes |
|-------|-------|-------|
| **Project** | `<YOUR_JIRA_PROJECT_KEY>` | Always |
| **Title** | `R{YYYY-MM-DD} {description}` | Release date prefix is MANDATORY |
| **Assignee** | `<YOUR_USER_ID>` | Always the user |
| **Labels** | `R{YYYY-MM-DD}` + 1-3 domain labels | Add via `editJiraIssue` after creation |
| **Description** | Structured markdown (see style guide below) | Never leave blank |
| **Status** | Transition after creation | Default = To Do, transition if --status given |

## Conventions (MUST FOLLOW)

1. **Title format**: `R{YYYY-MM-DD} {Task description}`
   - The `R` prefix + date = release date (NO dash after R: `R2026-02-23` not `R-2026-02-23`)
   - Example: `R2026-02-23 Fix DB connection pool exhaustion from leaked sync_to_async calls`
   - Release date = next Monday after the PR merge date (for completed work)

2. **Release date calculation**:
   - `this-week` = Monday of current week
   - `next-week` = Monday of next week
   - `YYYY-MM-DD` = exact date
   - For completed work without explicit release: use next Monday after PR merge date
   - **NEVER skip the release date** — if unsure, ask

3. **Issue type**: `Task` (always)

4. **Transition IDs**:
   - `11` = To Do
   - `21` = In Progress
   - `31` = Done

5. **PR grouping rules**:
   - Main branch PR + release cherry-pick PR = **ONE ticket** (not two)
   - Multiple related fixes for same root cause = **ONE ticket** (group them)
   - Unrelated fixes = separate tickets even if in same timeframe

6. **Labels are MANDATORY** — every ticket gets:
   - Release date label: `R2026-XX-XX` (matches title prefix)
   - 1-3 domain labels from: `bug-fix`, `feature`, `hotfix`, `mssp`, `saml`, `auth`, `aws-marketplace`, `db-pool`, `performance`, `security`, `on-call`, `incident-response`, `production-stability`, `code-review`, `team-support`, `chore`, `django-async`, `dependency-upgrade`

7. **Description is MANDATORY** — must include:
   - What changed (PRs with links)
   - Root cause (for bug fixes — explain the technical WHY)
   - Impact (which tenants/users were affected)

## Actions

### `create` - Create a new ticket

**3-step flow: Create → Label → Transition (all mandatory)**

1. **Calculate release date** from `--release` argument:
   - `this-week`: find this week's Monday date
   - `next-week`: find next week's Monday date
   - `YYYY-MM-DD`: use as-is
   - No release given + PR provided: calculate next Monday after PR merge date
   - No release given + no PR: ASK the user (don't skip it)

2. **Create the ticket**:
   ```
   mcp__atlassian__createJiraIssue(
     cloudId: "<YOUR_CLOUD_ID>",
     projectKey: "PP",
     issueTypeName: "Task",
     summary: "R{date} {title}",
     description: "{structured description — see style guide}",
     assignee_account_id: "<YOUR_USER_ID>"
   )
   ```

3. **Add labels** (MANDATORY — do this immediately after creation):
   ```
   mcp__atlassian__editJiraIssue(
     cloudId: "<YOUR_CLOUD_ID>",
     issueIdOrKey: "PP-XXX",
     fields: {"labels": ["R{date}", "{domain-label-1}", "{domain-label-2}"]}
   )
   ```

4. **Transition status** (if `--status` provided):
   ```
   mcp__atlassian__transitionJiraIssue(
     cloudId: "<YOUR_CLOUD_ID>",
     issueIdOrKey: "PP-XXX",
     transition: {"id": "31"}  // 21=InProgress, 31=Done
   )
   ```

5. **Confirm** to user: `Created PP-XXX — "R{date} {title}" | {Status} | Labels: {labels}`

### `update` - Update an existing ticket

`--title` = ticket key (e.g., PP-85)

1. Parse what needs updating from arguments
2. If `--release` provided, update title with new release prefix
3. If `--status` provided, transition to that status
4. If `--description` provided, update description
5. Use `mcp__atlassian__jira_update_issue` for field changes
6. Use `mcp__atlassian__jira_transition_issue` for status changes

### `status` - Move ticket to a status

`--title` = ticket key, `--status` = target status

1. Get ticket key from `--title`
2. Transition:
   - `todo`: ID `11`
   - `inprogress`: ID `21`
   - `done`: ID `31`

### `close` - Mark ticket as Done

`--title` = ticket key

1. Transition to Done (ID `31`)

### `backlog` - Create ticket and leave in To Do

Same as `create` but explicitly do NOT transition. Leave in To Do.

### `assign` - Assign ticket to the user

`--title` = ticket key

1. Update assignee to `user@example.com`

### `list` - List my current tickets

1. Search: `project = PP AND assignee = currentUser() AND status != Done ORDER BY created DESC`
2. Display as table: Key | Title | Status

## Examples

```
/jira --action create --title "Fix SAML vulnerability" --release next-week --status inprogress --pr 3758
→ Creates: PP-XX "R2026-02-16 Fix SAML vulnerability" | In Progress | Assigned to the user

/jira --action create --title "Prod hotfix cato networks" --release this-week --status done
→ Creates: PP-XX "R2026-02-09 Prod hotfix cato networks" | Done | Assigned to the user

/jira --action close --title PP-85
→ Transitions PP-85 to Done

/jira --action status --title PP-87 --status inprogress
→ Transitions PP-87 to In Progress

/jira --action update --title PP-85 --release 2026-02-23
→ Updates PP-85 title to have R2026-02-23 prefix

/jira --action backlog --title "LLM error codes" --release 2026-02-23 --pr 3707
→ Creates: PP-XX "R2026-02-23 LLM error codes" | To Do | Assigned to the user

/jira --action list
→ Shows all open PP tickets assigned to the user
```

## Ticket Description Style Guide

When creating tickets, follow these patterns learned from the user's actual tickets:

### For bug fix tickets (single PR or main+cherry-pick pair):
```
**PR:** https://github.com/your-org/your-repo/pull/{number}

**What:** {One line summary of the fix}

**Changes:**
* {file/area} - {what changed}
* {file/area} - {what changed}

**Root cause:** {Why the bug happened — be specific about the technical chain of events}

**Impact:** {Which tenants/users were affected and how}
```

### For multi-PR fix tickets (grouped related fixes):
```
Fixed {high-level description of what was broken}.

### PRs
- #{number} (main) - {title}
- #{number} (release) - {title}
- #{number} - {title}

All merged {date range}.
```

### For feature tickets:
```
{Brief description of what the feature does and why.}

### PRs
- #{number} (main) - {title}
- #{number} (release cherry-pick) - {title}

### Related tickets
- PP-XX - {related ticket description}
```

### For meta/aggregate tickets (PR reviews, on-call, incident response):
```
**{Context line — date range, scope}**

{What this ticket captures beyond individual code fixes}

**{Category 1} ({team members involved})**
* #{number} - {title}
* #{number} - {title}

**{Category 2}**
* #{number} - {title}

**Impact:**
* {Quantified result}
* {Quantified result}
```

### Key style rules:
- **Root cause is gold** — always explain WHY, not just what. Technical chain of events.
- **Be specific** — name the tenants affected, the exact error, the Django ticket number
- **Group cherry-picks** — main PR + release cherry-pick go on the same ticket, not separate ones
- **Cross-reference** — link related tickets with `Related tickets: PP-XX, PP-YY`
- **No fluff** — skip "This PR implements..." or formal language. Be direct.
- **Use markdown bold** for section headers within description, not H1/H2

## Labels Convention

Always add labels to tickets. Common labels:

| Label | When to use |
|-------|-------------|
| `R2026-XX-XX` | Release date (matches title prefix) |
| `bug-fix` | Bug fix PRs |
| `feature` | New feature |
| `hotfix` | Urgent production fix |
| `mssp` | MSSP/multi-tenant related |
| `saml`, `auth` | Authentication related |
| `aws-marketplace` | AWS Marketplace related |
| `db-pool` | Database connection issues |
| `performance` | Performance improvements |
| `security` | Security fixes/vulnerabilities |
| `on-call` | On-call/incident response work |
| `incident-response` | Production incident triage |
| `production-stability` | Prod stabilization efforts |
| `code-review` | PR review activity |
| `team-support` | Cross-team support work |
| `chore` | Minor maintenance tasks |

**Always include the release date label** (`R2026-XX-XX`) on every ticket.
Add 1-3 domain labels that categorize the work.

## Error Handling

- If transition fails, fetch available transitions first with `mcp__atlassian__jira_get_transitions`
- If assignee fails with email, try account ID: `<YOUR_USER_ID>`
- Always confirm action to user after completion with ticket key and final state
- Always use `editJiraIssue` with `{"labels": [...]}` to add labels after creation

## Atlassian Config

- Cloud ID: `<YOUR_CLOUD_ID>`
- Instance: `<YOUR_JIRA_INSTANCE>.atlassian.net`
- Assignee account ID: `<YOUR_USER_ID>`
- GitHub repo: `your-org/your-repo`
