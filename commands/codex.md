# Codex CLI Skill

Run OpenAI Codex CLI (v0.104+) for code analysis, reviews, and agentic coding tasks.

## Default Model: `gpt-5.3-codex`

Config at `~/.codex/config.toml` already sets `gpt-5.3-codex` as default. No need to override unless using a different model.

## Quick Reference

```bash
# Non-interactive exec (uses default gpt-5.3-codex)
codex exec --dangerously-bypass-approvals-and-sandbox "PROMPT"

# Full auto mode (sandboxed writes, auto-approves safe commands)
codex exec --full-auto "PROMPT"

# Code review (last N commits)
codex review --commit HEAD~N..HEAD

# Code review (uncommitted changes)
codex review --uncommitted

# Code review (against base branch)
codex review --base main

# With specific model override
codex exec -m gpt-5.1-codex-max "PROMPT"

# With image input
codex exec -i screenshot.png "What's wrong with this UI?"

# Custom working directory
codex exec -C /path/to/project "PROMPT"

# Read prompt from stdin (useful for long prompts)
echo "analyze this code" | codex exec -

# Resume previous session
codex resume --last

# Fork a previous session
codex fork --last
```

## Available Models

| Model | Use Case |
|-------|----------|
| `gpt-5.3-codex` | **Default.** Most capable coding model. Best for complex analysis, reviews, architecture |
| `gpt-5.3-codex-spark` | Real-time coding, fast responses (research preview) |
| `gpt-5.1-codex-max` | Long-running project-scale work, multi-context-window tasks |
| `gpt-5.1-codex` | Previous gen, still solid |
| `gpt-5-codex` | Original GPT-5 codex variant |
| `gpt-5-codex-mini` | Cost-effective, simple tasks |
| `o3` | Best reasoning (non-codex), complex analysis |
| `o4-mini` | Faster, cheaper reasoning |

## CLI Subcommands

| Command | What it does |
|---------|-------------|
| `exec` / `e` | Non-interactive execution |
| `review` | Code review (returns P1/P2/P3 findings) |
| `login` / `logout` | Manage auth |
| `mcp` | Manage external MCP servers |
| `mcp-server` | Run codex as MCP server (stdio) |
| `app` | Launch desktop app |
| `resume` | Resume previous session |
| `fork` | Fork a previous session |
| `apply` / `a` | Apply latest diff as git apply |
| `cloud` | Browse Codex Cloud tasks (experimental) |
| `sandbox` | Run commands in codex sandbox |
| `debug` | Debugging tools |

## Sandbox Modes (`-s`)

- `read-only` - can only read files (safe for analysis)
- `workspace-write` - can write within project dir
- `danger-full-access` - unrestricted (use with caution)

## Approval Policies (`-a`)

- `untrusted` - only trusted commands (ls, cat, sed) run without approval
- `on-request` - model decides when to ask (recommended with `--full-auto`)
- `never` - never ask (pair with sandbox for safety)

## Convenience Flags

- `--full-auto` = `-a on-request -s workspace-write` (sandboxed auto mode)
- `--dangerously-bypass-approvals-and-sandbox` = no sandbox, no prompts (analysis only)
- `--search` = enable web search tool during session
- `--oss` = use local model provider (LM Studio / Ollama)

## IMPORTANT: Requires Git Repo

Codex CLI must run inside a trusted git directory. Always use `-C /path/to/repo` if not already in one. Trusted repos are configured in `~/.codex/config.toml`:

```toml
[projects."/Users/user/repos/your-repo"]
trust_level = "trusted"
```

## MCP Server Mode

```bash
# Run as MCP server (for Claude Code integration)
codex mcp-server

# Manage MCP servers for codex
codex mcp list
codex mcp add <name> -- <command>
```

## Common Patterns

### Code review with PR
```bash
codex review --commit HEAD~3..HEAD
```

### Architecture review
```bash
codex exec -s read-only "Review the architecture. Focus on: scalability, security, maintainability."
```

### Validate code equivalence
```bash
codex exec --dangerously-bypass-approvals-and-sandbox \
  "Compare PATH_A and PATH_B. Trace edge cases. Verdict: identical or different?"
```

### Long prompt via stdin
```bash
cat prompt.txt | codex exec -
```

## Config

Config file: `~/.codex/config.toml`

```toml
model = "gpt-5.3-codex"
model_reasoning_effort = "high"  # low, medium, high

[projects."/path/to/project"]
trust_level = "trusted"
```

## Tips

- Default model is already `gpt-5.3-codex` in config — no need to override
- Use `--full-auto` for safe autonomous coding (sandboxed writes)
- Use `-s read-only` when you only need analysis
- Codex review returns P1/P2/P3 findings — fix P1s before merging
- Use `codex resume --last` to continue where you left off
- Use `codex apply` to apply the last generated diff to your working tree
