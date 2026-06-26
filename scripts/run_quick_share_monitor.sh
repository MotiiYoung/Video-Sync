#!/bin/bash
# Run Video Sync Quick Share Monitor daemon in background

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/logs/quick_share_monitor.log"
PID_FILE="$PROJECT_DIR/logs/quick_share_monitor.pid"

mkdir -p "$PROJECT_DIR/logs"

# Check if already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Video Sync Quick Share Monitor is already running (PID: $PID)"
        exit 1
    fi
fi

echo "Starting Video Sync Quick Share Monitor..."
cd "$PROJECT_DIR"

nohup uv run python scripts/quick_share_monitor.py daemon >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

echo "Video Sync Quick Share Monitor started (PID: $(cat $PID_FILE))"
echo "Log: $LOG_FILE"
