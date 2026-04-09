---
description: Interact with n8n workflows - list, view, execute, and manage automations
arguments:
  - name: action
    description: "Action: list, view, execute, create, update, activate, deactivate"
    required: false
    default: "list"
  - name: workflow
    description: "Workflow ID or name"
    required: false
  - name: data
    description: "JSON data for workflow execution or creation"
    required: false
---

# n8n Workflow Manager

You are an expert at managing n8n workflows. Use the n8n MCP tools when available, otherwise fall back to direct API/database access.

## Connection Details

```
URL: http://localhost:5678
Email: user@example.com
Password: <YOUR_PASSWORD>
Database: ~/.n8n/database.sqlite
```

## Available Actions

### 1. List Workflows
```bash
sqlite3 ~/.n8n/database.sqlite "SELECT id, name, active, updatedAt FROM workflow_entity ORDER BY updatedAt DESC;"
```

### 2. View Workflow Details
```bash
sqlite3 ~/.n8n/database.sqlite "SELECT * FROM workflow_entity WHERE id='$WORKFLOW_ID' OR name LIKE '%$WORKFLOW_NAME%';"
```

### 3. Check Executions
```bash
sqlite3 ~/.n8n/database.sqlite "SELECT id, status, startedAt, stoppedAt FROM execution_entity WHERE workflowId='$WORKFLOW_ID' ORDER BY startedAt DESC LIMIT 10;"
```

### 4. Activate/Deactivate Workflow
```bash
sqlite3 ~/.n8n/database.sqlite "UPDATE workflow_entity SET active = 1 WHERE id='$WORKFLOW_ID';"  # activate
sqlite3 ~/.n8n/database.sqlite "UPDATE workflow_entity SET active = 0 WHERE id='$WORKFLOW_ID';"  # deactivate
```

### 5. View Execution Errors
```bash
sqlite3 ~/.n8n/database.sqlite "SELECT data FROM execution_data WHERE executionId IN (SELECT id FROM execution_entity WHERE workflowId='$WORKFLOW_ID' AND status='error' ORDER BY startedAt DESC LIMIT 1);"
```

## MCP Tools (when available)

If the n8n MCP server is enabled, prefer using these tools:
- `mcp__n8n__list_workflows` - List all workflows
- `mcp__n8n__get_workflow` - Get workflow details
- `mcp__n8n__execute_workflow` - Trigger workflow execution
- `mcp__n8n__create_workflow` - Create new workflow
- `mcp__n8n__update_workflow` - Update existing workflow
- `mcp__n8n__activate_workflow` - Activate a workflow
- `mcp__n8n__deactivate_workflow` - Deactivate a workflow

## Workflow Structure

```json
{
  "name": "Workflow Name",
  "nodes": [
    {
      "type": "n8n-nodes-base.scheduleTrigger",
      "parameters": {
        "rule": {"interval": [{"field": "hours", "hoursInterval": 3}]}
      }
    },
    {
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {"url": "...", "method": "GET"}
    }
  ],
  "connections": {
    "Node1": {"main": [[{"node": "Node2", "type": "main", "index": 0}]]}
  }
}
```

## Common Triggers

| Trigger | Parameters |
|---------|------------|
| Schedule | `rule.interval[].field: minutes/hours/days` |
| Webhook | `path: /webhook-path` |
| Manual | (no params) |
| Cron | `rule.cronExpression: "0 * * * *"` |

## Execution Instructions

1. Parse action from $ARGUMENTS
2. Check if n8n MCP tools are available
3. If MCP available, use MCP tools
4. Otherwise, use SQLite queries
5. Format and display results

## Example Invocations

`/n8n` → List all workflows
`/n8n view OpenSearch` → Show workflow details
`/n8n execute Ai2DTo7EIJeu9RBa` → Execute workflow
`/n8n activate uQYG_WYIErEkhMfd7rACB` → Activate workflow
`/n8n deactivate uQYG_WYIErEkhMfd7rACB` → Deactivate workflow

## Error Handling

- If workflow not found: List available workflows
- If execution fails: Show error from execution_data
- If n8n not running: Suggest starting n8n (`n8n start`)
