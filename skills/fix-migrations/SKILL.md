---
name: fix-migrations
version: 1.0.0
description: |
  Fix Django migration conflicts on a feature branch after merging main.
  Detects duplicate migration numbers, renumbers branch-owned migrations
  to follow the latest on main, removes stale merge migrations, and
  updates dependency references. Use when asked to "fix migrations",
  "resolve migration conflicts", or after merging main into a branch
  that has migration collisions.
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - Agent
  - AskUserQuestion
---

# Fix Django Migration Conflicts

Resolve migration number collisions between a feature branch and main after a merge.

## Context

This project uses Django with `django-tenants`. Migrations live under:
```
python/backend/apps/*/migrations/
```

## Strategy

The correct fix is NOT merge migrations. Instead:
1. Identify which migration files were added by the branch (not main)
2. Renumber them to come after the latest migration on main
3. Update their `dependencies` to point to the correct predecessor
4. Delete any merge migrations that are no longer needed

## Steps

### 1. Identify branch-owned migrations

```bash
git diff origin/main...HEAD --name-only -- "*/migrations/*"
```

This shows only migrations added or modified by the branch.

### 2. Find duplicate migration numbers

For each app that has branch-owned migrations, check if main also has a migration with the same number:

```bash
# List all migration files in the app to spot number collisions
ls python/backend/apps/<app>/migrations/ | tail -20
```

### 3. Renumber branch migrations

For each conflicting migration:
1. Find the highest migration number on main for that app
2. Renumber the branch migration to `<highest + 1>`
3. Update the `dependencies` list inside the migration file to depend on the correct predecessor (the last migration on main for that app)

### 4. Remove merge migrations

Delete any merge migrations created by the branch (files with `merge` in the name that were added by the branch). These are unnecessary when you renumber properly.

### 5. Verify no dangling references

```bash
# Check nothing still references old migration names
grep -r "<old_migration_name>" python/backend/apps/
```

### 6. Verify clean chain

```bash
# List final state - should show no duplicate numbers for branch-affected apps
ls python/backend/apps/<app>/migrations/ | tail -10
```

## Important rules

- NEVER touch migrations that belong to main - only renumber branch-owned ones
- ALWAYS update the `dependencies` tuple inside the migration file after renumbering
- Migration content (operations) stays exactly the same - only the filename and dependencies change
- Check ALL apps, not just the one you know about - the branch may have migrations in multiple apps
- After fixing, grep for any remaining references to old migration filenames
