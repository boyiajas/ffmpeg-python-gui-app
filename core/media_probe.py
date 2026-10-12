"""
media_probe.py - Probes video and audio files using ffprobe / ffmpeg
to extract duration, resolution, codecs, channels, sample rate, and size.
"""

import json
import os
import re
import subprocess
from typing import Dict, Any, Optional
from core.ffmpeg_checker import FFmpegChecker


def format_duration(seconds: float) -> str:
    if seconds is None or seconds < 0:
        return "Unknown"
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 100)
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}.{millis:02d}"
    return f"{mins:02d}:{secs:02d}.{millis:02d}"


def format_filesize(bytes_size: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"


class MediaProbe:
    @classmethod
    def probe_file(cls, filepath: str) -> Dict[str, Any]:
        result = {
            "filepath": filepath,
            "filename": os.path.basename(filepath),
            "filesize": 0,
            "filesize_str": "0 B",
            "duration": 0.0,
            "duration_str": "00:00.00",
            "is_video": False,
            "is_audio": False,
            "has_video": False,
            "has_audio": False,
            "width": 0,
            "height": 0,
            "resolution": "",
            "fps": 0.0,
            "video_codec": "",
            "audio_codec": "",
            "audio_streams": [],
            "audio_channels": 0,
            "sample_rate": 0,
            "bitrate": 0,
            "raw_info": "",
        }

        if not os.path.isfile(filepath):
            return result

        try:
            result["filesize"] = os.path.getsize(filepath)
            result["filesize_str"] = format_filesize(result["filesize"])
        except Exception:
            pass

        ffprobe_bin = FFmpegChecker.find_ffprobe()
        if ffprobe_bin:
            cls._probe_via_ffprobe(ffprobe_bin, filepath, result)
        else:
            ffmpeg_bin = FFmpegChecker.find_ffmpeg()
            if ffmpeg_bin:
                cls._probe_via_ffmpeg(ffmpeg_bin, filepath, result)

        return result

    @classmethod
    def _probe_via_ffprobe(cls, ffprobe_bin: str, filepath: str, res: Dict[str, Any]):
        try:
            cmd = [
                ffprobe_bin,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                filepath,
            ]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=8)
            if proc.returncode != 0 or not proc.stdout:
                return

            data = json.loads(proc.stdout)
            streams = data.get("streams", [])
            fmt = data.get("format", {})

            # Format duration
            if "duration" in fmt:
                try:
                    res["duration"] = float(fmt["duration"])
                    res["duration_str"] = format_duration(res["duration"])
                except (ValueError, TypeError):
                    pass

            if "bit_rate" in fmt:
                try:
                    res["bitrate"] = int(fmt["bit_rate"])
                except (ValueError, TypeError):
                    pass

            audio_streams = []
            for s in streams:
                codec_type = s.get("codec_type")
                if codec_type == "video" and not res["has_video"]:
                    # ignore attached pictures (album art)
                    if s.get("disposition", {}).get("attached_pic") != 1:
                        res["has_video"] = True
                        res["is_video"] = True
                        res["video_codec"] = s.get("codec_name", "")
                        res["width"] = s.get("width", 0)
                        res["height"] = s.get("height", 0)
                        if res["width"] and res["height"]:
                            res["resolution"] = f"{res['width']}x{res['height']}"

                        # Framerate
                        r_frame_rate = s.get("r_frame_rate", "0/0")
                        if "/" in r_frame_rate:
                            num, den = r_frame_rate.split("/")
                            if float(den) > 0:
                                res["fps"] = round(float(num) / float(den), 2)

                elif codec_type == "audio":
                    res["has_audio"] = True
                    audio_info = {
                        "index": s.get("index"),
                        "codec": s.get("codec_name", ""),
                        "channels": s.get("channels", 2),
                        "sample_rate": s.get("sample_rate", 44100),
                        "channel_layout": s.get("channel_layout", ""),
                        "bitrate": s.get("bit_rate", ""),
                        "title": s.get("tags", {}).get("title", ""),
                        "language": s.get("tags", {}).get("language", "und"),
                    }
                    audio_streams.append(audio_info)

            res["audio_streams"] = audio_streams
            if audio_streams:
                first_a = audio_streams[0]
                res["audio_codec"] = first_a["codec"]
                res["audio_channels"] = first_a["channels"]
                try:
                    res["sample_rate"] = int(first_a["sample_rate"])
                except Exception:
                    pass

            if not res["has_video"] and res["has_audio"]:
                res["is_audio"] = True

        except Exception as e:
            res["raw_info"] = str(e)

    @classmethod
    def _probe_via_ffmpeg(cls, ffmpeg_bin: str, filepath: str, res: Dict[str, Any]):
        try:
            cmd = [ffmpeg_bin, "-i", filepath]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=8)
            output = proc.stderr

            dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", output)
            if dur_match:
                h, m, s = dur_match.groups()
                dur = int(h) * 3600 + int(m) * 60 + float(s)
                res["duration"] = dur
                res["duration_str"] = format_duration(dur)

            # Video stream
            v_match = re.search(r"Stream #\d+:\d+.*Video:\s*(\w+).*, (\d+)x(\d+)", output)
            if v_match:
                res["has_video"] = True
                res["is_video"] = True
                res["video_codec"] = v_match.group(1)
                res["width"] = int(v_match.group(2))
                res["height"] = int(v_match.group(3))
                res["resolution"] = f"{res['width']}x{res['height']}"

            # Audio stream
            a_match = re.search(r"Stream #\d+:\d+.*Audio:\s*(\w+).*, (\d+) Hz, (stereo|mono|[\d.]+ channels)", output)
            if a_match:
                res["has_audio"] = True
                res["audio_codec"] = a_match.group(1)
                res["sample_rate"] = int(a_match.group(2))
                ch_str = a_match.group(3)
                if "stereo" in ch_str:
                    res["audio_channels"] = 2
                elif "mono" in ch_str:
                    res["audio_channels"] = 1
                else:
                    res["audio_channels"] = 2

            if not res["has_video"] and res["has_audio"]:
                res["is_audio"] = True

        except Exception as e:
            res["raw_info"] = str(e)
