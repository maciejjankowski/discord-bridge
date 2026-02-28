#!/usr/bin/env python3
"""
Inject text into the iTerm2 session running Claude Code.
Finds the session by looking for 'claude' in session name.
Falls back to current session if no match found.

Requires: pip install iterm2
Also requires iTerm2 Python API enabled:
  iTerm2 -> Settings -> General -> Magic -> Enable Python API

Usage:
    python3 iterm_inject.py "text to inject"
    python3 iterm_inject.py --file /tmp/discord_new_message.flag
"""

import iterm2
import sys
import asyncio
from pathlib import Path


async def inject(text: str):
    connection = await iterm2.Connection.async_create()
    app = await iterm2.async_get_app(connection)

    # Strategy: find session running claude
    target_session = None

    for window in app.terminal_windows:
        for tab in window.tabs:
            for session in tab.sessions:
                name = session.name or ""
                if "claude" in name.lower():
                    target_session = session
                    break
            if target_session:
                break
        if target_session:
            break

    # Fallback: use the current session in the current window
    if not target_session:
        current_window = app.current_terminal_window
        if current_window:
            current_tab = current_window.current_tab
            if current_tab:
                target_session = current_tab.current_session

    if not target_session:
        print("ERROR: No iTerm2 session found", file=sys.stderr)
        sys.exit(1)

    # Send text then Enter (\r = carriage return for raw terminal mode)
    await target_session.async_send_text(text)
    await asyncio.sleep(0.3)
    await target_session.async_send_text("\r")
    print(f"Injected into session: {target_session.name or target_session.session_id}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    if sys.argv[1] == "--file":
        filepath = sys.argv[2] if len(sys.argv) > 2 else "/tmp/discord_new_message.flag"
        p = Path(filepath)
        if not p.exists():
            print(f"No file: {filepath}")
            sys.exit(0)
        text = p.read_text().strip()
    else:
        text = " ".join(sys.argv[1:])

    if not text:
        sys.exit(0)

    asyncio.run(inject(text))


if __name__ == "__main__":
    main()
