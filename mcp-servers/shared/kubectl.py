"""Kubernetes access via kubectl with kubeconfig contexts."""

import json
import os
import subprocess
from typing import Any

# Map user-friendly cluster names to kubectl context names
CLUSTER_CONTEXTS = {
    "prod": "prod-context",
    "staging": "staging",
    "stage": "staging",
}


def get_context_name(cluster: str) -> str:
    """Get kubectl context name for cluster."""
    return CLUSTER_CONTEXTS.get(cluster.lower(), cluster)


def run_kubectl(
    cluster: str,
    args: list[str],
    namespace: str | None = None,
    output_format: str = "json",
) -> dict[str, Any]:
    """Run kubectl command.

    Args:
        cluster: Cluster name (prod, staging, etc.)
        args: kubectl arguments (e.g., ["get", "pods"])
        namespace: Optional namespace
        output_format: Output format (json, yaml, wide, text)

    Returns:
        Dict with success status and result/error
    """
    context = get_context_name(cluster)
    cmd = ["kubectl", f"--context={context}"]

    if namespace:
        cmd.extend(["-n", namespace])

    cmd.extend(args)

    if output_format and output_format != "text":
        cmd.extend(["-o", output_format])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr or f"kubectl exited with code {result.returncode}",
                "cluster": cluster,
                "context": context,
            }

        if output_format == "json":
            return {
                "success": True,
                "data": json.loads(result.stdout) if result.stdout else {},
                "cluster": cluster,
                "context": context,
            }

        return {"success": True, "data": result.stdout, "cluster": cluster, "context": context}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "kubectl command timed out"}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Failed to parse kubectl output: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_pods(
    cluster: str,
    namespace: str = "default",
    label_selector: str | None = None,
) -> dict[str, Any]:
    """Get pods in cluster/namespace."""
    args = ["get", "pods"]
    if label_selector:
        args.extend(["-l", label_selector])
    return run_kubectl(cluster, args, namespace)


def get_pod_logs(
    cluster: str,
    pod_name: str,
    namespace: str = "default",
    tail_lines: int = 100,
    container: str | None = None,
) -> dict[str, Any]:
    """Get pod logs."""
    args = ["logs", pod_name, f"--tail={tail_lines}"]
    if container:
        args.extend(["-c", container])
    return run_kubectl(cluster, args, namespace, output_format="text")


def get_pod_events(
    cluster: str,
    pod_name: str,
    namespace: str = "default",
) -> dict[str, Any]:
    """Get events for a pod."""
    args = [
        "get",
        "events",
        f"--field-selector=involvedObject.name={pod_name}",
        "--sort-by=.lastTimestamp",
    ]
    return run_kubectl(cluster, args, namespace)


def describe_pod(
    cluster: str,
    pod_name: str,
    namespace: str = "default",
) -> dict[str, Any]:
    """Describe pod (detailed info)."""
    return run_kubectl(cluster, ["describe", "pod", pod_name], namespace, output_format="text")


def get_deployment_pods(
    cluster: str,
    deployment: str,
    namespace: str = "default",
) -> dict[str, Any]:
    """Get pods for a deployment."""
    return get_pods(cluster, namespace, label_selector=f"app={deployment}")
