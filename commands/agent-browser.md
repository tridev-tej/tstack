---
description: Browser automation via agent-browser CLI — open, snapshot, interact, extract
---

# agent-browser Skill

Headless browser automation for AI agents. Uses Playwright under the hood with a CLI designed for the snapshot→ref workflow.

## Quick Reference

| Command | What it does |
|---------|-------------|
| `agent-browser open <url>` | Navigate to URL |
| `agent-browser snapshot -i` | Get interactive elements with @refs |
| `agent-browser snapshot -i -C` | Include cursor-interactive elements too |
| `agent-browser click @e2` | Click element by ref |
| `agent-browser fill @e3 "text"` | Clear field and type |
| `agent-browser type @e3 "text"` | Append text (no clear) |
| `agent-browser press Enter` | Press key |
| `agent-browser get text @e1` | Extract text from element |
| `agent-browser get html @e1` | Get element HTML |
| `agent-browser screenshot` | Screenshot current viewport |
| `agent-browser screenshot --full` | Full page screenshot |
| `agent-browser screenshot --annotate` | Labeled screenshot for vision models |
| `agent-browser pdf out.pdf` | Save page as PDF |
| `agent-browser eval "document.title"` | Run JavaScript |
| `agent-browser wait --load networkidle` | Wait for page to finish loading |
| `agent-browser close` | Close browser |

## Core Workflow

Always follow: **open → wait → snapshot → interact → extract**

```bash
# 1. Open page and wait for it to load
agent-browser open https://news.ycombinator.com && agent-browser wait --load networkidle

# 2. Snapshot to get @refs for interactive elements
agent-browser snapshot -i

# 3. Use @refs from snapshot output to interact
agent-browser click @e5
agent-browser fill @e3 "search query"

# 4. Extract data
agent-browser get text @e1
agent-browser eval "document.querySelectorAll('.title a').forEach(a => console.log(a.textContent))"
```

**Key rule:** Never guess selectors. Always `snapshot -i` first to get @refs, then use those refs. Refs change on every snapshot — always re-snapshot after navigation or DOM changes.

## Selectors

Three ways to target elements (in order of preference):

1. **@ref** — from snapshot output. Fastest, most reliable: `agent-browser click @e2`
2. **CSS selector** — standard CSS: `agent-browser click "#submit-btn"`
3. **find command** — semantic locators:

```bash
agent-browser find role button click --name "Submit"
agent-browser find text "Sign In" click
agent-browser find label "Email" fill "user@example.com"
agent-browser find placeholder "Search..." type "query"
agent-browser find testid "login-form" click
```

## Data Extraction

```bash
# Text content
agent-browser get text @e1
agent-browser get text ".article-body"

# HTML
agent-browser get html @e1

# Attribute
agent-browser get attr href @e1

# Page info
agent-browser get title
agent-browser get url

# Element count
agent-browser get count ".list-item"

# JavaScript extraction (most flexible)
agent-browser eval "JSON.stringify([...document.querySelectorAll('.item')].map(e => e.textContent))"

# Screenshots
agent-browser screenshot                    # viewport
agent-browser screenshot --full             # full page
agent-browser screenshot --annotate         # numbered labels + legend
agent-browser screenshot page.png           # save to file

# PDF
agent-browser pdf output.pdf
```

## Session & Auth

```bash
# Persistent profile (cookies/storage survive across runs)
agent-browser --profile ~/.browser-profiles/myapp open https://app.com

# Named sessions (auto-save/restore state)
agent-browser --session-name myapp open https://app.com

# Set HTTP auth credentials
agent-browser set credentials admin secretpass

# Manual cookie management
agent-browser cookies set '{"name":"token","value":"abc123","domain":".example.com"}'
agent-browser cookies get
agent-browser cookies clear

# Local/session storage
agent-browser storage local get authToken
agent-browser storage local set key value
```

## Network & Advanced

```bash
# Intercept and mock API responses
agent-browser network route "*/api/users" --body '{"users":[]}'
agent-browser network route "*/ads/*" --abort
agent-browser network unroute

# View network requests
agent-browser network requests
agent-browser network requests --filter "api"

# Tab management
agent-browser tab new https://example.com
agent-browser tab list
agent-browser tab 2          # switch to tab
agent-browser tab close

# Browser settings
agent-browser set viewport 1920 1080
agent-browser set device "iPhone 15 Pro"
agent-browser set media dark
agent-browser set offline on

# Scroll
agent-browser scroll down 500
agent-browser scrollintoview @e10

# Debug
agent-browser console          # view console logs
agent-browser errors           # view page errors
agent-browser --headed open https://example.com   # visible browser window
```

## Common Patterns

### Scrape a page
```bash
agent-browser open https://example.com && agent-browser wait --load networkidle
agent-browser eval "JSON.stringify([...document.querySelectorAll('h2')].map(h => h.textContent))"
```

### Fill and submit a form
```bash
agent-browser open https://example.com/login && agent-browser wait --load networkidle
agent-browser snapshot -i
# use @refs from snapshot:
agent-browser fill @e1 "user@example.com" && agent-browser fill @e2 "password123" && agent-browser click @e3
```

### Login flow with persistent session
```bash
agent-browser --session-name myapp open https://app.com/login
agent-browser snapshot -i
agent-browser fill @e1 "user@test.com" && agent-browser fill @e2 "pass" && agent-browser click @e3
agent-browser wait --load networkidle
# next time: agent-browser --session-name myapp open https://app.com  (already logged in)
```

### Annotated screenshot for visual review
```bash
agent-browser open https://example.com && agent-browser wait --load networkidle
agent-browser screenshot --annotate --full
```

### Compare page states
```bash
agent-browser open https://example.com && agent-browser snapshot -i   # baseline
# ... do some interaction ...
agent-browser diff snapshot   # see what changed
```

## Limitations & Fallbacks

| Problem | Symptom | Fallback |
|---------|---------|----------|
| **CAPTCHAs** | Google/DDG/Cloudflare block with challenge | Use `mcp__exa__web_search_exa` or `WebSearch` for search queries |
| **Bot detection** | Page loads but content blocked | Use `mcp__hyperbrowser__scrape_webpage` (has stealth/proxy options) |
| **JS-heavy SPAs** | Snapshot shows nothing useful | `wait --load networkidle` first, or `eval` to query DOM directly |
| **Auth walls** | Redirected to login | Use `--profile` or `--session-name` to persist auth |
| **Rate limiting** | 429 errors | Slow down, add `agent-browser wait 2000` between requests |

**When to use agent-browser vs alternatives:**
- **agent-browser** — interactive workflows, form filling, multi-step navigation, screenshots, anything needing real browser
- **Exa/WebSearch** — search queries (avoid Google CAPTCHAs entirely)
- **WebFetch** — simple page content extraction, no interaction needed
- **Hyperbrowser MCP** — when you need stealth mode, proxies, or CAPTCHA solving

## Tips

- `--headed` shows the browser window — great for debugging
- Chain commands with `&&` — browser persists via daemon between calls
- Always `wait --load networkidle` after `open` for dynamic pages
- `snapshot -i` is your best friend — never interact blind
- `snapshot -i -C` catches clickable divs that `-i` alone misses
- `--annotate` screenshots are ideal when you need to show the user what you see
- Use `eval` for bulk extraction — it's faster than multiple `get text` calls
- `diff snapshot` after interactions to verify changes took effect
