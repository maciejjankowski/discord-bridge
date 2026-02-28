# Discord Bridge for Claude Code

Two-way Discord communication for Claude Code sessions. Let Claude read messages from a Discord channel and post updates back - so you can talk to your AI assistant from Discord.

## Why

Claude Code runs in a terminal. Sometimes you want to send it instructions or check on progress from your phone. This bridge connects a Discord channel to your Claude Code session.

## Setup

### 1. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. New Application -> name it whatever you want
3. Bot tab -> Reset Token -> copy the token
4. Bot tab -> enable "Message Content Intent"
5. OAuth2 -> URL Generator -> select `bot` scope -> select `Send Messages`, `Read Message History` permissions
6. Copy the generated URL, open it, invite bot to your server

### 2. Get IDs

Enable Developer Mode in Discord (Settings -> App Settings -> Advanced -> Developer Mode).

- **Channel ID**: Right-click the channel -> Copy Channel ID
- **Bot User ID**: Right-click the bot in the member list -> Copy User ID
- **Your User ID** (for allowlist): Right-click yourself -> Copy User ID

### 3. Configure

```bash
cp .env.example .env
# Edit .env with your values
```

### 4. Install dependency

```bash
pip install requests
```

### 5. Use

```bash
# Read recent messages
python3 discord_bridge.py read

# Read messages from last 10 minutes
python3 discord_bridge.py read --since 10

# Send a message (rate limited to 1 per 5 min)
python3 discord_bridge.py send "Task completed"

# Send bypassing rate limit
python3 discord_bridge.py send "Urgent update" --force

# Watch for new messages (polls every 30s)
python3 discord_bridge.py watch

# Check pending messages from allowed users
python3 discord_bridge.py interactions

# Reply to a specific message
python3 discord_bridge.py reply <message_id> "Here's the answer"

# Clean up bot spam
python3 discord_bridge.py cleanup 5

# List allowed users
python3 discord_bridge.py users
```

## Claude Code Integration

### Automatic (recommended)

Ready-made hooks are in the `hooks/` folder. Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "type": "command",
        "command": "/path/to/discord-bridge/hooks/discord_check_hook.sh"
      }
    ],
    "PostToolUse": [
      {
        "type": "command",
        "command": "/path/to/discord-bridge/hooks/discord_poll_hook.sh"
      }
    ]
  }
}
```

This gives you:
- **SessionStart**: checks for new messages when Claude Code starts
- **PostToolUse**: polls for new messages every ~15 tool calls while working

Make hooks executable: `chmod +x hooks/*.sh`

### In CLAUDE.md

Add to your project's CLAUDE.md:

```markdown
## Discord Communication
- Read messages: `python3 /path/to/discord_bridge.py read --since 60`
- Send updates: `python3 /path/to/discord_bridge.py send "message" --force`
- Check for instructions: `python3 /path/to/discord_bridge.py interactions`
```

### Allowlist

Set `DISCORD_ALLOWED_USERS` in `.env` to restrict who can send commands:

```
DISCORD_ALLOWED_USERS=123456789:Alice,987654321:Bob
```

If not set, messages from all users are shown.

## Rate Limiting

Default: 5 minutes between sends. Change with `DISCORD_RATE_LIMIT` env var. Use `--force` to bypass.

## License

MIT
