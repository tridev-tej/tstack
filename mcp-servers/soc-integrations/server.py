#!/usr/bin/env python3
"""SOC Integrations MCP Server.

Monitor integration health, API metrics, credential issues.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.teams import send_teams_notification
from shared.utils import error_result, send_error, send_response, tool_result

from health_checks import check_credential_validity, get_integration_api_status, get_integration_latency
from queries import get_entity_store_issues, get_integration_detail, get_integration_errors, get_integration_health, get_integration_report

SERVER_INFO = {"name": "soc-integrations", "version": "1.0.0", "description": "SOC Agent integration health monitoring"}

TOOLS = [
    {"name": "integration_health", "description": "All integrations with state (WORKING/WARNING/ERROR)",
     "inputSchema": {"type": "object", "properties": {"tenant": {"type": "string"}, "type": {"type": "string"}}, "required": ["tenant"]}},
    {"name": "integration_errors", "description": "Integrations with action_errors",
     "inputSchema": {"type": "object", "properties": {"tenant": {"type": "string"}, "time_range": {"type": "string", "default": "24h"}}, "required": ["tenant"]}},
    {"name": "integration_detail", "description": "Full detail (config masked, errors, warnings)",
     "inputSchema": {"type": "object", "properties": {"tenant": {"type": "string"}, "integration_id": {"type": "integer"}}, "required": ["tenant", "integration_id"]}},
    {"name": "integration_latency", "description": "API call latency percentiles",
     "inputSchema": {"type": "object", "properties": {"tenant": {"type": "string"}, "integration_id": {"type": "integer"}, "time_range": {"type": "string", "default": "1h"}}, "required": ["tenant"]}},
    {"name": "integration_api_status", "description": "Success/failure rates by status code",
     "inputSchema": {"type": "object", "properties": {"tenant": {"type": "string"}, "integration_id": {"type": "integer"}, "time_range": {"type": "string", "default": "1h"}}, "required": ["tenant"]}},
    {"name": "credential_check", "description": "Check integration credential validity",
     "inputSchema": {"type": "object", "properties": {"tenant": {"type": "string"}, "integration_id": {"type": "integer"}}, "required": ["tenant", "integration_id"]}},
    {"name": "entity_store_health", "description": "Entity store timeout issues",
     "inputSchema": {"type": "object", "properties": {"tenant": {"type": "string"}, "time_range": {"type": "string", "default": "1h"}}, "required": ["tenant"]}},
    {"name": "integration_report", "description": "Comprehensive health report per tenant",
     "inputSchema": {"type": "object", "properties": {"tenant": {"type": "string"}}, "required": ["tenant"]}},
    {"name": "notify_teams", "description": "Send notification to Microsoft Teams",
     "inputSchema": {"type": "object", "properties": {"message": {"type": "string"}, "severity": {"type": "string", "default": "info"}, "details": {"type": "object"}}, "required": ["message"]}},
]


def handle_tool_call(name: str, arguments: dict) -> dict:
    try:
        if name == "integration_health":
            return tool_result(get_integration_health(tenant=arguments["tenant"], integration_type=arguments.get("type")))
        elif name == "integration_errors":
            return tool_result(get_integration_errors(tenant=arguments["tenant"], time_range=arguments.get("time_range", "24h")))
        elif name == "integration_detail":
            result = get_integration_detail(tenant=arguments["tenant"], integration_id=arguments["integration_id"])
            return tool_result(result) if result else error_result("Integration not found")
        elif name == "integration_latency":
            return tool_result(get_integration_latency(tenant=arguments["tenant"], integration_id=arguments.get("integration_id"), time_range=arguments.get("time_range", "1h")))
        elif name == "integration_api_status":
            return tool_result(get_integration_api_status(tenant=arguments["tenant"], integration_id=arguments.get("integration_id"), time_range=arguments.get("time_range", "1h")))
        elif name == "credential_check":
            return tool_result(check_credential_validity(tenant=arguments["tenant"], integration_id=arguments["integration_id"]))
        elif name == "entity_store_health":
            return tool_result(get_entity_store_issues(tenant=arguments["tenant"], time_range=arguments.get("time_range", "1h")))
        elif name == "integration_report":
            return tool_result(get_integration_report(tenant=arguments["tenant"]))
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
