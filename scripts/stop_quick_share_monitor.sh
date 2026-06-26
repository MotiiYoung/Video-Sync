#!/bin/bash
# Stop Video Sync Quick Share Monitor daemon

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_DIR/logs/quick_share_monitor.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "Video Sync Quick Share Monitor is not running (no PID file)"
    exit 0
fi

PID=$(cat "$PID_FILE")

if ps -p "$PID" > /dev/null 2>&1; then
    echo "Stopping Video Sync Quick Share Monitor (PID: $PID)..."
    kill "$PID"
    rm -f "$PID_FILE"
    echo "Stopped"
else
    echo "Video Sync Quick Share Monitor is not running (stale PID file)"
    rm -f "$PID_FILE"
fi
