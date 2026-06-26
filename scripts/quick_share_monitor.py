#!/usr/bin/env python3
"""
Quick Share Monitor for Video Sync
Monitors #all_user_research for Quick Sharing messages and triggers Video Sync

Part of hybrid auto-trigger system:
1. Quick Share Monitor (Slack-based) - primary for Video Sync
2. Manual trigger ("Video Sync 해줘") - fallback
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

# Configuration
SLACK_CHANNEL_ID = "C056LP1M5P1"  # #all_user_research
CHECK_INTERVAL = 300  # 5 minutes
SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR.parent / "config" / "projects.json"
STATE_FILE = SCRIPT_DIR.parent / "data" / "video_sync_state.json"
FLAG_DIR = SCRIPT_DIR.parent / "data"
SLACK_TOKEN_FILE = Path.home() / ".sidekick/.env"

# Quick Sharing detection patterns
QUICK_SHARE_PATTERNS = [
    r"Quick\s*Sharing",
    r"QS[:\s]",
    r"quick-share",
    r"퀵\s*쉐어링",
]

# User number extraction pattern
USER_NUMBER_PATTERNS = [
    r"(\d+)(?:st|nd|rd|th)\s+(?:session|user|UT)",
    r"User\s*(\d+)",
    r"(\d+)번째",
    r"#(\d+)",
]


def log(message):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def get_slack_token():
    """Get Slack bot token from environment or file."""
    token = os.environ.get("SLACK_BOT_TOKEN")
    if token:
        return token

    if SLACK_TOKEN_FILE.exists():
        with open(SLACK_TOKEN_FILE) as f:
            for line in f:
                if line.startswith("SLACK_BOT_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"\'')
    return None


def load_config():
    """Load projects configuration."""
    if not CONFIG_FILE.exists():
        log(f"Config file not found: {CONFIG_FILE}")
        return None

    with open(CONFIG_FILE) as f:
        return json.load(f)


def load_state():
    """Load monitor state."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "last_checked_ts": None,
        "processed_messages": [],
        "synced_users": {},
        "last_run": None
    }


def save_state(state):
    """Save monitor state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_run"] = datetime.now().isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_channel_messages(token, channel_id, oldest_ts=None, limit=50):
    """Fetch recent messages from Slack channel."""
    url = "https://slack.com/api/conversations.history"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "channel": channel_id,
        "limit": limit
    }
    if oldest_ts:
        params["oldest"] = oldest_ts

    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        log(f"Slack API error: {response.status_code}")
        return []

    data = response.json()
    if not data.get("ok"):
        log(f"Slack API error: {data.get('error')}")
        return []

    return data.get("messages", [])


def is_quick_share_message(text):
    """Check if message is a Quick Sharing message."""
    if not text:
        return False

    for pattern in QUICK_SHARE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def extract_user_number(text):
    """Extract user number from message text."""
    if not text:
        return None

    for pattern in USER_NUMBER_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def extract_project_name(text):
    """Extract project name from message text."""
    if not text:
        return None

    patterns = [
        r"(SEP\+?UOL\s*(?:UT)?)",
        r"(LVL\s*(?:Research)?)",
        r"\[([^\]]+)\]",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def find_project_by_name(config, project_name):
    """Find project config by name."""
    if not project_name:
        return None

    project_name_lower = project_name.lower().replace(" ", "").replace("+", "")

    for project_id, project in config.get("projects", {}).items():
        name = project.get("name", "").lower().replace(" ", "").replace("+", "")
        if project_name_lower in name or name in project_name_lower:
            return project_id, project

    return None


def get_project_goal(config, project_id):
    """Get project Goal (target number of users)."""
    recruiting_config_path = Path.home() / "Projects/github/Recruiting/projects.json"
    if recruiting_config_path.exists():
        with open(recruiting_config_path) as f:
            recruiting_config = json.load(f)

        project = config.get("projects", {}).get(project_id, {})
        # Try to find recruiting_id or use project keywords
        for rp in recruiting_config.get("projects", []):
            project_name = project.get("name", "").lower()
            rp_name = rp.get("name", "").lower()
            if any(kw.lower() in rp_name for kw in project.get("calendar_keywords", [])):
                return rp.get("target", 0)

    return 0


def trigger_video_sync(project_id):
    """Trigger Video Sync for project."""
    log(f"Triggering Video Sync for project: {project_id}")

    try:
        result = subprocess.run(
            ["uv", "run", "python", "scripts/video_sync.py", "full", "--project", project_id],
            cwd=SCRIPT_DIR.parent,
            capture_output=True,
            text=True,
            timeout=180
        )

        if result.returncode == 0:
            log(f"Video Sync completed successfully")
            return True
        else:
            log(f"Video Sync failed: {result.stderr[:500]}")
            return False
    except subprocess.TimeoutExpired:
        log("Video Sync timed out")
        return False
    except Exception as e:
        log(f"Video Sync error: {e}")
        return False


def send_slack_notification(token, project_name, user_number):
    """Send notification about Quick Share detection triggering Video Sync."""
    text = f"🎬 *Quick Share Monitor*\nUser {user_number} Quick Sharing 감지\n→ {project_name} Video Sync 실행"

    notification_channel = "C0BBQNNAEV8"

    response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "channel": notification_channel,
            "text": text
        }
    )

    return response.status_code == 200 and response.json().get("ok")


def process_messages(token, config, state):
    """Process new messages and detect Quick Sharing for video sync."""
    messages = get_channel_messages(
        token,
        SLACK_CHANNEL_ID,
        oldest_ts=state.get("last_checked_ts"),
        limit=50
    )

    if not messages:
        return state

    processed = state.get("processed_messages", [])
    synced_users = state.get("synced_users", {})
    latest_ts = state.get("last_checked_ts")

    for msg in reversed(messages):
        msg_ts = msg.get("ts")
        text = msg.get("text", "")

        if msg_ts in processed:
            continue

        if latest_ts is None or float(msg_ts) > float(latest_ts):
            latest_ts = msg_ts

        if not is_quick_share_message(text):
            processed.append(msg_ts)
            continue

        log(f"Quick Sharing detected: {text[:100]}...")

        user_number = extract_user_number(text)
        project_name = extract_project_name(text)

        if not user_number or not project_name:
            log(f"  Could not extract user/project info")
            processed.append(msg_ts)
            continue

        log(f"  Project: {project_name}, User: {user_number}")

        project_match = find_project_by_name(config, project_name)
        if not project_match:
            log(f"  Project not found in config")
            processed.append(msg_ts)
            continue

        project_id, project = project_match

        # Check if already synced for this user
        project_synced = synced_users.get(project_id, [])
        if user_number in project_synced:
            log(f"  User {user_number} already synced, skipping")
            processed.append(msg_ts)
            continue

        # Trigger Video Sync for each Quick Sharing (unlike Payment Sync which waits for last user)
        log(f"  Triggering Video Sync for User {user_number}")
        if trigger_video_sync(project_id):
            if project_id not in synced_users:
                synced_users[project_id] = []
            synced_users[project_id].append(user_number)
            send_slack_notification(token, project_name, user_number)

        processed.append(msg_ts)

    state["processed_messages"] = processed[-100:]
    state["last_checked_ts"] = latest_ts
    state["synced_users"] = synced_users

    return state


def run_daemon():
    """Run the Quick Share monitor daemon for Video Sync."""
    log("Starting Video Sync Quick Share Monitor daemon...")

    token = get_slack_token()
    if not token:
        log("ERROR: Slack token not found")
        sys.exit(1)

    config = load_config()
    if not config:
        log("ERROR: Config not found")
        sys.exit(1)

    state = load_state()
    log(f"Loaded state: last_checked={state.get('last_checked_ts')}")
    log(f"Monitoring channel: {SLACK_CHANNEL_ID}")
    log(f"Check interval: {CHECK_INTERVAL} seconds")

    try:
        while True:
            try:
                config = load_config()
                state = process_messages(token, config, state)
                save_state(state)
            except Exception as e:
                log(f"Error processing messages: {e}")

            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        log("Shutting down...")
        save_state(state)


def run_once():
    """Run a single check (for testing)."""
    log("Running single Video Sync Quick Share check...")

    token = get_slack_token()
    if not token:
        log("ERROR: Slack token not found")
        return 1

    config = load_config()
    if not config:
        log("ERROR: Config not found")
        return 1

    state = load_state()
    state = process_messages(token, config, state)
    save_state(state)

    log("Check complete")
    return 0


def reset_state():
    """Reset synced users state for new project cycle."""
    state = load_state()
    state["synced_users"] = {}
    save_state(state)
    log("State reset - synced_users cleared")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Quick Share Monitor for Video Sync")
    parser.add_argument("command", nargs="?", default="daemon",
                       choices=["daemon", "check", "status", "reset"],
                       help="Command: daemon (continuous), check (once), status, reset")

    args = parser.parse_args()

    if args.command == "daemon":
        run_daemon()
    elif args.command == "check":
        sys.exit(run_once())
    elif args.command == "status":
        state = load_state()
        print(json.dumps(state, indent=2))
    elif args.command == "reset":
        reset_state()
