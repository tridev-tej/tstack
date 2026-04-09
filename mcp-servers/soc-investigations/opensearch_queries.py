"""OpenSearch queries for SOC investigations."""

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


def search_investigation_errors(
    tenant: str, pattern: str = "investigation", time_range: str = "1h", limit: int = 100,
) -> list[dict[str, Any]]:
    """Search OpenSearch for investigation error patterns."""
    url, auth = get_opensearch_client()

    time_map = {"5m": "now-5m", "15m": "now-15m", "30m": "now-30m", "1h": "now-1h", "6h": "now-6h", "24h": "now-24h", "7d": "now-7d"}
    gte_time = time_map.get(time_range, "now-1h")

    query = {
        "size": limit,
        "query": {
            "bool": {
                "must": [
                    {"match": {"tenant": tenant}},
                    {"match_phrase": {"message": pattern}},
                    {"term": {"levelname": "ERROR"}},
                    {"range": {"@timestamp": {"gte": gte_time}}},
                ]
            }
        },
        "sort": [{"@timestamp": {"order": "desc"}}],
    }

    try:
        response = requests.post(f"{url}/app-*/_search", json=query, auth=auth, timeout=30, verify=True)
        response.raise_for_status()
        data = response.json()

        hits = data.get("hits", {}).get("hits", [])
        return [
            {
                "timestamp": hit["_source"].get("@timestamp"),
                "message": hit["_source"].get("message"),
                "levelname": hit["_source"].get("levelname"),
                "pod": hit["_source"].get("kubernetes", {}).get("pod_name"),
                "logger": hit["_source"].get("logger"),
            }
            for hit in hits
        ]
    except requests.RequestException as e:
        return [{"error": str(e)}]


def get_failure_reasons(tenant: str, time_range: str = "24h") -> dict[str, Any]:
    """Aggregate investigation failure reasons from logs."""
    url, auth = get_opensearch_client()

    time_map = {"1h": "now-1h", "6h": "now-6h", "24h": "now-24h", "7d": "now-7d"}
    gte_time = time_map.get(time_range, "now-24h")

    query = {
        "size": 0,
        "query": {
            "bool": {
                "must": [
                    {"match": {"tenant": tenant}},
                    {"term": {"levelname": "ERROR"}},
                    {
                        "bool": {
                            "should": [
                                {"match_phrase": {"message": "investigation failed"}},
                                {"match_phrase": {"message": "quota exceeded"}},
                                {"match_phrase": {"message": "LLM error"}},
                                {"match_phrase": {"message": "no observables"}},
                                {"match_phrase": {"message": "timeout"}},
                            ]
                        }
                    },
                    {"range": {"@timestamp": {"gte": gte_time}}},
                ]
            }
        },
        "aggs": {"failure_types": {"terms": {"field": "message.keyword", "size": 20}}},
    }

    try:
        response = requests.post(f"{url}/app-*/_search", json=query, auth=auth, timeout=30, verify=True)
        response.raise_for_status()
        data = response.json()

        buckets = data.get("aggregations", {}).get("failure_types", {}).get("buckets", [])
        return {
            "time_range": time_range,
            "failure_reasons": [{"reason": b["key"][:100], "count": b["doc_count"]} for b in buckets],
        }
    except requests.RequestException as e:
        return {"error": str(e)}
