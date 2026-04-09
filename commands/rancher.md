---
description: Interact with Rancher API - list clusters, get kubeconfig, manage nodes, view workloads
arguments:
  - name: action
    description: "Action: clusters (default), cluster, kubeconfig, nodes, workloads, projects, namespaces"
    required: false
    default: "clusters"
  - name: cluster
    description: "Cluster ID or name (for cluster-specific actions)"
    required: false
  - name: project
    description: "Project ID (for project-specific actions)"
    required: false
  - name: namespace
    description: "Namespace name (for namespace-specific actions)"
    required: false
---

# Rancher API Skill

You are an expert at interacting with Rancher for Kubernetes cluster management.

## 🚨🚨🚨 CRITICAL: READ-ONLY OPERATIONS ONLY 🚨🚨🚨

```
╔══════════════════════════════════════════════════════════════════╗
║  ⛔ ALL PRODUCTION DATABASE OPERATIONS MUST BE READ-ONLY ⛔      ║
║                                                                  ║
║  NEVER EVER perform write operations on production databases!    ║
║  This includes <YOUR_CLUSTER> AND <YOUR_CLUSTER> clusters.     ║
╚══════════════════════════════════════════════════════════════════╝
```

**ABSOLUTELY FORBIDDEN:**
- ❌ NO INSERT - Do not add any data
- ❌ NO UPDATE - Do not modify any data
- ❌ NO DELETE - Do not remove any data
- ❌ NO DROP - Do not drop tables/schemas/databases
- ❌ NO ALTER - Do not alter table structures
- ❌ NO TRUNCATE - Do not truncate tables
- ❌ NO CREATE - Do not create new objects
- ❌ NO GRANT/REVOKE - Do not modify permissions

**ONLY ALLOWED:**
- ✅ SELECT queries for reading data
- ✅ information_schema queries for metadata
- ✅ pg_catalog queries for system info

**⚠️ VIOLATIONS CAN CAUSE:**
- Production data loss
- Service outages affecting real customers
- Compliance violations
- Security incidents

**ALWAYS double-check your query before executing!**

## Connection Details

```
API Endpoint: <YOUR_DOMAIN>
Token ID: <YOUR_TOKEN_ID>
Bearer Token: <YOUR_RANCHER_TOKEN>
```

## Authentication

All API calls use Bearer token authentication:
```bash
TOKEN="<YOUR_RANCHER_TOKEN>"
curl -s -H "Authorization: Bearer $TOKEN" "<YOUR_DOMAIN>/..."
```

## IMPORTANT: API Access Notes

The v3 management API (`/v3/clusters`) requires admin RBAC permissions and may return 401 even with valid tokens.
However, the **k8s proxy path works** for direct cluster access:
- Use: `<YOUR_DOMAIN>/k8s/clusters/<CLUSTER_ID>/api/v1/...`
- This proxies kubectl commands through Rancher

**To find cluster IDs:**
1. Go to Rancher UI → Click on a cluster
2. Look at URL: `/c/<CLUSTER_ID>/...` or `/dashboard/c/<CLUSTER_ID>/...`
3. Or download kubeconfig from UI which contains the cluster ID

## Action Handlers

### action: clusters (DEFAULT)
List all available clusters with their status.

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
     "<YOUR_DOMAIN>/v3/clusters" | jq -r '
  .data[] |
  "Cluster: \(.name)\n  ID: \(.id)\n  State: \(.state)\n  Provider: \(.provider // "unknown")\n  K8s Version: \(.version.gitVersion // "unknown")\n  Nodes: \(.nodeCount // 0)\n"'
```

**Output should include:**
- Cluster name and ID
- State (active, provisioning, etc.)
- Kubernetes version
- Node count

---

### action: cluster
Get detailed information about a specific cluster.

**Requires:** `cluster` argument (ID or name)

If cluster name provided, first resolve to ID:
```bash
# Get cluster ID from name
CLUSTER_ID=$(curl -s -H "Authorization: Bearer $TOKEN" \
     "<YOUR_DOMAIN>/v3/clusters" | jq -r '.data[] | select(.name=="<CLUSTER_NAME>") | .id')
```

Then get cluster details:
```bash
curl -s -H "Authorization: Bearer $TOKEN" \
     "<YOUR_DOMAIN>/v3/clusters/<CLUSTER_ID>" | jq '{
  name: .name,
  id: .id,
  state: .state,
  provider: .provider,
  k8sVersion: .version.gitVersion,
  nodeCount: .nodeCount,
  created: .created,
  apiEndpoint: .apiEndpoint,
  conditions: [.conditions[]? | {type: .type, status: .status, message: .message}]
}'
```

---

### action: kubeconfig
Generate and save kubeconfig for a cluster.

**Requires:** `cluster` argument (ID or name)

```bash
# Get cluster ID if name provided
CLUSTER_ID="<CLUSTER_ID_OR_RESOLVED>"

# Generate kubeconfig
curl -s -X POST \
     -H "Authorization: Bearer $TOKEN" \
     "<YOUR_DOMAIN>/v3/clusters/${CLUSTER_ID}?action=generateKubeconfig" | jq -r '.config'
```

**After getting kubeconfig:**
1. Show the user a preview of the contexts it contains
2. Ask if they want to save it (merge with existing or replace)
3. If saving, write to `~/.kube/config` or a separate file

---

### action: nodes
List nodes in a cluster with resource usage.

**Requires:** `cluster` argument (ID or name)

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
     "<YOUR_DOMAIN>/v3/clusters/<CLUSTER_ID>/nodes" | jq -r '
  .data[] |
  "Node: \(.nodeName // .hostname)\n  State: \(.state)\n  Role: \(.controlPlane // false | if . then "control-plane" else "worker" end)\n  IP: \(.ipAddress)\n  OS: \(.info.os.operatingSystem // "unknown")\n  CPU: \(.requested.cpu // "0")/\(.allocatable.cpu // "?")\n  Memory: \(.requested.memory // "0")/\(.allocatable.memory // "?")\n"'
```

---

### action: workloads
List workloads (deployments) in a cluster or project.

**Requires:** `cluster` argument, optionally `project` and `namespace`

```bash
# List all workloads in cluster
curl -s -H "Authorization: Bearer $TOKEN" \
     "<YOUR_DOMAIN>/v3/project/<PROJECT_ID>/workloads" | jq -r '
  .data[] |
  "Workload: \(.name)\n  Namespace: \(.namespaceId)\n  Type: \(.type)\n  State: \(.state)\n  Replicas: \(.scale // 1)\n  Image: \(.containers[0].image // "unknown")\n"'
```

To get project ID:
```bash
curl -s -H "Authorization: Bearer $TOKEN" \
     "<YOUR_DOMAIN>/v3/clusters/<CLUSTER_ID>/projects" | jq '.data[] | {name: .name, id: .id}'
```

---

### action: projects
List projects in a cluster.

**Requires:** `cluster` argument (ID or name)

```bash
curl -s -H "Authorization: Bearer $TOKEN" \
     "<YOUR_DOMAIN>/v3/clusters/<CLUSTER_ID>/projects" | jq -r '
  .data[] |
  "Project: \(.name)\n  ID: \(.id)\n  State: \(.state)\n  Namespaces: \(.namespaces | keys | join(", "))\n"'
```

---

### action: namespaces
List namespaces in a cluster or project.

**Requires:** `cluster` argument, optionally `project`

```bash
# All namespaces in cluster
curl -s -H "Authorization: Bearer $TOKEN" \
     "<YOUR_DOMAIN>/v3/clusters/<CLUSTER_ID>/namespaces" | jq -r '
  .data[] |
  "Namespace: \(.name)\n  Project: \(.projectId // "none")\n  State: \(.state)\n"'
```

---

## Cluster-Specific Setup (Example)

For each cluster you want to target, add a block like the one below to a private copy of this file. Keep cluster IDs, tokens, DB hosts, tenant counts, region details, and any other environment-specific details out of the tracked version.

```
Cluster Name: <YOUR_CLUSTER>
Cluster ID: <YOUR_CLUSTER_ID>
K8s Version: <YOUR_K8S_VERSION>
Rancher URL: <YOUR_DOMAIN>/dashboard/c/<YOUR_CLUSTER_ID>/explorer
```

### Kubeconfig template
```yaml
apiVersion: v1
kind: Config
clusters:
- name: "<YOUR_CLUSTER>"
  cluster:
    server: "<YOUR_DOMAIN>/k8s/clusters/<YOUR_CLUSTER_ID>"
users:
- name: "<YOUR_CLUSTER>"
  user:
    token: "<YOUR_KUBECONFIG_TOKEN>"
contexts:
- name: "<YOUR_CLUSTER>"
  context:
    user: "<YOUR_CLUSTER>"
    cluster: "<YOUR_CLUSTER>"
```

### Query Postgres via kubectl exec
```bash
kubectl exec <YOUR_POSTGRES_POD> -n <YOUR_NAMESPACE> -- bash -c \
  'PGPASSWORD="<YOUR_DB_PASSWORD>" psql -U postgres -d "<YOUR_DB_NAME>" -c "YOUR_QUERY_HERE"'
```

**IMPORTANT:** Always use READ-ONLY queries. Do not attempt INSERT, UPDATE, DELETE, or DDL operations on any production database.

## API Reference

### Base Endpoints
| Resource | Endpoint |
|----------|----------|
| Clusters | `/v3/clusters` |
| Cluster Detail | `/v3/clusters/{id}` |
| Nodes | `/v3/clusters/{id}/nodes` |
| Projects | `/v3/clusters/{id}/projects` |
| Namespaces | `/v3/clusters/{id}/namespaces` |
| Workloads | `/v3/project/{projectId}/workloads` |
| Pods | `/v3/project/{projectId}/pods` |
| Services | `/v3/project/{projectId}/services` |
| Secrets | `/v3/project/{projectId}/secrets` |
| ConfigMaps | `/v3/project/{projectId}/configMaps` |

### Useful Actions
| Action | Method | Endpoint |
|--------|--------|----------|
| Generate Kubeconfig | POST | `/v3/clusters/{id}?action=generateKubeconfig` |
| Rotate Certificates | POST | `/v3/clusters/{id}?action=rotateCertificates` |

## Error Handling

Common errors:
- `401 Unauthorized` - Token expired or invalid
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource doesn't exist

## Usage Examples

```
/rancher                           # List all clusters
/rancher cluster=aws-staging       # Get staging cluster details
/rancher action=kubeconfig cluster=c-m-pq9dkqnr  # Get kubeconfig for staging
/rancher action=nodes cluster=aws-production     # List production nodes
/rancher action=projects cluster=aws-staging     # List staging projects
```

---

## 🚨🚨🚨 FINAL REMINDER: PRODUCTION DATABASE SAFETY 🚨🚨🚨

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║   🛑 STOP AND THINK BEFORE EVERY PRODUCTION DATABASE QUERY! 🛑            ║
║                                                                           ║
║   1. Is this a SELECT query? (ONLY SELECT is allowed)                     ║
║   2. Am I 100% sure this won't modify data?                               ║
║   3. Have I double-checked for typos?                                     ║
║                                                                           ║
║   REMEMBER: Real customers depend on this data!                           ║
║   One wrong query = potential data loss + service outage                  ║
║                                                                           ║
║   ✅ SELECT, information_schema, pg_catalog = SAFE                        ║
║   ❌ INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE = FORBIDDEN            ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
```
