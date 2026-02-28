#!/usr/bin/env python3
"""
Discord Bridge for Claude Code
Two-way communication: read messages from Discord, post updates back.
Designed to let Claude Code communicate with users via Discord.

Setup:
  1. Create a Discord bot at https://discord.com/developers/applications
  2. Copy .env.example to .env and fill in your values
  3. Invite bot to your server with Messages permission
  4. Run: python3 discord_bridge.py read

Usage:
  python3 discord_bridge.py read              # Read recent messages
  python3 discord_bridge.py read --since 10   # Messages from last 10 minutes
  python3 discord_bridge.py send "message"    # Send a message (rate limited)
  python3 discord_bridge.py send "msg" --force  # Bypass rate limit
  python3 discord_bridge.py watch             # Watch for new messages
  python3 discord_bridge.py cleanup [N]       # Delete last N bot messages (default 5)
  python3 discord_bridge.py delete <msg_id>   # Delete specific message
  python3 discord_bridge.py interactions      # Check pending messages from allowed users
  python3 discord_bridge.py reply <msg_id> "response"  # Reply to a specific message
  python3 discord_bridge.py users             # List allowed interactive users

Environment variables (or .env file):
  DISCORD_BOT_TOKEN     - Your bot token (required)
  DISCORD_CHANNEL_ID    - Channel ID to monitor (required)
  DISCORD_BOT_ID        - Your bot's user ID (required, for filtering bot messages)
  DISCORD_ALLOWED_USERS - Comma-separated user_id:name pairs (optional)
                          Example: "123456:Alice,789012:Bob"
  DISCORD_RATE_LIMIT    - Seconds between sends (default: 300)
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Load .env from script directory or parent
for env_candidate in [Path.cwd() / ".env", Path(__file__).parent / ".env"]:
    if env_candidate.exists():
        for line in env_candidate.read_text().splitlines():
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                value = value.strip('"').strip("'")
                os.environ.setdefault(key.strip(), value.strip())
        break

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
BOT_ID = os.getenv("DISCORD_BOT_ID")

if not BOT_TOKEN:
    print("Error: DISCORD_BOT_TOKEN not set. Copy .env.example to .env and fill in your values.")
    sys.exit(1)

if not CHANNEL_ID:
    print("Error: DISCORD_CHANNEL_ID not set.")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bot {BOT_TOKEN}",
    "Content-Type": "application/json"
}

# Parse allowed users from env: "id1:Name1,id2:Name2"
ALLOWED_USERS = {}
allowed_str = os.getenv("DISCORD_ALLOWED_USERS", "")
if allowed_str:
    for pair in allowed_str.split(","):
        pair = pair.strip()
        if ":" in pair:
            uid, name = pair.split(":", 1)
            ALLOWED_USERS[uid.strip()] = name.strip()

# State files (in script directory)
STATE_DIR = Path(__file__).parent / ".state"
STATE_DIR.mkdir(exist_ok=True)
LAST_READ_FILE = STATE_DIR / "last_read"
LAST_INTERACTION_FILE = STATE_DIR / "last_interaction"
LAST_SEND_FILE = STATE_DIR / "last_send"

# Rate limiting
MIN_SEND_INTERVAL_SECONDS = int(os.getenv("DISCORD_RATE_LIMIT", "300"))


def get_messages(limit: int = 20, after: str = None) -> list:
    """Fetch messages from Discord channel."""
    url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages?limit={limit}"
    if after:
        url += f"&after={after}"

    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return []


def format_message(msg: dict) -> str:
    """Format a Discord message for CLI display."""
    author = msg['author'].get('global_name') or msg['author']['username']
    is_bot = msg['author'].get('bot', False)
    timestamp = msg['timestamp'][:16].replace('T', ' ')
    content = msg['content'][:500]

    prefix = "[BOT]" if is_bot else "[USER]"
    return f"{prefix} [{timestamp}] {author}: {content}"


def read_messages(since_minutes: int = None, show_bot: bool = False):
    """Read recent messages, optionally filtering by time."""
    messages = get_messages(limit=50)

    if not messages:
        print("No messages found.")
        return []

    if since_minutes:
        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=since_minutes)
        messages = [
            m for m in messages
            if datetime.fromisoformat(m['timestamp'].replace('Z', '+00:00')).replace(tzinfo=None) > cutoff
        ]

    if not show_bot and BOT_ID:
        messages = [m for m in messages if m['author']['id'] != BOT_ID]

    messages = list(reversed(messages))

    if not messages:
        print("No new messages from humans.")
        return []

    print(f"\n{'='*60}")
    print(f"Discord Messages")
    print(f"{'='*60}\n")

    for msg in messages:
        print(format_message(msg))
        print()

    if messages:
        LAST_READ_FILE.write_text(messages[-1]['id'])

    return messages


def read_unread():
    """Read only messages since last check."""
    after = None
    if LAST_READ_FILE.exists():
        after = LAST_READ_FILE.read_text().strip()

    messages = get_messages(limit=50, after=after) if after else get_messages(limit=10)

    if BOT_ID:
        messages = [m for m in messages if m['author']['id'] != BOT_ID]
    messages = list(reversed(messages))

    if not messages:
        print("No new messages.")
        return []

    print(f"\n{'='*60}")
    print(f"New Discord Messages")
    print(f"{'='*60}\n")

    for msg in messages:
        print(format_message(msg))
        print()

    if messages:
        LAST_READ_FILE.write_text(messages[-1]['id'])

    return messages


def send_message(content: str, force: bool = False) -> dict:
    """Send a message to Discord with rate limiting."""
    if LAST_SEND_FILE.exists() and not force:
        last_send = float(LAST_SEND_FILE.read_text().strip())
        elapsed = time.time() - last_send
        remaining = MIN_SEND_INTERVAL_SECONDS - elapsed

        if remaining > 0:
            print(f"RATE LIMITED: Wait {int(remaining)}s before sending another message")
            print(f"   (Use --force to bypass)")
            return {"error": "rate_limited", "wait_seconds": remaining}

    response = requests.post(
        f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages",
        headers=HEADERS,
        json={"content": content}
    )

    if response.status_code == 200:
        LAST_SEND_FILE.write_text(str(time.time()))
        print(f"Message sent")
        return response.json()
    else:
        print(f"Failed: {response.status_code}")
        return {"error": response.text}


def watch(interval: int = 30):
    """Watch for new messages continuously."""
    print(f"Watching for new messages (every {interval}s)...")
    print("Press Ctrl+C to stop.\n")

    while True:
        messages = read_unread()
        if messages:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Waiting for new messages...\n")
        time.sleep(interval)


def delete_message(message_id: str) -> dict:
    """Delete a message from Discord."""
    response = requests.delete(
        f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages/{message_id}",
        headers=HEADERS
    )

    if response.status_code == 204:
        print(f"Message {message_id} deleted")
        return {"success": True}
    else:
        print(f"Failed: {response.status_code} - {response.text}")
        return {"error": response.text}


def delete_recent_bot_messages(count: int = 5) -> dict:
    """Delete recent messages sent by the bot (cleanup spam)."""
    if not BOT_ID:
        print("DISCORD_BOT_ID not set, cannot identify bot messages")
        return {"deleted": 0}

    messages = get_messages(limit=50)
    bot_messages = [m for m in messages if m['author']['id'] == BOT_ID][:count]

    if not bot_messages:
        print("No bot messages to delete")
        return {"deleted": 0}

    deleted = 0
    for msg in bot_messages:
        result = delete_message(msg['id'])
        if result.get("success"):
            deleted += 1

    print(f"Deleted {deleted} bot messages")
    return {"deleted": deleted}


def get_context_for_claude() -> str:
    """Get recent messages formatted for Claude Code context."""
    messages = get_messages(limit=20)
    if BOT_ID:
        messages = [m for m in messages if m['author']['id'] != BOT_ID]
    messages = list(reversed(messages))

    if not messages:
        return "No recent Discord messages from humans."

    output = "Recent Discord messages:\n\n"
    for msg in messages:
        author = msg['author'].get('global_name') or msg['author']['username']
        content = msg['content']
        output += f"- {author}: {content}\n"

    return output


def is_allowed_user(user_id: str) -> bool:
    """Check if a user is in the allowlist."""
    if not ALLOWED_USERS:
        return True  # No allowlist = everyone allowed
    return user_id in ALLOWED_USERS


def get_user_label(msg: dict) -> str:
    """Get display label for a message author."""
    user_id = msg['author']['id']
    if user_id in ALLOWED_USERS:
        return ALLOWED_USERS[user_id]
    return msg['author'].get('global_name') or msg['author']['username']


def get_pending_interactions(since_minutes: int = 60) -> list:
    """Get messages from allowed users that haven't been responded to yet."""
    after = None
    if LAST_INTERACTION_FILE.exists():
        after = LAST_INTERACTION_FILE.read_text().strip()

    if after:
        messages = get_messages(limit=50, after=after)
    else:
        messages = get_messages(limit=50)
        if since_minutes:
            cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=since_minutes)
            messages = [
                m for m in messages
                if datetime.fromisoformat(m['timestamp'].replace('Z', '+00:00')).replace(tzinfo=None) > cutoff
            ]

    messages = [
        m for m in messages
        if (not BOT_ID or m['author']['id'] != BOT_ID) and is_allowed_user(m['author']['id'])
    ]
    messages = list(reversed(messages))

    if not messages:
        return []

    results = []
    for msg in messages:
        results.append({
            "id": msg['id'],
            "author": get_user_label(msg),
            "author_id": msg['author']['id'],
            "content": msg['content'],
            "timestamp": msg['timestamp'][:16].replace('T', ' '),
        })

    return results


def check_interactions(since_minutes: int = 60, mark_read: bool = True) -> list:
    """Check for pending interactions from allowed users and display them."""
    pending = get_pending_interactions(since_minutes=since_minutes)

    if not pending:
        print("No pending interactions from allowed users.")
        return []

    print(f"\n{'='*60}")
    print(f"Pending Interactions ({len(pending)} messages)")
    print(f"{'='*60}\n")

    for p in pending:
        print(f"  [{p['timestamp']}] {p['author']}: {p['content']}")
        print()

    if mark_read and pending:
        LAST_INTERACTION_FILE.write_text(pending[-1]['id'])

    return pending


def reply_to(message_id: str, content: str, force: bool = False) -> dict:
    """Reply to a specific message (with rate limiting)."""
    if LAST_SEND_FILE.exists() and not force:
        last_send = float(LAST_SEND_FILE.read_text().strip())
        elapsed = time.time() - last_send
        remaining = MIN_SEND_INTERVAL_SECONDS - elapsed

        if remaining > 0:
            print(f"Rate limited: wait {int(remaining)}s (use --force to bypass)")
            return {"error": "rate_limited", "wait_seconds": remaining}

    response = requests.post(
        f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages",
        headers=HEADERS,
        json={
            "content": content,
            "message_reference": {"message_id": message_id}
        }
    )

    if response.status_code == 200:
        LAST_SEND_FILE.write_text(str(time.time()))
        print(f"Replied to message {message_id}")
        return response.json()
    else:
        print(f"Failed: {response.status_code}")
        return {"error": response.text}


def list_allowed_users():
    """Show who can interact with the bot."""
    if not ALLOWED_USERS:
        print("\nNo allowlist configured - all users can interact.")
        print("Set DISCORD_ALLOWED_USERS in .env to restrict access.")
        return

    print("\nAllowed interactive users:")
    for uid, name in ALLOWED_USERS.items():
        print(f"  {name} (ID: {uid})")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]

    if command == "read":
        since = None
        if "--since" in sys.argv:
            idx = sys.argv.index("--since")
            since = int(sys.argv[idx + 1])
        read_messages(since_minutes=since)

    elif command == "unread":
        read_unread()

    elif command == "send":
        if len(sys.argv) < 3:
            print("Usage: discord_bridge.py send 'your message' [--force]")
        else:
            force = "--force" in sys.argv
            message_parts = [arg for arg in sys.argv[2:] if arg != "--force"]
            send_message(" ".join(message_parts), force=force)

    elif command == "watch":
        interval = 30
        if len(sys.argv) > 2:
            interval = int(sys.argv[2])
        watch(interval)

    elif command == "context":
        print(get_context_for_claude())

    elif command == "delete":
        if len(sys.argv) < 3:
            print("Usage: discord_bridge.py delete <message_id>")
        else:
            delete_message(sys.argv[2])

    elif command == "cleanup":
        count = 5
        if len(sys.argv) > 2:
            count = int(sys.argv[2])
        delete_recent_bot_messages(count)

    elif command == "interactions":
        since = 60
        if "--since" in sys.argv:
            idx = sys.argv.index("--since")
            since = int(sys.argv[idx + 1])
        no_mark = "--no-mark" in sys.argv
        result = check_interactions(since_minutes=since, mark_read=not no_mark)
        if "--json" in sys.argv:
            print(json.dumps(result, indent=2))

    elif command == "reply":
        if len(sys.argv) < 4:
            print("Usage: discord_bridge.py reply <message_id> 'response' [--force]")
        else:
            msg_id = sys.argv[2]
            force = "--force" in sys.argv
            reply_parts = [arg for arg in sys.argv[3:] if arg != "--force"]
            reply_to(msg_id, " ".join(reply_parts), force=force)

    elif command == "users":
        list_allowed_users()

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
