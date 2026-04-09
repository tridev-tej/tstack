# Fix CI/CD Pipeline

Make the GitHub CI/CD pipeline green by identifying and fixing failures iteratively.

## Workflow

### Step 1: Check Current CI Status

```bash
gh run list --branch $(git branch --show-current) --limit 5
```

If all green → done. If failed/in_progress → continue.

### Step 2: Get Failed Run Details

```bash
gh run view <RUN_ID> --log-failed
```

### Step 3: Identify Failure Type and Fix

#### Migration Conflicts
**Signal:** `Conflicting migrations detected` or `multiple leaf nodes`

**Fix:**
```bash
docker compose exec -T web python manage.py makemigrations --merge
```
Then commit the merge migration.

#### Missing Migrations
**Signal:** `Your models have changes that are not yet reflected` or `makemigrations --check` failed

**Fix:**
```bash
docker compose exec -T web python manage.py makemigrations
```
Then commit the new migration files.

#### Pyright Type Errors
**Signal:** `error: ...` with file:line references from pyright

**Fixes (in order of preference):**
1. Add proper type annotations to fix the actual issue
2. Use `[]` access instead of `.get()` for validated fields
3. For test files: add pyright disable comments at top of file:
   ```python
   # pyright: reportOptionalSubscript=false
   # pyright: reportArgumentType=false
   # pyright: reportAttributeAccessIssue=false
   ```

#### Checkstyle Failures (isort/black/ruff)
**Signal:** `isort`, `black`, or `ruff` errors

**Fix:**
```bash
make format
make ruff
```
Then commit the formatted files.

#### Hardcoded URL Check
**Signal:** `Hardcoded URL found` or URL pattern check failed

**Fix:** Add `# example:` comment on the line with the URL if it's intentional (docs, tests).

#### Test Failures
**Signal:** `FAILED tests/...` or `pytest` errors

**Fix:** Read the failing test, understand the assertion, fix the code or test.

### Step 4: Commit and Push

```bash
git add -A
git commit -m "fix: <brief description of fix>"
git push
```

### Step 5: Monitor New Run

```bash
gh run list --branch $(git branch --show-current) --limit 1
gh run watch <NEW_RUN_ID> --exit-status
```

### Step 6: Repeat Until Green

If still failing → go back to Step 2.

## Common Patterns

| Error Pattern | Likely Fix |
|---------------|------------|
| `Conflicting migrations` | `makemigrations --merge` |
| `models have changes` | `makemigrations` |
| `pyright` errors in views | Type annotations |
| `pyright` errors in tests | Disable comments |
| `isort` / `black` | `make format` |
| `ruff` errors | `make ruff` or manual fix |
| `Hardcoded URL` | `# example:` comment |

## Important Rules

1. **Do not push nonsense** - understand each fix before committing
2. **Keep commits atomic** - one fix per commit when possible
3. **Monitor until green** - don't stop at first push
4. **Read error logs carefully** - the fix is usually obvious from the error

## Example Session

```
1. gh run list → found failed run 21374462370
2. gh run view 21374462370 --log-failed → pyright errors
3. Fixed type annotations in views.py
4. git commit -m "fix: resolve pyright type errors"
5. git push
6. gh run watch <new_run_id> → still failing (migrations)
7. docker compose exec -T web python manage.py makemigrations
8. git commit -m "fix: add missing migrations"
9. git push
10. gh run watch <new_run_id> → ALL GREEN ✓
```
