#!/bin/bash
# Run Calendar Monitor daemon in background

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$PROJECT_DIR/logs/calendar_monitor.log"
PID_FILE="$PROJECT_DIR/logs/calendar_monitor.pid"

mkdir -p "$PROJECT_DIR/logs"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Calendar Monitor is already running (PID: $PID)"
        exit 1
    fi
fi

echo "Starting Calendar Monitor..."
cd "$PROJECT_DIR"

nohup uv run python scripts/calendar_monitor.py daemon >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

echo "Calendar Monitor started (PID: $(cat $PID_FILE))"
echo "Log: $LOG_FILE"
