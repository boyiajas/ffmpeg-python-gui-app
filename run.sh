#!/usr/bin/env bash
# Video & Audio Merger - Desktop Application Launcher for Ubuntu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check Python 3
if ! command -v python3 &>/dev/null; then
    echo "Error: Python 3 is not installed. Please install it with 'sudo apt install python3'."
    exit 1
fi

# Run Main Application
exec python3 "$SCRIPT_DIR/main.py" "$@"
