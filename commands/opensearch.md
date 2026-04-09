---
description: Query OpenSearch logs with flexible filters (cluster, tenant, level, patterns)
arguments:
  - name: cluster
    description: "Cluster name: prod, staging, or all"
    required: false
    default: "all"
  - name: tenant
    description: "Tenant name filter (e.g., qa, public, acme)"
    required: false
  - name: level
    description: "Log level: ERROR, WARN, INFO, DEBUG, or all"
    required: false
    default: "all"
  - name: pattern
    description: "Search pattern (regex supported)"
    required: false
  - name: pod
    description: "Pod name filter (partial match)"
    required: false
  - name: time
    description: "Time range: 5m, 15m, 1h, 6h, 24h, 7d"
    required: false
    default: "15m"
  - name: limit
    description: "Max results to return"
    required: false
    default: "50"
---

# OpenSearch Log Query Skill

You are an expert at querying OpenSearch logs for a multi-tenant platform.

## Connection Details

```
URL: <YOUR_DOMAIN>
Username: admin
Password: <YOUR_PASSWORD>
```

## Index Patterns

| Cluster | Index Pattern | Kubernetes Namespace |
|---------|---------------|---------------------|
| Production | `app-*` (excluding stage) | `app`, `prod` |
| Staging | `app-stage-*` | `stage`, `preprod` |

## Available Fields

### Core Fields
- `@timestamp` - Log timestamp (ISO 8601)
- `message` - Parsed log message
- `log` - Raw log line
- `levelname` - Log level (INFO, ERROR, DEBUG, WARN)
- `tenant` - Tenant/account name
- `cid` - Correlation ID for request tracing

### Kubernetes Fields
- `kubernetes.pod_name` - Pod name
- `kubernetes.namespace_name` - Namespace (app, stage, prod, preprod)
- `kubernetes.container_name` - Container name
- `kubernetes.host` - Node hostname

### Application Fields
- `filename` - Source file
- `lineno` - Line number
- `funcName` - Function name
- `asctime` - Application timestamp

## Query Execution

Use this Python script to query OpenSearch. Modify the query based on user parameters.

```python
import json
import urllib.request
import urllib.parse
import base64
import ssl

class OpenSearchClient:
    def __init__(self):
        self.url = "<YOUR_DOMAIN>"
        self.auth = base64.b64encode(b"admin:<YOUR_PASSWORD>").decode()

    def query(self, index, query_body, size=50):
        endpoint = f"{self.url}/{index}/_search"
        data = json.dumps({"size": size, "sort": [{"@timestamp": {"order": "desc"}}], **query_body}).encode()

        req = urllib.request.Request(endpoint, data=data, method="POST")
        req.add_header("Authorization", f"Basic {self.auth}")
        req.add_header("Content-Type", "application/json")

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            return json.loads(resp.read().decode())

    def count(self, index, query_body):
        endpoint = f"{self.url}/{index}/_count"
        data = json.dumps(query_body).encode()

        req = urllib.request.Request(endpoint, data=data, method="POST")
        req.add_header("Authorization", f"Basic {self.auth}")
        req.add_header("Content-Type", "application/json")

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            return json.loads(resp.read().decode())

client = OpenSearchClient()
```

## Query Building Rules

### 1. Cluster Selection
```python
# Production only
index = "app-*,-app-stage-*"

# Staging only
index = "app-stage-*"

# All clusters
index = "app-*"
```

### 2. Time Range Filter
```python
time_ranges = {
    "5m": "now-5m",
    "15m": "now-15m",
    "1h": "now-1h",
    "6h": "now-6h",
    "24h": "now-24h",
    "7d": "now-7d"
}

# Always include time filter
{"range": {"@timestamp": {"gte": time_ranges[time_param], "lte": "now"}}}
```

### 3. Building Bool Query
```python
def build_query(cluster="all", tenant=None, level=None, pattern=None, pod=None, time="15m"):
    must = []

    # Time range (always required)
    must.append({"range": {"@timestamp": {"gte": f"now-{time}", "lte": "now"}}})

    # Tenant filter
    if tenant:
        must.append({"term": {"tenant.keyword": tenant}})

    # Log level filter
    if level and level.upper() != "ALL":
        must.append({"term": {"levelname.keyword": level.upper()}})

    # Pod name filter (wildcard)
    if pod:
        must.append({"wildcard": {"kubernetes.pod_name.keyword": f"*{pod}*"}})

    # Pattern search (in message or log field)
    if pattern:
        must.append({
            "bool": {
                "should": [
                    {"regexp": {"message": {"value": pattern, "flags": "ALL"}}},
                    {"regexp": {"log": {"value": pattern, "flags": "ALL"}}},
                    {"match_phrase": {"message": pattern}},
                    {"match_phrase": {"log": pattern}}
                ],
                "minimum_should_match": 1
            }
        })

    return {"query": {"bool": {"must": must}}}
```

## Common Query Templates

### Errors in Last Hour
```python
index = "app-*"
query = {
    "query": {
        "bool": {
            "must": [
                {"range": {"@timestamp": {"gte": "now-1h"}}},
                {"term": {"levelname.keyword": "ERROR"}}
            ]
        }
    },
    "aggs": {
        "by_tenant": {"terms": {"field": "tenant.keyword", "size": 20}},
        "by_pod": {"terms": {"field": "kubernetes.pod_name.keyword", "size": 20}}
    }
}
```

### Tenant-Specific Logs
```python
index = "app-stage-*"
query = {
    "query": {
        "bool": {
            "must": [
                {"range": {"@timestamp": {"gte": "now-15m"}}},
                {"term": {"tenant.keyword": "qa"}}
            ]
        }
    }
}
```

### Pattern Search with Context
```python
index = "app-*"
query = {
    "query": {
        "bool": {
            "must": [
                {"range": {"@timestamp": {"gte": "now-1h"}}},
                {"match_phrase": {"message": "connection refused"}}
            ]
        }
    }
}
```

### Aggregations for Overview
```python
# Get log distribution
query = {
    "size": 0,
    "query": {"range": {"@timestamp": {"gte": "now-1h"}}},
    "aggs": {
        "by_level": {"terms": {"field": "levelname.keyword"}},
        "by_tenant": {"terms": {"field": "tenant.keyword", "size": 50}},
        "by_namespace": {"terms": {"field": "kubernetes.namespace_name.keyword"}},
        "over_time": {
            "date_histogram": {
                "field": "@timestamp",
                "fixed_interval": "5m"
            }
        }
    }
}
```

## Output Formatting

Format results in a readable table:

```
TIMESTAMP            LEVEL  TENANT     POD                                    MESSAGE
-------------------- ------ ---------- -------------------------------------- ----------------------------------------
2026-01-16 04:13:45  ERROR  qa         app-postgresql-0                       connection refused to upstream service
2026-01-16 04:13:44  INFO   public     app-web-7f8b9c6d4-x2k9p                Request completed in 234ms
```

For aggregations, show summary:
```
Log Level Distribution (last 1h):
  ERROR: 1,234
  WARN:  5,678
  INFO:  123,456
  DEBUG: 234,567

Top Tenants:
  public: 45,000
  qa: 12,000
  acme: 8,500
```

## Execution Instructions

1. Parse user arguments: $ARGUMENTS
2. Determine index pattern based on cluster parameter
3. Build the query using the rules above
4. Execute via Bash with the Python script
5. Format and display results
6. If user asks for more details, offer to:
   - Expand time range
   - Show surrounding context (logs before/after)
   - Aggregate by different fields
   - Export to file

## Error Handling

- Connection errors: Check if VPN is connected
- Auth errors: Credentials may have expired
- No results: Suggest broadening filters (longer time range, remove pattern)
- Timeout: Reduce time range or add more specific filters

## Example Invocations

User: `/opensearch --cluster staging --level ERROR --time 1h`
→ Query staging cluster for all ERROR logs in last hour

User: `/opensearch --tenant qa --pattern "connection.*timeout" --time 6h`
→ Search for connection timeout patterns in qa tenant logs

User: `/opensearch --pod worker --level ERROR`
→ Find errors in worker pods

User: `/opensearch --cluster prod --tenant public --level WARN --limit 100`
→ Get 100 WARN logs from production public tenant

---

## Advanced Debugging Patterns

Generic playbook for using OpenSearch to debug a distributed Python service:

1. **Pod restarts** → search for `SIGTERM`, `SIGKILL`, health check failures
2. **Thread dumps** → search for `Thread dump` or your framework's equivalent
3. **Sync-in-async blocking** → repeated stack frames pointing to synchronous HTTP / DB / sleep calls inside `async def` functions
4. **Pre-crash context** → narrow the time range to the 30s before a crash timestamp and pin `kubernetes.pod_name.keyword`
5. **Runaway background jobs** → aggregate job-start log lines by tenant and compare against the expected cadence
6. **DB connection resets** → search for `Connection reset by peer`, `unexpected EOF`, `could not receive data from client`

### Root Cause Analysis Checklist

1. Pod restarts? Search for SIGTERM / health check failure patterns
2. Thread dumps present? Search for the framework's thread dump marker
3. Same stack trace repeated? Indicates blocking
4. Sync function in async code? Look for `requests`, `time.sleep`
5. Single tenant affected? Check tenant-specific integrations
6. All pods affected? Systemic code issue
7. High job frequency? Check background task configs
