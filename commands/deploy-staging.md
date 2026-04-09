# Deploy to Staging

Build and deploy branches to the staging environment using GitHub Actions.

## Usage
```
/deploy-staging [branch-name] [--component <name>] [--webstatic <branch>]
```

**Examples:**
```
/deploy-staging                           # Deploy main for backend
/deploy-staging user/fix-bug            # Deploy feature branch
/deploy-staging user/fix-bug --webstatic main   # Deploy backend + webstatic
```

## Components

| Component | Description | Default |
|-----------|-------------|---------|
| `backend` | Main backend service | Always deployed |
| `webstatic` | Frontend static assets | Optional |

## Execution Steps

### Step 1: Parse Arguments and Determine Versions

```bash
SA_BRANCH="${1:-main}"
WEBSTATIC_BRANCH="${WEBSTATIC:-}"  # Optional, from --webstatic flag

# Get commits
SA_COMMIT=$(gh api repos/your-org/your-repo/commits/$SA_BRANCH --jq '.sha[:7]')

# Version format: branch-suffix.commit
# main -> main.abc1234
# user/fix-bug -> fix-bug.abc1234
get_version() {
  local branch=$1
  local commit=$2
  if [[ "$branch" == "main" ]]; then
    echo "main.$commit"
  else
    echo "${branch##*/}.$commit"
  fi
}

SA_VERSION=$(get_version "$SA_BRANCH" "$SA_COMMIT")

if [[ -n "$WEBSTATIC_BRANCH" ]]; then
  WEBSTATIC_COMMIT=$(gh api repos/your-org/your-repo/commits/$WEBSTATIC_BRANCH --jq '.sha[:7]')
  WEBSTATIC_VERSION=$(get_version "$WEBSTATIC_BRANCH" "$WEBSTATIC_COMMIT")
fi

echo "Backend: $SA_BRANCH -> $SA_VERSION"
[[ -n "$WEBSTATIC_BRANCH" ]] && echo "Webstatic: $WEBSTATIC_BRANCH -> $WEBSTATIC_VERSION"
```

### Step 2: Check for Existing Builds

```bash
# Check build
gh run list --repo your-org/your-repo --workflow "<YOUR_BUILD_WORKFLOW>" --branch $SA_BRANCH --limit 1 --json conclusion,status,headSha,databaseId
```

**Decision logic:**
- `conclusion: success` AND `headSha` matches commit -> Skip build
- `status: in_progress/queued` -> Wait for completion
- Otherwise -> Trigger new build

### Step 3: Build Components (if needed)

```bash
# IMPORTANT: --ref must be the branch you want to build
gh workflow run "<YOUR_BUILD_WORKFLOW>" --repo your-org/your-repo --ref $SA_BRANCH
sleep 10
SA_RUN_ID=$(gh run list --repo your-org/your-repo --workflow "<YOUR_BUILD_WORKFLOW>" --branch $SA_BRANCH --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch $SA_RUN_ID --repo your-org/your-repo --exit-status
```

### Step 4: Deploy to Staging

The deploy workflow accepts versions for each component. Use `"branch.commit"` (the default) to skip a component.

**CRITICAL:** The deploy workflow MUST be triggered from the **same branch** being deployed (use `--ref $SA_BRANCH`), NOT from main.

```bash
gh workflow run "<YOUR_DEPLOY_WORKFLOW>" --repo your-org/your-repo --ref $SA_BRANCH \
  -f backend-version="$SA_VERSION" \
  -f webstatic-version="$SA_VERSION"
```

Wait and watch:
```bash
sleep 3
DEPLOY_RUN_ID=$(gh run list --repo your-org/your-repo --workflow "<YOUR_DEPLOY_WORKFLOW>" --limit 1 --json databaseId --jq '.[0].databaseId')
gh run watch $DEPLOY_RUN_ID --repo your-org/your-repo --exit-status
```

### Step 5: Verify Deployment via Ping

After the deploy workflow succeeds, **always** verify the actual running version via `/ping`:

```bash
kubectl config use-context staging
kubectl rollout status deploy/<YOUR_BACKEND_DEPLOYMENT> -n <YOUR_NAMESPACE> --timeout=120s

# Verify via ping - the build field must match $SA_VERSION
# Use WebFetch to hit: https://<YOUR_STAGING_DOMAIN>/ping
# Expected: {"status": "ok", "build": "$SA_VERSION"}
```

**IMPORTANT:** Do NOT report success until the `/ping` endpoint returns the expected version. The deploy workflow succeeding does NOT guarantee the pods have actually updated.

### Step 6: Report Result

```
Deployed to staging (verified via /ping):
  Backend: $SA_BRANCH ($SA_COMMIT) -> $SA_VERSION
  Webstatic: $WEBSTATIC_BRANCH ($WEBSTATIC_COMMIT) -> $WEBSTATIC_VERSION  # if deployed

  Deploy run: https://github.com/your-org/your-repo/actions/runs/$DEPLOY_RUN_ID
```

## Version Format Reference

| Branch | Commit | Version Tag |
|--------|--------|-------------|
| `main` | `abc1234` | `main.abc1234` |
| `user/fix-bug` | `abc1234` | `fix-bug.abc1234` |
| `feature/auth` | `abc1234` | `auth.abc1234` |

## Error Handling

### "Image not found" during deploy
Build hasn't completed or failed:
```bash
gh run list --repo your-org/your-repo --workflow "<YOUR_BUILD_WORKFLOW>" --branch $BRANCH --limit 3
```

### Build fails
```bash
gh run view $RUN_ID --repo your-org/your-repo --log-failed
```

### Deploy fails
```bash
gh run view $DEPLOY_RUN_ID --repo your-org/your-repo --log-failed
```
