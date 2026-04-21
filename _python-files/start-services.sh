#!/bin/bash

echo "=== i7 AI Services ==="

# llama-embed (embedding server on RTX 2060)
if systemctl is-active --quiet llama-embed; then
    echo "[OK] llama-embed is running"
else
    echo "[..] llama-embed not running, starting..."
    sudo systemctl start llama-embed
    sleep 3
    if systemctl is-active --quiet llama-embed; then
        echo "[OK] llama-embed started"
    else
        echo "[FAIL] llama-embed failed to start"
        systemctl status llama-embed --no-pager -l
        exit 1
    fi
fi

# Verify embedding server is actually responding
if curl -s --max-time 5 http://127.0.0.1:11435/health | grep -q "ok"; then
    echo "[OK] Embedding server responding on port 11435"
else
    echo "[FAIL] Embedding server not responding"
    exit 1
fi

# Proxy (context enrichment, reranker, auto-verify)
if curl -s --max-time 3 http://127.0.0.1:8000/v1/models > /dev/null 2>&1; then
    echo "[OK] Proxy already running on port 8000"
else
    echo "[..] Starting proxy..."
    nohup /mnt/storage/mcp-tools/.venv/bin/python /mnt/storage/mcp-tools/proxy.py \
        > /tmp/proxy.log 2>&1 &
    sleep 3
    if curl -s --max-time 3 http://127.0.0.1:8000/v1/models > /dev/null 2>&1; then
        echo "[OK] Proxy started on port 8000"
    else
        echo "[FAIL] Proxy failed to start — check /tmp/proxy.log"
        exit 1
    fi
fi

echo ""
echo "All services ready. Open VS Code — Cline will handle the rest."
echo "Proxy log: /tmp/proxy.log"
