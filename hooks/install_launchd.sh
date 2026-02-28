#!/bin/bash
# Install macOS launchd watchdog - checks Discord every 60s
# When new message arrives:
#   1. macOS notification with sound
#   2. Injects text into iTerm2 Claude Code session automatically
#   3. Saves to /tmp/discord_new_message.flag
#
# Prerequisites:
#   pip install iterm2 requests
#   iTerm2 -> Settings -> General -> Magic -> Enable Python API
#
# Usage: ./hooks/install_launchd.sh
# Uninstall: launchctl unload ~/Library/LaunchAgents/com.discord-bridge.watchdog.plist

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_PATH="$HOME/Library/LaunchAgents/com.discord-bridge.watchdog.plist"
WATCHDOG="$SCRIPT_DIR/hooks/discord_watchdog.sh"

chmod +x "$WATCHDOG"

# Unload existing if present
launchctl unload "$PLIST_PATH" 2>/dev/null

# Create launchd plist
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.discord-bridge.watchdog</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$WATCHDOG</string>
    </array>
    <key>StartInterval</key>
    <integer>60</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/discord_watchdog_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/discord_watchdog_stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
        <key>SCRIPT_DIR</key>
        <string>$SCRIPT_DIR</string>
    </dict>
</dict>
</plist>
EOF

launchctl load "$PLIST_PATH"

echo "Installed! Discord watchdog runs every 60s."
echo ""
echo "What happens when someone writes on Discord:"
echo "  1. macOS notification with sound"
echo "  2. Text injected into iTerm2 Claude Code session"
echo "  3. Saved to /tmp/discord_new_message.flag"
echo ""
echo "Logs: /tmp/discord_watchdog.log"
echo "Uninstall: launchctl unload $PLIST_PATH"
