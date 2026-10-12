"""
command_builder.py - Emulates all common and advanced FFmpeg operations
for merging video and audio, mixing audio tracks, multi-track mapping,
audio delay/sync, looping, trim, codecs, and container formats.
"""

import os
import shlex
from typing import List, Dict, Any, Optional
from core.ffmpeg_checker import FFmpegChecker


class MergeMode:
    REPLACE_AUDIO = "replace_audio"      # Replace original video audio with new audio
    MIX_AUDIO = "mix_audio"              # Mix/combine video audio + new audio (volume controls)
    MULTI_TRACK = "multi_track"          # Keep video audio as Track 1, add new audio as Track 2 (dual audio)
    ADD_TO_SILENT = "add_to_silent"      # Add audio to silent video
    IMAGE_AUDIO = "image_audio"          # Merge still image + audio into video
    EXTRACT_AUDIO = "extract_audio"      # Extract audio track from video
    CUSTOM = "custom"                    # Custom / manual flags


class CommandBuilder:
    def __init__(self):
        self.mode: str = MergeMode.REPLACE_AUDIO
        self.video_path: str = ""
        self.audio_path: str = ""
        self.secondary_audio_paths: List[Dict[str, str]] = []  # list of {"path": ..., "lang": ..., "title": ...}
        self.output_path: str = ""

        # Duration & Timing
        self.duration_mode: str = "shortest"  # "shortest", "video", "audio", "longest", "custom"
        self.video_duration: float = 0.0
        self.audio_duration: float = 0.0
        self.custom_start_time: str = ""      # "00:00:00" or seconds
        self.custom_end_time: str = ""        # "00:00:00" or seconds
        self.loop_audio: bool = False         # loop audio if shorter than video
        self.audio_delay_ms: int = 0          # offset in milliseconds (+ or -)

        # Audio volumes (0.0 to 3.0, 1.0 is 100%)
        self.video_volume: float = 1.0
        self.audio_volume: float = 1.0

        # Codecs & Encoding
        self.video_codec: str = "copy"        # "copy", "libx264", "libx265", "libvpx-vp9", "libsvtav1", "none"
        self.video_preset: str = "medium"     # "ultrafast", "fast", "medium", "slow", "veryslow"
        self.video_crf: int = 23              # 18-28 typical
        self.audio_codec: str = "aac"         # "copy", "aac", "libmp3lame", "libopus", "flac", "ac3", "pcm_s16le"
        self.audio_bitrate: str = "192k"      # "96k", "128k", "192k", "256k", "320k", "auto"
        self.audio_channels: str = "auto"     # "auto", "1", "2", "6"
        self.audio_samplerate: str = "auto"   # "auto", "44100", "48000", "96000"

        # Output & Extra
        self.faststart: bool = True           # -movflags +faststart for MP4 web streaming
        self.extra_args: str = ""             # raw extra flags

    def build_command_args(self, validate: bool = True) -> List[str]:
        """Returns the ffmpeg command as an argument list suitable for subprocess."""
        ffmpeg_bin = FFmpegChecker.find_ffmpeg() or "ffmpeg"
        args = [ffmpeg_bin, "-y"]  # -y to overwrite output

        # If previewing and paths are empty, use readable placeholders
        v_path = self.video_path or ("<input_video.mp4>" if not validate else "")
        a_path = self.audio_path or ("<input_audio.mp3>" if not validate else "")
        o_path = self.output_path or ("<output_merged.mp4>" if not validate else "")

        # Validation
        if validate:
            if not self.output_path:
                raise ValueError("Output file path is required.")

            if self.mode == MergeMode.EXTRACT_AUDIO:
                if not self.video_path or not os.path.exists(self.video_path):
                    raise ValueError(f"Video file does not exist: {self.video_path}")
                return self._build_extract_audio(args, v_path, o_path)

            if self.mode == MergeMode.IMAGE_AUDIO:
                if not self.video_path or not os.path.exists(self.video_path):
                    raise ValueError(f"Image file does not exist: {self.video_path}")
                if not self.audio_path or not os.path.exists(self.audio_path):
                    raise ValueError(f"Audio file does not exist: {self.audio_path}")
                return self._build_image_audio(args, v_path, a_path, o_path)

            if not self.video_path or not os.path.exists(self.video_path):
                raise ValueError(f"Video file does not exist: {self.video_path}")

            if not self.audio_path or not os.path.exists(self.audio_path):
                raise ValueError(f"Audio file does not exist: {self.audio_path}")

        if self.mode == MergeMode.EXTRACT_AUDIO:
            return self._build_extract_audio(args, v_path, o_path)

        if self.mode == MergeMode.IMAGE_AUDIO:
            return self._build_image_audio(args, v_path, a_path, o_path)

        if self.mode == MergeMode.REPLACE_AUDIO:
            args = self._build_replace_audio(args, v_path, a_path)
        elif self.mode == MergeMode.MIX_AUDIO:
            args = self._build_mix_audio(args, v_path, a_path)
        elif self.mode == MergeMode.MULTI_TRACK:
            args = self._build_multi_track(args, v_path, a_path)
        elif self.mode == MergeMode.ADD_TO_SILENT:
            args = self._build_add_to_silent(args, v_path, a_path)
        else:
            args = self._build_replace_audio(args, v_path, a_path)

        args.append(o_path)
        return args

    def _build_replace_audio(self, args: List[str], v_path: str, a_path: str) -> List[str]:
        # Custom trim start before video input
        if self.custom_start_time:
            args.extend(["-ss", self.custom_start_time])

        # Video input
        args.extend(["-i", v_path])

        # Audio input (with loop or delay if needed)
        if self.loop_audio:
            args.extend(["-stream_loop", "-1"])

        if self.audio_delay_ms > 0:
            delay_sec = self.audio_delay_ms / 1000.0
            args.extend(["-itsoffset", f"{delay_sec:.3f}"])

        args.extend(["-i", a_path])

        # Custom trim end/duration
        if self.custom_end_time:
            args.extend(["-to", self.custom_end_time])

        # Stream mapping: 0:v:0 (video from input 0), 1:a:0 (audio from input 1)
        args.extend(["-map", "0:v:0", "-map", "1:a:0"])

        # Audio volume filter if audio volume != 1.0 or negative audio delay
        audio_filters = []
        if self.audio_delay_ms < 0:
            trim_sec = abs(self.audio_delay_ms) / 1000.0
            audio_filters.append(f"atrim=start={trim_sec:.3f},asetpts=PTS-STARTPTS")
        if abs(self.audio_volume - 1.0) > 0.01:
            audio_filters.append(f"volume={self.audio_volume:.2f}")

        if audio_filters:
            args.extend(["-af", ",".join(audio_filters)])

        # Duration handling
        if self.duration_mode == "shortest":
            args.append("-shortest")
        elif self.duration_mode == "video" and self.video_duration > 0:
            args.extend(["-t", f"{self.video_duration:.3f}"])

        # Codecs
        self._apply_codecs(args, force_audio_encode=bool(audio_filters))
        return args

    def _build_mix_audio(self, args: List[str], v_path: str, a_path: str) -> List[str]:
        # Custom trim start
        if self.custom_start_time:
            args.extend(["-ss", self.custom_start_time])

        args.extend(["-i", v_path])

        if self.loop_audio:
            args.extend(["-stream_loop", "-1"])

        args.extend(["-i", a_path])

        if self.custom_end_time:
            args.extend(["-to", self.custom_end_time])

        v_vol = self.audio_volume
        vid_vol = self.video_volume

        dur_param = "first" if self.duration_mode in ["video", "shortest"] else "longest"

        filter_parts = []
        filter_parts.append(f"[0:a]volume={vid_vol:.2f}[a0]")

        a1_filter = f"volume={v_vol:.2f}"
        if self.audio_delay_ms > 0:
            delay_ms = self.audio_delay_ms
            a1_filter = f"adelay={delay_ms}|{delay_ms}," + a1_filter
        elif self.audio_delay_ms < 0:
            trim_sec = abs(self.audio_delay_ms) / 1000.0
            a1_filter = f"atrim=start={trim_sec:.3f},asetpts=PTS-STARTPTS," + a1_filter

        filter_parts.append(f"[1:a]{a1_filter}[a1]")
        filter_parts.append(f"[a0][a1]amix=inputs=2:duration={dur_param}:dropout_transition=2[aout]")

        complex_filter = ";".join(filter_parts)
        args.extend(["-filter_complex", complex_filter])

        # Map video stream and mixed audio stream
        args.extend(["-map", "0:v:0", "-map", "[aout]"])

        if self.duration_mode == "shortest":
            args.append("-shortest")
        elif self.duration_mode == "video" and self.video_duration > 0:
            args.extend(["-t", f"{self.video_duration:.3f}"])

        # Video codec can be copy, but audio codec MUST be encoded because of amix filter
        audio_codec = self.audio_codec if self.audio_codec != "copy" else "aac"
        self._apply_codecs(args, force_audio_encode=True, forced_audio_codec=audio_codec)
        return args

    def _build_multi_track(self, args: List[str], v_path: str, a_path: str) -> List[str]:
        # Keeps original audio stream, adds new audio as second track
        if self.custom_start_time:
            args.extend(["-ss", self.custom_start_time])

        args.extend(["-i", v_path])
        args.extend(["-i", a_path])

        args.extend(["-map", "0:v:0", "-map", "0:a?", "-map", "1:a:0"])
        args.extend(["-metadata:s:a:1", "title=Secondary Audio Track"])

        input_idx = 2
        for item in self.secondary_audio_paths:
            path = item.get("path")
            if path and os.path.exists(path):
                args.extend(["-i", path])
                args.extend(["-map", f"{input_idx}:a:0"])
                lang = item.get("lang") or "und"
                title = item.get("title") or f"Audio Track {input_idx}"
                args.extend([f"-metadata:s:a:{input_idx}", f"language={lang}"])
                args.extend([f"-metadata:s:a:{input_idx}", f"title={title}"])
                input_idx += 1

        if self.duration_mode == "shortest":
            args.append("-shortest")

        self._apply_codecs(args, force_audio_encode=False)
        return args

    def _build_add_to_silent(self, args: List[str], v_path: str, a_path: str) -> List[str]:
        if self.custom_start_time:
            args.extend(["-ss", self.custom_start_time])

        args.extend(["-i", v_path])

        if self.loop_audio:
            args.extend(["-stream_loop", "-1"])

        args.extend(["-i", a_path])

        args.extend(["-map", "0:v:0", "-map", "1:a:0"])

        if self.duration_mode == "shortest":
            args.append("-shortest")
        elif self.duration_mode == "video" and self.video_duration > 0:
            args.extend(["-t", f"{self.video_duration:.3f}"])

        self._apply_codecs(args, force_audio_encode=False)
        return args

    def _build_image_audio(self, args: List[str], v_path: str, a_path: str, o_path: str) -> List[str]:
        args.extend(["-loop", "1", "-i", v_path, "-i", a_path])
        args.extend(["-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p"])

        audio_codec = self.audio_codec if self.audio_codec != "copy" else "aac"
        args.extend(["-c:a", audio_codec])
        if self.audio_bitrate != "auto":
            args.extend(["-b:a", self.audio_bitrate])

        args.append("-shortest")
        self._apply_movflags(args)
        args.append(o_path)
        return args

    def _build_extract_audio(self, args: List[str], v_path: str, o_path: str) -> List[str]:
        args.extend(["-i", v_path, "-vn"])
        if self.audio_codec == "copy":
            args.extend(["-c:a", "copy"])
        else:
            args.extend(["-c:a", self.audio_codec])
            if self.audio_bitrate != "auto":
                args.extend(["-b:a", self.audio_bitrate])
        args.append(o_path)
        return args

    def _apply_codecs(self, args: List[str], force_audio_encode: bool = False, forced_audio_codec: str = "aac"):
        if self.video_codec == "copy":
            args.extend(["-c:v", "copy"])
        elif self.video_codec == "none":
            args.append("-vn")
        else:
            args.extend(["-c:v", self.video_codec])
            if self.video_preset:
                args.extend(["-preset", self.video_preset])
            if self.video_codec in ["libx264", "libx265", "libsvtav1"]:
                args.extend(["-crf", str(self.video_crf)])
            elif self.video_codec == "libvpx-vp9":
                args.extend(["-b:v", "0", "-crf", str(self.video_crf)])

        if force_audio_encode and self.audio_codec == "copy":
            codec_to_use = forced_audio_codec
        else:
            codec_to_use = self.audio_codec

        args.extend(["-c:a", codec_to_use])

        if codec_to_use != "copy":
            if self.audio_bitrate != "auto":
                args.extend(["-b:a", self.audio_bitrate])
            if self.audio_channels != "auto":
                args.extend(["-ac", self.audio_channels])
            if self.audio_samplerate != "auto":
                args.extend(["-ar", self.audio_samplerate])

        self._apply_movflags(args)

        if self.extra_args.strip():
            extra_tokens = shlex.split(self.extra_args.strip())
            args.extend(extra_tokens)

    def _apply_movflags(self, args: List[str]):
        if self.faststart:
            ext = os.path.splitext(self.output_path or "")[1].lower()
            if ext in [".mp4", ".m4v", ".mov"]:
                args.extend(["-movflags", "+faststart"])

    def get_command_string(self, validate: bool = False) -> str:
        """Returns readable, shell-escaped command string for display and copying."""
        try:
            args = self.build_command_args(validate=validate)
            return " ".join(shlex.quote(arg) for arg in args)
        except Exception as e:
            return f"# Could not generate command: {e}"
