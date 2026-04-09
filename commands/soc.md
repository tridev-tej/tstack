---
description: SOC Agent troubleshooting - investigations, infrastructure, integrations health
arguments:
  - name: action
    description: "Action: health, stuck, failed, workers, integrations, errors, quota, notify"
    required: false
    default: "health"
  - name: tenant
    description: "Tenant name (e.g., tenant-a, tenant-b, tenant-c)"
    required: false
    default: "tenant-a"
  - name: cluster
    description: "Cluster: prod, staging"
    required: false
    default: "prod"
  - name: time
    description: "Time range: 15m, 1h, 6h, 24h, 7d"
    required: false
    default: "1h"
---

# SOC Agent Troubleshooting Skill

## 🛑 MANDATORY: User Approval Before ANY Database Query

**BEFORE running ANY SQL query against the production database, you MUST:**

1. **Show the user exactly what you're about to run:**
   - The exact SQL query (formatted)
   - Which database/schema it targets
   - What data it will return

2. **Explain the safety assessment:**
   - Confirm it's a SELECT-only query (no writes)
   - Confirm no destructive keywords (INSERT, UPDATE, DELETE, DROP, etc.)
   - State the expected impact (read-only, no side effects)

3. **Ask for explicit approval** using AskUserQuestion:
   ```
   "Run this query against [database]?"
   Options: ["Yes, run it", "No, cancel"]
   ```

4. **Only proceed if user approves**

**Example approval flow:**
```
I'll run this query against <YOUR_DB_NAME> (prod):

SELECT i.id, i.status, f.title
FROM {tenant}.investigations i
JOIN {tenant}.findings f ON i.finding_id = f.id
WHERE i.status = 'FAILED'
LIMIT 50;

✅ Safety check:
- Query type: SELECT (read-only)
- No write operations
- Returns: failed investigation IDs and titles

[Ask user: "Run this query?"]
```

**NEVER skip this approval step for database queries.**

---

You have access to 3 MCP servers for SOC troubleshooting:
- `soc-investigations` - Investigation health, stuck/failed analysis
- `soc-infrastructure` - Worker pods, DB health, OOM events
- `soc-integrations` - Integration health, API metrics

## Action Handlers

### action: health (DEFAULT)
Get investigation health dashboard for a tenant.

**Call:** `mcp__soc-investigations__investigation_health`
```json
{
  "tenant": "$ARGUMENTS.tenant",
  "time_range": "$ARGUMENTS.time"
}
```

**Output:** Show stuck count, failure rate, avg completion time, confidence.

---

### action: stuck
Find investigations stuck in PENDING/TRIAGE_PENDING state.

**Call:** `mcp__soc-investigations__stuck_investigations`
```json
{
  "tenant": "$ARGUMENTS.tenant",
  "threshold_minutes": 60,
  "limit": 20
}
```

**Output:** List stuck investigations with finding details, time stuck.

---

### action: failed
Get recent failed investigations with failure reasons.

**Call:** `mcp__soc-investigations__failed_investigations`
```json
{
  "tenant": "$ARGUMENTS.tenant",
  "time_range": "$ARGUMENTS.time",
  "limit": 50
}
```

**Output:** Show failures grouped by reason (quota, LLM error, no observables, timeout).

---

### action: workers
Check SOC worker pod health.

**Call:** `mcp__soc-infrastructure__worker_health`
```json
{
  "cluster": "$ARGUMENTS.cluster",
  "namespace": "<YOUR_NAMESPACE>",
  "pod_prefix": "worker"
}
```

**Then call:** `mcp__soc-infrastructure__recent_oom_events`
```json
{
  "cluster": "$ARGUMENTS.cluster",
  "namespace": "<YOUR_NAMESPACE>"
}
```

**Output:** Worker status, restarts, OOM events.

---

### action: integrations
Check integration health for a tenant.

**Call:** `mcp__soc-integrations__integration_health`
```json
{
  "tenant": "$ARGUMENTS.tenant"
}
```

**Output:** List integrations with state (WORKING/WARNING/ERROR).

---

### action: errors
Search OpenSearch for investigation error patterns.

**Call:** `mcp__soc-investigations__investigation_errors`
```json
{
  "tenant": "$ARGUMENTS.tenant",
  "pattern": "investigation",
  "time_range": "$ARGUMENTS.time"
}
```

**Output:** Recent errors with timestamps, pods, messages.

---

### action: quota
Check LLM quota usage for a tenant.

**Call:** `mcp__soc-investigations__tenant_llm_quota`
```json
{
  "tenant": "$ARGUMENTS.tenant"
}
```

**Output:** Today's usage vs quota limits.

---

### action: notify
Send a Teams notification (requires message in follow-up).

Ask user for:
- Message text
- Severity (critical/warning/info)
- Any details to include

**Call:** `mcp__soc-investigations__notify_teams`
```json
{
  "message": "<user provided>",
  "severity": "<user provided>",
  "details": { ... }
}
```

---

## Available Tools Reference

### soc-investigations
| Tool | Description |
|------|-------------|
| `investigation_health` | Dashboard: stuck counts, failure rates, avg time |
| `stuck_investigations` | List investigations stuck >N minutes |
| `failed_investigations` | Recent failures with reasons |
| `investigation_detail` | Full detail for specific investigation |
| `investigation_timeline` | Status history with timestamps |
| `retry_analysis` | Retry count and attempts for a finding |
| `low_confidence_report` | Completed with confidence < threshold |
| `investigation_errors` | Search OpenSearch for error patterns |
| `tenant_llm_quota` | LLM usage vs quota |
| `tenant_alert_volume` | Alert ingestion rate |
| `notify_teams` | Send Teams notification |

### soc-infrastructure
| Tool | Description |
|------|-------------|
| `worker_health` | Worker pod status, restarts, memory |
| `pod_status` | Detailed pod info with events |
| `db_health` | PostgreSQL connections, slow queries |
| `queue_depth` | Task queue depth per tenant |
| `infra_report` | Combined health report |
| `recent_oom_events` | Recent OOM kills |
| `disk_io_status` | Disk I/O metrics |
| `notify_teams` | Send Teams notification |

### soc-integrations
| Tool | Description |
|------|-------------|
| `integration_health` | All integrations with state |
| `integration_errors` | Integrations with errors |
| `integration_detail` | Full detail (config masked) |
| `integration_latency` | API call latency percentiles |
| `integration_api_status` | Success/failure rates by status code |
| `credential_check` | Check credential validity |
| `entity_store_health` | Entity store timeout issues |
| `integration_report` | Comprehensive health report |
| `notify_teams` | Send Teams notification |

---

## Example Usage

```
/soc                           # Health dashboard for default tenant
/soc tenant=tenant-b           # Health for specific tenant
/soc action=stuck              # Find stuck investigations
/soc action=failed time=24h    # Failed in last 24h
/soc action=workers cluster=staging  # Check staging workers
/soc action=integrations       # Integration health
/soc action=quota              # LLM quota check
/soc action=errors time=15m    # Recent errors
```

---

## Troubleshooting Flow

1. **Start with health:** `/soc` - get overview
2. **If high failure rate:** `/soc action=failed` - check reasons
3. **If stuck investigations:** `/soc action=stuck` - list them
4. **Check infrastructure:** `/soc action=workers` - OOM/restarts?
5. **Check integrations:** `/soc action=integrations` - any errors?
6. **Deep dive errors:** `/soc action=errors` - OpenSearch logs
7. **Alert team:** `/soc action=notify` - send Teams message
