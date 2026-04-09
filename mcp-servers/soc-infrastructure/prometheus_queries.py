"""Prometheus queries for SOC infrastructure."""

import os
from typing import Any

import requests
from requests.auth import HTTPBasicAuth


def get_prometheus_client() -> tuple[str, HTTPBasicAuth | None]:
    """Get Prometheus URL and auth."""
    url = os.environ.get("PROMETHEUS_URL", "https://prometheus.example.com")
    user = os.environ.get("PROMETHEUS_USER", "")
    password = os.environ.get("PROMETHEUS_PASSWORD", "")
    auth = HTTPBasicAuth(user, password) if user and password else None
    return url, auth


def query_prometheus(query: str) -> dict[str, Any]:
    """Execute PromQL query."""
    url, auth = get_prometheus_client()
    try:
        response = requests.get(f"{url}/api/v1/query", params={"query": query}, auth=auth, timeout=30, verify=True)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"status": "error", "error": str(e)}


def query_prometheus_range(query: str, start: str, end: str, step: str = "1m") -> dict[str, Any]:
    """Execute PromQL range query."""
    url, auth = get_prometheus_client()
    try:
        response = requests.get(f"{url}/api/v1/query_range", params={"query": query, "start": start, "end": end, "step": step}, auth=auth, timeout=30, verify=True)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"status": "error", "error": str(e)}


def get_pod_memory_usage(namespace: str = "default", pod_pattern: str = ".*") -> dict[str, Any]:
    return query_prometheus(f'100 * sum by (pod) (container_memory_working_set_bytes{{namespace="{namespace}", pod=~"{pod_pattern}"}}) / sum by (pod) (container_spec_memory_limit_bytes{{namespace="{namespace}", pod=~"{pod_pattern}"}} > 0)')

def get_pod_cpu_usage(namespace: str = "default", pod_pattern: str = ".*") -> dict[str, Any]:
    return query_prometheus(f'sum by (pod) (rate(container_cpu_usage_seconds_total{{namespace="{namespace}", pod=~"{pod_pattern}"}}[5m])) * 100')

def get_pod_restarts(namespace: str = "default", pod_pattern: str = ".*") -> dict[str, Any]:
    return query_prometheus(f'sum by (pod) (kube_pod_container_status_restarts_total{{namespace="{namespace}", pod=~"{pod_pattern}"}})')

def get_oom_kills(namespace: str = "default", lookback: str = "1h") -> dict[str, Any]:
    return query_prometheus(f'sum by (pod) (increase(kube_pod_container_status_last_terminated_reason{{namespace="{namespace}", reason="OOMKilled"}}[{lookback}])) > 0')

def get_db_connection_usage() -> dict[str, Any]:
    return query_prometheus('sum(pg_stat_activity_count) / max(pg_settings_max_connections) * 100')

def get_db_slow_queries(threshold_seconds: float = 1.0) -> dict[str, Any]:
    return query_prometheus(f'sum(pg_stat_activity_count{{state="active"}}) and on() (pg_stat_activity_max_tx_duration > {threshold_seconds})')

def get_queue_depth(tenant_pattern: str = ".*") -> dict[str, Any]:
    return query_prometheus(f'sum by (tenant) (task_queue_depth{{tenant=~"{tenant_pattern}"}})')

def get_disk_io_metrics(namespace: str = "default") -> dict[str, Any]:
    reads = query_prometheus(f'sum by (pod) (rate(container_fs_reads_bytes_total{{namespace="{namespace}"}}[5m]))')
    writes = query_prometheus(f'sum by (pod) (rate(container_fs_writes_bytes_total{{namespace="{namespace}"}}[5m]))')
    return {"reads": reads, "writes": writes}
