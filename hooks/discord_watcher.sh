#!/bin/bash
# Discord Bridge - Background watcher
# Run in a separate iTerm2 tab to see new messages in real-time
#
# Usage: ./hooks/discord_watcher.sh
# Or:    ./hooks/discord_watcher.sh 15   (check every 15 seconds)

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INTERVAL="${1:-30}"

python3 "$SCRIPT_DIR/discord_bridge.py" watch "$INTERVAL"
