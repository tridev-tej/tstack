---
description: Verify PR code changes against prod data - write scripts, run on pod, validate read-only
arguments:
  - name: pr
    description: "PR number or branch name to verify"
    required: true
  - name: tenant
    description: "Tenant schema to test against (e.g., example-tenant, your-tenant)"
    required: true
  - name: cluster
    description: "K8s context: <YOUR_CLUSTER_1>, <YOUR_CLUSTER_2>, <YOUR_CLUSTER_3>, <YOUR_STAGING_CLUSTER>"
    required: false
    default: "<YOUR_CLUSTER>"
---

# Prod Verify

Validate PR code changes against live prod data using standalone read-only scripts executed on K8s pods.

## ABSOLUTE SAFETY RULES

1. **READ-ONLY ONLY**: Only SELECT queries. NEVER INSERT/UPDATE/DELETE/DROP/ALTER.
2. **No ORM writes**: Never `.save()`, `.create()`, `.update()`, `.delete()`, `.bulk_create()`.
3. **Simulate, don't call**: Rewrite the logic inline in scripts. Don't import/call prod functions that might have side effects.
4. **No management commands**: No `manage.py migrate`, `loaddata`, etc.
5. **No API calls**: Don't POST/PUT/PATCH/DELETE to any endpoints.

## Workflow

### Phase 1: Understand the PR

Read the PR diff to identify changed functions, inputs, outputs, and code paths.

```bash
gh pr diff $PR_NUMBER --repo your-org/your-repo
# or
git diff origin/main...$BRANCH -- python/backend/
```

For each changed function, note:
- What data does it read?
- What logic changed (old vs new)?
- What should the output look like?

### Phase 2: Find the Pod

```bash
# Map cluster to context and namespace
# <YOUR_CLUSTER>  -> context: <YOUR_CLUSTER>,  namespace: <YOUR_NAMESPACE>
# <YOUR_STAGING_CLUSTER> -> context: <YOUR_STAGING_CLUSTER>, namespace: preprod

CONTEXT="$cluster"
NAMESPACE="<YOUR_NAMESPACE>"  # or preprod for staging

# Find the running backend pod
POD=$(kubectl --context $CONTEXT -n $NAMESPACE get po --no-headers | grep backend | grep Running | head -1 | awk '{print $1}')
```

### Phase 3: Explore Data Shape (Iterative)

Before writing the validation script, explore what data actually looks like on prod. This prevents wrong assumptions.

Write a small exploration script to `/tmp/explore.py`:

```python
import json
import sys
import os

sys.path.insert(0, "/code/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

import django
django.setup()

from django.db import connection

cur = connection.cursor()

# Use schema-qualified table names: {tenant}.{table}
# This is MORE RELIABLE than django-tenants schema_context for raw cursors
cur.execute("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema = %s AND table_name = %s
    ORDER BY ordinal_position
""", ['$tenant', 'table_name'])
print([r[0] for r in cur.fetchall()])

# Sample a few rows to see real data shape
cur.execute("SELECT * FROM $tenant.table_name LIMIT 3")
for row in cur.fetchall():
    print(row)
```

Copy and run:
```bash
kubectl --context $CONTEXT -n $NAMESPACE cp /tmp/explore.py $POD:/tmp/explore.py
kubectl --context $CONTEXT -n $NAMESPACE exec $POD -- python /tmp/explore.py 2>/dev/null
```

**Key learnings from real sessions:**
- JSON columns come as strings from raw SQL - always `json.loads()` them
- `schema_context()` doesn't reliably work for raw cursors - use schema-qualified table names (`example-tenant.alerts` not just `alerts`)
- Django model imports may fail if the prod version doesn't have your new code - use raw SQL instead
- Filter stderr noise: append `2>/dev/null` or pipe through `grep -v` for STATIC_URL/Tiktoken/Signal lines

### Phase 4: Write Validation Script

Write a self-contained Python script at `/tmp/validate.py` that:
1. Bootstraps Django
2. Reads prod data via SELECT queries
3. Reimplements the NEW logic inline (don't import from the codebase - it has old code)
4. Runs the new logic against every relevant row
5. Prints summary stats

**Script template:**

```python
import json
import sys
import os
from collections import defaultdict

sys.path.insert(0, "/code/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")

import django
django.setup()

from django.db import connection

# ============================================================
# REIMPLEMENT THE NEW LOGIC HERE (don't import from codebase)
# ============================================================

def new_logic(data):
    """The PR's new code path, reimplemented inline."""
    # ... copy the new logic from the PR diff ...
    pass

# ============================================================
# QUERY PROD DATA
# ============================================================

cur = connection.cursor()
cur.execute("""
    SELECT id, column1, column2
    FROM $tenant.table_name
    WHERE created_at >= NOW() - INTERVAL '$days days'
    ORDER BY created_at DESC
""")
rows = cur.fetchall()

# ============================================================
# VALIDATE AGAINST EVERY ROW
# ============================================================

total = 0
success = 0
failures = []
breakdown = defaultdict(int)

for row in rows:
    total += 1
    id, col1, col2 = row

    # Parse JSON columns
    if isinstance(col1, str):
        try:
            col1 = json.loads(col1)
        except (json.JSONDecodeError, TypeError):
            col1 = {}

    result = new_logic(col1)

    if result_is_valid(result):
        success += 1
        breakdown["success_reason"] += 1
    else:
        failures.append((id, result))
        breakdown["failure_reason"] += 1

# ============================================================
# PRINT SUMMARY
# ============================================================

print(f"Total: {total}, Success: {success}, Failed: {len(failures)}")
if total > 0:
    print(f"Success rate: {success/total*100:.1f}%")

print("\nBreakdown:")
for k, v in sorted(breakdown.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")

if failures:
    print(f"\nFirst 10 failures:")
    for id, result in failures[:10]:
        print(f"  {id}: {result}")
```

### Phase 5: Copy, Run, Iterate

```bash
# Copy script to pod
kubectl --context $CONTEXT -n $NAMESPACE cp /tmp/validate.py $POD:/tmp/validate.py

# Run it
kubectl --context $CONTEXT -n $NAMESPACE exec $POD -- python /tmp/validate.py 2>/dev/null
```

**Iteration pattern:**
1. Run script -> see unexpected results
2. Fix the script locally at /tmp/validate.py
3. Re-copy and re-run
4. Repeat until 100% or you understand every failure

Common iteration fixes:
- JSON columns need `json.loads()`
- Sentinel values (literal `"None"`, `"null"`, `"system"`) pass string checks
- Missing nested fields (check `isinstance` before `.get()`)
- Some rows have no data at all (ingestion gaps)

### Phase 6: Explore Failures

When validation isn't 100%, write a second script to deeply inspect the failures:

```python
# For each failure category, sample one row and dump all fields
# that might contain the data you need
for row in failure_samples:
    print(f"ID: {row['id']}")
    print(f"  All top-level keys: {list(row['data'].keys())}")
    print(f"  Nested field keys: {list(row['nested'].keys())}")
    print(f"  Relevant fields: ...")
```

This reveals alternative data sources you can add to the logic.

### Phase 7: Present Results

```
=== PROD VERIFY: PR #NNN ===
Tenant: $tenant, Cluster: $cluster, Time range: N days

[VALIDATION]
Total records: N
Success: N (X%)
Failed: N (Y%)

[BREAKDOWN BY SOURCE]
source_a: N (X%)
source_b: N (Y%)

[FAILURE ANALYSIS]  (if any)
Category 1 (N records): reason
Category 2 (N records): reason

[EDGE CASES CHECKED]
- Empty data: handled (returns default)
- Null JSON columns: handled (try/except)
- Sentinel values: filtered ("None", "null", etc.)

VERDICT: Safe to deploy / Needs fix for X
```

## Gotchas (from real sessions)

1. **django-tenants schema_context doesn't work for raw cursors** - Use schema-qualified table names (`tenant.table`) instead
2. **JSON columns are strings in raw SQL** - Always `json.loads()` before accessing nested fields
3. **Model imports fail on prod** - Prod has old code, your new models/functions don't exist. Use raw SQL.
4. **Sentinel string values** - Fields like `username: "None"` (literal string) pass `isinstance(val, str) and val` checks. Always filter.
5. **Large output** - Use `2>/dev/null` to suppress Django startup noise. Pipe through `head -N` or `tail -N` for large result sets.
6. **Background commands** - For scripts that take >30s, use Bash tool with `timeout: 60000`
7. **Pod names change** - Always re-fetch the pod name, don't hardcode it
8. **Empty tables** - Some schemas have tables that exist but are empty. Check which table actually has data before writing your validation script.

## Read-Only Reference

```python
# SAFE (read-only):
cur.execute("SELECT ...")
Model.objects.filter(...).count()
Model.objects.filter(...).values_list('field', flat=True)
Model.objects.filter(...).first()
Model.objects.filter(...).exists()

# FORBIDDEN (writes):
# cur.execute("INSERT/UPDATE/DELETE/DROP/ALTER ...")
# Model.objects.create/update/delete/bulk_create/bulk_update(...)
# instance.save() / instance.delete()
# manage.py migrate/loaddata/flush
```
