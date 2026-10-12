#!/usr/bin/env bash
# setup_desktop.sh - Installs Ubuntu Desktop Shortcut and Application Menu Entry

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ICON_PATH="$SCRIPT_DIR/assets/icon.png"
EXEC_PATH="$SCRIPT_DIR/run.sh"

APP_DIR="$HOME/.local/share/applications"
DESKTOP_DIR="$HOME/Desktop"

mkdir -p "$APP_DIR"

DESKTOP_ENTRY="[Desktop Entry]
Version=1.0
Type=Application
Name=Video & Audio Merger
GenericName=FFmpeg Media Merger
Comment=Merge video and audio streams with graphical interface
Exec=\"$EXEC_PATH\" %F
Icon=$ICON_PATH
Terminal=false
Categories=AudioVideo;Video;Audio;AudioVideoEditing;
Keywords=ffmpeg;video;audio;merge;mux;muxer;join;
StartupNotify=true
MimeType=video/mp4;video/x-matroska;video/quicktime;video/webm;audio/mpeg;audio/aac;audio/flac;
"

# 1. Install to Application Launcher (~/.local/share/applications)
echo "$DESKTOP_ENTRY" > "$APP_DIR/video-audio-merger.desktop"
chmod +x "$APP_DIR/video-audio-merger.desktop"
echo "✔ Created application menu entry: $APP_DIR/video-audio-merger.desktop"

# 2. Install to Desktop if Desktop folder exists
if [ -d "$DESKTOP_DIR" ]; then
    echo "$DESKTOP_ENTRY" > "$DESKTOP_DIR/video-audio-merger.desktop"
    chmod +x "$DESKTOP_DIR/video-audio-merger.desktop"
    # Mark as trusted for GNOME / Ubuntu Desktop if gio is available
    if command -v gio &>/dev/null; then
        gio set "$DESKTOP_DIR/video-audio-merger.desktop" metadata::trusted true 2>/dev/null || true
    fi
    echo "✔ Created desktop shortcut: $DESKTOP_DIR/video-audio-merger.desktop"
fi

# 3. Update desktop database if available
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$APP_DIR" 2>/dev/null || true
fi

echo "Desktop installation complete! You can now launch 'Video & Audio Merger' from your Ubuntu application menu or desktop."
