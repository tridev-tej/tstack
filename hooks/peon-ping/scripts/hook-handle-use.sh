#!/bin/bash
# UserPromptSubmit hook for /peon-ping-use command
# Intercepts `/peon-ping-use <pack>` before it reaches the LLM
set -euo pipefail

INPUT=$(cat)
LOG_FILE="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks/peon-ping/hook-handle-use.log"
LOG_FALLBACK="${TMPDIR:-/tmp}/peon-ping-hook.log"
log() {
  local line="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  echo "$line" >> "$LOG_FILE" 2>/dev/null || echo "$line" >> "$LOG_FALLBACK" 2>/dev/null || true
}

log "invoked stdin_len=${#INPUT}"

SESSION_ID=$(echo "$INPUT" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
    session = data.get("conversation_id") or data.get("session_id") or "default"
    print(session)
except:
    print("default")
' 2>/dev/null || echo "default")

PROMPT=$(echo "$INPUT" | python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get("prompt", ""))
except:
    pass
' 2>/dev/null || echo "")

if ! echo "$PROMPT" | grep -qE '^\s*/peon-ping-use\s+\S+'; then
  log "passthrough: not_our_cmd prompt_preview=${PROMPT:0:80}..."
  echo '{"continue": true}'
  exit 0
fi

PACK_NAME=$(echo "$PROMPT" | sed -E 's/^[[:space:]]*\/peon-ping-use[[:space:]]+([^[:space:]]+).*/\1/')
log "matched pack=$PACK_NAME sessionId=$SESSION_ID"

if ! echo "$PACK_NAME" | grep -qE '^[a-zA-Z0-9_-]+$'; then
  log "reject: invalid pack name charset pack=$PACK_NAME"
  echo '{"continue": false, "user_message": "[X] Invalid pack name (use only letters, numbers, underscores, hyphens)"}'
  exit 0
fi
if ! echo "$SESSION_ID" | grep -qE '^[a-zA-Z0-9_-]+$'; then
  log "sanitize: invalid session_id charset, using default"
  SESSION_ID="default"
fi

PEON_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/hooks/peon-ping"
if [ ! -d "$PEON_DIR" ]; then
  PEON_DIR="$HOME/.cursor/hooks/peon-ping"
fi

if [ ! -d "$PEON_DIR" ]; then
  log "error: peon-ping not installed"
  echo "{\"continue\": false, \"user_message\": \"[X] peon-ping not installed\"}"
  exit 0
fi

CONFIG="$PEON_DIR/config.json"
STATE="$PEON_DIR/.state.json"
PACKS_DIR="$PEON_DIR/packs"

if [ ! -d "$PACKS_DIR/$PACK_NAME" ]; then
  log "error: pack not found pack=$PACK_NAME"
  AVAILABLE=$(ls -1 "$PACKS_DIR" 2>/dev/null | tr '\n' ', ' | sed 's/,$//')
  if [ -z "$AVAILABLE" ]; then
    echo "{\"continue\": false, \"user_message\": \"[X] No packs installed\"}"
  else
    echo "{\"continue\": false, \"user_message\": \"[X] Pack '$PACK_NAME' not found\\n\\nAvailable packs: $AVAILABLE\"}"
  fi
  exit 0
fi

python3 -c "
import json, sys

config_path = '$CONFIG'
pack_name = '$PACK_NAME'

try:
    with open(config_path) as f:
        config = json.load(f)
except:
    config = {}

config['pack_rotation_mode'] = 'agentskill'

pack_rotation = config.get('pack_rotation', [])
if pack_name not in pack_rotation:
    pack_rotation.append(pack_name)
config['pack_rotation'] = pack_rotation

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')
"

python3 -c "
import json, sys, time

state_path = '$STATE'
session_id = '$SESSION_ID'
pack_name = '$PACK_NAME'

try:
    with open(state_path) as f:
        state = json.load(f)
except:
    state = {}

if 'session_packs' not in state:
    state['session_packs'] = {}

state['session_packs'][session_id] = {
    'pack': pack_name,
    'last_used': time.time()
}

with open(state_path, 'w') as f:
    json.dump(state, f, indent=2)
    f.write('\n')
"

log "success pack=$PACK_NAME sessionId=$SESSION_ID"
echo "{\"continue\": false, \"user_message\": \"Voice set to $PACK_NAME\"}"
exit 0
