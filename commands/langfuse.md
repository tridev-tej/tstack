# Langfuse LLM Insights

Query Langfuse for LLM usage insights, traces, costs, and performance metrics.

## Configuration

Read from `~/.claude/langfuse.local.md`:
```yaml
LANGFUSE_HOST: <YOUR_DOMAIN>
LANGFUSE_PUBLIC_KEY: <YOUR_LANGFUSE_PUBLIC_KEY>
LANGFUSE_SECRET_KEY: <YOUR_LANGFUSE_SECRET_KEY>
PROJECT_ID: <YOUR_PROJECT_ID>
```

## Quick Actions

When user invokes `/langfuse`, determine what they need and run the appropriate query:

### 1. Overview / Summary
```bash
export LANGFUSE_HOST="<YOUR_DOMAIN>"
export LANGFUSE_PUBLIC_KEY="<YOUR_LANGFUSE_PUBLIC_KEY>"
export LANGFUSE_SECRET_KEY="<YOUR_LANGFUSE_SECRET_KEY>"

# Get recent traces summary
curl -s -u "$LANGFUSE_PUBLIC_KEY:$LANGFUSE_SECRET_KEY" \
  "$LANGFUSE_HOST/api/public/traces?limit=100" | \
  jq '{
    totalTraces: (.data | length),
    totalCost: ([.data[].totalCost // 0] | add),
    avgLatency: ([.data[].latency // 0] | add / length),
    recentTraces: [.data[:5][] | {name, timestamp, cost: .totalCost, latency}]
  }'
```

### 2. Cost Analysis
```bash
curl -s -u "$LANGFUSE_PUBLIC_KEY:$LANGFUSE_SECRET_KEY" \
  "$LANGFUSE_HOST/api/public/observations?type=GENERATION&limit=500" | \
  jq '[.data[] | {model, cost: .calculatedTotalCost, tokens: (.promptTokens + .completionTokens)}] |
    group_by(.model) |
    map({
      model: .[0].model,
      totalCost: ([.[].cost // 0] | add),
      totalTokens: ([.[].tokens // 0] | add),
      count: length
    }) | sort_by(-.totalCost)'
```

### 3. Recent Generations
```bash
curl -s -u "$LANGFUSE_PUBLIC_KEY:$LANGFUSE_SECRET_KEY" \
  "$LANGFUSE_HOST/api/public/observations?type=GENERATION&limit=20" | \
  jq '.data[] | {
    name,
    model,
    promptTokens,
    completionTokens,
    cost: .calculatedTotalCost,
    time: .startTime
  }'
```

### 4. Errors / Failed Traces
```bash
curl -s -u "$LANGFUSE_PUBLIC_KEY:$LANGFUSE_SECRET_KEY" \
  "$LANGFUSE_HOST/api/public/traces?limit=200" | \
  jq '[.data[] | select(.level == "ERROR" or .level == "WARNING")] | {
    errorCount: length,
    errors: [.[:10][] | {name, level, timestamp, id}]
  }'
```

### 5. Slowest Traces
```bash
curl -s -u "$LANGFUSE_PUBLIC_KEY:$LANGFUSE_SECRET_KEY" \
  "$LANGFUSE_HOST/api/public/traces?limit=100" | \
  jq '[.data[] | select(.latency != null)] | sort_by(-.latency) | .[0:10] | .[] | {name, latency: "\(.latency)ms", cost: .totalCost, id}'
```

### 6. Token Usage
```bash
curl -s -u "$LANGFUSE_PUBLIC_KEY:$LANGFUSE_SECRET_KEY" \
  "$LANGFUSE_HOST/api/public/observations?type=GENERATION&limit=500" | \
  jq '{
    totalPromptTokens: ([.data[].promptTokens // 0] | add),
    totalCompletionTokens: ([.data[].completionTokens // 0] | add),
    totalCost: ([.data[].calculatedTotalCost // 0] | add),
    avgPromptTokens: ([.data[].promptTokens // 0] | add / length | floor),
    avgCompletionTokens: ([.data[].completionTokens // 0] | add / length | floor)
  }'
```

## Dashboard Links

- **Dashboard**: <YOUR_DOMAIN>/project/<YOUR_PROJECT_ID>
- **Traces**: <YOUR_DOMAIN>/project/<YOUR_PROJECT_ID>/traces
- **Generations**: <YOUR_DOMAIN>/project/<YOUR_PROJECT_ID>/generations

## Interpretation Guide

When presenting results:
1. **Cost**: Show in USD, highlight top spenders
2. **Latency**: Flag anything > 5s as slow
3. **Tokens**: Calculate cost efficiency (cost per 1K tokens)
4. **Errors**: Always surface errors first if any exist
