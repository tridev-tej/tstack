"""Common utilities for SOC MCP servers."""

import json
import sys
from datetime import datetime, timezone
from typing import Any


def parse_time_range(time_range: str) -> str:
    """Convert time range string to PostgreSQL interval."""
    mapping = {
        "5m": "5 minutes",
        "15m": "15 minutes",
        "30m": "30 minutes",
        "1h": "1 hour",
        "6h": "6 hours",
        "12h": "12 hours",
        "24h": "24 hours",
        "7d": "7 days",
        "30d": "30 days",
    }
    return mapping.get(time_range, "1 hour")


def format_timestamp(dt: datetime | None) -> str | None:
    """Format datetime to ISO string."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def send_response(response_id: int | str, result: Any) -> None:
    """Send JSON-RPC response to stdout."""
    response = {"jsonrpc": "2.0", "id": response_id, "result": result}
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()


def send_error(response_id: int | str | None, code: int, message: str) -> None:
    """Send JSON-RPC error to stdout."""
    response = {
        "jsonrpc": "2.0",
        "id": response_id,
        "error": {"code": code, "message": message},
    }
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()


def tool_result(content: str | dict | list) -> dict:
    """Format tool result for MCP response."""
    if isinstance(content, (dict, list)):
        text = json.dumps(content, indent=2, default=str)
    else:
        text = str(content)
    return {"content": [{"type": "text", "text": text}]}


def error_result(message: str) -> dict:
    """Format error result for MCP response."""
    return {"content": [{"type": "text", "text": f"Error: {message}"}], "isError": True}
