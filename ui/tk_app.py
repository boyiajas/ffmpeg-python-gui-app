"""
tk_app.py - Tkinter GUI implementation for Video Audio Merger.
Provides a modern ttk-styled interface if wxPython is not installed.
"""

import os
import shutil
import subprocess
import threading
from typing import Optional

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except ImportError:
    tk = None

from core.ffmpeg_checker import FFmpegChecker
from core.media_probe import MediaProbe
from core.command_builder import CommandBuilder, MergeMode
from core.merger_task import MergerTask
import ui.theme as theme


class TkApp:
    def __init__(self, root: "tk.Tk"):
        self.root = root
        self.root.title("Video & Audio Merger - FFmpeg GUI (Tkinter)")
        self.root.geometry(f"{theme.WINDOW_WIDTH}x{theme.WINDOW_HEIGHT}")
        self.root.minsize(theme.MIN_WIDTH, theme.MIN_HEIGHT)

        self.builder = CommandBuilder()
        self.current_task: Optional[MergerTask] = None
        self.ffmpeg_installed = False

        self._apply_style()
        self._init_ui()
        self.check_ffmpeg_status()
        self.update_command_preview()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _apply_style(self):
        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        self.style.configure(".", font=("Helvetica", 10))
        self.style.configure("Accent.TButton", font=("Helvetica", 10, "bold"), foreground="#FFFFFF", background=theme.UBUNTU_ORANGE)
        self.style.configure("Header.TLabel", font=("Helvetica", 11, "bold"))
        self.style.configure("Warn.TLabel", font=("Helvetica", 10, "bold"), foreground="#B45309")

    def _init_ui(self):
        # 1. FFmpeg Warning Banner
        self.banner_frame = tk.Frame(self.root, bg="#FEF3C7", padx=10, pady=8, highlightbackground="#F59E0B", highlightthickness=1)
        self.banner_label = tk.Label(
            self.banner_frame,
            text="⚠️ FFmpeg is not installed! It is required to merge media files.",
            bg="#FEF3C7", fg="#B45309", font=("Helvetica", 10, "bold")
        )
        self.banner_label.pack(side=tk.LEFT, padx=5)

        self.btn_copy_banner = ttk.Button(self.banner_frame, text="📋 Copy Install Command", command=self.on_copy_install_cmd)
        self.btn_copy_banner.pack(side=tk.RIGHT, padx=5)

        self.btn_recheck_banner = ttk.Button(self.banner_frame, text="🔄 Check Again", command=lambda: self.check_ffmpeg_status(notify=True))
        self.btn_recheck_banner.pack(side=tk.RIGHT, padx=5)

        self.btn_custom_banner = ttk.Button(self.banner_frame, text="📁 Custom Binary...", command=self.on_browse_custom_binary)
        self.btn_custom_banner.pack(side=tk.RIGHT, padx=5)

        # 2. Main Container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Mode Selection
        mode_frame = ttk.LabelFrame(main_frame, text=" Operation Mode ", padding="8")
        mode_frame.pack(fill=tk.X, pady=(0, 8))

        self.mode_choices = [
            ("Replace Audio (Mute Original)", MergeMode.REPLACE_AUDIO),
            ("Mix Audio (Blend Both with Volume Control)", MergeMode.MIX_AUDIO),
            ("Multi-Track (Add Secondary Track / Dual Audio)", MergeMode.MULTI_TRACK),
            ("Add Audio to Silent Video", MergeMode.ADD_TO_SILENT),
            ("Image + Audio (Still Picture to Video)", MergeMode.IMAGE_AUDIO),
            ("Extract Audio (Rip Audio from Video)", MergeMode.EXTRACT_AUDIO),
        ]
        self.mode_var = tk.StringVar(value=self.mode_choices[0][0])
        self.combo_mode = ttk.Combobox(mode_frame, textvariable=self.mode_var, values=[m[0] for m in self.mode_choices], state="readonly")
        self.combo_mode.pack(fill=tk.X)
        self.combo_mode.bind("<<ComboboxSelected>>", self.on_mode_changed)

        # Media Files Frame
        files_frame = ttk.LabelFrame(main_frame, text=" Media Files ", padding="8")
        files_frame.pack(fill=tk.X, pady=(0, 8))

        # Video Row
        v_frame = ttk.Frame(files_frame)
        v_frame.pack(fill=tk.X, pady=2)
        self.lbl_video_title = ttk.Label(v_frame, text="Video File:", width=12)
        self.lbl_video_title.pack(side=tk.LEFT)
        self.txt_video = ttk.Entry(v_frame)
        self.txt_video.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.txt_video.bind("<KeyRelease>", lambda e: self.on_video_path_changed())
        ttk.Button(v_frame, text="Browse Video...", command=self.on_browse_video).pack(side=tk.LEFT)

        self.lbl_video_info = ttk.Label(files_frame, text="No video selected", foreground="#6B7280")
        self.lbl_video_info.pack(anchor=tk.W, padx=85, pady=(0, 4))

        # Audio Row
        a_frame = ttk.Frame(files_frame)
        a_frame.pack(fill=tk.X, pady=2)
        self.lbl_audio_title = ttk.Label(a_frame, text="Audio File:", width=12)
        self.lbl_audio_title.pack(side=tk.LEFT)
        self.txt_audio = ttk.Entry(a_frame)
        self.txt_audio.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.txt_audio.bind("<KeyRelease>", lambda e: self.on_audio_path_changed())
        self.btn_browse_audio = ttk.Button(a_frame, text="Browse Audio...", command=self.on_browse_audio)
        self.btn_browse_audio.pack(side=tk.LEFT)

        self.lbl_audio_info = ttk.Label(files_frame, text="No audio selected", foreground="#6B7280")
        self.lbl_audio_info.pack(anchor=tk.W, padx=85, pady=(0, 4))

        # Output Row
        o_frame = ttk.Frame(files_frame)
        o_frame.pack(fill=tk.X, pady=2)
        ttk.Label(o_frame, text="Output File:", width=12).pack(side=tk.LEFT)
        self.txt_output = ttk.Entry(o_frame)
        self.txt_output.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.txt_output.bind("<KeyRelease>", lambda e: self.on_output_path_changed())
        ttk.Button(o_frame, text="Save As...", command=self.on_browse_output).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(o_frame, text="⚡ Video Folder", command=self.on_use_video_folder).pack(side=tk.LEFT)

        # Tabs for options
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # Tab 1: Audio Options
        self.tab_audio = ttk.Frame(self.notebook, padding="10")
        self._init_audio_tab(self.tab_audio)
        self.notebook.add(self.tab_audio, text="🎚️ Audio & Mixing")

        # Tab 2: Video & Timing
        self.tab_video = ttk.Frame(self.notebook, padding="10")
        self._init_video_tab(self.tab_video)
        self.notebook.add(self.tab_video, text="🎬 Video & Duration")

        # Tab 3: Live Command Preview & Log
        self.tab_cmd = ttk.Frame(self.notebook, padding="10")
        self._init_cmd_tab(self.tab_cmd)
        self.notebook.add(self.tab_cmd, text="💻 Live FFmpeg Command")

        # Bottom Progress & Action
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X)

        self.progress_bar = ttk.Progressbar(bottom_frame, mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(0, 6))

        action_row = ttk.Frame(bottom_frame)
        action_row.pack(fill=tk.X)

        self.lbl_status = ttk.Label(action_row, text="Status: Ready", font=("Helvetica", 10, "bold"))
        self.lbl_status.pack(side=tk.LEFT)

        self.btn_start = tk.Button(
            action_row, text="▶ Start Merge", bg=theme.UBUNTU_ORANGE, fg="#FFFFFF",
            font=("Helvetica", 10, "bold"), padx=15, pady=6, relief=tk.FLAT, command=self.on_start_merge
        )
        self.btn_start.pack(side=tk.RIGHT)

        self.btn_cancel = ttk.Button(action_row, text="⏹ Cancel", command=self.on_cancel_merge, state=tk.DISABLED)
        self.btn_cancel.pack(side=tk.RIGHT, padx=8)

    def _init_audio_tab(self, parent):
        grid = ttk.Frame(parent)
        grid.pack(fill=tk.X, pady=(0, 10))

        # Audio Codec
        ttk.Label(grid, text="Audio Codec:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.audio_codec_choices = [
            ("AAC (Standard for MP4)", "aac"),
            ("Stream Copy (Lossless / Fast)", "copy"),
            ("MP3 (libmp3lame)", "libmp3lame"),
            ("Opus (High Quality)", "libopus"),
            ("FLAC (Lossless)", "flac"),
            ("PCM / WAV", "pcm_s16le"),
        ]
        self.a_codec_var = tk.StringVar(value=self.audio_codec_choices[0][0])
        self.combo_a_codec = ttk.Combobox(grid, textvariable=self.a_codec_var, values=[c[0] for c in self.audio_codec_choices], state="readonly")
        self.combo_a_codec.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        self.combo_a_codec.bind("<<ComboboxSelected>>", self.on_option_changed)

        # Bitrate
        ttk.Label(grid, text="Audio Bitrate:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.bitrate_var = tk.StringVar(value="192k")
        self.combo_bitrate = ttk.Combobox(grid, textvariable=self.bitrate_var, values=["Auto", "96k", "128k", "192k", "256k", "320k"], state="readonly")
        self.combo_bitrate.grid(row=0, column=3, sticky=tk.EW, padx=5, pady=5)
        self.combo_bitrate.bind("<<ComboboxSelected>>", self.on_option_changed)

        # Channels
        ttk.Label(grid, text="Channels:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.channels_var = tk.StringVar(value="Auto")
        self.combo_channels = ttk.Combobox(grid, textvariable=self.channels_var, values=["Auto", "Stereo (2.0)", "Mono (1.0)", "5.1 Surround"], state="readonly")
        self.combo_channels.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        self.combo_channels.bind("<<ComboboxSelected>>", self.on_option_changed)

        # Sample Rate
        ttk.Label(grid, text="Sample Rate:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.samplerate_var = tk.StringVar(value="Auto")
        self.combo_samplerate = ttk.Combobox(grid, textvariable=self.samplerate_var, values=["Auto", "44100 Hz", "48000 Hz", "96000 Hz"], state="readonly")
        self.combo_samplerate.grid(row=1, column=3, sticky=tk.EW, padx=5, pady=5)
        self.combo_samplerate.bind("<<ComboboxSelected>>", self.on_option_changed)

        # Delay & Loop
        ttk.Label(grid, text="Delay (ms):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.delay_var = tk.IntVar(value=0)
        self.spin_delay = ttk.Spinbox(grid, from_=-10000, to=10000, textvariable=self.delay_var, command=self.on_option_changed)
        self.spin_delay.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=5)
        self.spin_delay.bind("<KeyRelease>", lambda e: self.on_option_changed())

        self.loop_var = tk.BooleanVar(value=False)
        self.chk_loop = ttk.Checkbutton(grid, text="Loop Audio if shorter", variable=self.loop_var, command=self.on_option_changed)
        self.chk_loop.grid(row=2, column=2, columnspan=2, sticky=tk.W, padx=5, pady=5)

        # Volume sliders
        vol_frame = ttk.LabelFrame(parent, text=" Audio Volume Levels (Mix Mode) ", padding="8")
        vol_frame.pack(fill=tk.X)

        self.vid_vol_var = tk.IntVar(value=100)
        self.lbl_vid_vol = ttk.Label(vol_frame, text="Original Video Audio: 100%")
        self.lbl_vid_vol.pack(anchor=tk.W)
        self.scale_vid_vol = ttk.Scale(vol_frame, from_=0, to=200, variable=self.vid_vol_var, command=self.on_vid_vol_changed)
        self.scale_vid_vol.pack(fill=tk.X, pady=(0, 6))

        self.aud_vol_var = tk.IntVar(value=100)
        self.lbl_aud_vol = ttk.Label(vol_frame, text="Added Audio Track: 100%")
        self.lbl_aud_vol.pack(anchor=tk.W)
        self.scale_aud_vol = ttk.Scale(vol_frame, from_=0, to=200, variable=self.aud_vol_var, command=self.on_aud_vol_changed)
        self.scale_aud_vol.pack(fill=tk.X)

    def _init_video_tab(self, parent):
        grid = ttk.Frame(parent)
        grid.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(grid, text="Video Codec:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.video_codec_choices = [
            ("Stream Copy (Lossless / Fast)", "copy"),
            ("H.264 / AVC (libx264 - Best)", "libx264"),
            ("H.265 / HEVC (libx265 - Small)", "libx265"),
            ("VP9 (libvpx-vp9 - WebM)", "libvpx-vp9"),
            ("AV1 (libsvtav1)", "libsvtav1"),
            ("Disable Video (Audio Only)", "none"),
        ]
        self.v_codec_var = tk.StringVar(value=self.video_codec_choices[0][0])
        self.combo_v_codec = ttk.Combobox(grid, textvariable=self.v_codec_var, values=[c[0] for c in self.video_codec_choices], state="readonly")
        self.combo_v_codec.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        self.combo_v_codec.bind("<<ComboboxSelected>>", self.on_option_changed)

        ttk.Label(grid, text="Preset:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.preset_var = tk.StringVar(value="medium")
        self.combo_preset = ttk.Combobox(grid, textvariable=self.preset_var, values=["ultrafast", "fast", "medium", "slow", "veryslow"], state="readonly")
        self.combo_preset.grid(row=0, column=3, sticky=tk.EW, padx=5, pady=5)
        self.combo_preset.bind("<<ComboboxSelected>>", self.on_option_changed)

        ttk.Label(grid, text="Duration:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.duration_choices = [
            ("Shortest Stream (-shortest)", "shortest"),
            ("Match Video Duration", "video"),
            ("Keep Longest Stream", "longest"),
            ("Custom Trim Range", "custom"),
        ]
        self.dur_var = tk.StringVar(value=self.duration_choices[0][0])
        self.combo_dur = ttk.Combobox(grid, textvariable=self.dur_var, values=[d[0] for d in self.duration_choices], state="readonly")
        self.combo_dur.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        self.combo_dur.bind("<<ComboboxSelected>>", self.on_option_changed)

        ttk.Label(grid, text="CRF Quality (18-28):").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        self.crf_var = tk.IntVar(value=23)
        self.spin_crf = ttk.Spinbox(grid, from_=0, to=51, textvariable=self.crf_var, command=self.on_option_changed)
        self.spin_crf.grid(row=1, column=3, sticky=tk.EW, padx=5, pady=5)
        self.spin_crf.bind("<KeyRelease>", lambda e: self.on_option_changed())

        ttk.Label(grid, text="Trim Start:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.txt_trim_start = ttk.Entry(grid)
        self.txt_trim_start.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=5)
        self.txt_trim_start.bind("<KeyRelease>", lambda e: self.on_option_changed())

        ttk.Label(grid, text="Trim End / Dur:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=5)
        self.txt_trim_end = ttk.Entry(grid)
        self.txt_trim_end.grid(row=2, column=3, sticky=tk.EW, padx=5, pady=5)
        self.txt_trim_end.bind("<KeyRelease>", lambda e: self.on_option_changed())

        self.faststart_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(grid, text="Web Faststart (-movflags +faststart)", variable=self.faststart_var, command=self.on_option_changed).grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

    def _init_cmd_tab(self, parent):
        top_row = ttk.Frame(parent)
        top_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(top_row, text="Dynamic FFmpeg Terminal Command:", font=("Helvetica", 9, "bold")).pack(side=tk.LEFT)
        ttk.Button(top_row, text="📋 Copy Command", command=self.on_copy_command).pack(side=tk.RIGHT)

        self.txt_cmd = tk.Text(parent, height=5, bg=theme.COLOR_CONSOLE_BG, fg=theme.COLOR_CONSOLE_FG, font=("Courier", 9), wrap=tk.WORD)
        self.txt_cmd.pack(fill=tk.X, pady=(0, 8))

        extra_row = ttk.Frame(parent)
        extra_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(extra_row, text="Extra Arguments:").pack(side=tk.LEFT)
        self.txt_extra = ttk.Entry(extra_row)
        self.txt_extra.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.txt_extra.bind("<KeyRelease>", lambda e: self.on_option_changed())

        ttk.Label(parent, text="Process Execution Log:", font=("Helvetica", 9, "bold")).pack(anchor=tk.W)
        self.txt_log = tk.Text(parent, height=6, bg="#111827", fg="#9CA3AF", font=("Courier", 8), wrap=tk.CHAR)
        self.txt_log.pack(fill=tk.BOTH, expand=True)

    # Handlers
    def check_ffmpeg_status(self, notify: bool = False):
        status = FFmpegChecker.check_system()
        self.ffmpeg_installed = status["installed"]

        if self.ffmpeg_installed:
            self.banner_frame.pack_forget()
            ver = status["version"].split("Copyright")[0].strip() if "Copyright" in status["version"] else status["version"]
            self.lbl_status.config(text=f"Status: Ready (FFmpeg: {ver or 'Detected'})", foreground=theme.COLOR_SUCCESS)
            if notify:
                messagebox.showinfo("FFmpeg Detected", f"FFmpeg is installed and ready!\nPath: {status['ffmpeg_path']}\n{status['version']}")
        else:
            self.banner_frame.pack(fill=tk.X, side=tk.TOP)
            self.lbl_status.config(text="Status: ⚠️ FFmpeg Not Installed (Required)", foreground=theme.COLOR_DANGER)
            if notify:
                messagebox.showwarning("FFmpeg Not Found", f"FFmpeg was not detected on the system.\nPlease run:\nsudo apt install -y ffmpeg")

    def on_copy_install_cmd(self):
        cmd = "sudo apt update && sudo apt install -y ffmpeg"
        self.root.clipboard_clear()
        self.root.clipboard_append(cmd)
        messagebox.showinfo("Copied", f"Copied command to clipboard:\n\n{cmd}\n\nPaste into terminal to install.")

    def on_browse_custom_binary(self):
        path = filedialog.askopenfilename(title="Select ffmpeg Binary")
        if path and os.access(path, os.X_OK):
            FFmpegChecker.set_custom_paths(ffmpeg_path=path)
            self.check_ffmpeg_status(notify=True)
            self.update_command_preview()

    def on_mode_changed(self, event=None):
        idx = self.combo_mode.current()
        mode_val = self.mode_choices[idx][1]
        self.builder.mode = mode_val

        if mode_val == MergeMode.IMAGE_AUDIO:
            self.lbl_video_title.config(text="Image File:")
        elif mode_val == MergeMode.EXTRACT_AUDIO:
            self.lbl_video_title.config(text="Video File:")
            self.txt_audio.config(state=tk.DISABLED)
            self.btn_browse_audio.config(state=tk.DISABLED)
        else:
            self.lbl_video_title.config(text="Video File:")
            self.txt_audio.config(state=tk.NORMAL)
            self.btn_browse_audio.config(state=tk.NORMAL)

        self.update_command_preview()

    def on_browse_video(self):
        mode_val = self.builder.mode
        types = [("Image files", "*.png *.jpg *.jpeg *.bmp *.webp"), ("All files", "*.*")] if mode_val == MergeMode.IMAGE_AUDIO else [("Video files", "*.mp4 *.mkv *.mov *.avi *.webm *.flv *.ts *.m4v"), ("All files", "*.*")]
        p = filedialog.askopenfilename(title="Select Visual Source", filetypes=types)
        if p:
            self.txt_video.delete(0, tk.END)
            self.txt_video.insert(0, p)
            self.on_video_path_changed()

    def on_browse_audio(self):
        types = [("Audio files", "*.mp3 *.wav *.aac *.m4a *.flac *.ogg *.opus *.wma"), ("All files", "*.*")]
        p = filedialog.askopenfilename(title="Select Audio File", filetypes=types)
        if p:
            self.txt_audio.delete(0, tk.END)
            self.txt_audio.insert(0, p)
            self.on_audio_path_changed()

    def on_browse_output(self):
        mode_val = self.builder.mode
        def_ext = ".mp3" if mode_val == MergeMode.EXTRACT_AUDIO else ".mp4"
        types = [("Audio MP3", "*.mp3"), ("All files", "*.*")] if mode_val == MergeMode.EXTRACT_AUDIO else [("MP4 Video", "*.mp4"), ("MKV Video", "*.mkv"), ("All files", "*.*")]
        p = filedialog.asksaveasfilename(title="Save Merged Output", defaultextension=def_ext, filetypes=types)
        if p:
            self.txt_output.delete(0, tk.END)
            self.txt_output.insert(0, p)
            self.on_output_path_changed()

    def on_use_video_folder(self):
        v = self.txt_video.get().strip()
        if not v:
            messagebox.showinfo("Notice", "Please select a video file first.")
            return
        d = os.path.dirname(v)
        b, ext = os.path.splitext(os.path.basename(v))
        out_ext = ".mp3" if self.builder.mode == MergeMode.EXTRACT_AUDIO else (ext or ".mp4")
        out_p = os.path.join(d, f"{b}_merged{out_ext}")
        self.txt_output.delete(0, tk.END)
        self.txt_output.insert(0, out_p)
        self.on_output_path_changed()

    def on_video_path_changed(self):
        v = self.txt_video.get().strip()
        self.builder.video_path = v
        if v and os.path.exists(v):
            info = MediaProbe.probe_file(v)
            self.builder.video_duration = info["duration"]
            parts = [info[k] for k in ["resolution", "video_codec", "duration_str", "filesize_str"] if info.get(k)]
            self.lbl_video_info.config(text="🎬 " + " | ".join(parts) if parts else "Video loaded")
        else:
            self.lbl_video_info.config(text="No valid video selected")
        self.update_command_preview()

    def on_audio_path_changed(self):
        a = self.txt_audio.get().strip()
        self.builder.audio_path = a
        if a and os.path.exists(a):
            info = MediaProbe.probe_file(a)
            self.builder.audio_duration = info["duration"]
            parts = [info[k] for k in ["audio_codec", "duration_str", "filesize_str"] if info.get(k)]
            self.lbl_audio_info.config(text="🎵 " + " | ".join(parts) if parts else "Audio loaded")
        else:
            self.lbl_audio_info.config(text="No valid audio selected")
        self.update_command_preview()

    def on_output_path_changed(self):
        self.builder.output_path = self.txt_output.get().strip()
        self.update_command_preview()

    def on_vid_vol_changed(self, val):
        v = int(float(val))
        self.lbl_vid_vol.config(text=f"Original Video Audio: {v}%")
        self.builder.video_volume = v / 100.0
        self.update_command_preview()

    def on_aud_vol_changed(self, val):
        v = int(float(val))
        self.lbl_aud_vol.config(text=f"Added Audio Track: {v}%")
        self.builder.audio_volume = v / 100.0
        self.update_command_preview()

    def on_option_changed(self, event=None):
        # Audio Codec
        a_idx = self.combo_a_codec.current()
        self.builder.audio_codec = self.audio_codec_choices[a_idx][1] if a_idx >= 0 else "aac"

        # Bitrate
        b_val = self.bitrate_var.get()
        self.builder.audio_bitrate = "auto" if b_val == "Auto" else b_val

        # Channels
        ch_val = self.channels_var.get()
        self.builder.audio_channels = "2" if "Stereo" in ch_val else ("1" if "Mono" in ch_val else ("6" if "5.1" in ch_val else "auto"))

        # Sample Rate
        sr_val = self.samplerate_var.get()
        self.builder.audio_samplerate = "44100" if "44100" in sr_val else ("48000" if "48000" in sr_val else ("96000" if "96000" in sr_val else "auto"))

        # Delay & Loop
        self.builder.audio_delay_ms = self.delay_var.get()
        self.builder.loop_audio = self.loop_var.get()

        # Video Codec
        v_idx = self.combo_v_codec.current()
        self.builder.video_codec = self.video_codec_choices[v_idx][1] if v_idx >= 0 else "copy"

        # Preset & CRF
        self.builder.video_preset = self.preset_var.get()
        self.builder.video_crf = self.crf_var.get()

        # Duration
        dur_idx = self.combo_dur.current()
        self.builder.duration_mode = self.duration_choices[dur_idx][1] if dur_idx >= 0 else "shortest"

        # Trim
        self.builder.custom_start_time = self.txt_trim_start.get().strip()
        self.builder.custom_end_time = self.txt_trim_end.get().strip()

        # Faststart & Extra
        self.builder.faststart = self.faststart_var.get()
        self.builder.extra_args = self.txt_extra.get().strip()

        self.update_command_preview()

    def update_command_preview(self):
        cmd = self.builder.get_command_string(validate=False)
        self.txt_cmd.delete("1.0", tk.END)
        self.txt_cmd.insert(tk.END, cmd)

    def on_copy_command(self):
        cmd = self.txt_cmd.get("1.0", tk.END).strip()
        self.root.clipboard_clear()
        self.root.clipboard_append(cmd)
        messagebox.showinfo("Copied", "FFmpeg command copied to clipboard!")

    def on_start_merge(self):
        if not self.ffmpeg_installed:
            messagebox.showerror(
                "FFmpeg Required",
                "FFmpeg is not installed on this system!\n\nPlease install it using:\nsudo apt install -y ffmpeg"
            )
            return

        try:
            cmd_args = self.builder.build_command_args(validate=True)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        out_p = self.builder.output_path
        if os.path.exists(out_p):
            if not messagebox.askyesno("Overwrite?", f"Output file already exists:\n{out_p}\n\nOverwrite it?"):
                return

        self.btn_start.config(state=tk.DISABLED)
        self.btn_cancel.config(state=tk.NORMAL)
        self.progress_bar["value"] = 0
        self.lbl_status.config(text="Status: Processing...", foreground="#3B82F6")
        self.txt_log.delete("1.0", tk.END)

        total_d = self.builder.video_duration or self.builder.audio_duration or 0.0
        self.current_task = MergerTask(
            cmd_args=cmd_args,
            total_duration=total_d,
            output_path=out_p,
            on_progress=self._task_progress,
            on_log=self._task_log,
            on_complete=self._task_complete,
        )
        self.current_task.start()

    def _task_progress(self, pct: float, curr_time: str, speed: str, line: str):
        def _u():
            self.progress_bar["value"] = pct
            t = f"⚡ Status: Processing ({pct:.1f}%) | Time: {curr_time}"
            if speed:
                t += f" | Speed: {speed}"
            self.lbl_status.config(text=t, foreground="#38BDF8")
        self.root.after(0, _u)

    def _task_log(self, line: str):
        def _l():
            self.txt_log.insert(tk.END, line + "\n")
            self.txt_log.see(tk.END)
        self.root.after(0, _l)

    def _task_complete(self, success: bool, code: int, msg: str, out_p: str):
        def _d():
            self.btn_start.config(state=tk.NORMAL)
            self.btn_cancel.config(state=tk.DISABLED)
            if success:
                self.progress_bar["value"] = 100
                self.lbl_status.config(text="Status: Merge Completed Successfully! 🎉", foreground=theme.COLOR_SUCCESS)
                if messagebox.askyesno("Complete", f"Merge finished successfully!\n\nSaved to: {out_p}\n\nOpen destination folder?"):
                    fld = os.path.dirname(out_p)
                    if os.path.isdir(fld):
                        subprocess.Popen(["xdg-open", fld])
            else:
                self.lbl_status.config(text=f"Status: Failed ({msg})", foreground=theme.COLOR_DANGER)
                messagebox.showerror("Error", f"Operation failed:\n\n{msg}")
        self.root.after(0, _d)

    def on_cancel_merge(self):
        if self.current_task and self.current_task.is_running:
            self.lbl_status.config(text="Status: Cancelling...")
            self.current_task.cancel()

    def on_close(self):
        if self.current_task and self.current_task.is_running:
            if not messagebox.askyesno("Confirm Exit", "A merge task is currently running. Cancel and exit?"):
                return
            self.current_task.cancel()
        self.root.destroy()


def run_app():
    if tk is None:
        raise RuntimeError("Tkinter is not available. Please install python3-tk.")
    root = tk.Tk()
    app = TkApp(root)
    root.mainloop()
