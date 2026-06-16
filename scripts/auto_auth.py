#!/usr/bin/env python3
"""
Auto Auth - Automatically refresh Google OAuth tokens on project startup
Run this at the start of any session to ensure tokens are valid.
"""

import json
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import requests

TOKEN_FILE = Path.home() / ".sidekick/sidekick/.claude/skills/google-oauth-token/.session/young.kim_oauth_token.json"
OAUTH_SKILL_DIR = Path.home() / ".sidekick/sidekick/.claude/skills/google-oauth-token"

REQUIRED_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def check_token():
    """Check if token exists and is valid."""
    if not TOKEN_FILE.exists():
        return False, "Token file not found"

    try:
        with open(TOKEN_FILE) as f:
            token_data = json.load(f)
    except json.JSONDecodeError:
        return False, "Invalid token file format"

    # Check required fields
    required_fields = ["access_token", "refresh_token", "client_id", "client_secret", "token_expiry"]
    for field in required_fields:
        if field not in token_data:
            return False, f"Missing field: {field}"

    # Check scopes
    token_scopes = set(token_data.get("scopes", []))
    missing_scopes = set(REQUIRED_SCOPES) - token_scopes
    if missing_scopes:
        return False, f"Missing scopes: {missing_scopes}"

    return True, token_data


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
        return False, f"Refresh failed: {response.text}"

    new_token = response.json()
    token_data["access_token"] = new_token["access_token"]
    token_data["token_expiry"] = (datetime.now() + timedelta(seconds=new_token["expires_in"])).isoformat()

    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    return True, "Token refreshed successfully"


def test_api_access(access_token):
    """Test if the token works with Google APIs."""
    # Test Sheets API
    response = requests.get(
        "https://sheets.googleapis.com/v4/spreadsheets/1BeJXx01MrayqJM7x6bAnMg2cqb13nDQN-5l0JlKCpI8?fields=spreadsheetId",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if response.status_code != 200:
        return False, "Sheets API test failed"

    # Test Drive API
    response = requests.get(
        "https://www.googleapis.com/drive/v3/about?fields=user",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if response.status_code != 200:
        return False, "Drive API test failed"

    return True, "API access verified"


def run_oauth_flow():
    """Run the OAuth flow to get new tokens."""
    print("\n[Auto OAuth] 새로운 인증이 필요합니다.")
    print("브라우저에서 Google 계정으로 로그인하세요.\n")

    try:
        result = subprocess.run(
            ["uv", "run", "python", "scripts/main.py", "--scopes", "drive", "sheets", "calendar", "gmail"],
            cwd=OAUTH_SKILL_DIR,
            capture_output=False,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"OAuth flow failed: {e}")
        return False


def main():
    print(f"\n{'='*60}")
    print("Auto Auth - Google OAuth Token Check")
    print(f"{'='*60}\n")

    # Step 1: Check token exists and has required fields
    print("[1/3] Checking token file...")
    valid, result = check_token()

    if not valid:
        print(f"  ❌ {result}")
        print("\n  Running OAuth flow to get new tokens...")
        if run_oauth_flow():
            print("  ✅ New tokens obtained")
            valid, result = check_token()
        else:
            print("  ❌ OAuth flow failed")
            return 1

    token_data = result
    print("  ✅ Token file valid")

    # Step 2: Check if token is expired and refresh if needed
    print("\n[2/3] Checking token expiry...")
    expiry = datetime.fromisoformat(token_data["token_expiry"])
    now = datetime.now()

    if now > expiry - timedelta(minutes=5):
        print("  ⚠️  Token expired or expiring soon, refreshing...")
        success, message = refresh_token(token_data)
        if success:
            print(f"  ✅ {message}")
            # Reload token data
            with open(TOKEN_FILE) as f:
                token_data = json.load(f)
        else:
            print(f"  ❌ {message}")
            print("\n  Running OAuth flow to get new tokens...")
            if run_oauth_flow():
                print("  ✅ New tokens obtained")
            else:
                return 1
    else:
        remaining = expiry - now
        print(f"  ✅ Token valid (expires in {remaining.seconds // 60} minutes)")

    # Step 3: Test API access
    print("\n[3/3] Testing API access...")
    success, message = test_api_access(token_data["access_token"])
    if success:
        print(f"  ✅ {message}")
    else:
        print(f"  ❌ {message}")
        print("  Trying to refresh token...")
        success, _ = refresh_token(token_data)
        if success:
            with open(TOKEN_FILE) as f:
                token_data = json.load(f)
            success, message = test_api_access(token_data["access_token"])
            if success:
                print(f"  ✅ {message}")
            else:
                print(f"  ❌ API access still failing")
                return 1

    print(f"\n{'='*60}")
    print("✅ Google OAuth 인증 완료!")
    print("   PaymentSync, VideoSync 사용 가능")
    print(f"{'='*60}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
