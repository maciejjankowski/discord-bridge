#!/bin/bash
# Discord Bridge - SessionStart hook for Claude Code
# Checks for new messages from allowed users at session start
#
# Add to .claude/settings.json:
# {
#   "hooks": {
#     "SessionStart": [{
#       "type": "command",
#       "command": "/path/to/discord-bridge/hooks/discord_check_hook.sh"
#     }]
#   }
# }

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$SCRIPT_DIR/discord_bridge.py" interactions --since 60
