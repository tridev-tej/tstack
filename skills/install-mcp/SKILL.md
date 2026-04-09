---
name: install-mcp
description: |
  Install, configure, and verify MCP servers for Claude Code. Handles package installation,
  config file updates, stdio handshake testing, and restart guidance.
  Use when asked to install an MCP server, add an MCP integration, or fix MCP setup issues.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - WebSearch
  - mcp__exa__web_search_exa
---

## Install MCP Server Skill

Install any MCP server into Claude Code - from search to working tools in one shot.

## Config Locations

- **MCP servers**: `~/.mcp.json` (home dir, NOT `~/.claude/.mcp.json`)
- **Enabled servers**: `~/.claude/settings.json` -> `enabledMcpjsonServers` array

Both files must be updated for a server to appear in `/mcp`.

## Installation Flow

### Phase 1: Research

1. Search for the MCP server (npm, pip, GitHub)
2. Find the correct package name, install command, and required args
3. Determine transport type (most use stdio)
4. Identify if subcommand needed (e.g., `server --transport stdio`)
5. Check for required env vars (API keys, auth tokens)

### Phase 2: Install Package

Common install methods:
```bash
# npm (runs via npx, no install needed)
# just add to config with: "command": "npx", "args": ["-y", "package-name"]

# pip/uv
uv tool install <package-name>
# or
pip install <package-name>

# go
go install <package>@latest
```

### Phase 3: Verify Binary

After installation, verify the binary exists and is executable:

```bash
# Check binary resolves
which <binary-name>

# Check help/version works
<binary-name> --help
# or
<binary-name> --version
```

If `which` fails, use the full path from the installer output (e.g., `~/.local/bin/`).

### Phase 4: Test MCP Handshake

This is the critical step - test that the server speaks MCP protocol over stdio:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | timeout 15 /full/path/to/binary [args] 2>/dev/null
```

**What to look for:**
- Valid JSON response with `"result"` containing `"protocolVersion"` and `"capabilities"` = SUCCESS
- Hangs/timeout = server might need subcommand (try `server` or `start`)
- Error output = check stderr separately: `2>&1 | head -20`
- Exit code 127 = binary not in PATH, use full path

If the binary prints banner/logs to stderr but responds on stdout, that's fine - Claude Code handles it.

### Phase 5: Configure

1. Read `~/.mcp.json`
2. Add server entry inside `mcpServers` object:

```json
{
  "mcpServers": {
    "existing-server": { ... },
    "new-server": {
      "command": "/full/path/to/binary",
      "args": ["server", "--transport", "stdio"],
      "env": {
        "API_KEY": "value"
      }
    }
  }
}
```

**Rules:**
- Always use full binary path (Claude Code's shell may not have user PATH)
- Only add `env` if the server needs it
- Only add `args` entries that are actually needed
- Server name should be short, lowercase, hyphenated

3. Read `~/.claude/settings.json`
4. Add server name to `enabledMcpjsonServers` array

### Phase 6: Verify Configuration

```bash
# Validate JSON syntax
python3 -c "import json; json.load(open('$HOME/.mcp.json'))" && echo "OK"
python3 -c "import json; json.load(open('$HOME/.claude/settings.json'))" && echo "OK"

# Confirm server is in both files
python3 -c "
import json
mcp = json.load(open('$HOME/.mcp.json'))
settings = json.load(open('$HOME/.claude/settings.json'))
name = 'SERVER_NAME'
in_mcp = name in mcp.get('mcpServers', {})
in_settings = name in settings.get('enabledMcpjsonServers', [])
print(f'In .mcp.json: {in_mcp}')
print(f'In settings.json: {in_settings}')
if in_mcp and in_settings:
    print('Ready - restart Claude Code')
else:
    print('MISSING from: ' + ('mcp.json ' if not in_mcp else '') + ('settings.json' if not in_settings else ''))
"
```

### Phase 7: Report

Only after ALL verification passes, tell the user:
```
MCP server "X" installed and configured.
Restart Claude Code, then check /mcp to confirm.
```

If auth is needed (API key, OAuth), mention that too.

## Common Gotchas

| Issue | Fix |
|-------|-----|
| Server not in `/mcp` list | Wrong config file - must be `~/.mcp.json`, not `~/.claude/.mcp.json` |
| Binary not found at runtime | Use full absolute path, not just command name |
| Server hangs on stdio test | Needs subcommand like `server` or `start` |
| `enabledMcpjsonServers` missing server | Must be in BOTH `.mcp.json` and `settings.json` |
| npx servers | Don't need install - just use `"command": "npx", "args": ["-y", "pkg"]` |
| Server needs auth first | Run auth command before adding to config (e.g., `notebooklm-mcp init`) |

## Uninstall

To remove an MCP server:
1. Remove from `~/.mcp.json` -> `mcpServers`
2. Remove from `~/.claude/settings.json` -> `enabledMcpjsonServers`
3. Optionally uninstall package: `uv tool uninstall <pkg>` or `npm uninstall -g <pkg>`
