#!/usr/bin/env bash
# install.sh — One-liner setup for mi-unlock-blaster
# Usage: bash install.sh

set -e

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║        🔓  MI UNLOCK BLASTER — Installer                ║"
echo "║        github.com/whitedevil0420/mi-unlock-blaster      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check Python 3
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] Python 3 not found. Install it first."
    exit 1
fi

PY=$(python3 --version 2>&1)
echo "[*] Found: $PY"

# Install dependencies
echo "[*] Installing dependencies..."
pip install -r requirements.txt

# Install package in editable mode
echo "[*] Installing mi-unlock-blaster..."
pip install -e .

echo ""
echo "✅  Done! Run the tool with:"
echo "       mi-unlock-blaster"
echo "   OR:"
echo "       python3 -m mi_unlock_blaster.main"
echo ""
