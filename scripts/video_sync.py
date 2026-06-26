#!/usr/bin/env python3
"""
Video Sync - Find Google Meet recordings, move to project folder, and sync links
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import requests

# Slack notification config
SLACK_CHANNEL = "C0BBQNNAEV8"
SLACK_TOKEN_FILE = Path.home() / ".sidekick/.env"


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


def send_slack_notification(project_name, video_count, folder_url):
    """Send completion notification to Slack."""
    token = get_slack_token()
    if not token:
        print("  Slack token not found, skipping notification")
        return False

    message = {
        "channel": SLACK_CHANNEL,
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🎬 *Video Sync 완료*\n• 프로젝트: {project_name}\n• 이동된 영상: {video_count}개\n• 폴더: <{folder_url}|[Recording] {project_name}>"
                }
            }
        ],
        "text": f"Video Sync 완료 - {project_name}"
    }

    response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json=message
    )

    if response.status_code == 200 and response.json().get("ok"):
        print("  Slack notification sent")
        return True
    else:
        print(f"  Slack notification failed: {response.text}")
        return False

# Paths
SCRIPT_DIR = Path(__file__).parent
CONFIG_DIR = SCRIPT_DIR.parent / "config"
PROJECTS_FILE = CONFIG_DIR / "projects.json"
TOKEN_FILE = Path.home() / ".sidekick/sidekick/.claude/skills/google-oauth-token/.session/young.kim_oauth_token.json"


def load_config():
    """Load projects configuration."""
    if not PROJECTS_FILE.exists():
        print(f"Error: Config file not found at {PROJECTS_FILE}")
        sys.exit(1)

    with open(PROJECTS_FILE) as f:
        return json.load(f)


def load_token():
    """Load and refresh OAuth token if needed."""
    if not TOKEN_FILE.exists():
        print(f"Error: Token file not found at {TOKEN_FILE}")
        print("\n[Auto OAuth] 토큰 파일이 없습니다. 다음 명령으로 인증하세요:")
        print("  cd ~/.sidekick/sidekick/.claude/skills/google-oauth-token")
        print("  uv run python scripts/main.py --scopes drive sheets calendar")
        sys.exit(1)

    with open(TOKEN_FILE) as f:
        token_data = json.load(f)

    expiry = datetime.fromisoformat(token_data["token_expiry"])
    if datetime.now() > expiry - timedelta(minutes=5):
        print("Access token expired, refreshing...")
        token_data = refresh_token(token_data)

    return token_data["access_token"]


def refresh_token(token_data):
    """Refresh the access token."""
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": token_data["client_id"],
            "client_secret": token_data["client_secret"],
            "refresh_token": token_data["refresh_token"],
            "grant_type": "refresh_token",
        }
    )

    if response.status_code != 200:
        print(f"Failed to refresh token: {response.text}")
        print("\n[Auto OAuth] 토큰 갱신 실패. 다음 명령으로 재인증하세요:")
        print("  cd ~/.sidekick/sidekick/.claude/skills/google-oauth-token")
        print("  uv run python scripts/main.py --scopes drive sheets calendar")
        sys.exit(1)

    new_token = response.json()
    token_data["access_token"] = new_token["access_token"]
    token_data["token_expiry"] = (datetime.now() + timedelta(seconds=new_token["expires_in"])).isoformat()

    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    print("Token refreshed successfully.")
    return token_data


def search_meet_recordings(access_token, project_keywords):
    """Search for Google Meet recordings in user's Drive."""
    # Google Meet recordings are typically named like "Meeting Recording" or have specific patterns
    # They're also in a "Meet Recordings" folder

    queries = []

    # Search for recordings with project keywords
    for keyword in project_keywords:
        queries.append(f"name contains '{keyword}' and mimeType='video/mp4'")

    # Also search in Meet Recordings folder
    queries.append("name contains 'Recording' and mimeType='video/mp4'")

    all_files = []
    seen_ids = set()

    for query in queries:
        url = "https://www.googleapis.com/drive/v3/files"
        params = {
            "q": query,
            "fields": "files(id,name,mimeType,webViewLink,parents,createdTime)",
            "orderBy": "createdTime desc",
            "pageSize": 50,
        }

        response = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, params=params)

        if response.status_code == 200:
            for f in response.json().get("files", []):
                if f["id"] not in seen_ids:
                    seen_ids.add(f["id"])
                    all_files.append(f)

    return all_files


def get_drive_files(access_token, folder_id):
    """List files in a Google Drive folder."""
    url = "https://www.googleapis.com/drive/v3/files"
    params = {
        "q": f"'{folder_id}' in parents",
        "fields": "files(id,name,mimeType,webViewLink)",
    }

    response = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, params=params)

    if response.status_code != 200:
        print(f"Failed to list drive files: {response.text}")
        return []

    return response.json().get("files", [])


def move_file_to_folder(access_token, file_id, target_folder_id, current_parents):
    """Move a file to a different folder."""
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
    params = {
        "addParents": target_folder_id,
        "removeParents": ",".join(current_parents) if current_parents else "",
    }

    response = requests.patch(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        params=params,
    )

    return response.status_code == 200


def extract_session_number(filename):
    """Extract session number from filename."""
    match = re.search(r'(\d+)(?:st|nd|rd|th)', filename, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def get_spreadsheet_sheets(access_token, spreadsheet_id):
    """Get list of sheets in a spreadsheet."""
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}?fields=sheets.properties"
    response = requests.get(url, headers={"Authorization": f"Bearer {access_token}"})

    if response.status_code != 200:
        return []

    return response.json().get("sheets", [])


def get_sheet_data(access_token, spreadsheet_id, sheet_name, range_notation):
    """Get data from a sheet."""
    encoded_sheet = quote(sheet_name, safe='')
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{encoded_sheet}!{range_notation}"
    response = requests.get(url, headers={"Authorization": f"Bearer {access_token}"})

    if response.status_code != 200:
        return []

    return response.json().get("values", [])


def update_cell_formula(access_token, spreadsheet_id, sheet_name, range_notation, formula):
    """Update a cell with a formula."""
    encoded_sheet = quote(sheet_name, safe='')
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{encoded_sheet}!{range_notation}?valueInputOption=USER_ENTERED"

    response = requests.put(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        json={"values": [[formula]]}
    )

    return response.status_code == 200


def extract_user_number(tab_name):
    """Extract user number from tab name."""
    match = re.search(r'User(\d+)', tab_name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def find_and_move_command(args):
    """Find Google Meet recordings and move to project folder."""
    config = load_config()

    project_id = args.project or config.get("default_project")
    if not project_id or project_id not in config["projects"]:
        print(f"Error: Project '{project_id}' not found.")
        return 1

    project = config["projects"][project_id]

    print(f"\n{'='*60}")
    print(f"Find & Move Recordings - {project['name']}")
    print(f"{'='*60}\n")

    video_folder_id = project.get("video_folder_id")
    if not video_folder_id:
        print("Error: No video folder configured for this project.")
        print("Add 'video_folder_id' to config/projects.json")
        return 1

    access_token = load_token()

    # Search for recordings
    keywords = project.get("calendar_keywords", ["UT", "User Research"])
    print(f"Searching for recordings with keywords: {keywords}")

    recordings = search_meet_recordings(access_token, keywords)

    if not recordings:
        print("No recordings found.")
        return 0

    print(f"Found {len(recordings)} potential recordings:\n")

    # Get files already in target folder
    existing_files = get_drive_files(access_token, video_folder_id)
    existing_names = {f["name"] for f in existing_files}

    to_move = []
    for rec in recordings:
        status = "✅ Already in folder" if rec["name"] in existing_names else "📁 Will move"
        in_folder = rec["name"] in existing_names

        # Check if already in target folder
        if video_folder_id in rec.get("parents", []):
            status = "✅ Already in folder"
            in_folder = True

        print(f"  [{extract_session_number(rec['name']) or '?'}] {rec['name'][:50]}...")
        print(f"      {status}")

        if not in_folder:
            to_move.append(rec)

    if not to_move:
        print("\nAll recordings are already in the project folder.")
        return 0

    print(f"\n{len(to_move)} file(s) to move.")

    if args.dry_run:
        print("\n[DRY RUN] No files moved.")
        return 0

    # Move files
    print("\nMoving files...")
    moved = 0
    for rec in to_move:
        if move_file_to_folder(access_token, rec["id"], video_folder_id, rec.get("parents", [])):
            print(f"  ✅ Moved: {rec['name'][:40]}...")
            moved += 1
        else:
            print(f"  ❌ Failed: {rec['name'][:40]}...")

    print(f"\nMoved {moved}/{len(to_move)} files.")
    return 0


def sync_videos(args):
    """Sync recorded video links from Google Drive to Observation Sheet."""
    config = load_config()

    project_id = args.project or config.get("default_project")
    if not project_id or project_id not in config["projects"]:
        print(f"Error: Project '{project_id}' not found.")
        return 1

    project = config["projects"][project_id]

    print(f"\n{'='*60}")
    print(f"Video Sync - {project['name']}")
    print(f"{'='*60}\n")

    video_folder_id = project.get("video_folder_id")
    if not video_folder_id:
        if args.folder:
            if "folders/" in args.folder:
                video_folder_id = args.folder.split("folders/")[1].split("?")[0].split("/")[0]
            else:
                video_folder_id = args.folder
        else:
            print("Error: No video folder configured.")
            print("Use --folder to specify Google Drive folder URL or ID")
            return 1

    access_token = load_token()

    # Get video files from Drive
    print("Getting video files from Google Drive...")
    video_files = get_drive_files(access_token, video_folder_id)

    if not video_files:
        print("No video files found in the folder.")
        return 1

    print(f"Found {len(video_files)} video files")

    # Create mapping: session number -> video info
    video_mapping = {}
    for f in video_files:
        session_num = extract_session_number(f["name"])
        if session_num:
            name = f["name"].replace(" – Recording", "").replace(" - Recording", "").strip()
            name = re.sub(r'(\d{4})/(\d{2})/(\d{2})', r'\1/\2/\3', name)

            video_mapping[session_num] = {
                "name": name,
                "link": f"https://drive.google.com/file/d/{f['id']}/view",
            }

    print(f"Mapped {len(video_mapping)} videos to sessions")

    # Get Observation Sheet tabs
    obs_config = project["observation_sheet"]
    spreadsheet_id = obs_config["spreadsheet_id"]

    sheets = get_spreadsheet_sheets(access_token, spreadsheet_id)

    user_tabs = []
    for sheet in sheets:
        title = sheet["properties"]["title"]
        user_num = extract_user_number(title)
        if user_num is not None:
            user_tabs.append({"title": title, "user_num": user_num})

    print(f"Found {len(user_tabs)} user tabs\n")

    # Update each user tab
    updated = 0
    for tab in sorted(user_tabs, key=lambda x: x["user_num"]):
        user_num = tab["user_num"]
        tab_title = tab["title"]

        if user_num not in video_mapping:
            print(f"  User {user_num}: No video found")
            continue

        video = video_mapping[user_num]

        # Find "Recorded Video" row
        data = get_sheet_data(access_token, spreadsheet_id, tab_title, "E1:F20")

        video_row = None
        for i, row in enumerate(data):
            if row and "Recorded Video" in row[0]:
                video_row = i + 1
                break

        if not video_row:
            print(f"  User {user_num}: 'Recorded Video' field not found")
            continue

        formula = f'=HYPERLINK("{video["link"]}", "{video["name"]}")'

        if args.dry_run:
            print(f"  User {user_num}: Would update -> {video['name'][:40]}...")
        else:
            if update_cell_formula(access_token, spreadsheet_id, tab_title, f"F{video_row}", formula):
                print(f"  User {user_num}: ✅ {video['name'][:40]}...")
                updated += 1
            else:
                print(f"  User {user_num}: ❌ Failed")

    print(f"\n{'='*60}")
    if args.dry_run:
        print(f"[DRY RUN] Would update {len(video_mapping)} videos")
    else:
        print(f"Updated {updated}/{len(video_mapping)} video links")
    print(f"{'='*60}")

    return 0


def list_videos(args):
    """List video files in the configured Google Drive folder."""
    config = load_config()

    project_id = args.project or config.get("default_project")
    if not project_id or project_id not in config["projects"]:
        print(f"Error: Project '{project_id}' not found.")
        return 1

    project = config["projects"][project_id]
    video_folder_id = project.get("video_folder_id")

    if not video_folder_id:
        if args.folder:
            if "folders/" in args.folder:
                video_folder_id = args.folder.split("folders/")[1].split("?")[0].split("/")[0]
            else:
                video_folder_id = args.folder
        else:
            print("Error: No video folder configured. Use --folder to specify.")
            return 1

    access_token = load_token()

    print(f"\n{'='*60}")
    print(f"Video Files in Google Drive")
    print(f"{'='*60}\n")

    video_files = get_drive_files(access_token, video_folder_id)

    for f in sorted(video_files, key=lambda x: extract_session_number(x["name"]) or 0):
        session_num = extract_session_number(f["name"])
        print(f"  [{session_num or '?'}] {f['name']}")

    print(f"\nTotal: {len(video_files)} files")
    return 0


def full_sync(args):
    """Full sync: Find recordings, move to folder, then sync links."""
    config = load_config()
    project_id = args.project or config.get("default_project")
    project = config["projects"].get(project_id, {})

    print(f"\n{'='*60}")
    print("Full Video Sync")
    print(f"{'='*60}")

    # Step 1: Find and move
    print("\n[Step 1/2] Finding and moving recordings...")
    args_copy = argparse.Namespace(**vars(args))
    find_and_move_command(args_copy)

    # Step 2: Sync links
    print("\n[Step 2/2] Syncing video links...")
    sync_videos(args_copy)

    print(f"\n{'='*60}")
    print("Full sync complete!")
    print(f"{'='*60}")

    # Send Slack notification
    if not args.dry_run:
        video_folder_id = project.get("video_folder_id", "")
        folder_url = f"https://drive.google.com/drive/folders/{video_folder_id}"
        video_files = get_drive_files(load_token(), video_folder_id) if video_folder_id else []
        send_slack_notification(project.get("name", project_id), len(video_files), folder_url)

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Video Sync - Manage recorded video links"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Full sync command (find, move, sync)
    full_parser = subparsers.add_parser("full", help="Full sync: find, move, and sync")
    full_parser.add_argument("--project", "-p", help="Project ID")
    full_parser.add_argument("--dry-run", action="store_true", help="Preview without applying")
    full_parser.set_defaults(func=full_sync)

    # Find and move command
    find_parser = subparsers.add_parser("find", help="Find Meet recordings and move to project folder")
    find_parser.add_argument("--project", "-p", help="Project ID")
    find_parser.add_argument("--dry-run", action="store_true", help="Preview without moving")
    find_parser.set_defaults(func=find_and_move_command)

    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Sync video links to Observation Sheet")
    sync_parser.add_argument("--project", "-p", help="Project ID")
    sync_parser.add_argument("--folder", "-f", help="Google Drive folder URL or ID")
    sync_parser.add_argument("--dry-run", action="store_true", help="Preview without applying")
    sync_parser.set_defaults(func=sync_videos)

    # List command
    list_parser = subparsers.add_parser("list", help="List video files in folder")
    list_parser.add_argument("--project", "-p", help="Project ID")
    list_parser.add_argument("--folder", "-f", help="Google Drive folder URL or ID")
    list_parser.set_defaults(func=list_videos)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
