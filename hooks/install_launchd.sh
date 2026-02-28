#!/bin/bash
# Install macOS launchd agent that checks Discord every 30 seconds
# New messages are saved to ~/.discord_bridge_latest.txt
# Claude Code can read this file at session start
#
# Usage: ./hooks/install_launchd.sh
# Uninstall: launchctl unload ~/Library/LaunchAgents/com.discord-bridge.checker.plist

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_PATH="$HOME/Library/LaunchAgents/com.discord-bridge.checker.plist"
OUTPUT_FILE="$HOME/.discord_bridge_latest.txt"
CHECKER_SCRIPT="$SCRIPT_DIR/hooks/discord_bg_check.sh"

# Create the background checker script
cat > "$CHECKER_SCRIPT" << 'BGEOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_FILE="$HOME/.discord_bridge_latest.txt"

result=$(python3 "$SCRIPT_DIR/discord_bridge.py" interactions --since 5 --json 2>/dev/null)

if [ -n "$result" ] && [ "$result" != "[]" ] && [ "$result" != "No pending interactions from allowed users." ]; then
    echo "$result" > "$OUTPUT_FILE"
    # macOS notification
    osascript -e "display notification \"New Discord message\" with title \"Discord Bridge\"" 2>/dev/null
fi
BGEOF
chmod +x "$CHECKER_SCRIPT"

# Create launchd plist
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.discord-bridge.checker</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$CHECKER_SCRIPT</string>
    </array>
    <key>StartInterval</key>
    <integer>30</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/discord_bridge.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/discord_bridge.log</string>
</dict>
</plist>
EOF

launchctl load "$PLIST_PATH"
echo "Installed! Discord Bridge checks every 30s."
echo "New messages -> $OUTPUT_FILE + macOS notification"
echo "Logs: /tmp/discord_bridge.log"
echo "Uninstall: launchctl unload $PLIST_PATH"
