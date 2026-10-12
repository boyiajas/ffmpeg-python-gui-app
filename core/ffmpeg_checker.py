"""
ffmpeg_checker.py - Detects FFmpeg and FFprobe on the system,
verifies executable permissions, retrieves version info, and
provides Ubuntu installation guidance if missing.
"""

import os
import shutil
import subprocess
from typing import Dict, Optional, Tuple


COMMON_LINUX_PATHS = [
    "/usr/bin/ffmpeg",
    "/usr/local/bin/ffmpeg",
    "/snap/bin/ffmpeg",
    os.path.expanduser("~/.local/bin/ffmpeg"),
    os.path.expanduser("~/bin/ffmpeg"),
    "/opt/ffmpeg/bin/ffmpeg",
    "/opt/ffmpeg/ffmpeg",
]

COMMON_FFPROBE_PATHS = [
    "/usr/bin/ffprobe",
    "/usr/local/bin/ffprobe",
    "/snap/bin/ffprobe",
    os.path.expanduser("~/.local/bin/ffprobe"),
    os.path.expanduser("~/bin/ffprobe"),
    "/opt/ffmpeg/bin/ffprobe",
    "/opt/ffmpeg/ffprobe",
]


class FFmpegChecker:
    _custom_ffmpeg_path: Optional[str] = None
    _custom_ffprobe_path: Optional[str] = None

    @classmethod
    def set_custom_paths(cls, ffmpeg_path: Optional[str] = None, ffprobe_path: Optional[str] = None):
        if ffmpeg_path and os.path.isfile(ffmpeg_path) and os.access(ffmpeg_path, os.X_OK):
            cls._custom_ffmpeg_path = os.path.abspath(ffmpeg_path)
            # Try finding ffprobe in the same directory if not specified
            if not ffprobe_path:
                probe_candidate = os.path.join(os.path.dirname(ffmpeg_path), "ffprobe")
                if os.path.isfile(probe_candidate) and os.access(probe_candidate, os.X_OK):
                    cls._custom_ffprobe_path = probe_candidate
        if ffprobe_path and os.path.isfile(ffprobe_path) and os.access(ffprobe_path, os.X_OK):
            cls._custom_ffprobe_path = os.path.abspath(ffprobe_path)

    @classmethod
    def find_ffmpeg(cls) -> Optional[str]:
        # 1. Custom path
        if cls._custom_ffmpeg_path and os.path.isfile(cls._custom_ffmpeg_path) and os.access(cls._custom_ffmpeg_path, os.X_OK):
            return cls._custom_ffmpeg_path

        # 2. PATH lookup
        path_bin = shutil.which("ffmpeg")
        if path_bin:
            return path_bin

        # 3. Known Linux locations
        for p in COMMON_LINUX_PATHS:
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p

        return None

    @classmethod
    def find_ffprobe(cls) -> Optional[str]:
        # 1. Custom path
        if cls._custom_ffprobe_path and os.path.isfile(cls._custom_ffprobe_path) and os.access(cls._custom_ffprobe_path, os.X_OK):
            return cls._custom_ffprobe_path

        # 2. Near custom ffmpeg
        if cls._custom_ffmpeg_path:
            probe_candidate = os.path.join(os.path.dirname(cls._custom_ffmpeg_path), "ffprobe")
            if os.path.isfile(probe_candidate) and os.access(probe_candidate, os.X_OK):
                return probe_candidate

        # 3. PATH lookup
        path_bin = shutil.which("ffprobe")
        if path_bin:
            return path_bin

        # 4. Known Linux locations
        for p in COMMON_FFPROBE_PATHS:
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p

        return None

    @classmethod
    def get_version(cls, binary_path: str) -> str:
        try:
            res = subprocess.run(
                [binary_path, "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
            )
            if res.returncode == 0 and res.stdout:
                first_line = res.stdout.strip().splitlines()[0]
                return first_line
        except Exception as e:
            return f"Error retrieving version: {e}"
        return "Unknown version"

    @classmethod
    def check_system(cls) -> Dict[str, any]:
        ffmpeg_bin = cls.find_ffmpeg()
        ffprobe_bin = cls.find_ffprobe()

        installed = ffmpeg_bin is not None
        version_info = cls.get_version(ffmpeg_bin) if installed else ""

        status = {
            "installed": installed,
            "ffmpeg_path": ffmpeg_bin or "",
            "ffprobe_installed": ffprobe_bin is not None,
            "ffprobe_path": ffprobe_bin or "",
            "version": version_info,
            "ubuntu_install_cmd": "sudo apt update && sudo apt install -y ffmpeg",
            "snap_install_cmd": "sudo snap install ffmpeg",
        }
        return status
