#!/bin/bash
# Discord Bridge - PostToolUse hook for Claude Code
# Checks for new messages every ~15 tool calls
#
# Add to .claude/settings.json:
# {
#   "hooks": {
#     "PostToolUse": [{
#       "type": "command",
#       "command": "/path/to/discord-bridge/hooks/discord_poll_hook.sh"
#     }]
#   }
# }

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COUNTER_FILE="$SCRIPT_DIR/.state/tool_counter"

# Increment counter
count=0
if [ -f "$COUNTER_FILE" ]; then
    count=$(cat "$COUNTER_FILE")
fi
count=$((count + 1))
echo "$count" > "$COUNTER_FILE"

# Check every 15 tool calls
if [ $((count % 15)) -eq 0 ]; then
    result=$(python3 "$SCRIPT_DIR/discord_bridge.py" interactions --since 30 --json 2>/dev/null)
    if [ -n "$result" ] && [ "$result" != "[]" ]; then
        echo "New Discord messages found - run: python3 $SCRIPT_DIR/discord_bridge.py read --since 30"
    fi
fi
