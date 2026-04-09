#!/usr/bin/env python3
"""
Error Status Report - RCA, Stacktraces, Affected Tenants
Usage: python status_report.py [cluster] [time]
  cluster: prod, staging, or all (default: all)
  time: 1h, 6h, 12h, 24h, 7d (default: 12h)
"""

import json
import urllib.request
import base64
import ssl
import re
import os
from collections import defaultdict
from datetime import datetime
import sys

URL = os.environ.get("OPENSEARCH_URL", "https://opensearch.example.com")
_user = os.environ.get("OPENSEARCH_USER", "admin")
_pass = os.environ.get("OPENSEARCH_PASSWORD", "")
AUTH = base64.b64encode(f"{_user}:{_pass}".encode()).decode()

SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

SEVERITY_RULES = {
    "CRITICAL": [
        r"database.*down", r"connection.*refused", r"out of memory", r"disk.*full",
        r"cluster.*red", r"data.*loss", r"security.*breach", r"authentication.*failed.*mass",
        r"ssl.*certificate.*expired", r"quota.*exceeded.*100%", r"deadlock", r"corruption",
        r"oom", r"killed", r"fatal"
    ],
    "HIGH": [
        r"column.*does not exist", r"migration.*failed", r"timeout.*exceeded",
        r"connection.*reset", r"internal server error", r"\b500\b", r"\b502\b", r"\b503\b", r"\b504\b",
        r"rate.*limit", r"quota.*exceeded", r"unauthorized", r"\b401\b", r"forbidden", r"\b403\b",
        r"null.*pointer", r"index.*out.*range", r"key.*error", r"attribute.*error",
        r"undefined.*column", r"relation.*does not exist", r"programming.*error"
    ],
    "MEDIUM": [
        r"warning", r"deprecated", r"retry", r"reconnect", r"slow.*query",
        r"high.*latency", r"memory.*pressure", r"cpu.*high", r"queue.*full",
        r"cache.*miss", r"stale.*data", r"parse.*error"
    ],
    "LOW": [
        r"info", r"debug", r"notice"
    ]
}

RCA_PATTERNS = {
    r"column.*does not exist": {
        "rca": "Database schema mismatch - missing column from migration",
        "fix": "Check pending migrations: python manage.py showmigrations",
        "severity": "HIGH",
        "category": "Database Migration"
    },
    r"daily quota.*has been reached": {
        "rca": "Tenant LLM quota exhausted",
        "fix": "Wait for quota reset or increase tenant quota in admin panel",
        "severity": "MEDIUM",
        "category": "Quota/Limits"
    },
    r"401.*unauthorized|unauthorized.*401": {
        "rca": "Invalid or expired API credentials for external integration",
        "fix": "Refresh/update integration credentials in tenant settings",
        "severity": "HIGH",
        "category": "Authentication"
    },
    r"connection.*refused": {
        "rca": "Target service unavailable or network issue",
        "fix": "Check target service health and network connectivity",
        "severity": "CRITICAL",
        "category": "Connectivity"
    },
    r"timeout|timed out": {
        "rca": "Operation exceeded time limit - possible performance issue",
        "fix": "Check service performance, increase timeout, or optimize query",
        "severity": "HIGH",
        "category": "Performance"
    },
    r"out of memory|oom|killed": {
        "rca": "Pod/container memory exhausted",
        "fix": "Increase memory limits or investigate memory leak",
        "severity": "CRITICAL",
        "category": "Resources"
    },
    r"rate.*limit": {
        "rca": "External API rate limit exceeded",
        "fix": "Implement backoff or request rate limit increase",
        "severity": "MEDIUM",
        "category": "Rate Limiting"
    },
    r"ssl.*certificate|certificate.*expired": {
        "rca": "SSL/TLS certificate issue",
        "fix": "Renew or fix certificate configuration",
        "severity": "CRITICAL",
        "category": "Security"
    },
    r"parse error|invalid json|malformed": {
        "rca": "Malformed data received - JSON/XML parsing failed",
        "fix": "Check data source format and validation",
        "severity": "MEDIUM",
        "category": "Data Parsing"
    },
    r"health check failed": {
        "rca": "Service health check failing repeatedly",
        "fix": "Investigate dependent services and restart if needed",
        "severity": "HIGH",
        "category": "Health"
    },
    r"deadlock": {
        "rca": "Database deadlock detected",
        "fix": "Review transaction isolation and query patterns",
        "severity": "CRITICAL",
        "category": "Database"
    },
    r"disk.*full|no space left": {
        "rca": "Disk space exhausted",
        "fix": "Clean up disk space or increase volume size",
        "severity": "CRITICAL",
        "category": "Resources"
    },
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
    with urllib.request.urlopen(req, context=ctx, timeout=120) as resp:
        return json.loads(resp.read().decode())


def get_index(cluster):
    if cluster == "staging":
        return "app-stage-*"
    elif cluster == "prod":
        return "app-*,-app-stage-*"
    return "app-*"


def classify_severity(message, exc_info=""):
    combined = f"{message} {exc_info}".lower()
    for severity in SEVERITY_ORDER:
        for pattern in SEVERITY_RULES.get(severity, []):
            if re.search(pattern, combined, re.IGNORECASE):
                return severity
    return "LOW"


def get_rca(message, exc_info=""):
    combined = f"{message} {exc_info}".lower()
    for pattern, info in RCA_PATTERNS.items():
        if re.search(pattern, combined, re.IGNORECASE):
            return info
    return None


def normalize_message(msg):
    """Normalize message for grouping by removing UUIDs, timestamps, IDs"""
    if not msg:
        return ""
    msg = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '<UUID>', msg, flags=re.I)
    msg = re.sub(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', '<TIMESTAMP>', msg)
    msg = re.sub(r'\b\d{5,}\b', '<ID>', msg)
    msg = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '<IP>', msg)
    return msg[:200]


def generate_report(cluster="all", time="12h"):
    index = get_index(cluster)

    query = {
        "size": 1000,
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
            "by_namespace": {"terms": {"field": "kubernetes.namespace_name.keyword", "size": 20}},
            "by_file": {"terms": {"field": "filename.keyword", "size": 30}},
            "over_time": {
                "date_histogram": {"field": "@timestamp", "fixed_interval": "1h"}
            }
        }
    }

    result = request(f"{index}/_search", query)
    hits = result.get("hits", {})
    aggs = result.get("aggregations", {})
    total_errors = hits.get("total", {}).get("value", 0)

    error_groups = defaultdict(lambda: {
        "count": 0,
        "tenants": set(),
        "pods": set(),
        "files": set(),
        "namespaces": set(),
        "first_seen": None,
        "last_seen": None,
        "sample_message": None,
        "sample_stacktrace": None,
        "severity": "LOW",
        "rca": None
    })

    for hit in hits.get("hits", []):
        src = hit.get("_source", {})
        raw_msg = src.get("message", src.get("log", ""))
        exc_info = src.get("exc_info", "")
        tenant = src.get("tenant", "unknown")
        pod = src.get("kubernetes", {}).get("pod_name", "unknown")
        namespace = src.get("kubernetes", {}).get("namespace_name", "unknown")
        filename = src.get("filename", "unknown")
        lineno = src.get("lineno", "")
        ts = src.get("@timestamp", "")

        normalized = normalize_message(raw_msg)
        group = error_groups[normalized]
        group["count"] += 1
        if tenant and tenant != "unknown":
            group["tenants"].add(tenant)
        group["pods"].add(pod)
        group["namespaces"].add(namespace)
        if filename != "unknown":
            file_loc = f"{filename}:{lineno}" if lineno else filename
            group["files"].add(file_loc)

        if not group["first_seen"] or ts < group["first_seen"]:
            group["first_seen"] = ts
        if not group["last_seen"] or ts > group["last_seen"]:
            group["last_seen"] = ts

        if not group["sample_message"]:
            group["sample_message"] = raw_msg[:500] if isinstance(raw_msg, str) else str(raw_msg)[:500]

        if exc_info and not group["sample_stacktrace"]:
            group["sample_stacktrace"] = exc_info

        severity = classify_severity(raw_msg, exc_info)
        if SEVERITY_ORDER.index(severity) < SEVERITY_ORDER.index(group["severity"]):
            group["severity"] = severity

        if not group["rca"]:
            group["rca"] = get_rca(raw_msg, exc_info)

    sorted_errors = sorted(
        error_groups.items(),
        key=lambda x: (SEVERITY_ORDER.index(x[1]["severity"]), -x[1]["count"])
    )

    return {
        "total_errors": total_errors,
        "time_range": time,
        "cluster": cluster,
        "errors": sorted_errors,
        "tenant_summary": aggs.get("by_tenant", {}).get("buckets", []),
        "pod_summary": aggs.get("by_pod", {}).get("buckets", []),
        "namespace_summary": aggs.get("by_namespace", {}).get("buckets", []),
        "file_summary": aggs.get("by_file", {}).get("buckets", []),
        "timeline": aggs.get("over_time", {}).get("buckets", [])
    }


def print_report(report):
    cluster_label = report['cluster'].upper()
    if report['cluster'] == 'all':
        cluster_label = 'PROD + STAGING'

    print("=" * 120)
    print(f"  ERROR STATUS REPORT - {cluster_label}")
    print(f"  Time Range: Last {report['time_range']} | Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Total Errors: {report['total_errors']:,}")
    print("=" * 120)

    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for msg, data in report["errors"]:
        severity_counts[data["severity"]] += data["count"]

    print(f"\n  CRITICAL: {severity_counts['CRITICAL']:>8,}  |  HIGH: {severity_counts['HIGH']:>8,}  |  MEDIUM: {severity_counts['MEDIUM']:>8,}  |  LOW: {severity_counts['LOW']:>8,}")

    print("\n## TOP AFFECTED TENANTS")
    print("-" * 60)
    for t in report["tenant_summary"][:15]:
        print(f"  {t['key']:<25} {t['doc_count']:>8,}")

    print("\n" + "=" * 120)
    print("  ERRORS RANKED BY SEVERITY (with RCA & Stacktraces)")
    print("=" * 120)

    current_severity = None
    error_num = 0

    for normalized_msg, data in report["errors"][:40]:
        if data["severity"] != current_severity:
            current_severity = data["severity"]
            print(f"\n{'='*120}")
            print(f"  {current_severity} SEVERITY ERRORS")
            print(f"{'='*120}")

        error_num += 1
        tenants_list = list(data['tenants'])[:10]
        pods_list = list(data['pods'])[:5]
        files_list = list(data['files'])[:3]

        print(f"\n  [{error_num}]")
        print(f"  Count: {data['count']:,} occurrences")
        print(f"  Time: {data['first_seen'][:19] if data['first_seen'] else 'N/A'} -> {data['last_seen'][:19] if data['last_seen'] else 'N/A'}")
        print(f"  Tenants ({len(data['tenants'])}): {', '.join(tenants_list)}")
        print(f"  Pods ({len(data['pods'])}): {', '.join(pods_list)}")
        print(f"  Files: {', '.join(files_list) if files_list else 'N/A'}")

        msg = data['sample_message'] or normalized_msg
        for line in msg.split('\n')[:3]:
            print(f"    {line[:110]}")

        if data["rca"]:
            print(f"  RCA: {data['rca']['rca']}")
            print(f"  FIX: {data['rca']['fix']}")
            print(f"  Category: {data['rca']['category']}")

        if data["sample_stacktrace"]:
            print(f"  STACKTRACE:")
            for line in data["sample_stacktrace"].split("\n")[:20]:
                print(f"    {line[:110]}")

    print("\n" + "=" * 120)
    print("  END OF REPORT")
    print("=" * 120)


if __name__ == "__main__":
    cluster = sys.argv[1] if len(sys.argv) > 1 else "all"
    time = sys.argv[2] if len(sys.argv) > 2 else "12h"

    print(f"\nGenerating error status report for {cluster} (last {time})...\n")
    report = generate_report(cluster, time)
    print_report(report)
