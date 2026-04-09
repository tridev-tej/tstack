# Tstack - Claude Code Power User Configuration

My Claude Code setup for software engineering, SOC operations, and product management - 51 skills, 34 commands, 7 custom MCP servers, 14 plugins, custom hooks, and multi-agent orchestration.

> **All PII, API keys, passwords, and server URLs have been stripped.** This is a reference/inspiration repo, not a drop-in config.

---

## Table of Contents

- [MCP Servers](#mcp-servers)
- [Plugins](#plugins)
- [Skills](#skills)
- [Custom Commands](#custom-commands)
- [Hooks](#hooks)
- [Agents & Teams](#agents--teams)
- [Settings Highlights](#settings-highlights)

---

## MCP Servers

Custom Python MCP servers plus third-party servers for external tool access:

| Server | Package / Runtime | Purpose |
|--------|-------------------|---------|
| **brave-search** | `@brave/brave-search-mcp-server` (npx) | Web search via Brave API |
| **puppeteer** | `@modelcontextprotocol/server-puppeteer` (npx) | Headless browser automation |
| **sequential-thinking** | `@modelcontextprotocol/server-sequential-thinking` (npx) | Chain-of-thought reasoning |
| **opensearch** | Custom Python server | Query OpenSearch clusters (logs, errors, traces) |
| **atlassian** | `@anthropic/mcp-server-atlassian` (npx) | Jira ticket management |
| **prometheus** | Custom Python server | Prometheus metrics queries and alerting |
| **notion** | Custom Python server (uv + httpx) | Notion API via cookie auth |
| **soc-investigations** | Custom Python server (uv + psycopg2) | Example SOC investigation queries against a Postgres DB |
| **soc-infrastructure** | Custom Python server (uv + psycopg2) | Example infrastructure health checks (pods, OOMs, disk, queues) |
| **soc-integrations** | Custom Python server (uv + psycopg2) | Example integration health and error monitoring |
| **gmail** | `@gongrzhe/server-gmail-autoauth-mcp` (npx) | Gmail read/send/draft with OAuth |
| **computer-use** | Anthropic Computer Use MCP | Native desktop app automation |
| **chrome-devtools** | Chrome DevTools MCP | Browser DOM interaction |
| **macos-automator** | macOS Automator MCP | AppleScript/JXA execution |
| **exa** | Exa search MCP | AI-native web search |

### MCP Server Architecture

```
mcp-servers/
  opensearch-direct/      # Direct OpenSearch queries (Python)
  opensearch-dashboards/  # OpenSearch dashboards proxy (Python)
  prometheus/             # PromQL queries (Python)
  notion/                 # Notion internal API (Python)
  soc-investigations/     # Alert & investigation queries
  soc-infrastructure/     # Pod health, OOMs, disk IO
  soc-integrations/       # Integration status & errors
  shared/                 # Shared utilities (DB, kubectl, Teams webhook)
```

---

## Plugins

14 installed plugins (12 active):

| Plugin | Marketplace | Status | Purpose |
|--------|-------------|--------|---------|
| **plugin-dev** | claude-code-plugins | Active | Plugin development toolkit (create skills, agents, hooks) |
| **canvas** | claude-canvas | Active | Terminal TUI canvases (calendars, documents, flights) |
| **claude-delegator** | jarrodwatts-claude-delegator | Active | Delegate tasks to Codex/other agents |
| **pm-toolkit** | pm-skills | Active | NDA drafts, resume review, proofreading, privacy policies |
| **pm-product-strategy** | pm-skills | Active | SWOT, PESTLE, Porter's 5 Forces, pricing, business models |
| **pm-product-discovery** | pm-skills | Active | Feature prioritization, experiments, interview scripts |
| **pm-market-research** | pm-skills | Active | Competitor analysis, personas, journey maps, market sizing |
| **pm-data-analytics** | pm-skills | Active | Cohort analysis, A/B testing, SQL generation |
| **pm-marketing-growth** | pm-skills | Active | North Star metrics, positioning, product naming |
| **pm-go-to-market** | pm-skills | Active | GTM strategy, growth loops, battlecards, ICP |
| **pm-execution** | pm-skills | Active | PRDs, OKRs, sprints, user stories, stakeholder maps |
| **ralph-loop** | claude-plugins-official | Disabled | Recurring task loops |
| **ralph-wiggum** | claude-code-plugins | Disabled | Companion blob |
| **frontend-design** | claude-code-plugins | Disabled | Frontend design assistance |

### Custom Marketplace
- **pm-skills** from `phuryn/pm-skills` (GitHub) - Full PM toolkit suite

---

## Skills

### Engineering & DevOps

| Skill | Description |
|-------|-------------|
| `/ship` | Full ship workflow - merge base, tests, review, version bump, changelog, PR |
| `/review` | Pre-landing PR review (SQL safety, LLM trust boundaries, side effects) |
| `/review-pr` | Review PR and leave comments |
| `/review-pr-dual` | Dual-model validation (Codex + Opus) with cross-validated findings |
| `/review-pr-codex` | Review PR with OpenAI Codex |
| `/check-pr` | Check PR for unresolved comments, failing checks |
| `/understand-pr` | Navigate large PRs systematically - file by file |
| `/fix-ci` | Fix CI/CD pipeline issues |
| `/fix-migrations` | Fix Django migration conflicts after merging main |
| `/investigate` | Systematic debugging with root cause investigation (4 phases) |
| `/git-pr-bug-attribution` | Determine whether a bug was introduced by a specific PR |
| `/simplify` | Review changed code for reuse, quality, efficiency |
| `/greploop` | Loop Greptile review until zero comments |
| `/document-release` | Post-ship documentation updates |
| `/land-and-deploy` | Merge PR, wait for CI, verify production health |
| `/deploy-staging` | Deploy to staging environment |
| `/deploy-preprod` | Deploy to preprod environment |
| `/setup-deploy` | Configure deployment platform settings |
| `/prod-verify` | Verify PR code changes against prod data |
| `/codex` | OpenAI Codex CLI - review, challenge, delegate modes |
| `/codex-swarm` | Spawn parallel Codex agents for subtasks |
| `/orchestrate` | Orchestrate multiple Claude/Codex agents in tmux panes |
| `/swarm-review` | 6 parallel agents - Docker, frontend, Codex, Playwright, Opus, live |
| `/retro` | Weekly engineering retrospective with trend tracking |
| `/weekly-report` | Generate weekly report from GitHub activity |

### Browser & QA

| Skill | Description |
|-------|-------------|
| `/browse` | Fast headless browser for QA and site dogfooding |
| `/gstack` | Headless browser CLI (Playwright-based) for testing |
| `/gstack-upgrade` | Upgrade gstack to latest version |
| `/connect-chrome` | Launch real Chrome controlled by gstack with Side Panel |
| `/qa` | Systematically QA test web app and fix bugs found |
| `/qa-only` | Report-only QA testing with health score and screenshots |
| `/design-review` | Designer's eye QA - visual inconsistency, spacing, hierarchy |
| `/canary` | Post-deploy canary monitoring for errors and regressions |
| `/benchmark` | Performance regression detection with browse daemon |
| `/teardown` | Reverse-engineer web app architecture from frontend |
| `/setup-browser-cookies` | Import cookies from real browser into headless session |
| `/agent-browser` | Browser automation via agent-browser CLI |
| `/electron` | Automate Electron desktop apps via CDP |

### Security & SOC

| Skill | Description |
|-------|-------------|
| `/soc` | SOC Agent troubleshooting - investigations, infra, integrations |
| `/status` | Error status report with RCA, stacktraces, affected tenants |
| `/alert-errors` | Check OpenSearch for errors, create Zenduty incidents |
| `/cso` | Chief Security Officer mode - infrastructure-first security audit |
| `/opensearch` | Query OpenSearch logs with flexible filters |
| `/opensearch-traceback-retrieval` | Retrieve full Python stack traces from structured logs |
| `/prometheus` | Query Prometheus metrics, health checks, PromQL |
| `/langfuse` | Langfuse LLM observability insights |
| `/rancher` | Rancher API - clusters, kubeconfig, nodes, workloads |

### Productivity & Communication

| Skill | Description |
|-------|-------------|
| `/notion` | Interact with Notion's internal API |
| `/jira` | Create/manage Jira tickets |
| `/n8n` | Interact with n8n workflows |
| `/tmux` | Manage Claude Code sessions in tmux |
| `/find-chat` | Search Claude Code chat history and open matching session |
| `/deep-research` | Deep research with Graph of Thoughts - parallel exploration |
| `/youtube-to-ebook` | Transform YouTube videos into formatted ebook articles |
| `/learn` | Learning skill |
### Writing & Style

| Skill | Description |
|-------|-------------|
| `/devils-advocate` | Adversarial argument loop - steelman then demolish |
| `/frontend-slides` | Create animation-rich HTML presentations |

### Planning & Review

| Skill | Description |
|-------|-------------|
| `/plan-ceo-review` | CEO/founder-mode plan review - 10-star product thinking |
| `/plan-eng-review` | Eng manager plan review - architecture, data flow, edge cases |
| `/plan-design-review` | Designer's eye plan review - rates each dimension 0-10 |
| `/autoplan` | Auto-review pipeline - runs CEO, design, eng reviews sequentially |
| `/planning-with-files` | Manus-style file-based planning with task_plan.md |
| `/design-consultation` | Full design system proposal (aesthetic, typography, colors) |
| `/product-management` | PM mode for non-developers - bridge design and engineering |
| `/vibe-coding` | Vibe coding best practices for rapid prototyping |

### Infrastructure & Config

| Skill | Description |
|-------|-------------|
| `/install-mcp` | Install and configure MCP servers |
| `/create-command` | Create Claude Code slash commands |
| `/freeze` / `/unfreeze` | Restrict/unrestrict file edits to specific directory |
| `/guard` | Full safety mode - destructive warnings + directory scoping |
| `/careful` | Safety guardrails for destructive commands |
| `/drawio` | Create diagrams, flowcharts, architecture diagrams |
| `/ink` | Ink terminal renderer for JSON specs |
| `/raycast` | Manage Raycast script commands |
| `/inference-profile` | AWS Bedrock inference profile details |
| `/find-skills` | Discover and install agent skills |

### Reference Docs (in skills/)

These are standalone skill files that serve as reference guides, not slash commands:

| File | Description |
|------|-------------|
| `code-review-senior-guidelines.md` | General senior-reviewer patterns for backend code |
| `codex-delegation.md` | How to delegate tasks to OpenAI Codex |
| `engineering-judgment.md` | "Spinach Rule" - when to push back on flawed assumptions |
| `generate-ralph-loop.md` | Auto-generate recurring task loop commands |
| `pr-workflow.md` | PR creation, review, and commit workflow template |
| `ui-testing.md` | UI testing reference (always use incognito mode) |

---

## Custom Commands

34 slash commands in `commands/`:

YAML-frontmatter markdown files that define prompts, tool permissions, and behaviors for specific workflows. Categories include PR review, deployment, research, monitoring, and productivity.

---

## Hooks

Lifecycle hooks with shell automation:

| Event | Hooks | Purpose |
|-------|-------|---------|
| **SessionStart** | peon-ping, iterm2-claude | Sound notification, iTerm2 integration |
| **Stop** | peon-ping, iterm2-claude | Completion notification |
| **Notification** | peon-ping, iterm2-claude | Alert notification |
| **UserPromptSubmit** | hook-handle-use, iterm2-claude | Usage tracking |

### Included in repo

- **iterm2-claude.sh** - iTerm2 tab color/badge integration based on session state
- **peon-ping/scripts/hook-handle-use.sh** - Sound pack switcher hook

Note: The main `peon.sh` script and sound files are not included (they reference local audio assets).

---

## Agents & Teams

### Built-in Agent Types
- **general-purpose** - Complex multi-step tasks
- **Explore** - Fast codebase exploration (quick/medium/very thorough)
- **Plan** - Software architect for implementation planning
- **claude-code-guide** - Claude Code / API documentation questions

### Plugin Agents
- **plugin-dev:skill-reviewer** - Review skill quality
- **plugin-dev:plugin-validator** - Validate plugin structure
- **plugin-dev:agent-creator** - Create new agents

### Multi-Agent Orchestration
- `/orchestrate` - Run multiple Claude/Codex agents in tmux panes
- `/codex-swarm` - Break tasks into subtasks across parallel Codex agents
- `/swarm-review` - 6 parallel review agents simultaneously
- Agent teams via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`

---

## Settings Highlights

### Permission Model
```json
{
  "defaultMode": "auto",
  "allow": [
    "Bash(xargs cat:*)",
    "Bash(git pull:*)",
    "Bash(git show:*)"
  ]
}
```

### Spinner Customization
Custom Sanskrit mantra spinner verbs (108 mantras) replace default loading messages.

### Status Line
Custom bash script for status bar integration with iTerm2.

### Memory System
File-based persistent memory at `~/.claude/projects/<project>/memory/` with types:
- **user** - Role, goals, preferences
- **feedback** - Corrections and confirmed approaches
- **project** - Ongoing work context
- **reference** - Pointers to external systems

---

## Directory Structure

```
tstack/
  README.md                # This file
  mcp.json.example         # MCP server config template
  settings.json.example    # Claude Code settings template
  skills/                  # 45 skill directories + 6 reference docs
    ship/SKILL.md
    review/SKILL.md
    investigate/SKILL.md
    ...
    code-review-senior-guidelines.md
    engineering-judgment.md
    pr-workflow.md
    ...
  commands/                # 34 slash command definitions
    deploy-staging.md
    review-pr.md
    soc.md
    ...
  hooks/                   # Lifecycle shell scripts
    iterm2-claude.sh
    peon-ping/scripts/hook-handle-use.sh
  mcp-servers/             # 7 custom MCP server implementations
    shared/                # DB, kubectl, Teams webhook utilities
    opensearch-direct/     # OpenSearch query server
    opensearch-dashboards/ # OpenSearch dashboards proxy
    prometheus/            # PromQL server
    notion/                # Notion API server
    soc-investigations/    # Example investigation queries
    soc-infrastructure/    # Example pod health, OOMs, disk IO
    soc-integrations/      # Example integration health monitoring
```

---

## How to Use This as Inspiration

1. **Start with MCP servers** - They give Claude real-world access. Start with `sequential-thinking` and `puppeteer`, add domain-specific ones as needed.
2. **Build skills incrementally** - Each skill is just a markdown file with a prompt. Start with your most repeated workflows.
3. **Hooks are underrated** - `UserPromptSubmit` hooks let you inject behavior on every prompt. Use them for auto-logging or safety checks.
4. **Plugins extend the system** - The PM skills suite alone adds 80+ product management capabilities.
5. **Memory persists context** - Use it for user preferences and project context that shouldn't be re-discovered each session.

---

## License

MIT
