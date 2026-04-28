#!/bin/bash
# Start the LLM proxy and the LLM monitor frontend

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[start-all] Starting proxy..."
cd /mnt/storage/mcp-tools
.venv/bin/python proxy.py &
PROXY_PID=$!
echo "[start-all] Proxy started (PID $PROXY_PID)"

echo "[start-all] Starting LLM monitor..."
cd "$REPO_DIR/frontend-llmmonitor"
npm run dev &
MONITOR_PID=$!
echo "[start-all] Monitor started (PID $MONITOR_PID) — http://localhost:3333"

echo "[start-all] Both services running. Press Ctrl+C to stop."

trap "echo '[start-all] Stopping...'; kill $PROXY_PID $MONITOR_PID 2>/dev/null" SIGINT SIGTERM

wait
