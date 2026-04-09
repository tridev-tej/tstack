#!/usr/bin/env python3
"""SOC Investigations MCP Server.

Diagnose investigation issues: stuck, failed, low confidence investigations.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.teams import send_teams_notification
from shared.utils import error_result, send_error, send_response, tool_result

from queries import (
    get_failed_investigations,
    get_investigation_detail,
    get_investigation_health,
    get_investigation_timeline,
    get_low_confidence_report,
    get_retry_analysis,
    get_stuck_investigations,
    get_tenant_alert_volume,
    get_tenant_llm_quota,
)
from opensearch_queries import get_failure_reasons, search_investigation_errors

SERVER_INFO = {
    "name": "soc-investigations",
    "version": "1.0.0",
    "description": "SOC Agent investigation health and troubleshooting",
}

TOOLS = [
    {
        "name": "investigation_health",
        "description": "Dashboard: stuck counts, failure rates, avg completion time",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tenant": {"type": "string", "description": "Tenant name (required)"},
                "time_range": {"type": "string", "description": "Time range: 5m, 15m, 1h, 6h, 24h, 7d", "default": "1h"},
            },
            "required": ["tenant"],
        },
    },
    {
        "name": "stuck_investigations",
        "description": "List investigations stuck in PENDING/TRIAGE_PENDING",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tenant": {"type": "string", "description": "Tenant name (required)"},
                "threshold_minutes": {"type": "integer", "description": "Minutes to consider stuck", "default": 60},
                "limit": {"type": "integer", "description": "Max results", "default": 20},
            },
            "required": ["tenant"],
        },
    },
    {
        "name": "failed_investigations",
        "description": "Recent failures with reasons (quota, LLM, no observables)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tenant": {"type": "string", "description": "Tenant name (required)"},
                "time_range": {"type": "string", "description": "Time range: 1h, 6h, 24h, 7d", "default": "24h"},
                "limit": {"type": "integer", "description": "Max results", "default": 50},
            },
            "required": ["tenant"],
        },
    },
    {
        "name": "investigation_detail",
        "description": "Full detail for specific investigation",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tenant": {"type": "string", "description": "Tenant name (required)"},
                "investigation_id": {"type": "integer", "description": "Investigation ID"},
            },
            "required": ["tenant", "investigation_id"],
        },
    },
    {
        "name": "investigation_timeline",
        "description": "Status history with timestamps",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tenant": {"type": "string", "description": "Tenant name (required)"},
                "investigation_id": {"type": "integer", "description": "Investigation ID"},
            },
            "required": ["tenant", "investigation_id"],
        },
    },
    {
        "name": "retry_analysis",
        "description": "Check retry count, list all attempts for finding",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tenant": {"type": "string", "description": "Tenant name (required)"},
                "finding_id": {"type": "integer", "description": "Finding ID"},
            },
            "required": ["tenant", "finding_id"],
        },
    },
    {
        "name": "low_confidence_report",
        "description": "Completed investigations with confidence < threshold",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tenant": {"type": "string", "description": "Tenant name (required)"},
                "threshold": {"type": "integer", "description": "Confidence threshold", "default": 50},
                "time_range": {"type": "string", "description": "Time range: 1h, 6h, 24h, 7d", "default": "24h"},
            },
            "required": ["tenant"],
        },
    },
    {
        "name": "investigation_errors",
        "description": "Search OpenSearch for error patterns",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tenant": {"type": "string", "description": "Tenant name (required)"},
                "pattern": {"type": "string", "description": "Search pattern in messages", "default": "investigation"},
                "time_range": {"type": "string", "description": "Time range: 5m, 15m, 1h, 6h, 24h", "default": "1h"},
            },
            "required": ["tenant"],
        },
    },
    {
        "name": "tenant_llm_quota",
        "description": "Current LLM usage vs quota",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tenant": {"type": "string", "description": "Tenant name (required)"},
            },
            "required": ["tenant"],
        },
    },
    {
        "name": "tenant_alert_volume",
        "description": "Alert ingestion rate and backlog",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tenant": {"type": "string", "description": "Tenant name (required)"},
                "time_range": {"type": "string", "description": "Time range: 1h, 6h, 24h, 7d", "default": "24h"},
            },
            "required": ["tenant"],
        },
    },
    {
        "name": "notify_teams",
        "description": "Send notification to Microsoft Teams",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Notification message"},
                "severity": {"type": "string", "description": "Severity: critical, warning, info, success", "default": "info"},
                "details": {"type": "object", "description": "Additional details as key-value pairs"},
            },
            "required": ["message"],
        },
    },
]


def handle_tool_call(name: str, arguments: dict) -> dict:
    """Handle tool execution."""
    try:
        if name == "investigation_health":
            result = get_investigation_health(tenant=arguments["tenant"], time_range=arguments.get("time_range", "1h"))
            return tool_result(result)
        elif name == "stuck_investigations":
            result = get_stuck_investigations(tenant=arguments["tenant"], threshold_minutes=arguments.get("threshold_minutes", 60), limit=arguments.get("limit", 20))
            return tool_result(result)
        elif name == "failed_investigations":
            investigations = get_failed_investigations(tenant=arguments["tenant"], time_range=arguments.get("time_range", "24h"), limit=arguments.get("limit", 50))
            reasons = get_failure_reasons(tenant=arguments["tenant"], time_range=arguments.get("time_range", "24h"))
            return tool_result({"investigations": investigations, "failure_reasons": reasons})
        elif name == "investigation_detail":
            result = get_investigation_detail(tenant=arguments["tenant"], investigation_id=arguments["investigation_id"])
            if result is None:
                return error_result("Investigation not found")
            return tool_result(result)
        elif name == "investigation_timeline":
            result = get_investigation_timeline(tenant=arguments["tenant"], investigation_id=arguments["investigation_id"])
            return tool_result(result)
        elif name == "retry_analysis":
            result = get_retry_analysis(tenant=arguments["tenant"], finding_id=arguments["finding_id"])
            return tool_result(result)
        elif name == "low_confidence_report":
            result = get_low_confidence_report(tenant=arguments["tenant"], threshold=arguments.get("threshold", 50), time_range=arguments.get("time_range", "24h"))
            return tool_result(result)
        elif name == "investigation_errors":
            result = search_investigation_errors(tenant=arguments["tenant"], pattern=arguments.get("pattern", "investigation"), time_range=arguments.get("time_range", "1h"))
            return tool_result(result)
        elif name == "tenant_llm_quota":
            result = get_tenant_llm_quota(tenant=arguments["tenant"])
            return tool_result(result)
        elif name == "tenant_alert_volume":
            result = get_tenant_alert_volume(tenant=arguments["tenant"], time_range=arguments.get("time_range", "24h"))
            return tool_result(result)
        elif name == "notify_teams":
            result = send_teams_notification(message=arguments["message"], severity=arguments.get("severity", "info"), details=arguments.get("details"))
            return tool_result(result)
        else:
            return error_result(f"Unknown tool: {name}")
    except Exception as e:
        return error_result(str(e))


def handle_request(request: dict) -> None:
    """Handle incoming JSON-RPC request."""
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
        result = handle_tool_call(params.get("name"), params.get("arguments", {}))
        send_response(request_id, result)
    elif method == "ping":
        send_response(request_id, {})
    else:
        send_error(request_id, -32601, f"Method not found: {method}")


def main():
    """Main server loop."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            handle_request(request)
        except json.JSONDecodeError as e:
            send_error(None, -32700, f"Parse error: {e}")
        except Exception as e:
            send_error(None, -32603, f"Internal error: {e}")


if __name__ == "__main__":
    main()
