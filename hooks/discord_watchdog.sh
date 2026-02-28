#!/bin/bash
# Discord Watchdog - polls Discord every 60s via launchd
# When new human message arrives:
#   1. Saves to /tmp/discord_new_message.flag
#   2. Sends macOS notification with sound
#   3. Injects text into iTerm2 Claude Code session
#
# Install: ./hooks/install_launchd.sh

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_FILE="/tmp/discord_watchdog.log"
FLAG_FILE="/tmp/discord_new_message.flag"
STATE_FILE="/tmp/discord_watchdog_state"

cd "$SCRIPT_DIR" || exit 1

python3 - <<'PYEOF'
import os, json, sys, subprocess, requests
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(os.environ.get("SCRIPT_DIR", Path(__file__).parent))
FLAG = Path("/tmp/discord_new_message.flag")
STATE = Path("/tmp/discord_watchdog_state")
LOG = Path("/tmp/discord_watchdog.log")

# Load .env
for env_candidate in [SCRIPT_DIR / ".env", Path.cwd() / ".env"]:
    if env_candidate.exists():
        for line in env_candidate.read_text().splitlines():
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        break

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
BOT_ID = os.getenv("DISCORD_BOT_ID")

if not BOT_TOKEN or not CHANNEL_ID:
    sys.exit(1)

HEADERS = {"Authorization": f"Bot {BOT_TOKEN}"}

# Load last seen message ID
last_seen_id = None
if STATE.exists():
    last_seen_id = STATE.read_text().strip()

url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages?limit=10"
if last_seen_id:
    url += f"&after={last_seen_id}"

try:
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    messages = resp.json()
except Exception as e:
    with open(LOG, "a") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | ERROR: {e}\n")
    sys.exit(1)

if not messages:
    with open(LOG, "a") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | no new messages\n")
    sys.exit(0)

# Update last_seen_id to the newest message
STATE.write_text(messages[0]["id"])

# Filter to human messages only
human_msgs = [m for m in reversed(messages) if not m["author"].get("bot", False)]

now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if human_msgs:
    lines = []
    for m in human_msgs:
        author = m["author"].get("global_name") or m["author"]["username"]
        content = m["content"]
        ts = m["timestamp"][:19].replace("T", " ")
        lines.append(f"[{ts}] {author}: {content}")

    msg_text = "\n".join(lines)
    FLAG.write_text(msg_text)

    # macOS notification
    first_msg = human_msgs[0]
    author = first_msg["author"].get("global_name") or first_msg["author"]["username"]
    preview = first_msg["content"][:80].replace('"', '\\"')
    safe_author = author.replace('"', '\\"')
    os.system(f'osascript -e \'display notification "{preview}" with title "Discord: {safe_author}" sound name "Ping"\' 2>/dev/null')

    # Inject into iTerm2 Claude Code session
    author_name = human_msgs[0]["author"].get("global_name", human_msgs[0]["author"]["username"])
    msg_content = human_msgs[0]["content"]
    inject_text = f"[Discord from {author_name}]: {msg_content}"

    inject_script = SCRIPT_DIR / "hooks" / "iterm_inject.py"
    if inject_script.exists():
        result = subprocess.run(
            [sys.executable, str(inject_script), inject_text],
            capture_output=True, text=True, timeout=15
        )
        with open(LOG, "a") as f:
            if result.returncode != 0:
                f.write(f"{now} | INJECT FAIL: {result.stderr.strip()[:200]}\n")
                # AppleScript fallback
                safe_text = inject_text.replace('\\', '\\\\').replace('"', '\\"')
                scpt = Path("/tmp/discord_inject.scpt")
                scpt.write_text(f'tell application "iTerm2"\n    tell current session of current window\n        write text "{safe_text}"\n    end tell\nend tell\n')
                r2 = subprocess.run(["osascript", str(scpt)], capture_output=True, text=True, timeout=10)
                if r2.returncode == 0:
                    f.write(f"{now} | INJECTED via AppleScript fallback\n")
                else:
                    f.write(f"{now} | INJECT FAIL (both): {r2.stderr.strip()[:100]}\n")
            else:
                f.write(f"{now} | INJECTED: {result.stdout.strip()[:100]}\n")
    else:
        with open(LOG, "a") as f:
            f.write(f"{now} | iterm_inject.py not found, skipping injection\n")

    with open(LOG, "a") as f:
        f.write(f"{now} | NEW: {msg_text}\n")
else:
    with open(LOG, "a") as f:
        f.write(f"{now} | {len(messages)} bot msgs only\n")

# Trim log
if LOG.exists():
    log_lines = LOG.read_text().splitlines()
    if len(log_lines) > 100:
        LOG.write_text("\n".join(log_lines[-100:]) + "\n")
PYEOF
