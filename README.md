# 🎬 Video & Audio Merger - Python GUI for Ubuntu (FFmpeg)

A complete, modern desktop GUI application designed for Ubuntu Linux that eliminates the need to remember complex `ffmpeg` terminal syntax. Easily merge, mix, replace, and sync video and audio with a clean, native interface.

![Video & Audio Merger Icon](assets/icon_64.png)

---

## ✨ Features

- **Automatic FFmpeg Detection & Friendly Prompt**:
  - Automatically checks if `ffmpeg` and `ffprobe` are installed on your Ubuntu system.
  - If missing, displays a prominent alert banner and dialog prompting you with the exact installation command (`sudo apt update && sudo apt install -y ffmpeg`).
  - Includes a one-click **"📋 Copy Install Command"** button, **"🔄 Check Again"** refresh button, and a **"📁 Browse Binary"** option for custom/portable FFmpeg builds.
- **Emulates All Common FFmpeg Merge Operations**:
  - **Replace Audio**: Mutes existing video audio and attaches your new audio track (`-map 0:v:0 -map 1:a:0`).
  - **Mix Audio (Background Music / Voiceover)**: Blends existing video audio with new background music, complete with independent volume sliders (`0% - 200%`) using FFmpeg's `amix` filter.
  - **Multi-Track Audio (Dual / Multi-Language)**: Keeps original audio as Track 1 and adds the new audio file as a selectable secondary audio stream (e.g. commentary or language dubs in VLC).
  - **Add Audio to Silent Video**: Attaches an audio soundtrack to silent videos.
  - **Still Image + Audio**: Creates a video slideshow/podcast video from a static picture + audio track (`-loop 1`).
  - **Extract Audio**: Rips audio directly from video files without re-encoding or transcoded to MP3/AAC/FLAC.
- **Timing, Duration & Audio Sync**:
  - **Duration Modes**: Shortest stream (`-shortest`), Match Video Duration, Keep Longest, or Custom Trim.
  - **Audio Sync Offset**: Fix out-of-sync audio with a millisecond delay spinner (e.g., `+500ms` or `-250ms`).
  - **Seamless Audio Looping**: Repeat shorter audio tracks to match video length (`-stream_loop -1`).
  - **Custom Trim**: Specify Start Time (`HH:MM:SS`) and End Time.
- **Audio & Video Codec Controls**:
  - **Video Codecs**: Stream Copy (`-c:v copy`, lossless & instant), H.264/AVC (`libx264`), H.265/HEVC (`libx265`), VP9 (`libvpx-vp9`), AV1 (`libsvtav1`).
  - **Presets & CRF**: Adjustable CRF quality (18-28) and speed presets (`ultrafast` to `veryslow`).
  - **Audio Codecs**: AAC, Stream Copy, MP3, Opus, FLAC, AC3, WAV/PCM.
  - **Audio Bitrates**: 96k, 128k, 192k (HQ), 256k, 320k.
  - **Channels & Sample Rates**: Stereo (2.0), Mono (1.0), 5.1 Surround; 44100 Hz, 48000 Hz, 96000 Hz.
  - **Web Faststart**: Automatically enables `-movflags +faststart` for MP4/MOV streaming.
- **Live FFmpeg Terminal Command Display**:
  - Real-time command preview box showing the exact shell command being constructed as you change options.
  - **"📋 Copy Command"** button to copy the command directly to your clipboard.
  - Extra arguments field to pass custom flags.
- **Non-Freezing Execution & Progress Reporting**:
  - Multithreaded background processing prevents GUI freezing.
  - Dynamic progress bar (`0% - 100%`), speed multiplier (`3.5x`), and elapsed time.
  - Live console output viewer with auto-scroll.
  - Clean cancel/stop button with process termination.
  - Post-merge dialog to immediately **"Open File"** or **"Open Folder"** in Ubuntu Nautilus.
- **Drag & Drop and File Browsers**:
  - Drag and drop video and audio files directly onto the window.
  - Native GTK3 file choosers with filter presets.
  - One-click **"⚡ Video Folder"** button to save output alongside the source file.

---

## 🚀 Quick Start on Ubuntu

### 1. Requirements

Ensure Python 3 is installed:
```bash
sudo apt update
sudo apt install -y python3 python3-wxgtk4.0 ffmpeg
```

> **Note:** If `ffmpeg` is not yet installed, the app will launch and prompt you with an interactive dialog and copyable installation command.

### 2. Run the App

From the project directory:
```bash
./run.sh
```
Or directly via Python:
```bash
python3 main.py
```

### 3. Add to Ubuntu Application Menu & Desktop

To add the app to your Ubuntu Dash / Application menu and desktop:
```bash
./setup_desktop.sh
```
Or copy `video-audio-merger.desktop` to `~/.local/share/applications/`.

---

## 🖥️ Command-Line Options

```bash
# Launch GUI (auto-detects native GTK / wxPython or Tkinter)
python3 main.py

# Launch specifically with wxPython
python3 main.py --gui wx

# Launch with Tkinter fallback
python3 main.py --gui tk

# Check FFmpeg and FFprobe installation status from terminal
python3 main.py --check-ffmpeg

# Display installation instructions
python3 main.py --install-help
```

---

## 📁 Project Structure

```
video-audio-merger/
├── main.py                     # Main CLI and GUI launcher
├── run.sh                      # Shell launch script
├── setup_desktop.sh            # Ubuntu desktop and application menu installer
├── video-audio-merger.desktop  # Desktop entry file
├── requirements.txt            # Package requirements
├── README.md                   # Documentation
├── assets/
│   ├── icon.svg                # Vector app icon
│   ├── icon.png                # 256x256 application icon
│   └── icon_64.png             # 64x64 application icon
├── core/
│   ├── __init__.py
│   ├── ffmpeg_checker.py       # Detects ffmpeg & ffprobe binaries, parses versions
│   ├── media_probe.py          # Probes media metadata (duration, codecs, resolution)
│   ├── command_builder.py      # Constructs FFmpeg argument lists for all merge modes
│   └── merger_task.py          # Background process runner, parses progress and speed
└── ui/
    ├── __init__.py
    ├── wx_app.py               # Native GTK3 / wxPython graphical application
    ├── tk_app.py               # Tkinter GUI fallback implementation
    └── theme.py                # Ubuntu Yaru palette & styling constants
```

---

## 🛠️ Common FFmpeg Commands Emulated

| Task | GUI Selection | Equivalent FFmpeg Terminal Command |
|------|---------------|-----------------------------------|
| **Replace Audio** | Mode: `Replace Audio` | `ffmpeg -i video.mp4 -i audio.mp3 -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -shortest out.mp4` |
| **Mix Audio** | Mode: `Mix Audio` | `ffmpeg -i video.mp4 -i audio.mp3 -filter_complex "[0:a]volume=1.0[a0];[1:a]volume=0.5[a1];[a0][a1]amix=inputs=2:duration=first[aout]" -map 0:v:0 -map "[aout]" -c:v copy -c:a aac out.mp4` |
| **Dual Audio Track** | Mode: `Multi-Track` | `ffmpeg -i video.mp4 -i audio.mp3 -map 0:v:0 -map 0:a? -map 1:a:0 -metadata:s:a:1 title="Secondary Track" -c:v copy -c:a copy out.mkv` |
| **Audio to Silent** | Mode: `Add to Silent Video` | `ffmpeg -i silent.mp4 -i audio.mp3 -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac out.mp4` |
| **Picture + Audio** | Mode: `Image + Audio` | `ffmpeg -loop 1 -i cover.jpg -i music.mp3 -c:v libx264 -tune stillimage -pix_fmt yuv420p -c:a aac -shortest out.mp4` |
| **Extract Audio** | Mode: `Extract Audio` | `ffmpeg -i video.mp4 -vn -c:a copy out.mp3` |
| **Audio Sync Fix** | Delay: `+500 ms` | Adds `-itsoffset 0.500 -i audio.mp3` or `adelay` filter |
| **Loop Short Audio** | Checkbox: `Loop Audio` | Adds `-stream_loop -1 -i audio.mp3` |
