# Discord Bridge for Claude Code

Two-way Discord communication for Claude Code sessions. Messages from Discord get injected directly into your Claude Code terminal via iTerm2.

## How it works

1. macOS launchd daemon polls Discord every 30s
2. New message arrives -> macOS notification + sound
3. Message gets typed into your iTerm2 Claude Code session automatically
4. Claude Code sees it as user input and responds

## Setup

### 1. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. New Application -> name it
3. Bot tab -> Reset Token -> copy the token
4. Bot tab -> enable **"Message Content Intent"** (required to read message text)
5. OAuth2 -> URL Generator -> select `bot` scope -> select permissions:
   - `Send Messages`
   - `Read Message History`
   - `View Channels`
6. Copy the generated URL, open it, invite bot to your server

**Important:** If the bot gets 403 "Missing Access" on a channel, the server admin needs to:
- Go to Channel Settings -> Permissions -> add the bot role
- Grant: View Channel, Send Messages, Read Message History

### 2. Get IDs

Enable Developer Mode in Discord (Settings -> Advanced -> Developer Mode).

- **Channel ID**: Right-click channel -> Copy Channel ID
- **Bot User ID**: Right-click bot in member list -> Copy User ID

### 3. Install

```bash
git clone https://github.com/maciejjankowski/discord-bridge.git
cd discord-bridge
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your token, channel ID, bot ID
```

### 4. Enable iTerm2 Python API

iTerm2 -> Settings -> General -> Magic -> **Enable Python API**

Without this, the auto-inject feature won't work (notifications and flag files still work).

### 5. Install daemon

```bash
./hooks/install_launchd.sh
```

Done. Messages will now auto-inject into your Claude Code session.

### 6. Add to CLAUDE.md

```markdown
## Discord
- Read messages: `python3 /path/to/discord-bridge/discord_bridge.py read --since 60`
- Send updates: `python3 /path/to/discord-bridge/discord_bridge.py send "message" --force`
- Check for instructions: `python3 /path/to/discord-bridge/discord_bridge.py interactions`
```

## CLI commands

```bash
python3 discord_bridge.py read              # Read recent messages
python3 discord_bridge.py read --since 10   # Last 10 minutes
python3 discord_bridge.py send "message"    # Send (rate limited 5 min)
python3 discord_bridge.py send "msg" --force  # Bypass rate limit
python3 discord_bridge.py interactions      # Pending messages from allowed users
python3 discord_bridge.py reply <id> "text" # Reply to specific message
python3 discord_bridge.py cleanup 5         # Delete last 5 bot messages
python3 discord_bridge.py watch             # Poll in terminal (alternative to daemon)
```

Messages over 2000 characters are automatically split into multiple parts.

## Allowlist

Set `DISCORD_ALLOWED_USERS` in `.env` to restrict who can interact:

```
DISCORD_ALLOWED_USERS=123456789:Alice,987654321:Bob
```

If not set, all users can interact.

## Troubleshooting

### 403 Missing Access
The bot doesn't have permissions on the channel. Ask the server admin to add the bot role to the channel with View Channel, Send Messages, Read Message History.

### iterm_inject.py fails
1. Check iTerm2 Python API is enabled: Settings -> General -> Magic -> Enable Python API
2. Check `iterm2` package is installed: `pip install iterm2`
3. The daemon falls back to AppleScript if the Python API fails

### Daemon not running
```bash
# Check status
launchctl list | grep discord-bridge

# Check logs
cat /tmp/discord_watchdog_stdout.log
cat /tmp/discord_watchdog_stderr.log

# Reload
launchctl unload ~/Library/LaunchAgents/com.discord-bridge.watchdog.plist
launchctl load ~/Library/LaunchAgents/com.discord-bridge.watchdog.plist
```

### Messages not showing up
1. Check bot token is valid: `python3 discord_bridge.py read`
2. Check channel ID is correct (right-click channel -> Copy Channel ID)
3. Check the bot is in the server and has channel access
4. Check state file: `cat .state/last_read` - if stuck, delete it

### Python/requests not found
The daemon runs with system PATH. If `requests` isn't installed system-wide:
```bash
# Option 1: Install for system python
/usr/bin/python3 -m pip install requests iterm2

# Option 2: Update plist PATH to include your venv
# Edit ~/Library/LaunchAgents/com.discord-bridge.watchdog.plist
```

## Uninstall daemon

```bash
launchctl unload ~/Library/LaunchAgents/com.discord-bridge.watchdog.plist
rm ~/Library/LaunchAgents/com.discord-bridge.watchdog.plist
```

## Files

```
discord_bridge.py          # CLI tool - read/send/watch/reply (auto-chunks long messages)
hooks/
  install_launchd.sh       # One-command daemon setup (30s polling)
  discord_watchdog.sh      # Daemon script (polls + notifies + injects into iTerm2)
  iterm_inject.py          # iTerm2 Python API injection (with AppleScript fallback)
.env.example               # Configuration template
requirements.txt           # Python dependencies (requests + iterm2)
```

## License

MIT
