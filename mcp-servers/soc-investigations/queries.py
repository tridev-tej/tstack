"""SQL queries for SOC investigations."""

import os
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.db import execute_query
from shared.utils import parse_time_range


def get_investigation_health(tenant: str, time_range: str = "1h") -> dict[str, Any]:
    """Get investigation health dashboard metrics."""
    interval = parse_time_range(time_range)

    stuck_query = """
        SELECT COUNT(*) as count
        FROM investigations i
        WHERE i.investigation_status IN ('PENDING', 'TRIAGE_PENDING')
          AND i.updated_at < NOW() - INTERVAL '1 hour'
    """

    failed_query = f"""
        SELECT COUNT(*) as count
        FROM investigations i
        WHERE i.investigation_status = 'FAILED'
          AND i.updated_at > NOW() - INTERVAL '{interval}'
    """

    completed_query = f"""
        SELECT
            COUNT(*) as count,
            AVG(EXTRACT(EPOCH FROM (i.updated_at - i.created_at))) as avg_seconds,
            AVG(i.confidence) as avg_confidence
        FROM investigations i
        WHERE i.investigation_status = 'COMPLETED'
          AND i.updated_at > NOW() - INTERVAL '{interval}'
    """

    total_query = f"""
        SELECT COUNT(*) as count
        FROM investigations i
        WHERE i.created_at > NOW() - INTERVAL '{interval}'
    """

    stuck = execute_query(tenant, stuck_query)
    failed = execute_query(tenant, failed_query)
    completed = execute_query(tenant, completed_query)
    total = execute_query(tenant, total_query)

    completed_data = completed[0] if completed else {}
    avg_seconds = completed_data.get("avg_seconds") or 0
    avg_confidence = completed_data.get("avg_confidence") or 0
    completed_count = completed_data.get("count") or 0
    total_count = total[0].get("count", 0) if total else 0

    failure_rate = 0
    if total_count > 0:
        failure_rate = round((failed[0].get("count", 0) / total_count) * 100, 2)

    return {
        "time_range": time_range,
        "stuck_count": stuck[0].get("count", 0) if stuck else 0,
        "failed_count": failed[0].get("count", 0) if failed else 0,
        "completed_count": completed_count,
        "total_count": total_count,
        "failure_rate_pct": failure_rate,
        "avg_completion_seconds": round(avg_seconds, 1) if avg_seconds else None,
        "avg_confidence": round(avg_confidence, 1) if avg_confidence else None,
    }


def get_stuck_investigations(tenant: str, threshold_minutes: int = 60, limit: int = 20) -> list[dict[str, Any]]:
    """Get investigations stuck in PENDING or TRIAGE_PENDING."""
    query = f"""
        SELECT
            i.id as investigation_id, i.investigation_status, i.updated_at, i.created_at,
            i.confidence, i.finding_id, f.title as finding_title, f.source, f.severity,
            EXTRACT(EPOCH FROM (NOW() - i.updated_at))/60 as stuck_minutes
        FROM investigations i
        JOIN alerts f ON i.finding_id = f.id
        WHERE i.investigation_status IN ('PENDING', 'TRIAGE_PENDING')
          AND i.updated_at < NOW() - INTERVAL '{threshold_minutes} minutes'
        ORDER BY i.updated_at
        LIMIT {limit}
    """
    return execute_query(tenant, query)


def get_failed_investigations(tenant: str, time_range: str = "24h", limit: int = 50) -> list[dict[str, Any]]:
    """Get recently failed investigations."""
    interval = parse_time_range(time_range)
    query = f"""
        SELECT
            i.id as investigation_id, i.investigation_status, i.updated_at, i.created_at,
            i.finding_id, f.title as finding_title, f.source, f.severity, i.investigation_report
        FROM investigations i
        JOIN alerts f ON i.finding_id = f.id
        WHERE i.investigation_status = 'FAILED'
          AND i.updated_at > NOW() - INTERVAL '{interval}'
        ORDER BY i.updated_at DESC
        LIMIT {limit}
    """
    return execute_query(tenant, query)


def get_investigation_detail(tenant: str, investigation_id: int) -> dict[str, Any] | None:
    """Get full details for a specific investigation."""
    query = """
        SELECT i.*, f.title as finding_title, f.source, f.severity,
            f.created_at as finding_created_at, f.raw_alert
        FROM investigations i
        JOIN alerts f ON i.finding_id = f.id
        WHERE i.id = %s
    """
    results = execute_query(tenant, query, (investigation_id,))
    return results[0] if results else None


def get_investigation_timeline(tenant: str, investigation_id: int) -> list[dict[str, Any]]:
    """Get status history for an investigation."""
    query = """
        SELECT id, old_status, new_status, changed_at, changed_by, reason
        FROM investigation_status_history
        WHERE investigation_id = %s
        ORDER BY changed_at
    """
    return execute_query(tenant, query, (investigation_id,))


def get_retry_analysis(tenant: str, finding_id: int) -> dict[str, Any]:
    """Analyze retries for a finding."""
    attempts_query = """
        SELECT i.id as investigation_id, i.investigation_status, i.created_at,
            i.updated_at, i.confidence, i.investigation_report
        FROM investigations i
        WHERE i.finding_id = %s
        ORDER BY i.created_at
    """
    attempts = execute_query(tenant, attempts_query, (finding_id,))

    finding_query = """
        SELECT id, title, source, severity, created_at
        FROM alerts WHERE id = %s
    """
    finding_results = execute_query(tenant, finding_query, (finding_id,))

    return {
        "finding": finding_results[0] if finding_results else None,
        "retry_count": len(attempts),
        "attempts": attempts,
    }


def get_low_confidence_report(tenant: str, threshold: int = 50, time_range: str = "24h", limit: int = 50) -> list[dict[str, Any]]:
    """Get completed investigations with low confidence."""
    interval = parse_time_range(time_range)
    query = f"""
        SELECT
            i.id as investigation_id, i.confidence, i.updated_at, i.finding_id,
            f.title as finding_title, f.source, f.severity, i.investigation_report
        FROM investigations i
        JOIN alerts f ON i.finding_id = f.id
        WHERE i.investigation_status = 'COMPLETED'
          AND i.confidence < {threshold}
          AND i.updated_at > NOW() - INTERVAL '{interval}'
        ORDER BY i.confidence ASC
        LIMIT {limit}
    """
    return execute_query(tenant, query)


def get_tenant_llm_quota(tenant: str) -> dict[str, Any]:
    """Get LLM usage vs quota for tenant."""
    usage_query = """
        SELECT SUM(input_tokens) as total_input_tokens, SUM(output_tokens) as total_output_tokens,
            SUM(cost_cents) as total_cost_cents, COUNT(*) as call_count
        FROM llm_usage
        WHERE created_at > DATE_TRUNC('day', NOW())
    """
    quota_query = """
        SELECT daily_llm_calls_limit, daily_llm_tokens_limit
        FROM tenant_quota LIMIT 1
    """
    usage = execute_query(tenant, usage_query)
    quota = execute_query(tenant, quota_query)
    usage_data = usage[0] if usage else {}
    quota_data = quota[0] if quota else {}

    return {
        "today_usage": {
            "input_tokens": usage_data.get("total_input_tokens") or 0,
            "output_tokens": usage_data.get("total_output_tokens") or 0,
            "cost_cents": usage_data.get("total_cost_cents") or 0,
            "call_count": usage_data.get("call_count") or 0,
        },
        "quota": {
            "daily_calls_limit": quota_data.get("daily_llm_calls_limit"),
            "daily_tokens_limit": quota_data.get("daily_llm_tokens_limit"),
        },
    }


def get_tenant_alert_volume(tenant: str, time_range: str = "24h") -> dict[str, Any]:
    """Get alert ingestion metrics."""
    interval = parse_time_range(time_range)
    volume_query = f"""
        SELECT COUNT(*) as total_alerts,
            COUNT(CASE WHEN status = 'NEW' THEN 1 END) as pending,
            COUNT(CASE WHEN status = 'INVESTIGATING' THEN 1 END) as investigating,
            COUNT(CASE WHEN status = 'RESOLVED' THEN 1 END) as resolved
        FROM alerts
        WHERE created_at > NOW() - INTERVAL '{interval}'
    """
    hourly_query = f"""
        SELECT DATE_TRUNC('hour', created_at) as hour, COUNT(*) as count
        FROM alerts
        WHERE created_at > NOW() - INTERVAL '{interval}'
        GROUP BY DATE_TRUNC('hour', created_at)
        ORDER BY hour DESC LIMIT 24
    """
    volume = execute_query(tenant, volume_query)
    hourly = execute_query(tenant, hourly_query)

    return {"time_range": time_range, "summary": volume[0] if volume else {}, "hourly_breakdown": hourly}
