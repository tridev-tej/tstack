"""Kubernetes operations for SOC infrastructure."""

import os
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.kubectl import describe_pod, get_deployment_pods, get_pod_events, get_pod_logs, get_pods, run_kubectl


def get_worker_health(cluster: str, namespace: str = "default", pod_prefix: str = "worker") -> dict[str, Any]:
    """Get SOC worker pod health status."""
    result = get_pods(cluster, namespace)
    if not result["success"]:
        return result

    pods = result["data"].get("items", [])
    worker_pods = [p for p in pods if pod_prefix in p.get("metadata", {}).get("name", "")]

    health_data = []
    for pod in worker_pods:
        metadata = pod.get("metadata", {})
        status = pod.get("status", {})
        container_statuses = status.get("containerStatuses", [])
        restarts = sum(c.get("restartCount", 0) for c in container_statuses)
        ready_containers = sum(1 for c in container_statuses if c.get("ready", False))

        last_state = None
        for cs in container_statuses:
            last_terminated = cs.get("lastState", {}).get("terminated", {})
            if last_terminated:
                last_state = {"reason": last_terminated.get("reason"), "exitCode": last_terminated.get("exitCode"), "finishedAt": last_terminated.get("finishedAt")}

        health_data.append({
            "name": metadata.get("name"), "phase": status.get("phase"),
            "ready": f"{ready_containers}/{len(container_statuses)}", "restarts": restarts,
            "last_termination": last_state, "node": status.get("hostIP"), "started_at": status.get("startTime"),
        })

    return {"success": True, "cluster": cluster, "namespace": namespace, "worker_count": len(health_data), "workers": health_data}


def get_pod_status(cluster: str, pod_name: str | None = None, deployment: str | None = None, namespace: str = "default") -> dict[str, Any]:
    """Get detailed pod status."""
    if deployment:
        pods_result = get_deployment_pods(cluster, deployment, namespace)
        if not pods_result["success"]:
            return pods_result
        pods = pods_result["data"].get("items", [])
    elif pod_name:
        pods_result = get_pods(cluster, namespace)
        if not pods_result["success"]:
            return pods_result
        pods = [p for p in pods_result["data"].get("items", []) if pod_name in p.get("metadata", {}).get("name", "")]
    else:
        return {"success": False, "error": "Provide pod_name or deployment"}

    pod_details = []
    for pod in pods:
        name = pod.get("metadata", {}).get("name")
        events_result = get_pod_events(cluster, name, namespace)
        events = []
        if events_result["success"]:
            for event in events_result["data"].get("items", [])[-5:]:
                events.append({"type": event.get("type"), "reason": event.get("reason"), "message": event.get("message"), "last_timestamp": event.get("lastTimestamp")})
        pod_details.append({"name": name, "status": pod.get("status", {}), "recent_events": events})

    return {"success": True, "cluster": cluster, "namespace": namespace, "pods": pod_details}


def get_recent_oom_events(cluster: str, namespace: str = "default", time_range: str = "1h") -> dict[str, Any]:
    """Get pods with recent OOM kills."""
    pods_result = get_pods(cluster, namespace)
    if not pods_result["success"]:
        return pods_result

    oom_pods = []
    for pod in pods_result["data"].get("items", []):
        for cs in pod.get("status", {}).get("containerStatuses", []):
            last_terminated = cs.get("lastState", {}).get("terminated", {})
            if last_terminated.get("reason") == "OOMKilled":
                oom_pods.append({
                    "pod": pod.get("metadata", {}).get("name"), "container": cs.get("name"),
                    "exit_code": last_terminated.get("exitCode"), "finished_at": last_terminated.get("finishedAt"),
                    "restarts": cs.get("restartCount", 0),
                })

    return {"success": True, "cluster": cluster, "namespace": namespace, "oom_count": len(oom_pods), "oom_events": oom_pods}


def get_infra_report(cluster: str, namespace: str = "default") -> dict[str, Any]:
    """Combined infrastructure health report."""
    worker_health = get_worker_health(cluster, namespace)
    oom_events = get_recent_oom_events(cluster, namespace)

    summary = {
        "cluster": cluster, "namespace": namespace,
        "worker_health": worker_health if worker_health["success"] else None,
        "oom_events": oom_events if oom_events["success"] else None,
        "alerts": [],
    }

    if worker_health["success"]:
        for w in worker_health.get("workers", []):
            if w.get("restarts", 0) > 5:
                summary["alerts"].append({"severity": "warning", "message": f"Pod {w['name']} has {w['restarts']} restarts"})

    if oom_events["success"] and oom_events.get("oom_count", 0) > 0:
        summary["alerts"].append({"severity": "critical", "message": f"{oom_events['oom_count']} OOM events detected"})

    return summary
