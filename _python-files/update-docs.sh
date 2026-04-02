#!/bin/bash

set -e

echo "=== Updating AI Documentation ==="
echo ""

# React docs
echo "[1/4] Pulling latest React docs..."
git -C /mnt/storage/docs/frameworks/react-docs pull --ff-only
echo ""

# React Native docs
echo "[2/4] Pulling latest React Native docs..."
git -C /mnt/storage/docs/frameworks/react-native-docs pull --ff-only
echo ""

# Cesium npm package
echo "[3/5] Updating Cesium npm package..."
npm install --prefix /mnt/storage/docs/frameworks/cesium cesium@latest
echo ""

# JUCE headers
echo "[4/6] Pulling latest JUCE headers..."
git -C /mnt/storage/docs/frameworks/juce-docs pull --ff-only
echo ""

# Cmajor docs, headers and stdlib
echo "[5/6] Pulling latest Cmajor docs..."
git -C /mnt/storage/docs/frameworks/cmajor-docs pull --ff-only
echo ""

# Electron docs
echo "[6/8] Pulling latest Electron docs..."
git -C /mnt/storage/docs/frameworks/electron-docs pull --ff-only
echo ""

# electron-react-boilerplate
echo "[7/8] Pulling latest electron-react-boilerplate..."
git -C /mnt/storage/docs/frameworks/electron-react-boilerplate pull --ff-only
echo ""

# TypeScript docs
echo "[8/9] Pulling latest TypeScript docs..."
git -C /mnt/storage/docs/frameworks/typescript-docs pull --ff-only
echo ""

# Re-index changed docs
echo "[9/9] Re-indexing docs (changed files only)..."
/mnt/storage/mcp-tools/.venv/bin/python /mnt/storage/mcp-tools/index_docs.py
echo ""

echo "=== All docs updated ==="
