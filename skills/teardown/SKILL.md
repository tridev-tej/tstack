---
name: teardown
description: |
  Reverse-engineer any web app's architecture from the frontend using Chrome DevTools.
  Captures network traffic, JS bundles, API contracts, auth flows, and named internal systems.
  Use when asked to "teardown", "reverse-engineer", "analyze how X works", "decompile",
  or "explore the architecture of" any website or web app.
version: 2.0.0
author: user
allowed-tools:
  - Bash
  - Bash(agent-browser:*)
  - Bash(npx agent-browser:*)
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Agent
  - Skill
---

# Web App Architecture Teardown

Reverse-engineer any web application's architecture by analyzing what the frontend reveals through Chrome DevTools - network requests, JS bundles, API contracts, headers, auth flows.

## What This Skill Does

Opens a target web app, captures all network traffic during load and interaction, then produces a grounded technical teardown covering:
- Named internal systems (leaked through headers, JS filenames, API paths)
- API architecture (REST, GraphQL, gRPC-web, WebSocket)
- Boot sequence (what loads when, in what order)
- Auth mechanisms (cookies, tokens, OAuth flows)
- CDN/infrastructure signals
- Non-obvious implementation details

## Input

`$ARGUMENTS` = URL of the web app to teardown (e.g., `https://netflix.com`, `https://slack.com`)

If no URL provided, ask the user.

## Execution

### Phase 0: Cookie Extraction (Authentication)

Before opening agent-browser, try to extract existing auth cookies from Comet browser using the `comet-cookies` skill. This avoids manual login.

1. Extract the domain from the URL (e.g., `https://app.example.com` -> `example.com`)
2. Run the comet cookie extraction script:

```python
python3 << 'PYEOF'
import subprocess, sqlite3, hashlib, os, json

password = subprocess.run(
    ["security", "find-generic-password", "-s", "Comet Safe Storage", "-w"],
    capture_output=True, text=True
).stdout.strip()

if not password:
    print("NO_COMET_KEY")
    exit(0)

key = hashlib.pbkdf2_hmac('sha1', password.encode(), b'saltysalt', 1003, dklen=16)

from Crypto.Cipher import AES

db_path = os.path.expanduser("~/Library/Application Support/Comet/Default/Cookies")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Replace DOMAIN with the extracted domain
cursor.execute("""
    SELECT name, encrypted_value, host_key, path, is_httponly, is_secure
    FROM cookies WHERE host_key LIKE '%DOMAIN%'
""")

cookies = []
for name, enc, host, path, httponly, secure in cursor.fetchall():
    if enc[:3] == b'v10':
        iv = b' ' * 16
        cipher = AES.new(key, AES.MODE_CBC, iv)
        dec = cipher.decrypt(enc[3:])
        pad = dec[-1]
        if isinstance(pad, int) and 1 <= pad <= 16:
            dec = dec[:-pad]
        raw = dec.decode('utf-8', errors='replace')
        clean = raw
        for i in range(1, min(32, len(raw))):
            run = raw[i:i+8]
            if len(run) >= 8 and all(c.isascii() and c.isprintable() for c in run):
                clean = raw[i:]
                break
    else:
        clean = enc.decode('utf-8', errors='replace')

    cookies.append({"name": name, "value": clean, "host": host, "path": path,
                     "httponly": bool(httponly), "secure": bool(secure)})

conn.close()
print(json.dumps(cookies))
PYEOF
```

3. If cookies were found, open agent-browser and inject them:

```bash
agent-browser --headed open $URL

# For each extracted cookie:
agent-browser cookies set COOKIE_NAME "COOKIE_VALUE" --domain "DOMAIN" --path "/" --secure
# Add --httpOnly for httpOnly cookies

# Reload to activate auth
agent-browser open $URL && agent-browser wait --load networkidle
```

4. If no Comet cookies found (or Keychain denied), fall back to manual login:
   - Tell the user: "No existing session found in Comet. Please log in using the browser window, then tell me when you're ready."
   - Wait for user confirmation

### Phase 1: Initial Capture (Network Traffic)

After authenticated page load, capture all resources via the Performance API (more reliable than `network requests` which misses pre-listener traffic):

```bash
# Get all fetch/XHR requests (API calls)
agent-browser eval 'JSON.stringify(performance.getEntriesByType("resource").filter(function(r){return r.initiatorType==="fetch"||r.initiatorType==="xmlhttprequest"}).map(function(r){return {url:r.name,size:r.transferSize}}))'

# Get all scripts
agent-browser eval 'JSON.stringify([...document.querySelectorAll("script[src]")].map(s=>s.src))'
```

**IMPORTANT:** `agent-browser eval` with backtick-quoted strings causes syntax errors. Always use single-quote JS strings inside eval, or write the JS to a temp file and eval via `"$(cat /tmp/script.js)"`.

### Phase 2: Deep Network Analysis

```bash
# Get all loaded resources grouped by type
cat > /tmp/teardown_resources.js << 'EOF'
var resources = performance.getEntriesByType("resource");
var scripts = resources.filter(function(r) { return r.initiatorType === "script"; });
var fetches = resources.filter(function(r) { return r.initiatorType === "fetch" || r.initiatorType === "xmlhttprequest"; });
JSON.stringify({
  totalResources: resources.length,
  totalScripts: scripts.length,
  totalJsKB: Math.round(scripts.reduce(function(a,b) { return a + b.transferSize; }, 0) / 1024),
  apiCalls: fetches.map(function(r) { return {url: r.name.substring(0, 150), size: r.transferSize}; })
});
EOF
agent-browser eval "$(cat /tmp/teardown_resources.js)"
```

### Phase 3: JavaScript Bundle & Global Analysis

```bash
# Window globals (custom namespaces reveal internal systems)
cat > /tmp/teardown_globals.js << 'EOF'
var keys = Object.keys(window);
var custom = [];
for (var i = 0; i < keys.length; i++) {
  var k = keys[i];
  try {
    if (typeof window[k] === "object" && window[k] !== null) {
      custom.push(k);
    }
  } catch(e) {}
}
JSON.stringify(custom.slice(0, 80));
EOF
agent-browser eval "$(cat /tmp/teardown_globals.js)"

# Meta tags (framework, build info)
agent-browser eval 'JSON.stringify([...document.querySelectorAll("meta")].map(m=>({name:m.name||m.getAttribute("property"),content:m.content})).filter(m=>m.name))'

# Next.js / Nuxt / framework-specific data
agent-browser eval 'typeof __NEXT_DATA__!=="undefined"?JSON.stringify({buildId:__NEXT_DATA__.buildId,page:__NEXT_DATA__.page,propsKeys:Object.keys(__NEXT_DATA__.props.pageProps||{})}):"NO_NEXT"'

# Storage keys
agent-browser eval 'JSON.stringify({localStorage:Object.keys(localStorage),sessionStorage:Object.keys(sessionStorage)})'

# Cookie names (non-HttpOnly visible to JS)
agent-browser eval 'JSON.stringify(document.cookie.split(";").map(c=>c.trim().split("=")[0]))'
```

### Phase 4: GraphQL Schema Discovery (if GraphQL detected)

If API calls hit `/graphql` or similar, probe the schema via error messages:

```bash
# Try introspection first
curl -s -X POST 'https://SITE.com/graphql/' \
  -H 'Content-Type: application/json' \
  -H 'Cookie: EXTRACTED_COOKIES' \
  -H 'Origin: https://SITE.com' \
  -d '{"query":"{ __schema { queryType { name } types { name kind } } }"}'

# If introspection disabled, use typo probing - error messages leak query names
curl -s -X POST 'https://SITE.com/graphql/' \
  -H 'Content-Type: application/json' \
  -H 'Cookie: EXTRACTED_COOKIES' \
  -d '{"query":"query { xxx }"}'
# Response: "Did you mean X, Y, or Z?" -> leaked schema!

# Probe each discovered query to find return types and required args
curl -s -X POST 'https://SITE.com/graphql/' \
  -H 'Content-Type: application/json' \
  -H 'Cookie: EXTRACTED_COOKIES' \
  -d '{"query":"query { discoveredQuery }"}'
# Response: "Field X of type Y must have a sub selection" -> leaked types!
# Response: "resolve_X() missing N required args: 'a' and 'b'" -> leaked signatures!
```

### Phase 5: Interactive Exploration

Navigate to 3-5 key sections of the app to capture more API patterns:

```bash
# Navigate to a new section
agent-browser open https://SITE.com/some-section && agent-browser wait --load networkidle

# Capture fresh API calls via Performance API
agent-browser eval 'JSON.stringify(performance.getEntriesByType("resource").filter(function(r){return (r.initiatorType==="fetch"||r.initiatorType==="xmlhttprequest")&&r.name.indexOf("SITE")!==-1}).map(function(r){return r.name.substring(0,120)}))'

# Check response headers on REST endpoints
curl -sI 'https://SITE.com/api/endpoint/' -H 'Cookie: COOKIES' 2>&1 | head -20
```

### Phase 6: Synthesize Teardown Report

After gathering all data, produce TWO outputs:

#### Output 1: Detailed Markdown (`~/teardowns/{app-name}-teardown.md`)

Full prose teardown with tables for Named Systems, API Architecture, Boot Sequence, Auth, CDN, Frontend Stack, Non-Obvious Details, and Required Backend Services. Every claim must cite evidence (header name, JS filename, API path, cookie name).

#### Output 2: Commented Architecture Diagram (shown to user)

Present the findings as a large commented ASCII diagram. This is the final output the user sees. Structure it as:

```
# ═══════════════════════════════════════════════════════════════
# [APP NAME] - ARCHITECTURE TEARDOWN
# [date] | ~[N] requests | frontend-only analysis
# ═══════════════════════════════════════════════════════════════
#
#
#  [INFRASTRUCTURE LAYER]
#  ┌─────────────────────────────────────────────────────────┐
#  │  CDN / Edge / Bot Protection                            │
#  │  (details with evidence)                                │
#  └────────────────────────┬────────────────────────────────┘
#                           │
#          ┌────────────────┼────────────────┐
#          ▼                ▼                ▼
#  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
#  │ Static Assets│ │ App Server   │ │ API Layer    │
#  │ (CDN domain) │ │ (framework)  │ │ (REST/GQL)   │
#  └──────────────┘ └──────────────┘ └──────┬───────┘
#                                           │
#
#  [API ARCHITECTURE]
#  Show primary and secondary APIs with:
#  - Endpoints / query names
#  - Auth mechanism
#  - Return types (if discovered)
#
#  [BOOT SEQUENCE]
#  Show as timeline:
#  t=0ms   ┌─────────────────┐
#  SSG     │  Phase 1: ...   │
#          └────────┬────────┘
#                   ▼
#  t=Nms   ┌─────────────────┐
#  JS      │  Phase 2: ...   │
#          └────────┬────────┘
#
#  [AUTH FLOW]
#  Show token structure, cookie map
#
#  [CODE EXECUTION / KEY FLOWS]
#  Show as sequence diagrams for the most interesting
#  interaction patterns (e.g., code submission, search, etc.)
#
#  [ANALYTICS PIPELINE]
#  Show all tracking services firing on page view
#
#  [NON-OBVIOUS FINDINGS]
#  Numbered list of the most surprising discoveries
#
# ═══════════════════════════════════════════════════════════════
```

**Diagram rules:**
- Use box-drawing characters: `┌ ┐ └ ┘ │ ─ ┬ ┴ ├ ┤ ┼ ▼ ▲`
- Every line prefixed with `#  ` (comment + 2 spaces)
- Include actual values (IDs, URLs, cookie names) - not placeholders
- Group by architectural concern, not by discovery order
- Annotate each box with evidence source

## Important Notes

- **This is frontend-only analysis.** Be explicit about this in both outputs.
- **Evidence-based.** Every claim must cite where the signal was found.
- **Named systems are gold.** Internal system names leaked through headers, JS filenames, API paths, error messages, or config objects are the highest-value findings.
- **Use temp files for complex JS evals.** Write JS to `/tmp/teardown_*.js` and eval via `"$(cat /tmp/teardown_*.js)"` to avoid quoting issues with agent-browser eval.
- **Performance API over network requests.** Use `performance.getEntriesByType("resource")` instead of `agent-browser network requests` - it captures everything including pre-listener traffic.
- **GraphQL error probing is powerful.** Even with introspection disabled, sending typo queries and malformed queries leaks schema details via error messages.

## Adapt Per App Type

- **SaaS/dashboards** - Focus on API contracts, RBAC signals, multi-tenancy hints
- **Streaming/media** - Focus on CDN, DRM, adaptive bitrate, pre-fetch patterns
- **Social/messaging** - Focus on WebSocket, real-time, notification systems
- **E-commerce** - Focus on search, cart, checkout, payment API integration
- **Developer tools** - Focus on collaboration protocols, sync mechanisms
