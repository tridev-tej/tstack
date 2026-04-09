# Deploy to Preprod

Deploy branches to the preprod environment by updating deploy-config and raising a PR.

## Overview

Preprod runs in the **staging cluster, preprod namespace**. Deployment requires:
1. Update `values.yaml` in `deploy-config` repo (staging directory)
2. Raise a PR for review
3. Merge to apply changes

## Usage
```
/deploy-preprod <branch> [--component <name>] [--webstatic <branch>]
```

**Examples:**
```
/deploy-preprod user/fix-auth              # Deploy backend branch to preprod
/deploy-preprod main --webstatic main        # Deploy main for both components
```

## Execution Steps

### Step 1: Clone/Update deploy-config

```bash
# Clone if not exists, otherwise pull latest
if [[ -d ~/repos/deploy-config ]]; then
  cd ~/repos/deploy-config && git checkout main && git pull
else
  gh repo clone your-org/deploy-config ~/repos/deploy-config
  cd ~/repos/deploy-config
fi
```

### Step 2: Determine Versions

```bash
SA_BRANCH="${1:-main}"
WEBSTATIC_BRANCH="${WEBSTATIC:-}"

# Get commits
SA_COMMIT=$(gh api repos/your-org/your-repo/commits/$SA_BRANCH --jq '.sha[:7]')

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

echo "Backend: $SA_VERSION"
[[ -n "$WEBSTATIC_BRANCH" ]] && echo "Webstatic: $WEBSTATIC_VERSION"
```

### Step 3: Create Branch and Update values.yaml

```bash
DEPLOY_BRANCH="user/preprod-$(date +%Y%m%d-%H%M)"
git checkout -b $DEPLOY_BRANCH

# File to update
VALUES_FILE="staging/values.yaml"
```

**Update the image tags in values.yaml:**

The file structure typically has sections like:
```yaml
backend:
  image:
    tag: "branch.commit"

webstatic:
  image:
    tag: "branch.commit"
```

Use sed or yq to update:
```bash
# Update backend tag
sed -i '' "s/\(backend:.*tag:\s*\"\)[^\"]*\"/\1$SA_VERSION\"/" $VALUES_FILE

# Update webstatic tag if specified
if [[ -n "$WEBSTATIC_VERSION" ]]; then
  sed -i '' "s/\(webstatic:.*tag:\s*\"\)[^\"]*\"/\1$WEBSTATIC_VERSION\"/" $VALUES_FILE
fi
```

**Alternative with yq (more reliable):**
```bash
yq -i ".backend.image.tag = \"$SA_VERSION\"" $VALUES_FILE
[[ -n "$WEBSTATIC_VERSION" ]] && yq -i ".webstatic.image.tag = \"$WEBSTATIC_VERSION\"" $VALUES_FILE
```

### Step 4: Commit and Push

```bash
git add $VALUES_FILE
git commit -m "preprod: deploy $SA_VERSION"
git push -u origin $DEPLOY_BRANCH
```

### Step 5: Create PR

```bash
PR_BODY="## Preprod Deployment

**Components:**
- backend: \`$SA_VERSION\` (branch: $SA_BRANCH)
$([ -n "$WEBSTATIC_VERSION" ] && echo "- webstatic: \`$WEBSTATIC_VERSION\` (branch: $WEBSTATIC_BRANCH)")

**Environment:** staging cluster / preprod namespace
"

gh pr create --repo your-org/deploy-config \
  --title "preprod: deploy $SA_VERSION" \
  --body "$PR_BODY" \
  --base main
```

### Step 6: Report Result

```
✓ Created preprod deployment PR

  Components:
    Backend: $SA_BRANCH -> $SA_VERSION
    Webstatic: $WEBSTATIC_BRANCH → $WEBSTATIC_VERSION

  PR: <pr-url>

  Next steps:
  1. Get PR reviewed and approved
  2. Merge to deploy
```

## Important Files

| Path | Purpose |
|------|---------|
| `staging/values.yaml` | Preprod component versions |
| `staging/` directory | All preprod k8s configs |

## Adding/Modifying Preprod Resources

To add env vars, secrets, or other resources:

1. Edit files in `staging/` directory
2. Common files:
   - `staging/configmap.yaml` - Environment variables
   - `staging/secrets.yaml` - Secrets (encrypted)
   - `staging/deployment.yaml` - Deployment specs
3. Raise PR with changes

## Reference PR

Sample deployment PR: https://github.com/your-org/deploy-config/pull/491

## Rollback

To rollback, create a new PR reverting to the previous version:
```bash
git revert HEAD
git push
gh pr create --title "preprod: rollback to previous version"
```

## Troubleshooting

### PR merge doesn't trigger deployment
- Check ArgoCD sync status
- Preprod namespace: `kubectl -n preprod get pods`

### Image not found
- Ensure the image was built first (check build workflows)
- Image tag format must match: `branch.commit`

### Changes not reflected
- ArgoCD may take a few minutes to sync
- Force sync: Check ArgoCD UI or use CLI
