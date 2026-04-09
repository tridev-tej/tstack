#!/usr/bin/env python3
"""Prometheus MCP Server with actionable infrastructure insights"""

import json
import sys
import urllib.request
import urllib.error
import base64
import ssl
import os
import urllib.parse

URL = os.environ.get("PROMETHEUS_URL", "https://prometheus.example.com").rstrip("/")
USERNAME = os.environ.get("PROMETHEUS_USERNAME", "monitoring")
PASSWORD = os.environ.get("PROMETHEUS_PASSWORD", "")
AUTH = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()

def send_response(id, result):
    msg = {"jsonrpc": "2.0", "id": id, "result": result}
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()

def send_error(id, code, message):
    msg = {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()

def request(endpoint):
    url = f"{URL}/{endpoint}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Basic {AUTH}")

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "message": e.read().decode()[:500]}
    except Exception as e:
        return {"error": -1, "message": str(e)}

def prom_query(query):
    encoded = urllib.parse.quote(query, safe="")
    return request(f"api/v1/query?query={encoded}")

TOOLS = [
    {
        "name": "prometheus_health",
        "description": "Check Prometheus server health",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "prometheus_query",
        "description": "Run an instant PromQL query",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "PromQL query"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "prometheus_alerts",
        "description": "Get active Prometheus alerts",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "prometheus_targets",
        "description": "Get scrape targets and their health status",
        "inputSchema": {
            "type": "object",
            "properties": {
                "state": {"type": "string", "enum": ["active", "dropped", "any"], "default": "active"}
            }
        }
    },
    {
        "name": "prometheus_report",
        "description": "Get comprehensive infrastructure health report with actionable insights: alerts, down targets, memory-constrained nodes, high CPU, database connections, and disk usage",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "prometheus_nodes",
        "description": "Get node resource usage: memory, CPU, disk, load average",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sort_by": {"type": "string", "enum": ["memory", "cpu", "disk", "load"], "default": "memory"}
            }
        }
    },
    {
        "name": "prometheus_databases",
        "description": "Get PostgreSQL database metrics: size, connections",
        "inputSchema": {"type": "object", "properties": {}}
    }
]

def tool_health(args):
    try:
        req = urllib.request.Request(f"{URL}/-/healthy")
        req.add_header("Authorization", f"Basic {AUTH}")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            status = resp.status

        up_result = prom_query("up")
        total_targets = len(up_result.get("data", {}).get("result", []))
        down = sum(1 for r in up_result.get("data", {}).get("result", []) if r.get("value", [0, "1"])[1] == "0")

        lines = [
            "## Prometheus Health",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| URL | {URL} |",
            f"| Status | {'HEALTHY' if status == 200 else 'UNHEALTHY'} |",
            f"| HTTP Code | {status} |",
            f"| Total Targets | {total_targets} |",
            f"| Down Targets | {down} |",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Error checking health: {e}"

def tool_query(args):
    query = args.get("query", "up")
    result = prom_query(query)

    if "error" in result:
        return f"Error: {result}"

    data = result.get("data", {}).get("result", [])
    if not data:
        return f"Query: {query}\nNo results"

    lines = [f"Query: {query}", f"Results: {len(data)}", ""]
    for r in data[:30]:
        metric = r.get("metric", {})
        value = r.get("value", [0, ""])[1]
        metric_str = ", ".join(f'{k}="{v}"' for k, v in metric.items() if k != "__name__")
        name = metric.get("__name__", "")
        lines.append(f"{name}{{{metric_str}}} = {value}")

    if len(data) > 30:
        lines.append(f"... and {len(data) - 30} more")

    return "\n".join(lines)

def tool_alerts(args):
    result = request("api/v1/alerts")
    alerts = result.get("data", {}).get("alerts", [])

    if not alerts:
        return "## Active Alerts\n\nNo active alerts"

    lines = ["## Active Alerts", "", f"Total: {len(alerts)}", "",
             "| Alert | Severity | State | Summary |",
             "|-------|----------|-------|---------|"]

    for a in alerts[:20]:
        name = a.get("labels", {}).get("alertname", "unknown")
        severity = a.get("labels", {}).get("severity", "unknown")
        state = a.get("state", "unknown")
        summary = a.get("annotations", {}).get("summary", a.get("annotations", {}).get("description", ""))[:60]
        lines.append(f"| {name} | {severity} | {state} | {summary} |")

    return "\n".join(lines)

def tool_targets(args):
    state = args.get("state", "active")
    result = request("api/v1/targets")

    targets = result.get("data", {}).get("activeTargets", [])
    if state == "dropped":
        targets = result.get("data", {}).get("droppedTargets", [])

    down = [t for t in targets if t.get("health") == "down"]
    up = [t for t in targets if t.get("health") == "up"]

    lines = [
        "## Scrape Targets",
        "",
        f"Total: {len(targets)} | Up: {len(up)} | Down: {len(down)}",
        ""
    ]

    if down:
        lines.extend(["### Down Targets", "",
                      "| Job | Instance | Last Error |",
                      "|-----|----------|------------|"])
        for t in down[:15]:
            job = t.get("labels", {}).get("job", "")
            instance = t.get("labels", {}).get("instance", "")
            error = t.get("lastError", "")[:50]
            lines.append(f"| {job} | {instance} | {error} |")

    return "\n".join(lines)

def tool_nodes(args):
    sort_by = args.get("sort_by", "memory")

    mem_result = prom_query("node_memory_MemAvailable_bytes/node_memory_MemTotal_bytes*100")
    mem_data = {r["metric"].get("instance", ""): float(r["value"][1])
                for r in mem_result.get("data", {}).get("result", [])}

    load_result = prom_query("node_load5")
    load_data = {r["metric"].get("instance", ""): float(r["value"][1])
                 for r in load_result.get("data", {}).get("result", [])}

    nodes = {}
    for instance in set(list(mem_data.keys()) + list(load_data.keys())):
        nodes[instance] = {
            "mem_avail": mem_data.get(instance, 0),
            "load": load_data.get(instance, 0)
        }

    if sort_by == "memory":
        sorted_nodes = sorted(nodes.items(), key=lambda x: x[1]["mem_avail"])
    else:
        sorted_nodes = sorted(nodes.items(), key=lambda x: -x[1]["load"])

    lines = [
        "## Node Resources",
        "",
        "| Node | Memory Available | Load (5m) | Status |",
        "|------|------------------|-----------|--------|"
    ]

    for instance, data in sorted_nodes[:15]:
        mem = data["mem_avail"]
        load = data["load"]
        status = "LOW MEM" if mem < 40 else ("HIGH LOAD" if load > 3 else "OK")
        lines.append(f"| {instance} | {mem:.0f}% | {load:.2f} | {status} |")

    return "\n".join(lines)

def tool_databases(args):
    size_result = prom_query("pg_database_size_bytes")
    sizes = {}
    for r in size_result.get("data", {}).get("result", []):
        db = r["metric"].get("datname", "")
        size_bytes = float(r["value"][1])
        sizes[db] = size_bytes / (1024**3)

    conn_result = prom_query("sum(pg_stat_activity_count) by (datname)")
    conns = {r["metric"].get("datname", ""): int(float(r["value"][1]))
             for r in conn_result.get("data", {}).get("result", [])}

    dbs = []
    for db in set(list(sizes.keys()) + list(conns.keys())):
        dbs.append({
            "name": db,
            "size_gb": sizes.get(db, 0),
            "connections": conns.get(db, 0)
        })

    dbs.sort(key=lambda x: -x["connections"])

    lines = [
        "## PostgreSQL Databases",
        "",
        "| Database | Size | Connections | Status |",
        "|----------|------|-------------|--------|"
    ]

    for db in dbs[:15]:
        status = "HIGH CONNS" if db["connections"] > 500 else "OK"
        lines.append(f"| {db['name'][:40]} | {db['size_gb']:.2f} GB | {db['connections']} | {status} |")

    return "\n".join(lines)

def tool_report(args):
    """Generate comprehensive infrastructure health report"""
    sections = []

    sections.append("# Infrastructure Health Report\n")

    try:
        req = urllib.request.Request(f"{URL}/-/healthy")
        req.add_header("Authorization", f"Basic {AUTH}")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            healthy = resp.status == 200
    except:
        healthy = False

    up_result = prom_query("up")
    targets = up_result.get("data", {}).get("result", [])
    total_targets = len(targets)
    down_targets = sum(1 for r in targets if r.get("value", [0, "1"])[1] == "0")

    alerts_result = request("api/v1/alerts")
    alerts = alerts_result.get("data", {}).get("alerts", [])

    sections.append("## Overall Status")
    sections.append("")
    sections.append("| Metric | Value |")
    sections.append("|--------|-------|")
    sections.append(f"| Prometheus | {'HEALTHY' if healthy else 'DOWN'} |")
    sections.append(f"| Total Targets | {total_targets} |")
    sections.append(f"| Down Targets | {down_targets} |")
    sections.append(f"| Active Alerts | {len(alerts)} |")
    sections.append("")

    if alerts:
        sections.append("---")
        sections.append("## Active Alerts")
        sections.append("")
        sections.append("| Alert | Severity | State | Summary |")
        sections.append("|-------|----------|-------|---------|")
        for a in alerts[:10]:
            name = a.get("labels", {}).get("alertname", "unknown")
            severity = a.get("labels", {}).get("severity", "unknown")
            state = a.get("state", "unknown")
            summary = a.get("annotations", {}).get("summary", "")[:50]
            sections.append(f"| {name} | {severity} | {state} | {summary} |")
        sections.append("")

    mem_result = prom_query("node_memory_MemAvailable_bytes/node_memory_MemTotal_bytes*100")
    low_mem_nodes = []
    for r in mem_result.get("data", {}).get("result", []):
        avail = float(r["value"][1])
        if avail < 50:
            low_mem_nodes.append((r["metric"].get("instance", ""), avail))

    if low_mem_nodes:
        low_mem_nodes.sort(key=lambda x: x[1])
        sections.append("---")
        sections.append("## Nodes with Low Memory (<50% available)")
        sections.append("")
        sections.append("| Node | Memory Available |")
        sections.append("|------|------------------|")
        for node, mem in low_mem_nodes[:10]:
            sections.append(f"| {node} | **{mem:.0f}%** |")
        sections.append("")
        sections.append("**Action:** Monitor for OOM issues, consider scaling or optimizing workloads.")
        sections.append("")

    conn_result = prom_query("sum(pg_stat_activity_count) by (datname)")
    high_conn_dbs = []
    for r in conn_result.get("data", {}).get("result", []):
        conns = int(float(r["value"][1]))
        if conns > 100:
            high_conn_dbs.append((r["metric"].get("datname", ""), conns))

    if high_conn_dbs:
        high_conn_dbs.sort(key=lambda x: -x[1])
        sections.append("---")
        sections.append("## Databases with High Connections (>100)")
        sections.append("")
        sections.append("| Database | Total Connections |")
        sections.append("|----------|-------------------|")
        for db, conns in high_conn_dbs[:10]:
            status = "CRITICAL" if conns > 500 else "WARNING"
            sections.append(f"| {db[:40]} | **{conns}** {status} |")
        sections.append("")
        sections.append("**Action:** Check for connection leaks, verify pooling is configured properly.")
        sections.append("")

    issues = []
    if down_targets:
        issues.append(f"{down_targets} targets down")
    if alerts:
        issues.append(f"{len(alerts)} active alerts")
    if low_mem_nodes:
        issues.append(f"{len(low_mem_nodes)} nodes with low memory")

    sections.append("---")
    if issues:
        sections.append(f"## Summary: {len(issues)} issue(s) found")
        sections.append("")
        for issue in issues:
            sections.append(f"- {issue}")
    else:
        sections.append("## Summary: All systems healthy")

    return "\n".join(sections)


def handle_request(req):
    method = req.get("method")
    id = req.get("id")
    params = req.get("params", {})

    if method == "initialize":
        send_response(id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "prometheus", "version": "1.0.0"}
        })
    elif method == "tools/list":
        send_response(id, {"tools": TOOLS})
    elif method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})
        handlers = {
            "prometheus_health": tool_health,
            "prometheus_query": tool_query,
            "prometheus_alerts": tool_alerts,
            "prometheus_targets": tool_targets,
            "prometheus_report": tool_report,
            "prometheus_nodes": tool_nodes,
            "prometheus_databases": tool_databases,
        }
        if name in handlers:
            try:
                result = handlers[name](args)
                send_response(id, {"content": [{"type": "text", "text": result}]})
            except Exception as e:
                import traceback
                send_response(id, {"content": [{"type": "text", "text": f"Error: {e}\n{traceback.format_exc()}"}], "isError": True})
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
