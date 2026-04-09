#!/usr/bin/env python3
"""
OpenSearch Direct Query Tool
Usage: python query.py <action> [args...]

Actions:
  search <index> <query_json> [size]
  count <index> <query_json>
  indices
  health
  agg <index> <field> [time_range]
  logs <cluster> <tenant> <level> <pattern> <pod> <time> <limit>
"""

import json
import sys
import urllib.request
import urllib.error
import base64
import ssl
import os
from datetime import datetime

URL = os.environ.get("OPENSEARCH_URL", "https://opensearch.example.com")
_user = os.environ.get("OPENSEARCH_USER", "admin")
_pass = os.environ.get("OPENSEARCH_PASSWORD", "")
AUTH = base64.b64encode(f"{_user}:{_pass}".encode('utf-8')).decode()

def request(endpoint, method="GET", body=None):
    url = f"{URL}/{endpoint}"
    data = json.dumps(body).encode() if body else None

    req = urllib.request.Request(url, data=data, method=method if not data else "POST")
    req.add_header("Authorization", f"Basic {AUTH}")
    req.add_header("Content-Type", "application/json")

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "message": e.read().decode()[:1000]}
    except Exception as e:
        return {"error": -1, "message": str(e)}

def get_index_pattern(cluster):
    if cluster == "staging":
        return "app-stage-*"
    elif cluster == "prod":
        return "app-*,-app-stage-*"
    else:
        return "app-*"

def build_query(tenant=None, level=None, pattern=None, pod=None, time="15m"):
    must = [{"range": {"@timestamp": {"gte": f"now-{time}", "lte": "now"}}}]

    if tenant and tenant != "all":
        must.append({"term": {"tenant.keyword": tenant}})

    if level and level.upper() not in ("ALL", ""):
        must.append({"term": {"levelname.keyword": level.upper()}})

    if pod and pod != "all":
        must.append({"wildcard": {"kubernetes.pod_name.keyword": f"*{pod}*"}})

    if pattern and pattern != "all":
        must.append({
            "bool": {
                "should": [
                    {"match_phrase": {"message": pattern}},
                    {"match_phrase": {"log": pattern}}
                ],
                "minimum_should_match": 1
            }
        })

    return {"query": {"bool": {"must": must}}}

def format_logs(hits, show_raw=False):
    print(f"\n{'TIMESTAMP':<20} {'LEVEL':<6} {'TENANT':<15} {'POD':<40} MESSAGE")
    print("-" * 140)

    for hit in hits:
        src = hit.get("_source", {})
        ts = src.get("@timestamp", "")[:19].replace("T", " ")
        level = src.get("levelname", "LOG")[:5]
        tenant = src.get("tenant", "-")[:14]
        pod = src.get("kubernetes", {}).get("pod_name", "-")[:39]
        msg = src.get("message", src.get("log", ""))
        if isinstance(msg, str):
            msg = msg[:80].replace("\n", " ")
        else:
            msg = str(msg)[:80]

        print(f"{ts:<20} {level:<6} {tenant:<15} {pod:<40} {msg}")

def cmd_search(index, query_json, size=50):
    query = json.loads(query_json) if isinstance(query_json, str) else query_json
    query["size"] = int(size)
    query["sort"] = [{"@timestamp": {"order": "desc"}}]

    result = request(f"{index}/_search", body=query)

    if "error" in result and isinstance(result["error"], int):
        print(f"Error: {result}")
        return

    hits = result.get("hits", {})
    total = hits.get("total", {})
    total_count = total.get("value", total) if isinstance(total, dict) else total

    print(f"Total: {total_count:,} matching logs")
    format_logs(hits.get("hits", []))

def cmd_count(index, query_json):
    query = json.loads(query_json) if isinstance(query_json, str) else query_json
    result = request(f"{index}/_count", body=query)
    print(f"Count: {result.get('count', 'error')}")

def cmd_indices():
    result = request("_cat/indices?format=json&h=index,docs.count,store.size,health")
    if isinstance(result, list):
        result.sort(key=lambda x: x.get("docs.count", "0"), reverse=True)
        print(f"{'INDEX':<40} {'DOCS':>15} {'SIZE':>10} {'HEALTH':<8}")
        print("-" * 80)
        for idx in result[:30]:
            name = idx.get("index", "")
            if name.startswith("."):
                continue
            docs = idx.get("docs.count", "0")
            size = idx.get("store.size", "-")
            health = idx.get("health", "-")
            print(f"{name:<40} {docs:>15} {size:>10} {health:<8}")
    else:
        print(json.dumps(result, indent=2))

def cmd_health():
    result = request("_cluster/health")
    print(json.dumps(result, indent=2))

def cmd_agg(index, field, time="1h"):
    query = {
        "size": 0,
        "query": {"range": {"@timestamp": {"gte": f"now-{time}"}}},
        "aggs": {
            "by_field": {"terms": {"field": f"{field}.keyword", "size": 50}}
        }
    }
    result = request(f"{index}/_search", body=query)

    buckets = result.get("aggregations", {}).get("by_field", {}).get("buckets", [])
    total = result.get("hits", {}).get("total", {})
    total_count = total.get("value", 0) if isinstance(total, dict) else total

    print(f"\nAggregation by {field} (last {time}, total: {total_count:,})\n")
    for b in buckets:
        print(f"  {b['key']:<40} {b['doc_count']:>12,}")

def cmd_logs(cluster="all", tenant="all", level="all", pattern="all", pod="all", time="15m", limit="50"):
    index = get_index_pattern(cluster)
    query = build_query(tenant, level, pattern, pod, time)
    query["size"] = int(limit)
    query["sort"] = [{"@timestamp": {"order": "desc"}}]

    result = request(f"{index}/_search", body=query)

    if "error" in result and isinstance(result["error"], int):
        print(f"Error: {result}")
        return

    hits = result.get("hits", {})
    total = hits.get("total", {})
    total_count = total.get("value", total) if isinstance(total, dict) else total

    cluster_label = cluster if cluster != "all" else "all clusters"
    print(f"\n[{cluster_label.upper()}] {total_count:,} logs matching filters (showing {limit})")
    print(f"Filters: tenant={tenant}, level={level}, pattern={pattern}, pod={pod}, time={time}")

    format_logs(hits.get("hits", []))

def cmd_errors(cluster="all", time="1h"):
    """Get error summary with aggregations"""
    index = get_index_pattern(cluster)
    query = {
        "size": 20,
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
            "by_tenant": {"terms": {"field": "tenant.keyword", "size": 20}},
            "by_pod": {"terms": {"field": "kubernetes.pod_name.keyword", "size": 20}},
            "by_message": {"terms": {"field": "message.keyword", "size": 10}}
        }
    }

    result = request(f"{index}/_search", body=query)
    hits = result.get("hits", {})
    aggs = result.get("aggregations", {})
    total = hits.get("total", {})
    total_count = total.get("value", total) if isinstance(total, dict) else total

    print(f"\n{'='*80}")
    print(f"ERROR SUMMARY - {cluster.upper()} (last {time}): {total_count:,} errors")
    print(f"{'='*80}")

    print("\nBy Tenant:")
    for b in aggs.get("by_tenant", {}).get("buckets", [])[:10]:
        print(f"  {b['key']:<30} {b['doc_count']:>8,}")

    print("\nBy Pod:")
    for b in aggs.get("by_pod", {}).get("buckets", [])[:10]:
        print(f"  {b['key']:<50} {b['doc_count']:>8,}")

    print("\nRecent Errors:")
    format_logs(hits.get("hits", []))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "search": cmd_search,
        "count": cmd_count,
        "indices": cmd_indices,
        "health": cmd_health,
        "agg": cmd_agg,
        "logs": cmd_logs,
        "errors": cmd_errors
    }

    if cmd in commands:
        commands[cmd](*args)
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
