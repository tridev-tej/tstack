#!/usr/bin/env python3
"""OpenSearch MCP Server with direct cluster access"""

import json
import sys
import urllib.request
import urllib.error
import base64
import ssl
import os

URL = os.environ.get("OPENSEARCH_URL", "https://opensearch.example.com")
_user = os.environ.get("OPENSEARCH_USER", "admin")
_pass = os.environ.get("OPENSEARCH_PASSWORD", "")
AUTH = base64.b64encode(f"{_user}:{_pass}".encode('utf-8')).decode()

def send_response(id, result):
    msg = {"jsonrpc": "2.0", "id": id, "result": result}
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()

def send_error(id, code, message):
    msg = {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()

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
        return {"error": e.code, "message": e.read().decode()[:500]}
    except Exception as e:
        return {"error": -1, "message": str(e)}

def get_index_pattern(cluster):
    if cluster == "staging":
        return "app-stage-*"
    elif cluster == "prod":
        return "app-*,-app-stage-*"
    return "app-*"

def build_log_query(tenant=None, level=None, pattern=None, pod=None, time="15m"):
    must = [{"range": {"@timestamp": {"gte": f"now-{time}", "lte": "now"}}}]

    if tenant:
        must.append({"term": {"tenant.keyword": tenant}})
    if level and level.upper() != "ALL":
        must.append({"term": {"levelname.keyword": level.upper()}})
    if pod:
        must.append({"wildcard": {"kubernetes.pod_name.keyword": f"*{pod}*"}})
    if pattern:
        must.append({"bool": {"should": [
            {"match_phrase": {"message": pattern}},
            {"match_phrase": {"log": pattern}}
        ], "minimum_should_match": 1}})

    return {"query": {"bool": {"must": must}}}

TOOLS = [
    {
        "name": "opensearch_logs",
        "description": "Query logs from OpenSearch with flexible filters. Returns formatted log entries.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cluster": {"type": "string", "enum": ["all", "prod", "staging"], "description": "Cluster: prod, staging, or all", "default": "all"},
                "tenant": {"type": "string", "description": "Tenant name"},
                "level": {"type": "string", "enum": ["all", "ERROR", "WARN", "INFO", "DEBUG"], "description": "Log level filter", "default": "all"},
                "pattern": {"type": "string", "description": "Search pattern in message/log fields"},
                "pod": {"type": "string", "description": "Pod name filter (partial match)"},
                "time": {"type": "string", "description": "Time range: 5m, 15m, 1h, 6h, 24h, 7d", "default": "15m"},
                "limit": {"type": "integer", "description": "Max results", "default": 50}
            }
        }
    },
    {
        "name": "opensearch_errors",
        "description": "Get error summary with aggregations by tenant and pod",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cluster": {"type": "string", "enum": ["all", "prod", "staging"], "default": "all"},
                "time": {"type": "string", "description": "Time range", "default": "1h"}
            }
        }
    },
    {
        "name": "opensearch_search",
        "description": "Execute raw OpenSearch query DSL",
        "inputSchema": {
            "type": "object",
            "properties": {
                "index": {"type": "string", "description": "Index pattern", "default": "app-*"},
                "query": {"type": "object", "description": "OpenSearch query DSL"},
                "size": {"type": "integer", "default": 50}
            },
            "required": ["query"]
        }
    },
    {
        "name": "opensearch_agg",
        "description": "Aggregate logs by a field (tenant, pod, level, etc.)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cluster": {"type": "string", "enum": ["all", "prod", "staging"], "default": "all"},
                "field": {"type": "string", "description": "Field to aggregate: tenant, levelname, kubernetes.pod_name, kubernetes.namespace_name"},
                "time": {"type": "string", "default": "1h"}
            },
            "required": ["field"]
        }
    },
    {
        "name": "opensearch_indices",
        "description": "List all indices with doc counts and sizes",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "opensearch_health",
        "description": "Get cluster health status",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "opensearch_count",
        "description": "Count documents matching filters",
        "inputSchema": {
            "type": "object",
            "properties": {
                "cluster": {"type": "string", "enum": ["all", "prod", "staging"], "default": "all"},
                "tenant": {"type": "string"},
                "level": {"type": "string"},
                "pattern": {"type": "string"},
                "time": {"type": "string", "default": "15m"}
            }
        }
    }
]

def format_logs(hits):
    lines = [f"{'TIMESTAMP':<20} {'LEVEL':<6} {'TENANT':<15} {'POD':<40} MESSAGE", "-" * 140]
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
        lines.append(f"{ts:<20} {level:<6} {tenant:<15} {pod:<40} {msg}")
    return "\n".join(lines)

def tool_logs(args):
    cluster = args.get("cluster", "all")
    index = get_index_pattern(cluster)
    query = build_log_query(
        args.get("tenant"), args.get("level"), args.get("pattern"),
        args.get("pod"), args.get("time", "15m")
    )
    query["size"] = args.get("limit", 50)
    query["sort"] = [{"@timestamp": {"order": "desc"}}]

    result = request(f"{index}/_search", body=query)
    if "error" in result and isinstance(result["error"], int):
        return f"Error: {result}"

    hits = result.get("hits", {})
    total = hits.get("total", {})
    total_count = total.get("value", total) if isinstance(total, dict) else total

    output = [f"[{cluster.upper()}] {total_count:,} logs matching filters", ""]
    output.append(format_logs(hits.get("hits", [])))
    return "\n".join(output)

def tool_errors(args):
    cluster = args.get("cluster", "all")
    time = args.get("time", "1h")
    index = get_index_pattern(cluster)

    query = {
        "size": 20,
        "sort": [{"@timestamp": {"order": "desc"}}],
        "query": {"bool": {"must": [
            {"range": {"@timestamp": {"gte": f"now-{time}"}}},
            {"term": {"levelname.keyword": "ERROR"}}
        ]}},
        "aggs": {
            "by_tenant": {"terms": {"field": "tenant.keyword", "size": 20}},
            "by_pod": {"terms": {"field": "kubernetes.pod_name.keyword", "size": 20}}
        }
    }

    result = request(f"{index}/_search", body=query)
    if "error" in result and isinstance(result["error"], int):
        return f"Error: {result}"

    hits = result.get("hits", {})
    aggs = result.get("aggregations", {})
    total = hits.get("total", {})
    total_count = total.get("value", total) if isinstance(total, dict) else total

    lines = [f"ERROR SUMMARY - {cluster.upper()} (last {time}): {total_count:,} errors", ""]
    lines.append("By Tenant:")
    for b in aggs.get("by_tenant", {}).get("buckets", [])[:10]:
        lines.append(f"  {b['key']:<30} {b['doc_count']:>8,}")
    lines.append("\nBy Pod:")
    for b in aggs.get("by_pod", {}).get("buckets", [])[:10]:
        lines.append(f"  {b['key']:<50} {b['doc_count']:>8,}")
    lines.append("\nRecent Errors:")
    lines.append(format_logs(hits.get("hits", [])))

    return "\n".join(lines)

def tool_search(args):
    index = args.get("index", "app-*")
    query = args.get("query", {"match_all": {}})
    size = args.get("size", 50)

    body = {"query": query, "size": size, "sort": [{"@timestamp": {"order": "desc"}}]}
    result = request(f"{index}/_search", body=body)
    return json.dumps(result, indent=2)

def tool_agg(args):
    cluster = args.get("cluster", "all")
    field = args.get("field", "tenant")
    time = args.get("time", "1h")
    index = get_index_pattern(cluster)

    query = {
        "size": 0,
        "query": {"range": {"@timestamp": {"gte": f"now-{time}"}}},
        "aggs": {"by_field": {"terms": {"field": f"{field}.keyword", "size": 50}}}
    }

    result = request(f"{index}/_search", body=query)
    if "error" in result and isinstance(result["error"], int):
        return f"Error: {result}"

    buckets = result.get("aggregations", {}).get("by_field", {}).get("buckets", [])
    total = result.get("hits", {}).get("total", {})
    total_count = total.get("value", 0) if isinstance(total, dict) else total

    lines = [f"Aggregation by {field} (last {time}, total: {total_count:,})", ""]
    for b in buckets:
        lines.append(f"  {b['key']:<50} {b['doc_count']:>12,}")
    return "\n".join(lines)

def tool_indices(args):
    result = request("_cat/indices?format=json&h=index,docs.count,store.size,health")
    if isinstance(result, list):
        result = [r for r in result if not r.get("index", "").startswith(".")]
        result.sort(key=lambda x: int(x.get("docs.count", "0") or "0"), reverse=True)
        lines = [f"{'INDEX':<45} {'DOCS':>15} {'SIZE':>10} {'HEALTH':<8}", "-" * 85]
        for idx in result[:40]:
            lines.append(f"{idx.get('index', ''):<45} {idx.get('docs.count', '0'):>15} {idx.get('store.size', '-'):>10} {idx.get('health', '-'):<8}")
        return "\n".join(lines)
    return json.dumps(result, indent=2)

def tool_health(args):
    return json.dumps(request("_cluster/health"), indent=2)

def tool_count(args):
    cluster = args.get("cluster", "all")
    index = get_index_pattern(cluster)
    query = build_log_query(
        args.get("tenant"), args.get("level"), args.get("pattern"),
        None, args.get("time", "15m")
    )

    result = request(f"{index}/_count", body=query)
    return f"Count: {result.get('count', 'error'):,}"

def handle_request(req):
    method = req.get("method")
    id = req.get("id")
    params = req.get("params", {})

    if method == "initialize":
        send_response(id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "opensearch-direct", "version": "1.0.0"}
        })
    elif method == "tools/list":
        send_response(id, {"tools": TOOLS})
    elif method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})
        handlers = {
            "opensearch_logs": tool_logs,
            "opensearch_errors": tool_errors,
            "opensearch_search": tool_search,
            "opensearch_agg": tool_agg,
            "opensearch_indices": tool_indices,
            "opensearch_health": tool_health,
            "opensearch_count": tool_count
        }
        if name in handlers:
            try:
                result = handlers[name](args)
                send_response(id, {"content": [{"type": "text", "text": result}]})
            except Exception as e:
                send_response(id, {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True})
        else:
            send_error(id, -32601, f"Unknown tool: {name}")
    elif method == "notifications/initialized":
        pass
    else:
        send_error(id, -32601, f"Method not found: {method}")

def main():
    for line in sys.stdin:
        try:
            req = json.loads(line.strip())
            handle_request(req)
        except json.JSONDecodeError:
            pass
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")

if __name__ == "__main__":
    main()
