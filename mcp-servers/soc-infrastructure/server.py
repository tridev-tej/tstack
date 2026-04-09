#!/usr/bin/env python3
"""SOC Infrastructure MCP Server.

Monitor worker health, K8s pods, database metrics.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.db import execute_query
from shared.teams import send_teams_notification
from shared.utils import error_result, send_error, send_response, tool_result

from kubectl_client import get_infra_report, get_pod_status, get_recent_oom_events, get_worker_health
from prometheus_queries import get_db_connection_usage, get_disk_io_metrics, get_oom_kills, get_pod_cpu_usage, get_pod_memory_usage, get_pod_restarts, get_queue_depth

SERVER_INFO = {"name": "soc-infrastructure", "version": "1.0.0", "description": "SOC Agent infrastructure health monitoring"}

TOOLS = [
    {"name": "worker_health", "description": "SOC worker pod status (restarts, OOM, memory)",
     "inputSchema": {"type": "object", "properties": {"cluster": {"type": "string"}, "namespace": {"type": "string", "default": "default"}, "pod_prefix": {"type": "string", "default": "worker"}}, "required": ["cluster"]}},
    {"name": "pod_status", "description": "Detailed pod info (status, restarts, events)",
     "inputSchema": {"type": "object", "properties": {"cluster": {"type": "string"}, "pod_name": {"type": "string"}, "deployment": {"type": "string"}, "namespace": {"type": "string", "default": "default"}}, "required": ["cluster"]}},
    {"name": "db_health", "description": "PostgreSQL: connections, pool exhaustion, slow queries",
     "inputSchema": {"type": "object", "properties": {"tenant": {"type": "string"}}, "required": ["tenant"]}},
    {"name": "queue_depth", "description": "Task manager queue depth per tenant",
     "inputSchema": {"type": "object", "properties": {"tenant": {"type": "string"}}}},
    {"name": "infra_report", "description": "Combined health report with actionable insights",
     "inputSchema": {"type": "object", "properties": {"cluster": {"type": "string"}, "namespace": {"type": "string", "default": "default"}}, "required": ["cluster"]}},
    {"name": "recent_oom_events", "description": "Pods with recent OOM kills",
     "inputSchema": {"type": "object", "properties": {"cluster": {"type": "string"}, "namespace": {"type": "string", "default": "default"}, "time_range": {"type": "string", "default": "1h"}}, "required": ["cluster"]}},
    {"name": "disk_io_status", "description": "Disk I/O metrics for DB and workers",
     "inputSchema": {"type": "object", "properties": {"cluster": {"type": "string"}, "namespace": {"type": "string", "default": "default"}}, "required": ["cluster"]}},
    {"name": "notify_teams", "description": "Send notification to Microsoft Teams",
     "inputSchema": {"type": "object", "properties": {"message": {"type": "string"}, "severity": {"type": "string", "default": "info"}, "details": {"type": "object"}}, "required": ["message"]}},
]


def get_db_health_metrics(tenant: str) -> dict:
    """Get database health metrics from system views."""
    connection_query = """
        SELECT count(*) as total_connections,
            count(*) FILTER (WHERE state = 'active') as active,
            count(*) FILTER (WHERE state = 'idle') as idle,
            count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction,
            count(*) FILTER (WHERE wait_event_type IS NOT NULL) as waiting
        FROM pg_stat_activity WHERE datname = current_database()
    """
    locks_query = "SELECT count(*) as blocked_queries FROM pg_stat_activity WHERE wait_event_type = 'Lock'"
    long_running_query = """
        SELECT pid, now() - pg_stat_activity.query_start AS duration, query, state
        FROM pg_stat_activity
        WHERE (now() - pg_stat_activity.query_start) > interval '5 seconds' AND state != 'idle'
        ORDER BY duration DESC LIMIT 5
    """
    try:
        connections = execute_query(tenant, connection_query)
        locks = execute_query(tenant, locks_query)
        long_running = execute_query(tenant, long_running_query)
        prometheus_usage = get_db_connection_usage()
        return {
            "connections": connections[0] if connections else {},
            "blocked_queries": locks[0].get("blocked_queries", 0) if locks else 0,
            "long_running_queries": long_running,
            "pool_usage_pct": prometheus_usage.get("data", {}).get("result", []),
        }
    except Exception as e:
        return {"error": str(e)}


def handle_tool_call(name: str, arguments: dict) -> dict:
    try:
        if name == "worker_health":
            return tool_result(get_worker_health(cluster=arguments["cluster"], namespace=arguments.get("namespace", "default"), pod_prefix=arguments.get("pod_prefix", "worker")))
        elif name == "pod_status":
            return tool_result(get_pod_status(cluster=arguments["cluster"], pod_name=arguments.get("pod_name"), deployment=arguments.get("deployment"), namespace=arguments.get("namespace", "default")))
        elif name == "db_health":
            return tool_result(get_db_health_metrics(tenant=arguments["tenant"]))
        elif name == "queue_depth":
            return tool_result(get_queue_depth(tenant_pattern=arguments.get("tenant", ".*")))
        elif name == "infra_report":
            return tool_result(get_infra_report(cluster=arguments["cluster"], namespace=arguments.get("namespace", "default")))
        elif name == "recent_oom_events":
            kubectl_result = get_recent_oom_events(cluster=arguments["cluster"], namespace=arguments.get("namespace", "default"))
            prometheus_result = get_oom_kills(namespace=arguments.get("namespace", "default"), lookback=arguments.get("time_range", "1h"))
            return tool_result({"kubectl": kubectl_result, "prometheus": prometheus_result})
        elif name == "disk_io_status":
            return tool_result(get_disk_io_metrics(namespace=arguments.get("namespace", "default")))
        elif name == "notify_teams":
            return tool_result(send_teams_notification(message=arguments["message"], severity=arguments.get("severity", "info"), details=arguments.get("details")))
        else:
            return error_result(f"Unknown tool: {name}")
    except Exception as e:
        return error_result(str(e))


def handle_request(request: dict) -> None:
    method = request.get("method")
    request_id = request.get("id")
    if method == "initialize":
        send_response(request_id, {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": SERVER_INFO})
    elif method == "notifications/initialized":
        pass
    elif method == "tools/list":
        send_response(request_id, {"tools": TOOLS})
    elif method == "tools/call":
        params = request.get("params", {})
        send_response(request_id, handle_tool_call(params.get("name"), params.get("arguments", {})))
    elif method == "ping":
        send_response(request_id, {})
    else:
        send_error(request_id, -32601, f"Method not found: {method}")


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            handle_request(json.loads(line))
        except json.JSONDecodeError as e:
            send_error(None, -32700, f"Parse error: {e}")
        except Exception as e:
            send_error(None, -32603, f"Internal error: {e}")


if __name__ == "__main__":
    main()
