"""Integration health checks and connectivity tests."""

import os
from typing import Any

import requests
from requests.auth import HTTPBasicAuth


def get_opensearch_client() -> tuple[str, HTTPBasicAuth]:
    """Get OpenSearch URL and auth."""
    url = os.environ.get("OPENSEARCH_URL", "https://opensearch.example.com")
    user = os.environ.get("OPENSEARCH_USER", "")
    password = os.environ.get("OPENSEARCH_PASSWORD", "")
    return url, HTTPBasicAuth(user, password)


def get_integration_latency(tenant: str, integration_id: int | None = None, time_range: str = "1h") -> dict[str, Any]:
    """Get API call latency percentiles from OpenSearch logs."""
    url, auth = get_opensearch_client()
    time_map = {"15m": "now-15m", "1h": "now-1h", "6h": "now-6h", "24h": "now-24h"}
    gte_time = time_map.get(time_range, "now-1h")

    integration_filter = [{"term": {"integration_id": integration_id}}] if integration_id else []

    query = {
        "size": 0,
        "query": {"bool": {"must": [{"match": {"tenant": tenant}}, {"exists": {"field": "response_time_ms"}}, {"range": {"@timestamp": {"gte": gte_time}}}, *integration_filter]}},
        "aggs": {
            "latency_stats": {"percentiles": {"field": "response_time_ms", "percents": [50, 90, 95, 99]}},
            "by_integration": {"terms": {"field": "integration_name.keyword", "size": 20}, "aggs": {"avg_latency": {"avg": {"field": "response_time_ms"}}, "p99_latency": {"percentiles": {"field": "response_time_ms", "percents": [99]}}}},
        },
    }

    try:
        response = requests.post(f"{url}/app-*/_search", json=query, auth=auth, timeout=30, verify=True)
        response.raise_for_status()
        aggs = response.json().get("aggregations", {})
        return {
            "overall": aggs.get("latency_stats", {}).get("values", {}),
            "by_integration": [{"name": b["key"], "avg_ms": b.get("avg_latency", {}).get("value"), "p99_ms": b.get("p99_latency", {}).get("values", {}).get("99.0"), "count": b["doc_count"]} for b in aggs.get("by_integration", {}).get("buckets", [])],
        }
    except requests.RequestException as e:
        return {"error": str(e)}


def get_integration_api_status(tenant: str, integration_id: int | None = None, time_range: str = "1h") -> dict[str, Any]:
    """Get success/failure rates by HTTP status code."""
    url, auth = get_opensearch_client()
    time_map = {"15m": "now-15m", "1h": "now-1h", "6h": "now-6h", "24h": "now-24h"}
    gte_time = time_map.get(time_range, "now-1h")

    integration_filter = [{"term": {"integration_id": integration_id}}] if integration_id else []

    query = {
        "size": 0,
        "query": {"bool": {"must": [{"match": {"tenant": tenant}}, {"exists": {"field": "http_status"}}, {"range": {"@timestamp": {"gte": gte_time}}}, *integration_filter]}},
        "aggs": {
            "by_status": {"terms": {"field": "http_status", "size": 20}},
            "by_integration": {"terms": {"field": "integration_name.keyword", "size": 20}, "aggs": {"status_codes": {"terms": {"field": "http_status", "size": 10}}}},
        },
    }

    try:
        response = requests.post(f"{url}/app-*/_search", json=query, auth=auth, timeout=30, verify=True)
        response.raise_for_status()
        aggs = response.json().get("aggregations", {})
        status_buckets = aggs.get("by_status", {}).get("buckets", [])
        total = sum(b["doc_count"] for b in status_buckets)
        success = sum(b["doc_count"] for b in status_buckets if 200 <= b["key"] < 300)
        errors = sum(b["doc_count"] for b in status_buckets if b["key"] >= 400)

        return {
            "total_calls": total, "success_count": success, "error_count": errors,
            "success_rate_pct": round((success / total) * 100, 2) if total > 0 else 0,
            "by_status_code": [{"status": b["key"], "count": b["doc_count"]} for b in status_buckets],
            "by_integration": [{"name": b["key"], "total": b["doc_count"], "status_breakdown": [{"status": s["key"], "count": s["doc_count"]} for s in b.get("status_codes", {}).get("buckets", [])]} for b in aggs.get("by_integration", {}).get("buckets", [])],
        }
    except requests.RequestException as e:
        return {"error": str(e)}


def check_credential_validity(tenant: str, integration_id: int) -> dict[str, Any]:
    """Check if integration credentials are valid (read-only DB check)."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from shared.db import execute_query

    query = """
        SELECT ic.id, ic.credential_type, ic.is_valid, ic.last_validated_at, ic.validation_error,
            i.name as integration_name, i.integration_type
        FROM integration_credentials ic
        JOIN integrations i ON ic.integration_id = i.id
        WHERE ic.integration_id = %s
    """
    results = execute_query(tenant, query, (integration_id,))
    if not results:
        return {"integration_id": integration_id, "status": "NO_CREDENTIALS", "message": "No credentials found for integration"}

    all_valid = all(r.get("is_valid", False) for r in results)
    has_errors = any(r.get("validation_error") for r in results)
    return {"integration_id": integration_id, "status": "VALID" if all_valid else "INVALID" if has_errors else "UNKNOWN", "credentials": results}
