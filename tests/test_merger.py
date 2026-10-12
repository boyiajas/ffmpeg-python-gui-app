"""
test_merger.py - Automated tests for FFmpeg checker, command builder, and media probing.
"""

import unittest
from core.ffmpeg_checker import FFmpegChecker
from core.command_builder import CommandBuilder, MergeMode
from core.media_probe import format_duration, format_filesize


class TestVideoAudioMerger(unittest.TestCase):
    def test_ffmpeg_checker(self):
        status = FFmpegChecker.check_system()
        self.assertIn("installed", status)
        self.assertIn("ubuntu_install_cmd", status)
        self.assertIn("sudo apt install -y ffmpeg", status["ubuntu_install_cmd"])

    def test_replace_audio_command(self):
        b = CommandBuilder()
        b.video_path = "/tmp/test_vid.mp4"
        b.audio_path = "/tmp/test_aud.mp3"
        b.output_path = "/tmp/out.mp4"
        b.mode = MergeMode.REPLACE_AUDIO
        cmd = b.get_command_string()
        self.assertIn("-map 0:v:0", cmd)
        self.assertIn("-map 1:a:0", cmd)
        self.assertIn("-shortest", cmd)
        self.assertIn("-c:v copy", cmd)
        self.assertIn("-c:a aac", cmd)

    def test_mix_audio_command(self):
        b = CommandBuilder()
        b.video_path = "/tmp/test_vid.mp4"
        b.audio_path = "/tmp/test_aud.mp3"
        b.output_path = "/tmp/out.mp4"
        b.mode = MergeMode.MIX_AUDIO
        b.video_volume = 0.8
        b.audio_volume = 0.4
        cmd = b.get_command_string()
        self.assertIn("amix=inputs=2", cmd)
        self.assertIn("volume=0.80", cmd)
        self.assertIn("volume=0.40", cmd)
        self.assertIn("-map 0:v:0", cmd)

    def test_audio_delay_sync(self):
        b = CommandBuilder()
        b.video_path = "/tmp/test_vid.mp4"
        b.audio_path = "/tmp/test_aud.mp3"
        b.output_path = "/tmp/out.mp4"
        b.audio_delay_ms = 750
        cmd = b.get_command_string()
        self.assertIn("-itsoffset 0.750", cmd)

    def test_loop_audio(self):
        b = CommandBuilder()
        b.video_path = "/tmp/test_vid.mp4"
        b.audio_path = "/tmp/test_aud.mp3"
        b.output_path = "/tmp/out.mp4"
        b.loop_audio = True
        cmd = b.get_command_string()
        self.assertIn("-stream_loop -1", cmd)

    def test_multi_track(self):
        b = CommandBuilder()
        b.video_path = "/tmp/test_vid.mp4"
        b.audio_path = "/tmp/test_aud.mp3"
        b.output_path = "/tmp/out.mkv"
        b.mode = MergeMode.MULTI_TRACK
        cmd = b.get_command_string()
        self.assertIn("-map 0:v:0", cmd)
        self.assertIn("0:a?", cmd)
        self.assertIn("-map 1:a:0", cmd)

    def test_extract_audio(self):
        b = CommandBuilder()
        b.video_path = "/tmp/test_vid.mp4"
        b.output_path = "/tmp/out.mp3"
        b.mode = MergeMode.EXTRACT_AUDIO
        b.audio_codec = "libmp3lame"
        b.audio_bitrate = "320k"
        cmd = b.get_command_string()
        self.assertIn("-vn", cmd)
        self.assertIn("-c:a libmp3lame", cmd)
        self.assertIn("-b:a 320k", cmd)

    def test_image_plus_audio(self):
        b = CommandBuilder()
        b.video_path = "/tmp/cover.jpg"
        b.audio_path = "/tmp/music.mp3"
        b.output_path = "/tmp/out.mp4"
        b.mode = MergeMode.IMAGE_AUDIO
        cmd = b.get_command_string()
        self.assertIn("-loop 1", cmd)
        self.assertIn("-tune stillimage", cmd)
        self.assertIn("-shortest", cmd)

    def test_format_helpers(self):
        self.assertEqual(format_duration(65.5), "01:05.50")
        self.assertEqual(format_duration(3661.0), "01:01:01.00")
        self.assertEqual(format_filesize(1048576), "1.0 MB")


if __name__ == "__main__":
    unittest.main()
