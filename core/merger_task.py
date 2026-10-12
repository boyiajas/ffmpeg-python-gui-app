"""
merger_task.py - Executes FFmpeg subprocess in a background thread,
streams output lines, parses real-time progress / speed / elapsed time,
and supports clean cancellation.
"""

import os
import re
import signal
import subprocess
import threading
import time
from typing import Callable, Optional, List
from core.ffmpeg_checker import FFmpegChecker


class MergerTask:
    def __init__(
        self,
        cmd_args: List[str],
        total_duration: float = 0.0,
        output_path: str = "",
        on_progress: Optional[Callable[[float, str, str, str], None]] = None,
        on_log: Optional[Callable[[str], None]] = None,
        on_complete: Optional[Callable[[bool, int, str, str], None]] = None,
    ):
        self.cmd_args = cmd_args
        self.total_duration = total_duration
        self.output_path = output_path
        self.on_progress = on_progress
        self.on_log = on_log
        self.on_complete = on_complete

        self._process: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._is_cancelled = False
        self._is_running = False
        self._start_time = 0.0

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self):
        if self._is_running:
            return
        self._is_cancelled = False
        self._is_running = True
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self):
        if not self._is_running:
            return
        self._is_cancelled = True
        if self._process:
            try:
                # Send SIGINT first to let ffmpeg close cleanly if possible, else terminate
                self._process.send_signal(signal.SIGINT)
                threading.Timer(1.5, self._force_kill).start()
            except Exception:
                self._force_kill()

    def _force_kill(self):
        if self._process and self._process.poll() is None:
            try:
                self._process.kill()
            except Exception:
                pass

    def _run(self):
        ffmpeg_bin = FFmpegChecker.find_ffmpeg()
        if not ffmpeg_bin:
            self._is_running = False
            msg = "FFmpeg is not installed on the system! Please install it using 'sudo apt install -y ffmpeg'."
            if self.on_log:
                self.on_log(f"ERROR: {msg}")
            if self.on_complete:
                self.on_complete(False, -1, msg, self.output_path)
            return

        # Replace first argument with verified binary if needed
        if self.cmd_args and (self.cmd_args[0] == "ffmpeg" or not os.path.exists(self.cmd_args[0])):
            self.cmd_args[0] = ffmpeg_bin

        if self.on_log:
            self.on_log(f"Executing: {' '.join(self.cmd_args)}")

        time_pattern = re.compile(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)")
        speed_pattern = re.compile(r"speed=\s*([\d\.]+)x")
        fps_pattern = re.compile(r"fps=\s*([\d\.]+)")

        try:
            # We use preexec_fn=os.setsid on Unix to create a separate process group
            self._process = subprocess.Popen(
                self.cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            # Read stderr line by line
            for line in self._process.stderr:
                line_clean = line.strip()
                if not line_clean:
                    continue

                if self.on_log:
                    self.on_log(line_clean)

                # Parse progress
                curr_seconds = 0.0
                curr_time_str = "00:00:00"
                curr_speed_str = "1.0x"

                t_match = time_pattern.search(line_clean)
                if t_match:
                    h, m, s = t_match.groups()
                    curr_seconds = int(h) * 3600 + int(m) * 60 + float(s)
                    curr_time_str = f"{int(h):02d}:{int(m):02d}:{int(float(s)):02d}"

                s_match = speed_pattern.search(line_clean)
                if s_match:
                    curr_speed_str = f"{s_match.group(1)}x"

                # Calculate percentage
                pct = 0.0
                if self.total_duration > 0 and curr_seconds > 0:
                    pct = min(100.0, (curr_seconds / self.total_duration) * 100.0)

                if self.on_progress and (t_match or s_match):
                    self.on_progress(pct, curr_time_str, curr_speed_str, line_clean)

            self._process.wait()
            ret_code = self._process.returncode

            self._is_running = False
            elapsed_total = time.time() - self._start_time

            if self._is_cancelled:
                # Remove incomplete output file
                if os.path.exists(self.output_path):
                    try:
                        os.remove(self.output_path)
                    except Exception:
                        pass
                if self.on_log:
                    self.on_log("Operation was cancelled by user.")
                if self.on_complete:
                    self.on_complete(False, -9, "Operation cancelled by user.", self.output_path)
            elif ret_code == 0:
                success_msg = f"Completed successfully in {elapsed_total:.1f} seconds!"
                if self.on_progress:
                    self.on_progress(100.0, "Done", "", "")
                if self.on_log:
                    self.on_log(f"SUCCESS: {success_msg}")
                if self.on_complete:
                    self.on_complete(True, ret_code, success_msg, self.output_path)
            else:
                fail_msg = f"FFmpeg failed with exit code {ret_code}."
                if self.on_log:
                    self.on_log(f"FAILED: {fail_msg}")
                if self.on_complete:
                    self.on_complete(False, ret_code, fail_msg, self.output_path)

        except Exception as e:
            self._is_running = False
            err_msg = f"Process error: {e}"
            if self.on_log:
                self.on_log(err_msg)
            if self.on_complete:
                self.on_complete(False, -1, err_msg, self.output_path)
