#!/bin/bash
# iTerm2 integration for Claude Code: tab colors + badge
# Reads hook event JSON from stdin
set -uo pipefail

INPUT=$(cat)
EVENT=$(echo "$INPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('hook_event_name',''))" 2>/dev/null)
NTYPE=$(echo "$INPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('notification_type',''))" 2>/dev/null)
CWD=$(echo "$INPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('cwd',''))" 2>/dev/null)

set_tab_color() {
  printf "\033]6;1;bg;red;brightness;%s\a" "$1" > /dev/tty 2>/dev/null
  printf "\033]6;1;bg;green;brightness;%s\a" "$2" > /dev/tty 2>/dev/null
  printf "\033]6;1;bg;blue;brightness;%s\a" "$3" > /dev/tty 2>/dev/null
}

reset_tab_color() {
  printf "\033]6;1;bg;*;default\a" > /dev/tty 2>/dev/null
}

set_badge() {
  printf "\e]1337;SetBadgeFormat=%s\a" "$(echo -n "$1" | base64)" > /dev/tty 2>/dev/null
}

case "$EVENT" in
  SessionStart)
    # Blue tab = session active
    set_tab_color 40 80 200
    # Badge = project folder name
    if [ -n "$CWD" ]; then
      PROJECT=$(basename "$CWD")
      set_badge "$PROJECT"
    fi
    ;;
  Stop)
    # Green tab = done, needs input
    set_tab_color 40 180 80
    ;;
  Notification)
    case "$NTYPE" in
      permission_prompt)
        # Orange tab = needs permission
        set_tab_color 230 140 30
        ;;
      idle_prompt)
        # Green tab = ready for input
        set_tab_color 40 180 80
        ;;
    esac
    ;;
  UserPromptSubmit)
    # Blue tab = working
    set_tab_color 40 80 200
    ;;
esac
