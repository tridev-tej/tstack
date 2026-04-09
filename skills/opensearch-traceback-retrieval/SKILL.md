---
name: opensearch-traceback-retrieval
description: |
  Retrieve full Python stack traces from OpenSearch structured JSON logs. Use when:
  (1) opensearch_logs tool shows truncated error messages ending in "...",
  (2) you need the full AttributeError/TypeError/Exception traceback with file/line,
  (3) logs are in structured JSON format with separate `message` and `exc_info` fields.
  Key pattern: full tracebacks live in `exc_info` field, NOT `message`. Search the raw
  `log` field using match_phrase for both filename and "Traceback" together.
author: Claude Code
version: 1.0.0
date: 2026-03-17
---

# OpenSearch Full Traceback Retrieval

## Problem

The `opensearch_logs` MCP tool truncates long messages. When an ERROR log contains a
Python exception, the `message` field shows only the first line (e.g., `'str' object has
no attribute 'get'`) — the full stack trace is cut off.

## Context / Trigger Conditions

- `opensearch_logs` returns messages ending with `...` or cut off mid-sentence
- You need to know which file/line caused the exception
- Python structured logging is in use (JSON logs with `asctime`, `levelname`, `message`, `filename`, `lineno` keys)
- The app logs via a JSON formatter (common in Django/Celery/worker services)

## Solution

Python's `logging` module stores exception info in a separate `exc_info` key in the JSON
log entry. The raw `log` field (the entire JSON string) contains it.

**Step 1 — search the raw `log` field using `match_phrase` for both `filename` and `Traceback`:**

```json
{
  "bool": {
    "must": [
      {"term": {"tenant": "<tenant>"}},
      {"match_phrase": {"log": "<relevant_filename>.py"}},
      {"match_phrase": {"log": "Traceback"}},
      {"range": {"@timestamp": {"gte": "now-24h"}}}
    ]
  }
}
```

Use `mcp__opensearch__opensearch_search` (raw DSL) — NOT `opensearch_logs`.

**Step 2 — the result `_source` will contain a parsed `exc_info` field** with the full
multi-line traceback string, e.g.:

```
"exc_info": "Traceback (most recent call last):\n  File \"task_manager.py\", line 350...\nAttributeError: 'str' object has no attribute 'get'"
```

## Verification

The `_source.exc_info` field contains the complete stack trace with all frame locations.

## Example

```python
# Searching for full traceback for investigation_report.py errors on tenant "example-tenant"
query = {
  "bool": {
    "must": [
      {"term": {"tenant": "example-tenant"}},
      {"match_phrase": {"log": "investigation_report.py"}},
      {"match_phrase": {"log": "Traceback"}},
      {"range": {"@timestamp": {"gte": "now-24h"}}}
    ]
  }
}
# Result _source.exc_info contains the full Python traceback
```

## Notes

- The `log` field is the raw JSON string as emitted by the container — it contains ALL
  fields including `exc_info` as a substring, making `match_phrase` effective.
- The parsed `exc_info` key in `_source` is what you want to read for the full trace.
- This pattern applies to any Django/Python service using JSON structured logging
  (e.g., `worker`, `backend`).
- If `exc_info` is absent, the exception was caught without `exc_info=True` in the
  logger call — look for `message` fields with the raw exception text instead.
- Cluster index patterns: `app-stage-YYYY.MM.DD` for staging, `<YOUR_CLUSTER>YYYY.MM.DD` for prod.
