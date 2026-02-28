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
4. Bot tab -> enable "Message Content Intent"
5. OAuth2 -> URL Generator -> select `bot` scope -> select `Send Messages`, `Read Message History`
6. Copy the generated URL, open it, invite bot to your server

### 2. Get IDs

Enable Developer Mode in Discord (Settings -> Advanced -> Developer Mode).

- **Channel ID**: Right-click channel -> Copy Channel ID
- **Bot User ID**: Right-click bot -> Copy User ID

### 3. Configure

```bash
git clone https://github.com/maciejjankowski/discord-bridge.git
cd discord-bridge
pip install requests iterm2
cp .env.example .env
# Edit .env with your token, channel ID, bot ID
```

### 4. Enable iTerm2 Python API

iTerm2 -> Settings -> General -> Magic -> Enable Python API

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

## Allowlist

Set `DISCORD_ALLOWED_USERS` in `.env` to restrict who can interact:

```
DISCORD_ALLOWED_USERS=123456789:Alice,987654321:Bob
```

If not set, all users can interact.

## Uninstall daemon

```bash
launchctl unload ~/Library/LaunchAgents/com.discord-bridge.watchdog.plist
```

## Files

```
discord_bridge.py          # CLI tool - read/send/watch/reply
hooks/
  install_launchd.sh       # One-command daemon setup
  discord_watchdog.sh      # Daemon script (polls + injects)
  iterm_inject.py          # iTerm2 Python API injection
```

## License

MIT
