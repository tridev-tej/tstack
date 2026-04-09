---
description: Query Prometheus metrics - check health, run PromQL queries, view alerts and targets
arguments:
  - name: action
    description: "Action: report (default), health, query, alerts, targets, nodes, databases"
    required: false
    default: "report"
  - name: query
    description: "PromQL query (for query action)"
    required: false
  - name: sort_by
    description: "Sort by: memory, cpu, load (for nodes action)"
    required: false
    default: "memory"
---

# Prometheus Query Skill

You are an expert at querying Prometheus metrics for a multi-tenant platform.

## Connection Details

```
URL: <YOUR_DOMAIN>
Username: <YOUR_USERNAME>
Password: <YOUR_PASSWORD>
```

## MCP Server Tools

This skill uses the Prometheus MCP server. Available tools:
- `mcp__prometheus__prometheus_report` - **Get comprehensive infrastructure health report** (DEFAULT)
- `mcp__prometheus__prometheus_health` - Check Prometheus health
- `mcp__prometheus__prometheus_query` - Run instant PromQL query
- `mcp__prometheus__prometheus_alerts` - Get active alerts
- `mcp__prometheus__prometheus_targets` - Get scrape targets
- `mcp__prometheus__prometheus_nodes` - Get node resource usage
- `mcp__prometheus__prometheus_databases` - Get PostgreSQL database metrics

## Action Handlers

### action: report (DEFAULT)
Get comprehensive infrastructure health report with actionable insights.

**Use MCP tool:** `mcp__prometheus__prometheus_report`

This returns:
- Overall status (targets up/down, alert count)
- Active alerts with severity
- Nodes with low memory (<50% available)
- Nodes with high load (>2.5)
- Databases with high connections (>100)
- Database sizes (>5GB)
- Summary with action items

### action: health
Check if Prometheus is healthy and responsive.

**Use MCP tool:** `mcp__prometheus__prometheus_health`

### action: query
Run an instant PromQL query.

**Use MCP tool:** `mcp__prometheus__prometheus_query` with `query` parameter

### action: alerts
Get all active alerts.

**Use MCP tool:** `mcp__prometheus__prometheus_alerts`

### action: targets
Get scrape targets and their status.

**Use MCP tool:** `mcp__prometheus__prometheus_targets`

### action: nodes
Get node resource usage sorted by memory, CPU, or load.

**Use MCP tool:** `mcp__prometheus__prometheus_nodes` with optional `sort_by` parameter

### action: databases
Get PostgreSQL database metrics (size, connections).

**Use MCP tool:** `mcp__prometheus__prometheus_databases`

## Fallback: Direct HTTP Queries

If MCP tools are NOT available, fall back to curl:

```bash
# Health check
curl -s -w "\nHTTP Status: %{http_code}" -u "<YOUR_USERNAME>:<YOUR_PASSWORD>" \
  "<YOUR_DOMAIN>/-/healthy"

# Instant query
curl -s -u "<YOUR_USERNAME>:<YOUR_PASSWORD>" \
  "<YOUR_DOMAIN>/api/v1/query?query=up" | jq .

# Active alerts
curl -s -u "<YOUR_USERNAME>:<YOUR_PASSWORD>" \
  "<YOUR_DOMAIN>/api/v1/alerts" | jq '.data.alerts'

# Targets
curl -s -u "<YOUR_USERNAME>:<YOUR_PASSWORD>" \
  "<YOUR_DOMAIN>/api/v1/targets" | jq '.data.activeTargets[] | select(.health == "down")'

# Low memory nodes
curl -s -u "<YOUR_USERNAME>:<YOUR_PASSWORD>" \
  '<YOUR_DOMAIN>/api/v1/query?query=node_memory_MemAvailable_bytes/node_memory_MemTotal_bytes*100' \
  | jq -r '.data.result[] | "\(.metric.instance)|\(.value[1] | tonumber | floor)%"' | sort -t'|' -k2 -n

# Database connections
curl -s -u "<YOUR_USERNAME>:<YOUR_PASSWORD>" \
  '<YOUR_DOMAIN>/api/v1/query?query=sum(pg_stat_activity_count)by(datname)' \
  | jq -r '.data.result[] | select(.value[1] | tonumber > 100) | "\(.metric.datname)|\(.value[1])"'

# Database sizes
curl -s -u "<YOUR_USERNAME>:<YOUR_PASSWORD>" \
  '<YOUR_DOMAIN>/api/v1/query?query=pg_database_size_bytes' \
  | jq -r '.data.result[] | "\(.metric.datname)|\(.value[1] | tonumber / 1024 / 1024 / 1024 | . * 100 | floor / 100)GB"' | sort -t'|' -k2 -rn
```

## Common PromQL Queries

### System Health
```promql
up                                    # All targets up/down
up{job="backend-web"}                 # Target health by job
```

### Node Resources
```promql
# Memory available %
node_memory_MemAvailable_bytes/node_memory_MemTotal_bytes*100

# CPU usage %
100-(avg(rate(node_cpu_seconds_total{mode="idle"}[5m]))by(instance)*100)

# Load average (5m)
node_load5

# Disk usage %
100-((node_filesystem_avail_bytes{mountpoint="/"}*100)/node_filesystem_size_bytes{mountpoint="/"})
```

### PostgreSQL
```promql
pg_stat_activity_count                           # Connections by state
sum(pg_stat_activity_count) by (datname)         # Total connections per DB
pg_database_size_bytes                           # Database sizes
```

## Execution Instructions

1. Parse user arguments: $ARGUMENTS
2. Default action is `report` - use `mcp__prometheus__prometheus_report`
3. For other actions, use the corresponding MCP tool
4. If MCP unavailable, fall back to curl commands
5. Format output in readable markdown tables
6. Highlight issues with ⚠️ emoji

## Example Invocations

User: `/prometheus`
→ Run full infrastructure health report (default)

User: `/prometheus --action health`
→ Quick health check

User: `/prometheus --action alerts`
→ Show all active alerts

User: `/prometheus --action nodes --sort_by load`
→ Show nodes sorted by load average

User: `/prometheus --action databases`
→ Show PostgreSQL database metrics

User: `/prometheus --action query --query "up{job=~\".*backend.*\"}"`
→ Run custom PromQL query

---

## Advanced Debugging Queries

### Pod Restarts and Crashes

```promql
# Recent pod restarts (last hour)
increase(kube_pod_container_status_restarts_total[1h]) > 0

# Pods restarted multiple times
sum by (pod, namespace) (increase(kube_pod_container_status_restarts_total[6h])) > 2

# OOMKilled containers
kube_pod_container_status_last_terminated_reason{reason="OOMKilled"}

# Container restart reasons
kube_pod_container_status_last_terminated_reason
```

### Event Loop Health Indicators

When async event loops block, you'll see these patterns:

```promql
# Request latency spikes (p99)
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

# Requests timing out (correlate with thread dumps)
rate(http_request_duration_seconds_count{status=~"5.."}[5m])

# Connection pool saturation
pg_stat_activity_count / pg_settings_max_connections * 100

# Long-running database queries
pg_stat_activity_max_tx_duration
```

### Resource Correlation with Crashes

```promql
# Memory at time of crash (use with crash timestamp)
node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100

# CPU during incident
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)

# Network issues
rate(node_network_receive_errs_total[5m]) > 0
rate(node_network_transmit_errs_total[5m]) > 0
```

### Database Health

```promql
# Active connections by database
sum by (datname) (pg_stat_activity_count)

# Connections waiting for lock
pg_stat_activity_count{state="idle in transaction"}

# Database size growth
pg_database_size_bytes

# Replication lag (if applicable)
pg_replication_lag
```

### Service Health During Incidents

```promql
# Targets down
up == 0

# Error rate spike
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100

# Request queue depth (if exposed)
http_request_queue_length
```

### Correlation Query Strategy

When debugging crashes:

1. **Find crash time** from OpenSearch logs
2. **Query these metrics at crash time:**
   - Memory: Was node under pressure?
   - CPU: Was there a spike?
   - Connections: Pool exhausted?
   - Request latency: Did it spike before crash?

3. **Compare healthy vs incident period:**
   ```promql
   # Healthy baseline (previous day)
   avg_over_time(metric[1h] offset 24h)

   # Incident period
   avg_over_time(metric[1h])
   ```
