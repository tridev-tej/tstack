---
description: Get error status report with RCA, stacktraces, and affected tenants for prod/staging
arguments:
  - name: cluster
    description: "Cluster: prod, staging, or all"
    required: false
    default: "all"
  - name: time
    description: "Time range: 1h, 6h, 12h, 24h, 7d"
    required: false
    default: "12h"
  - name: severity
    description: "Minimum severity: critical, high, medium, low"
    required: false
    default: "low"
---

# Error Status Report Skill

Generate a comprehensive error status report with RCA, stacktraces, and affected tenants.

## Connection Details

```python
URL = "<YOUR_DOMAIN>"
AUTH = base64.b64encode("user:<YOUR_PASSWORD>".encode()).decode()
```

## Execution Script

Run this Python script to generate the status report:

```python
#!/usr/bin/env python3
"""Error Status Report - RCA, Stacktraces, Affected Tenants"""

import json
import urllib.request
import base64
import ssl
from collections import defaultdict
from datetime import datetime

URL = "<YOUR_DOMAIN>"
AUTH = base64.b64encode("user:<YOUR_PASSWORD>".encode()).decode()

# Severity classification rules
SEVERITY_RULES = {
    "CRITICAL": [
        "database.*down", "connection.*refused", "out of memory", "disk.*full",
        "cluster.*red", "data.*loss", "security.*breach", "authentication.*failed.*mass",
        "ssl.*certificate.*expired", "quota.*exceeded.*100%", "deadlock", "corruption"
    ],
    "HIGH": [
        "column.*does not exist", "migration.*failed", "timeout.*exceeded",
        "connection.*reset", "internal server error", "500", "502", "503", "504",
        "rate.*limit", "quota.*exceeded", "unauthorized.*401", "forbidden.*403",
        "null.*pointer", "index.*out.*range", "key.*error", "attribute.*error"
    ],
    "MEDIUM": [
        "warning", "deprecated", "retry", "reconnect", "slow.*query",
        "high.*latency", "memory.*pressure", "cpu.*high", "queue.*full",
        "cache.*miss", "stale.*data"
    ],
    "LOW": [
        "info", "debug", "notice"
    ]
}

# Generic error patterns for RCA. Extend this dict with your own known patterns.
RCA_PATTERNS = {
    "401.*Unauthorized": {
        "rca": "Invalid or expired API credentials for external integration",
        "fix": "Refresh/update integration credentials",
        "severity": "HIGH",
        "category": "Authentication"
    },
    "connection.*refused": {
        "rca": "Target service unavailable or network issue",
        "fix": "Check target service health and network connectivity",
        "severity": "CRITICAL",
        "category": "Connectivity"
    },
    "timeout": {
        "rca": "Operation exceeded time limit - possible performance issue",
        "fix": "Check service performance, increase timeout, or optimize query",
        "severity": "HIGH",
        "category": "Performance"
    },
    "out of memory": {
        "rca": "Pod/container memory exhausted",
        "fix": "Increase memory limits or investigate memory leak",
        "severity": "CRITICAL",
        "category": "Resources"
    },
    "rate.*limit": {
        "rca": "External API rate limit exceeded",
        "fix": "Implement backoff or request rate limit increase",
        "severity": "MEDIUM",
        "category": "Rate Limiting"
    },
    "SSL.*certificate": {
        "rca": "SSL/TLS certificate issue",
        "fix": "Renew or fix certificate configuration",
        "severity": "CRITICAL",
        "category": "Security"
    },
    "parse error": {
        "rca": "Malformed data received - JSON/XML parsing failed",
        "fix": "Check data source format and validation",
        "severity": "MEDIUM",
        "category": "Data Parsing"
    },
    "Health check failed": {
        "rca": "Service health check failing repeatedly",
        "fix": "Investigate dependent services and restart if needed",
        "severity": "HIGH",
        "category": "Health"
    },
    "Connection reset by peer": {
        "rca": "Client connections timing out - possible event loop blocking or high load",
        "fix": "Check for sync-in-async patterns, connection pool settings, or scale resources",
        "severity": "HIGH",
        "category": "Connection"
    }
}

def request(endpoint, body=None):
    url = f"{URL}/{endpoint}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    req.add_header("Authorization", f"Basic {AUTH}")
    req.add_header("Content-Type", "application/json")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
        return json.loads(resp.read().decode())

def get_index(cluster):
    if cluster == "staging":
        return "app-stage-*"
    elif cluster == "prod":
        return "app-*,-app-stage-*"
    return "app-*"

def classify_severity(message):
    msg_lower = message.lower() if message else ""
    for severity, patterns in SEVERITY_RULES.items():
        for pattern in patterns:
            import re
            if re.search(pattern, msg_lower):
                return severity
    return "LOW"

def get_rca(message, exc_info=""):
    combined = f"{message} {exc_info}".lower()
    for pattern, info in RCA_PATTERNS.items():
        import re
        if re.search(pattern.lower(), combined):
            return info
    return None

def generate_report(cluster="all", time="12h"):
    index = get_index(cluster)

    # Query for all ERROR logs with aggregations
    query = {
        "size": 500,
        "sort": [{"@timestamp": {"order": "desc"}}],
        "query": {
            "bool": {
                "must": [
                    {"range": {"@timestamp": {"gte": f"now-{time}"}}},
                    {"term": {"levelname.keyword": "ERROR"}}
                ]
            }
        },
        "aggs": {
            "by_tenant": {"terms": {"field": "tenant.keyword", "size": 100}},
            "by_pod": {"terms": {"field": "kubernetes.pod_name.keyword", "size": 50}},
            "by_file": {"terms": {"field": "filename.keyword", "size": 30}},
            "by_message": {"terms": {"field": "message.keyword", "size": 100}},
            "over_time": {
                "date_histogram": {"field": "@timestamp", "fixed_interval": "1h"}
            }
        }
    }

    result = request(f"{index}/_search", query)
    hits = result.get("hits", {})
    aggs = result.get("aggregations", {})
    total_errors = hits.get("total", {}).get("value", 0)

    # Group errors by unique message pattern
    error_groups = defaultdict(lambda: {
        "count": 0,
        "tenants": set(),
        "pods": set(),
        "files": set(),
        "first_seen": None,
        "last_seen": None,
        "sample_stacktrace": None,
        "severity": "LOW",
        "rca": None
    })

    for hit in hits.get("hits", []):
        src = hit.get("_source", {})
        msg = src.get("message", "")[:200]  # Truncate for grouping
        exc_info = src.get("exc_info", "")
        tenant = src.get("tenant", "unknown")
        pod = src.get("kubernetes", {}).get("pod_name", "unknown")
        filename = src.get("filename", "unknown")
        ts = src.get("@timestamp", "")

        group = error_groups[msg]
        group["count"] += 1
        group["tenants"].add(tenant)
        group["pods"].add(pod)
        group["files"].add(filename)

        if not group["first_seen"] or ts < group["first_seen"]:
            group["first_seen"] = ts
        if not group["last_seen"] or ts > group["last_seen"]:
            group["last_seen"] = ts

        if exc_info and not group["sample_stacktrace"]:
            group["sample_stacktrace"] = exc_info

        severity = classify_severity(f"{msg} {exc_info}")
        if SEVERITY_RULES.keys() and list(SEVERITY_RULES.keys()).index(severity) < list(SEVERITY_RULES.keys()).index(group["severity"]):
            group["severity"] = severity

        if not group["rca"]:
            group["rca"] = get_rca(msg, exc_info)

    # Sort by severity then count
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    sorted_errors = sorted(
        error_groups.items(),
        key=lambda x: (severity_order.get(x[1]["severity"], 4), -x[1]["count"])
    )

    return {
        "total_errors": total_errors,
        "time_range": time,
        "cluster": cluster,
        "errors": sorted_errors,
        "tenant_summary": aggs.get("by_tenant", {}).get("buckets", []),
        "pod_summary": aggs.get("by_pod", {}).get("buckets", []),
        "timeline": aggs.get("over_time", {}).get("buckets", [])
    }

def print_report(report):
    print("=" * 100)
    print(f"ERROR STATUS REPORT - {report['cluster'].upper()} (Last {report['time_range']})")
    print(f"Generated: {datetime.now().isoformat()}")
    print(f"Total Errors: {report['total_errors']:,}")
    print("=" * 100)

    # Summary by severity
    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for msg, data in report["errors"]:
        severity_counts[data["severity"]] += data["count"]

    print("\n## SEVERITY SUMMARY")
    print(f"  🔴 CRITICAL: {severity_counts['CRITICAL']:,}")
    print(f"  🟠 HIGH:     {severity_counts['HIGH']:,}")
    print(f"  🟡 MEDIUM:   {severity_counts['MEDIUM']:,}")
    print(f"  🟢 LOW:      {severity_counts['LOW']:,}")

    # Top affected tenants
    print("\n## TOP AFFECTED TENANTS")
    for t in report["tenant_summary"][:10]:
        print(f"  {t['key']:<30} {t['doc_count']:>8,} errors")

    # Detailed errors by severity
    print("\n" + "=" * 100)
    print("## ERRORS RANKED BY SEVERITY")
    print("=" * 100)

    current_severity = None
    for i, (msg, data) in enumerate(report["errors"][:30], 1):
        if data["severity"] != current_severity:
            current_severity = data["severity"]
            severity_emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(current_severity, "⚪")
            print(f"\n### {severity_emoji} {current_severity} SEVERITY")
            print("-" * 80)

        print(f"\n[{i}] Count: {data['count']:,} | Tenants: {len(data['tenants'])} | Pods: {len(data['pods'])}")
        print(f"    First: {data['first_seen'][:19] if data['first_seen'] else 'N/A'} | Last: {data['last_seen'][:19] if data['last_seen'] else 'N/A'}")
        print(f"    Message: {msg[:100]}")
        print(f"    Files: {', '.join(list(data['files'])[:3])}")
        print(f"    Tenants: {', '.join(list(data['tenants'])[:5])}")

        if data["rca"]:
            print(f"\n    📋 RCA: {data['rca']['rca']}")
            print(f"    🔧 FIX: {data['rca']['fix']}")
            print(f"    📁 Category: {data['rca']['category']}")

        if data["sample_stacktrace"]:
            print(f"\n    📜 STACKTRACE:")
            for line in data["sample_stacktrace"].split("\n")[:15]:
                print(f"       {line[:100]}")

    print("\n" + "=" * 100)
    print("## POD HEALTH SUMMARY")
    print("-" * 80)
    for p in report["pod_summary"][:15]:
        print(f"  {p['key'][:55]:<55} {p['doc_count']:>8,} errors")

if __name__ == "__main__":
    import sys
    cluster = sys.argv[1] if len(sys.argv) > 1 else "all"
    time = sys.argv[2] if len(sys.argv) > 2 else "12h"
    report = generate_report(cluster, time)
    print_report(report)
```

## Usage Instructions

1. Parse user arguments from $ARGUMENTS
2. Execute the Python script with cluster and time parameters
3. The script will:
   - Query all ERROR logs from OpenSearch
   - Group by unique error message
   - Classify severity (CRITICAL > HIGH > MEDIUM > LOW)
   - Match against known RCA patterns
   - Extract stacktraces
   - List affected tenants
   - Rank by severity then count

## Example Invocations

```bash
/status                           # All clusters, last 12h
/status --cluster staging         # Staging only
/status --cluster prod --time 24h # Production, last 24h
/status --severity high           # Only HIGH+ severity
```

## Output Format

The report includes:
1. **Severity Summary** - Counts by CRITICAL/HIGH/MEDIUM/LOW
2. **Top Affected Tenants** - Most impacted tenants
3. **Errors Ranked by Severity** - Each error with:
   - Count and affected tenants/pods
   - First/last occurrence
   - RCA (Root Cause Analysis) if pattern matched
   - Recommended fix
   - Full stacktrace
4. **Pod Health Summary** - Errors by pod

## Severity Classification

| Severity | Patterns |
|----------|----------|
| CRITICAL | DB down, OOM, disk full, security breach, SSL expired |
| HIGH | Missing columns, 5xx errors, auth failures, timeouts |
| MEDIUM | Warnings, retries, slow queries, cache misses |
| LOW | Info, debug, notices |

## Known RCA Patterns

The skill auto-detects and provides RCA for:
- Missing database migrations
- Quota exhaustion
- Authentication failures
- Connection issues
- Timeout problems
- Memory issues
- Rate limiting
- SSL/TLS problems
- Parse errors
- Health check failures

---

## Advanced Debugging Playbook

Generic workflow for triaging prod incidents:

1. **Gather symptoms** — what's broken, when did it start, which tenants affected
2. **Infrastructure health** — check `/prometheus` and aggregate error counts
3. **Identify crash patterns** — search logs for SIGTERM / health check failures
4. **Analyze thread dumps** — look for repeated stack frames, especially sync calls inside async functions
5. **Check job frequency** — aggregate job-start events by tenant and compare against expected cadence
6. **Correlate with deployments** — check image tags and error rate before/after
7. **Document findings** — root cause, evidence, fix, prevention

### RCA Decision Tree

```
Pod Restarts/Crashes
├── Health check failures?
│   ├── Yes → Event loop likely blocked
│   │   └── Check thread dumps for sync-in-async
│   └── No → Check resource limits
│       ├── OOMKilled? → Memory leak or undersized
│       └── CPU throttled? → Performance issue
│
UI Unresponsive
├── Backend healthy?
│   ├── Yes → Event loop blocked
│   │   └── Thread dump analysis
│   └── No → Database/service issue
│
High Error Rate
├── Single tenant? → Tenant-specific issue (credentials, config)
└── Cross-tenant? → System-wide issue (recent deploy, infra)
```

### MCP Tools Quick Reference

```python
mcp__opensearch__opensearch_logs(cluster="prod", pattern="...", time="6h")
mcp__opensearch__opensearch_errors(cluster="prod", time="1h")
mcp__opensearch__opensearch_count(cluster="prod", pattern="...", tenant="...")
mcp__opensearch__opensearch_agg(cluster="prod", field="tenant", time="1h")
mcp__prometheus__prometheus_report()
```
