"""Microsoft Teams webhook notifications."""

import json
import os
from typing import Any

import requests

SEVERITY_COLORS = {
    "critical": "#FF0000",
    "warning": "#FFA500",
    "info": "#0078D4",
    "success": "#00FF00",
}


def send_teams_notification(
    message: str,
    severity: str = "info",
    details: dict[str, Any] | None = None,
    webhook_url: str | None = None,
) -> dict[str, Any]:
    """Send notification to Microsoft Teams via webhook.

    Args:
        message: Main message text
        severity: One of critical, warning, info, success
        details: Optional dict with additional details
        webhook_url: Teams webhook URL (or use TEAMS_WEBHOOK_URL env)

    Returns:
        Dict with success status and message
    """
    url = webhook_url or os.environ.get("TEAMS_WEBHOOK_URL")
    if not url:
        return {"success": False, "error": "No webhook URL configured"}

    color = SEVERITY_COLORS.get(severity.lower(), SEVERITY_COLORS["info"])

    facts = []
    if details:
        for key, value in details.items():
            facts.append({"name": key, "value": str(value)})

    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": color.lstrip("#"),
        "summary": message[:50],
        "sections": [
            {
                "activityTitle": f"SOC Alert: {severity.upper()}",
                "activitySubtitle": message,
                "facts": facts,
                "markdown": True,
            }
        ],
    }

    try:
        response = requests.post(
            url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        response.raise_for_status()
        return {"success": True, "message": "Notification sent"}
    except requests.RequestException as e:
        return {"success": False, "error": str(e)}
