#!/usr/bin/env python3
"""
Video & Audio Merger - Python GUI Application for FFmpeg
A modern, native desktop application for Ubuntu to merge, mix, and process
video and audio streams without writing terminal commands.
"""

import sys
import argparse
import os

from core.ffmpeg_checker import FFmpegChecker


def print_banner():
    print("=" * 64)
    print("       Video & Audio Merger - FFmpeg Desktop GUI for Ubuntu")
    print("=" * 64)


def print_ffmpeg_status():
    status = FFmpegChecker.check_system()
    if status["installed"]:
        print(f"✔ FFmpeg: DETECTED ({status['ffmpeg_path']})")
        print(f"  Version: {status['version']}")
        if status["ffprobe_installed"]:
            print(f"✔ FFprobe: DETECTED ({status['ffprobe_path']})")
        else:
            print("ℹ FFprobe: Not found (FFmpeg fallback mode active)")
    else:
        print("✘ FFmpeg: NOT DETECTED on your system!")
        print("  FFmpeg is required to merge and process media files.")
        print("\n  To install FFmpeg on Ubuntu, run:")
        print(f"    {status['ubuntu_install_cmd']}")
        print(f"  Or via Snap:\n    {status['snap_install_cmd']}")
    print("-" * 64)


def main():
    parser = argparse.ArgumentParser(description="Video & Audio Merger GUI for Ubuntu")
    parser.add_argument("--gui", choices=["auto", "wx", "tk"], default="auto",
                        help="GUI engine to use (default: auto)")
    parser.add_argument("--check-ffmpeg", action="store_true",
                        help="Check if FFmpeg and FFprobe are installed and exit")
    parser.add_argument("--install-help", action="store_true",
                        help="Show Ubuntu installation commands for FFmpeg")
    args = parser.parse_args()

    if args.check_ffmpeg:
        print_banner()
        print_ffmpeg_status()
        sys.exit(0)

    if args.install_help:
        print_banner()
        print("Ubuntu / Debian Installation Command:")
        print("  sudo apt update && sudo apt install -y ffmpeg\n")
        print("Snap Installation Command:")
        print("  sudo snap install ffmpeg\n")
        print("GUI Library Requirements (if needed):")
        print("  sudo apt install -y python3-wxgtk4.0 python3-tk")
        sys.exit(0)

    # Launch GUI
    # Determine which GUI backend to use
    selected_engine = args.gui

    if selected_engine == "auto":
        # Check wxPython first (native GTK3 on Ubuntu)
        try:
            import wx
            selected_engine = "wx"
        except ImportError:
            try:
                import tkinter
                selected_engine = "tk"
            except ImportError:
                selected_engine = None

    if selected_engine == "wx":
        try:
            from ui.wx_app import run_app
            run_app()
        except ImportError as e:
            print(f"Error launching wxPython GUI: {e}")
            print("Please install wxPython via: sudo apt install -y python3-wxgtk4.0")
            sys.exit(1)

    elif selected_engine == "tk":
        try:
            from ui.tk_app import run_app
            run_app()
        except Exception as e:
            print(f"Error launching Tkinter GUI: {e}")
            print("Please install python3-tk via: sudo apt install -y python3-tk")
            sys.exit(1)

    else:
        print_banner()
        print("Error: Neither wxPython nor Tkinter is installed on this Python environment.")
        print("To install wxPython (recommended for native Ubuntu GTK appearance):")
        print("  sudo apt install -y python3-wxgtk4.0\n")
        print("Or to install Tkinter:")
        print("  sudo apt install -y python3-tk\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
