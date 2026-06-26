#!/usr/bin/env python3
"""
Calendar Monitor for Video Sync
Monitors Google Calendar for user research sessions and triggers Video Sync after meeting ends.

Flow:
1. Check Google Calendar for user research events
2. Detect when event ends
3. Wait for buffer time (recording processing)
4. Trigger Video Sync to move recordings

Part of hybrid auto-trigger system:
1. Recruiting Dashboard (completed >= target) - Full sync
2. Calendar Monitor (meeting ended) - Per-session sync
3. Quick Share Monitor (Quick Sharing posted) - Backup
4. Manual trigger - Fallback
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

# Configuration
CHECK_INTERVAL = 300  # 5 minutes
RECORDING_BUFFER = 7200  # 2 hours - wait for recording to be processed after meeting ends
IST = ZoneInfo("Asia/Kolkata")

SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR.parent / "config" / "projects.json"
STATE_FILE = SCRIPT_DIR.parent / "data" / "calendar_monitor_state.json"
TOKEN_FILE = Path.home() / ".sidekick/sidekick/.claude/skills/google-oauth-token/.session/young.kim_oauth_token.json"
SLACK_TOKEN_FILE = Path.home() / ".sidekick/.env"


def log(message):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def get_slack_token():
    """Get Slack bot token."""
    if SLACK_TOKEN_FILE.exists():
        with open(SLACK_TOKEN_FILE) as f:
            for line in f:
                if line.startswith("SLACK_BOT_TOKEN="):
                    return line.split("=", 1)[1].strip().strip('"\'')
    return None


def load_config():
    """Load projects configuration."""
    if not CONFIG_FILE.exists():
        return None
    with open(CONFIG_FILE) as f:
        return json.load(f)


def load_state():
    """Load monitor state."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "processed_events": {},
        "last_run": None
    }


def save_state(state):
    """Save monitor state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_run"] = datetime.now().isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def load_google_token():
    """Load and refresh Google OAuth token if needed."""
    if not TOKEN_FILE.exists():
        log(f"Token file not found: {TOKEN_FILE}")
        return None

    with open(TOKEN_FILE) as f:
        token_data = json.load(f)

    expiry = datetime.fromisoformat(token_data["token_expiry"])
    if datetime.now() > expiry - timedelta(minutes=5):
        log("Refreshing Google token...")
        response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": token_data["client_id"],
                "client_secret": token_data["client_secret"],
                "refresh_token": token_data["refresh_token"],
                "grant_type": "refresh_token",
            }
        )
        if response.status_code == 200:
            new_token = response.json()
            token_data["access_token"] = new_token["access_token"]
            token_data["token_expiry"] = (datetime.now() + timedelta(seconds=new_token["expires_in"])).isoformat()
            with open(TOKEN_FILE, "w") as f:
                json.dump(token_data, f, indent=2)
        else:
            log(f"Token refresh failed: {response.text}")
            return None

    return token_data["access_token"]


def get_calendar_events(access_token, time_min, time_max):
    """Get calendar events in time range."""
    url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    params = {
        "timeMin": time_min.isoformat() + "Z",
        "timeMax": time_max.isoformat() + "Z",
        "singleEvents": "true",
        "orderBy": "startTime",
    }

    response = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, params=params)

    if response.status_code != 200:
        log(f"Calendar API error: {response.text}")
        return []

    return response.json().get("items", [])


def is_user_research_event(event, project_keywords):
    """Check if event is a user research session."""
    summary = event.get("summary", "").lower()
    description = event.get("description", "").lower()

    for keyword in project_keywords:
        if keyword.lower() in summary or keyword.lower() in description:
            return True
    return False


def extract_session_number(event_summary):
    """Extract session number from event summary."""
    # Patterns: "1st", "2nd", "3rd", "4th", "User 1", "User1", "#1"
    patterns = [
        r'(\d+)(?:st|nd|rd|th)',
        r'User\s*(\d+)',
        r'#(\d+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, event_summary, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


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
            log("Video Sync completed successfully")
            return True
        else:
            log(f"Video Sync failed: {result.stderr[:500]}")
            return False
    except Exception as e:
        log(f"Video Sync error: {e}")
        return False


def send_slack_notification(token, project_name, session_number):
    """Send notification about calendar-triggered Video Sync."""
    text = f"📅 *Calendar Monitor*\nUser {session_number} 세션 종료 감지\n→ {project_name} Video Sync 실행"

    response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "channel": "C0BBQNNAEV8",
            "text": text
        }
    )

    return response.status_code == 200 and response.json().get("ok")


def process_events(access_token, config, state):
    """Process calendar events and trigger Video Sync for ended sessions."""
    now = datetime.now(IST)

    # Check events from past 2 hours to now
    time_min = now - timedelta(hours=2)
    time_max = now

    events = get_calendar_events(access_token, time_min.replace(tzinfo=None), time_max.replace(tzinfo=None))

    if not events:
        return state

    processed = state.get("processed_events", {})
    slack_token = get_slack_token()

    for project_id, project in config.get("projects", {}).items():
        project_name = project.get("name", project_id)
        keywords = project.get("calendar_keywords", [])

        for event in events:
            event_id = event.get("id")
            summary = event.get("summary", "")

            # Skip if not user research event
            if not is_user_research_event(event, keywords):
                continue

            # Skip if already processed
            if event_id in processed:
                continue

            # Check if event has ended
            end_time_str = event.get("end", {}).get("dateTime")
            if not end_time_str:
                continue

            # Parse end time
            end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
            end_time_ist = end_time.astimezone(IST)

            # Check if event ended + buffer time passed
            if now < end_time_ist + timedelta(seconds=RECORDING_BUFFER):
                log(f"Event '{summary}' ended but waiting for recording buffer...")
                continue

            session_number = extract_session_number(summary)
            log(f"Session ended: {summary} (User {session_number})")

            # Trigger Video Sync
            if trigger_video_sync(project_id):
                processed[event_id] = {
                    "summary": summary,
                    "session": session_number,
                    "processed_at": now.isoformat()
                }
                if slack_token:
                    send_slack_notification(slack_token, project_name, session_number)

    # Clean up old processed events (keep last 50)
    if len(processed) > 50:
        sorted_events = sorted(processed.items(), key=lambda x: x[1].get("processed_at", ""), reverse=True)
        processed = dict(sorted_events[:50])

    state["processed_events"] = processed
    return state


def run_daemon():
    """Run the calendar monitor daemon."""
    log("Starting Calendar Monitor daemon...")

    config = load_config()
    if not config:
        log("ERROR: Config not found")
        sys.exit(1)

    state = load_state()
    log(f"Check interval: {CHECK_INTERVAL} seconds")
    log(f"Recording buffer: {RECORDING_BUFFER} seconds")

    try:
        while True:
            try:
                access_token = load_google_token()
                if access_token:
                    config = load_config()
                    state = process_events(access_token, config, state)
                    save_state(state)
                else:
                    log("No valid Google token, skipping...")
            except Exception as e:
                log(f"Error: {e}")

            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        log("Shutting down...")
        save_state(state)


def run_once():
    """Run a single check."""
    log("Running single calendar check...")

    access_token = load_google_token()
    if not access_token:
        log("ERROR: No valid Google token")
        return 1

    config = load_config()
    if not config:
        log("ERROR: Config not found")
        return 1

    state = load_state()
    state = process_events(access_token, config, state)
    save_state(state)

    log("Check complete")
    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Calendar Monitor for Video Sync")
    parser.add_argument("command", nargs="?", default="daemon",
                       choices=["daemon", "check", "status"],
                       help="Command: daemon (continuous), check (once), status")

    args = parser.parse_args()

    if args.command == "daemon":
        run_daemon()
    elif args.command == "check":
        sys.exit(run_once())
    elif args.command == "status":
        state = load_state()
        print(json.dumps(state, indent=2))
