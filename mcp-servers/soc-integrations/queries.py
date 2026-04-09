"""SQL queries for SOC integrations."""

import os
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.db import execute_query
from shared.utils import parse_time_range


def get_integration_health(tenant: str, integration_type: str | None = None) -> list[dict[str, Any]]:
    type_filter = ""
    params: tuple = ()
    if integration_type:
        type_filter = "AND i.integration_type = %s"
        params = (integration_type,)

    query = f"""
        SELECT i.id, i.name, i.integration_type, i.is_active, i.action_errors, i.action_warnings, i.last_sync_at, i.created_at,
            CASE
                WHEN i.action_errors IS NOT NULL AND i.action_errors != '[]' THEN 'ERROR'
                WHEN i.action_warnings IS NOT NULL AND i.action_warnings != '[]' THEN 'WARNING'
                WHEN i.is_active = false THEN 'INACTIVE'
                ELSE 'WORKING'
            END as health_state
        FROM integrations i WHERE 1=1 {type_filter}
        ORDER BY CASE WHEN i.action_errors IS NOT NULL AND i.action_errors != '[]' THEN 0 WHEN i.action_warnings IS NOT NULL AND i.action_warnings != '[]' THEN 1 ELSE 2 END, i.name
    """
    return execute_query(tenant, query, params)


def get_integration_errors(tenant: str, time_range: str = "24h") -> list[dict[str, Any]]:
    interval = parse_time_range(time_range)
    query = f"""
        SELECT i.id, i.name, i.integration_type, i.action_errors, i.action_warnings, i.last_sync_at, i.updated_at
        FROM integrations i
        WHERE (i.action_errors IS NOT NULL AND i.action_errors != '[]') AND i.updated_at > NOW() - INTERVAL '{interval}'
        ORDER BY i.updated_at DESC
    """
    return execute_query(tenant, query)


def get_integration_detail(tenant: str, integration_id: int) -> dict[str, Any] | None:
    query = """
        SELECT i.id, i.name, i.integration_type, i.is_active, i.action_errors, i.action_warnings, i.last_sync_at, i.created_at, i.updated_at, i.config_keys
        FROM integrations i WHERE i.id = %s
    """
    results = execute_query(tenant, query, (integration_id,))
    if not results:
        return None
    integration = results[0]

    credentials_query = """
        SELECT id, credential_type, is_valid, last_validated_at, validation_error
        FROM integration_credentials WHERE integration_id = %s
    """
    integration["credentials"] = execute_query(tenant, credentials_query, (integration_id,))
    return integration


def get_integration_types(tenant: str) -> list[dict[str, Any]]:
    query = """
        SELECT integration_type, COUNT(*) as count, COUNT(*) FILTER (WHERE is_active) as active_count,
            COUNT(*) FILTER (WHERE action_errors IS NOT NULL AND action_errors != '[]') as error_count
        FROM integrations GROUP BY integration_type ORDER BY count DESC
    """
    return execute_query(tenant, query)


def get_integration_report(tenant: str) -> dict[str, Any]:
    summary_query = """
        SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE is_active) as active,
            COUNT(*) FILTER (WHERE action_errors IS NOT NULL AND action_errors != '[]') as with_errors,
            COUNT(*) FILTER (WHERE action_warnings IS NOT NULL AND action_warnings != '[]') as with_warnings,
            COUNT(*) FILTER (WHERE last_sync_at < NOW() - INTERVAL '24 hours') as stale
        FROM integrations
    """
    summary = execute_query(tenant, summary_query)
    types = get_integration_types(tenant)
    errors = get_integration_errors(tenant, "24h")
    return {"summary": summary[0] if summary else {}, "by_type": types, "recent_errors": errors[:10]}


def get_entity_store_issues(tenant: str, time_range: str = "1h") -> list[dict[str, Any]]:
    query = """
        SELECT i.id, i.name, i.integration_type, i.action_errors, i.updated_at
        FROM integrations i
        WHERE i.action_errors::text ILIKE '%timeout%' OR i.action_errors::text ILIKE '%entity%' OR i.action_errors::text ILIKE '%store%'
        ORDER BY i.updated_at DESC LIMIT 50
    """
    return execute_query(tenant, query)
