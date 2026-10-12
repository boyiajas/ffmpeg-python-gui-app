"""
wx_app.py - Main GUI application built with wxPython (native GTK3 on Ubuntu).
Provides complete controls for merging video and audio, audio mixing,
multi-track audio, codecs, real-time command preview, media inspection,
background execution with progress bar, cancellation, and FFmpeg detection.
"""

import os
import shutil
import subprocess
import threading
from datetime import datetime
import wx

from core.ffmpeg_checker import FFmpegChecker
from core.media_probe import MediaProbe
from core.command_builder import CommandBuilder, MergeMode
from core.merger_task import MergerTask
import ui.theme as theme


class FileDropTargetHelper(wx.FileDropTarget):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def OnDropFiles(self, x, y, filenames):
        if filenames:
            self.callback(filenames)
            return True
        return False


class FFmpegInstallDialog(wx.Dialog):
    """Dialog displayed when FFmpeg is not found, providing copyable terminal commands."""
    def __init__(self, parent):
        super().__init__(parent, title="FFmpeg Required to Proceed", size=(620, 420),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.SetBackgroundColour(wx.Colour(theme.COLOR_PANEL_BG))
        self._init_ui()
        self.CentreOnParent()

    def _init_ui(self):
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Header with warning badge
        header_panel = wx.Panel(self)
        header_panel.SetBackgroundColour(wx.Colour("#FEF2F2"))
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)

        warn_icon = wx.StaticText(header_panel, label="⚠️")
        font_icon = warn_icon.GetFont()
        font_icon.SetPointSize(24)
        warn_icon.SetFont(font_icon)

        text_sizer = wx.BoxSizer(wx.VERTICAL)
        title = wx.StaticText(header_panel, label="FFmpeg is Not Installed on Your System")
        title_font = title.GetFont()
        title_font.SetPointSize(13)
        title_font.SetWeight(wx.FONTWEIGHT_BOLD)
        title.SetFont(title_font)
        title.SetForegroundColour(wx.Colour(theme.COLOR_DANGER))

        subtitle = wx.StaticText(
            header_panel,
            label="FFmpeg is the core multimedia engine required to merge, mix, and encode video & audio."
        )
        subtitle.SetForegroundColour(wx.Colour(theme.COLOR_TEXT_MUTED))
        text_sizer.Add(title, 0, wx.BOTTOM, 4)
        text_sizer.Add(subtitle, 0, wx.EXPAND)

        h_sizer.Add(warn_icon, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 12)
        h_sizer.Add(text_sizer, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 8)
        header_panel.SetSizer(h_sizer)

        vbox.Add(header_panel, 0, wx.EXPAND | wx.BOTTOM, 12)

        # Content area
        content_sizer = wx.BoxSizer(wx.VERTICAL)

        instruct_label = wx.StaticText(
            self,
            label="To proceed, open your Ubuntu Terminal (Ctrl+Alt+T) and run this command:"
        )
        instruct_label_font = instruct_label.GetFont()
        instruct_label_font.SetWeight(wx.FONTWEIGHT_SEMIBOLD)
        instruct_label.SetFont(instruct_label_font)
        content_sizer.Add(instruct_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)

        # Terminal command box
        self.cmd_text = wx.TextCtrl(
            self,
            value="sudo apt update && sudo apt install -y ffmpeg",
            style=wx.TE_READONLY | wx.BORDER_SIMPLE
        )
        self.cmd_text.SetBackgroundColour(wx.Colour(theme.COLOR_CONSOLE_BG))
        self.cmd_text.SetForegroundColour(wx.Colour(theme.COLOR_CONSOLE_FG))
        font_mono = wx.Font(11, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.cmd_text.SetFont(font_mono)
        content_sizer.Add(self.cmd_text, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)

        # Copy button & Custom Path
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        copy_btn = wx.Button(self, label="📋 Copy Command")
        copy_btn.Bind(wx.EVT_BUTTON, self.on_copy_cmd)
        btn_row.Add(copy_btn, 0, wx.RIGHT, 10)

        browse_custom_btn = wx.Button(self, label="📁 Browse Existing ffmpeg Binary...")
        browse_custom_btn.Bind(wx.EVT_BUTTON, self.on_browse_binary)
        btn_row.Add(browse_custom_btn, 0)

        content_sizer.Add(btn_row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)

        # Note about snap alternative
        note_text = wx.StaticText(
            self,
            label="Alternatively, if using Snap: sudo snap install ffmpeg\n"
                  "Once installed, click 'Check Again' below without restarting the app."
        )
        note_text.SetForegroundColour(wx.Colour(theme.COLOR_TEXT_MUTED))
        content_sizer.Add(note_text, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)

        vbox.Add(content_sizer, 1, wx.EXPAND)

        # Bottom buttons
        bottom_sizer = wx.BoxSizer(wx.HORIZONTAL)
        bottom_sizer.AddStretchSpacer()

        recheck_btn = wx.Button(self, label="🔄 Check Again", id=wx.ID_OK)
        bottom_sizer.Add(recheck_btn, 0, wx.RIGHT, 8)

        close_btn = wx.Button(self, label="Dismiss", id=wx.ID_CANCEL)
        bottom_sizer.Add(close_btn, 0)

        vbox.Add(bottom_sizer, 0, wx.EXPAND | wx.ALL, 16)
        self.SetSizer(vbox)

    def on_copy_cmd(self, event):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self.cmd_text.GetValue()))
            wx.TheClipboard.Close()
            wx.MessageBox("Command copied to clipboard!\nPaste it into your Ubuntu terminal.",
                            "Copied", wx.OK | wx.ICON_INFORMATION, self)

    def on_browse_binary(self, event):
        wildcard = "FFmpeg Executable (ffmpeg*)|ffmpeg*|All files (*.*)|*.*"
        dlg = wx.FileDialog(self, "Select ffmpeg Binary", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            if os.access(path, os.X_OK):
                FFmpegChecker.set_custom_paths(ffmpeg_path=path)
                self.EndModal(wx.ID_OK)
            else:
                wx.MessageBox("The selected file is not executable.", "Error", wx.OK | wx.ICON_ERROR, self)
        dlg.Destroy()


class MainWindow(wx.Frame):
    def __init__(self):
        super().__init__(
            None,
            title="Video & Audio Merger - FFmpeg GUI",
            size=(theme.WINDOW_WIDTH, theme.WINDOW_HEIGHT),
            style=wx.DEFAULT_FRAME_STYLE
        )
        self.SetMinSize((theme.MIN_WIDTH, theme.MIN_HEIGHT))

        # Application state
        self.builder = CommandBuilder()
        self.current_task: MergerTask = None
        self.ffmpeg_installed = False

        # Load Icon
        icon_path = os.path.join(os.path.dirname(__file__), "..", "assets", "icon_64.png")
        if os.path.exists(icon_path):
            self.SetIcon(wx.Icon(icon_path))

        self._init_ui()
        self.check_ffmpeg_status(prompt_if_missing=False)
        self.update_command_preview()

        # Bind closing
        self.Bind(wx.EVT_CLOSE, self.on_close)

    def _init_ui(self):
        main_panel = wx.Panel(self)
        self.main_panel = main_panel
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # 1. FFmpeg Status Alert Banner (Shown if missing)
        self.banner_panel = wx.Panel(main_panel)
        self.banner_panel.SetBackgroundColour(wx.Colour("#FFFBEB"))  # Light amber
        banner_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.banner_label = wx.StaticText(
            self.banner_panel,
            label="⚠️ FFmpeg is not detected! FFmpeg is required to merge media files."
        )
        self.banner_label.SetForegroundColour(wx.Colour("#B45309"))
        banner_font = self.banner_label.GetFont()
        banner_font.SetWeight(wx.FONTWEIGHT_BOLD)
        self.banner_label.SetFont(banner_font)
        banner_sizer.Add(self.banner_label, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 10)

        self.banner_copy_btn = wx.Button(self.banner_panel, label="📋 Copy Install Command", size=(-1, 28))
        self.banner_copy_btn.Bind(wx.EVT_BUTTON, self.on_copy_install_command)
        banner_sizer.Add(self.banner_copy_btn, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 8)

        self.banner_recheck_btn = wx.Button(self.banner_panel, label="🔄 Check Again", size=(-1, 28))
        self.banner_recheck_btn.Bind(wx.EVT_BUTTON, lambda e: self.check_ffmpeg_status(prompt_if_missing=False, notify_success=True))
        banner_sizer.Add(self.banner_recheck_btn, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 8)

        self.banner_custom_btn = wx.Button(self.banner_panel, label="📁 Custom Path...", size=(-1, 28))
        self.banner_custom_btn.Bind(wx.EVT_BUTTON, self.on_select_custom_ffmpeg)
        banner_sizer.Add(self.banner_custom_btn, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 10)

        self.banner_panel.SetSizer(banner_sizer)
        main_sizer.Add(self.banner_panel, 0, wx.EXPAND)

        # 2. Main Controls Scroll/Notebook container
        content_panel = wx.Panel(main_panel)
        content_sizer = wx.BoxSizer(wx.VERTICAL)

        # Section: Mode Selection
        mode_box = wx.StaticBox(content_panel, label=" Operation Mode ")
        mode_sizer = wx.StaticBoxSizer(mode_box, wx.HORIZONTAL)

        self.mode_choices = [
            ("Replace Audio (Mute Original)", MergeMode.REPLACE_AUDIO),
            ("Mix Audio (Blend Both with Volume Control)", MergeMode.MIX_AUDIO),
            ("Multi-Track (Add Secondary Track / Dual Audio)", MergeMode.MULTI_TRACK),
            ("Add Audio to Silent Video", MergeMode.ADD_TO_SILENT),
            ("Image + Audio (Still Picture to Video)", MergeMode.IMAGE_AUDIO),
            ("Extract Audio (Rip Audio from Video)", MergeMode.EXTRACT_AUDIO),
        ]
        self.mode_combo = wx.ComboBox(
            content_panel,
            choices=[m[0] for m in self.mode_choices],
            style=wx.CB_READONLY
        )
        self.mode_combo.SetSelection(0)
        self.mode_combo.Bind(wx.EVT_COMBOBOX, self.on_mode_changed)
        mode_sizer.Add(self.mode_combo, 1, wx.ALL | wx.EXPAND, 6)

        content_sizer.Add(mode_sizer, 0, wx.EXPAND | wx.ALL, 8)

        # Section: File Pickers (Video, Audio, Output)
        files_box = wx.StaticBox(content_panel, label=" Media Files ")
        files_sizer = wx.StaticBoxSizer(files_box, wx.VERTICAL)

        # Video Picker Row
        v_row = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_video = wx.StaticText(content_panel, label="Video File:", size=(90, -1))
        v_row.Add(self.lbl_video, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)

        self.txt_video = wx.TextCtrl(content_panel)
        self.txt_video.Bind(wx.EVT_TEXT, self.on_video_path_changed)
        v_row.Add(self.txt_video, 1, wx.EXPAND | wx.RIGHT, 6)

        btn_browse_video = wx.Button(content_panel, label="Browse Video...")
        btn_browse_video.Bind(wx.EVT_BUTTON, self.on_browse_video)
        v_row.Add(btn_browse_video, 0)
        files_sizer.Add(v_row, 0, wx.EXPAND | wx.ALL, 4)

        # Video Info Label
        self.lbl_video_info = wx.StaticText(content_panel, label="No video selected (Drag & drop file here)")
        font_vinfo = self.lbl_video_info.GetFont()
        font_vinfo.SetPointSize(10)
        self.lbl_video_info.SetFont(font_vinfo)
        self.lbl_video_info.SetForegroundColour(wx.Colour(theme.get_text_muted()))
        files_sizer.Add(self.lbl_video_info, 0, wx.LEFT | wx.BOTTOM, 6)

        # Audio Picker Row
        a_row = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_audio = wx.StaticText(content_panel, label="Audio File:", size=(90, -1))
        a_row.Add(self.lbl_audio, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)

        self.txt_audio = wx.TextCtrl(content_panel)
        self.txt_audio.Bind(wx.EVT_TEXT, self.on_audio_path_changed)
        a_row.Add(self.txt_audio, 1, wx.EXPAND | wx.RIGHT, 6)

        btn_browse_audio = wx.Button(content_panel, label="Browse Audio...")
        btn_browse_audio.Bind(wx.EVT_BUTTON, self.on_browse_audio)
        a_row.Add(btn_browse_audio, 0)
        files_sizer.Add(a_row, 0, wx.EXPAND | wx.ALL, 4)

        # Audio Info Label
        self.lbl_audio_info = wx.StaticText(content_panel, label="No audio selected (Drag & drop file here)")
        font_ainfo = self.lbl_audio_info.GetFont()
        font_ainfo.SetPointSize(10)
        self.lbl_audio_info.SetFont(font_ainfo)
        self.lbl_audio_info.SetForegroundColour(wx.Colour(theme.get_text_muted()))
        files_sizer.Add(self.lbl_audio_info, 0, wx.LEFT | wx.BOTTOM, 6)

        # Output Picker Row
        o_row = wx.BoxSizer(wx.HORIZONTAL)
        lbl_out = wx.StaticText(content_panel, label="Output File:", size=(90, -1))
        o_row.Add(lbl_out, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)

        self.txt_output = wx.TextCtrl(content_panel)
        self.txt_output.Bind(wx.EVT_TEXT, self.on_output_path_changed)
        o_row.Add(self.txt_output, 1, wx.EXPAND | wx.RIGHT, 6)

        btn_browse_output = wx.Button(content_panel, label="Save As...")
        btn_browse_output.Bind(wx.EVT_BUTTON, self.on_browse_output)
        o_row.Add(btn_browse_output, 0, wx.RIGHT, 6)

        btn_same_folder = wx.Button(content_panel, label="⚡ Video Folder")
        btn_same_folder.Bind(wx.EVT_BUTTON, self.on_use_video_folder)
        o_row.Add(btn_same_folder, 0)

        files_sizer.Add(o_row, 0, wx.EXPAND | wx.ALL, 4)
        content_sizer.Add(files_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Drag and Drop support
        self.SetDropTarget(FileDropTargetHelper(self.on_dropped_files))

        # Section: Configuration Tabs (Audio, Video, Command Preview)
        self.notebook = wx.Notebook(content_panel)

        # Tab 1: Audio Settings
        tab_audio = wx.Panel(self.notebook)
        self._init_audio_tab(tab_audio)
        self.notebook.AddPage(tab_audio, "🎚️ Audio & Mixing")

        # Tab 2: Video & Timing Settings
        tab_video = wx.Panel(self.notebook)
        self._init_video_tab(tab_video)
        self.notebook.AddPage(tab_video, "🎬 Video & Duration")

        # Tab 3: FFmpeg Command Preview
        tab_cmd = wx.Panel(self.notebook)
        self._init_cmd_tab(tab_cmd)
        self.notebook.AddPage(tab_cmd, "💻 Live FFmpeg Command")

        content_sizer.Add(self.notebook, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Section: Progress Bar & Execution Actions
        action_panel = wx.Panel(content_panel)
        action_sizer = wx.BoxSizer(wx.VERTICAL)

        # Progress bar
        self.gauge = wx.Gauge(action_panel, range=100, size=(-1, 16))
        action_sizer.Add(self.gauge, 0, wx.EXPAND | wx.BOTTOM, 6)

        # Status & Action Buttons row
        bottom_row = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_status = wx.StaticText(action_panel, label="Status: Ready")
        font_status = self.lbl_status.GetFont()
        font_status.SetPointSize(11)
        font_status.SetWeight(wx.FONTWEIGHT_BOLD)
        self.lbl_status.SetFont(font_status)
        self.lbl_status.SetForegroundColour(wx.Colour(theme.get_text_primary()))
        bottom_row.Add(self.lbl_status, 1, wx.ALIGN_CENTER_VERTICAL)

        self.btn_cancel = wx.Button(action_panel, label="⏹ Cancel", size=(100, 36))
        self.btn_cancel.Bind(wx.EVT_BUTTON, self.on_cancel_merge)
        self.btn_cancel.Disable()
        bottom_row.Add(self.btn_cancel, 0, wx.RIGHT, 8)

        self.btn_start = wx.Button(action_panel, label="▶ Start Merge", size=(140, 36))
        self.btn_start.SetBackgroundColour(wx.Colour(theme.UBUNTU_ORANGE))
        self.btn_start.SetForegroundColour(wx.Colour("#FFFFFF"))
        font_btn = self.btn_start.GetFont()
        font_btn.SetWeight(wx.FONTWEIGHT_BOLD)
        self.btn_start.SetFont(font_btn)
        self.btn_start.Bind(wx.EVT_BUTTON, self.on_start_merge)
        bottom_row.Add(self.btn_start, 0)

        action_sizer.Add(bottom_row, 0, wx.EXPAND)
        action_panel.SetSizer(action_sizer)

        content_sizer.Add(action_panel, 0, wx.EXPAND | wx.ALL, 8)

        content_panel.SetSizer(content_sizer)
        main_sizer.Add(content_panel, 1, wx.EXPAND)

        main_panel.SetSizer(main_sizer)

    def _init_audio_tab(self, parent: wx.Panel):
        sizer = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(rows=4, cols=4, vgap=10, hgap=16)
        grid.AddGrowableCol(1)
        grid.AddGrowableCol(3)

        # Row 1: Audio Codec & Bitrate
        grid.Add(wx.StaticText(parent, label="Audio Codec:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.audio_codec_choices = [
            ("AAC (Standard for MP4/MKV)", "aac"),
            ("Stream Copy (Lossless / Fast)", "copy"),
            ("MP3 (libmp3lame)", "libmp3lame"),
            ("Opus (High Quality/Low Bitrate)", "libopus"),
            ("FLAC (Lossless Audio)", "flac"),
            ("AC3 (Dolby Digital)", "ac3"),
            ("PCM / WAV (Uncompressed)", "pcm_s16le"),
        ]
        self.combo_audio_codec = wx.ComboBox(
            parent,
            choices=[c[0] for c in self.audio_codec_choices],
            style=wx.CB_READONLY
        )
        self.combo_audio_codec.SetSelection(0)
        self.combo_audio_codec.Bind(wx.EVT_COMBOBOX, self.on_option_changed)
        grid.Add(self.combo_audio_codec, 1, wx.EXPAND)

        grid.Add(wx.StaticText(parent, label="Audio Bitrate:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.combo_audio_bitrate = wx.ComboBox(
            parent,
            choices=["Auto / Original", "96k", "128k", "192k", "256k", "320k"],
            style=wx.CB_READONLY
        )
        self.combo_audio_bitrate.SetSelection(3)  # 192k default
        self.combo_audio_bitrate.Bind(wx.EVT_COMBOBOX, self.on_option_changed)
        grid.Add(self.combo_audio_bitrate, 1, wx.EXPAND)

        # Row 2: Channels & Sample Rate
        grid.Add(wx.StaticText(parent, label="Channels:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.combo_audio_channels = wx.ComboBox(
            parent,
            choices=["Auto / Keep Original", "Stereo (2.0)", "Mono (1.0)", "5.1 Surround"],
            style=wx.CB_READONLY
        )
        self.combo_audio_channels.SetSelection(0)
        self.combo_audio_channels.Bind(wx.EVT_COMBOBOX, self.on_option_changed)
        grid.Add(self.combo_audio_channels, 1, wx.EXPAND)

        grid.Add(wx.StaticText(parent, label="Sample Rate:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.combo_samplerate = wx.ComboBox(
            parent,
            choices=["Auto / Keep Original", "44100 Hz (CD)", "48000 Hz (Video)", "96000 Hz (Hi-Res)"],
            style=wx.CB_READONLY
        )
        self.combo_samplerate.SetSelection(0)
        self.combo_samplerate.Bind(wx.EVT_COMBOBOX, self.on_option_changed)
        grid.Add(self.combo_samplerate, 1, wx.EXPAND)

        # Row 3: Audio Delay & Looping
        grid.Add(wx.StaticText(parent, label="Audio Delay (ms):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.spin_delay = wx.SpinCtrl(parent, min=-10000, max=10000, initial=0)
        self.spin_delay.Bind(wx.EVT_SPINCTRL, self.on_option_changed)
        grid.Add(self.spin_delay, 1, wx.EXPAND)

        self.chk_loop = wx.CheckBox(parent, label="Loop Audio if shorter than Video")
        self.chk_loop.Bind(wx.EVT_CHECKBOX, self.on_option_changed)
        grid.Add(self.chk_loop, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(wx.StaticText(parent, label=""), 0)

        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 12)

        # Audio Volume Sliders (Mix Mode)
        vol_box = wx.StaticBox(parent, label=" Audio Volumes (For Mix Mode) ")
        vol_sizer = wx.StaticBoxSizer(vol_box, wx.VERTICAL)

        v_slider_row = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_vid_vol = wx.StaticText(parent, label="Original Video Audio: 100%", size=(200, -1))
        self.slider_vid_vol = wx.Slider(parent, value=100, minValue=0, maxValue=200, style=wx.SL_HORIZONTAL)
        self.slider_vid_vol.Bind(wx.EVT_SLIDER, self.on_vid_vol_changed)
        v_slider_row.Add(self.lbl_vid_vol, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        v_slider_row.Add(self.slider_vid_vol, 1, wx.EXPAND)
        vol_sizer.Add(v_slider_row, 0, wx.EXPAND | wx.ALL, 4)

        a_slider_row = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_aud_vol = wx.StaticText(parent, label="Added Audio Track: 100%", size=(200, -1))
        self.slider_aud_vol = wx.Slider(parent, value=100, minValue=0, maxValue=200, style=wx.SL_HORIZONTAL)
        self.slider_aud_vol.Bind(wx.EVT_SLIDER, self.on_aud_vol_changed)
        a_slider_row.Add(self.lbl_aud_vol, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        a_slider_row.Add(self.slider_aud_vol, 1, wx.EXPAND)
        vol_sizer.Add(a_slider_row, 0, wx.EXPAND | wx.ALL, 4)

        sizer.Add(vol_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        parent.SetSizer(sizer)

    def _init_video_tab(self, parent: wx.Panel):
        sizer = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(rows=4, cols=4, vgap=10, hgap=16)
        grid.AddGrowableCol(1)
        grid.AddGrowableCol(3)

        # Row 1: Video Codec & Preset
        grid.Add(wx.StaticText(parent, label="Video Codec:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.video_codec_choices = [
            ("Stream Copy (Lossless / Fast)", "copy"),
            ("H.264 / AVC (libx264 - Best Compatibility)", "libx264"),
            ("H.265 / HEVC (libx265 - Smaller Size)", "libx265"),
            ("VP9 (libvpx-vp9 - WebM standard)", "libvpx-vp9"),
            ("AV1 (libsvtav1 - Next Gen)", "libsvtav1"),
            ("Disable Video (Audio Only)", "none"),
        ]
        self.combo_video_codec = wx.ComboBox(
            parent,
            choices=[c[0] for c in self.video_codec_choices],
            style=wx.CB_READONLY
        )
        self.combo_video_codec.SetSelection(0)
        self.combo_video_codec.Bind(wx.EVT_COMBOBOX, self.on_option_changed)
        grid.Add(self.combo_video_codec, 1, wx.EXPAND)

        grid.Add(wx.StaticText(parent, label="Preset:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.combo_preset = wx.ComboBox(
            parent,
            choices=["ultrafast", "fast", "medium", "slow", "veryslow"],
            style=wx.CB_READONLY
        )
        self.combo_preset.SetSelection(2)  # medium
        self.combo_preset.Bind(wx.EVT_COMBOBOX, self.on_option_changed)
        grid.Add(self.combo_preset, 1, wx.EXPAND)

        # Row 2: Duration Handling & CRF
        grid.Add(wx.StaticText(parent, label="Duration Handling:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.duration_choices = [
            ("Shortest Stream (-shortest)", "shortest"),
            ("Match Video Duration", "video"),
            ("Keep Longest Stream", "longest"),
            ("Custom Trim Range", "custom"),
        ]
        self.combo_duration = wx.ComboBox(
            parent,
            choices=[d[0] for d in self.duration_choices],
            style=wx.CB_READONLY
        )
        self.combo_duration.SetSelection(0)
        self.combo_duration.Bind(wx.EVT_COMBOBOX, self.on_option_changed)
        grid.Add(self.combo_duration, 1, wx.EXPAND)

        grid.Add(wx.StaticText(parent, label="CRF Quality (18-28):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.spin_crf = wx.SpinCtrl(parent, min=0, max=51, initial=23)
        self.spin_crf.Bind(wx.EVT_SPINCTRL, self.on_option_changed)
        grid.Add(self.spin_crf, 1, wx.EXPAND)

        # Row 3: Custom Trim Times
        grid.Add(wx.StaticText(parent, label="Trim Start (HH:MM:SS):"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.txt_trim_start = wx.TextCtrl(parent, value="")
        self.txt_trim_start.Bind(wx.EVT_TEXT, self.on_option_changed)
        grid.Add(self.txt_trim_start, 1, wx.EXPAND)

        grid.Add(wx.StaticText(parent, label="Trim End / Duration:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.txt_trim_end = wx.TextCtrl(parent, value="")
        self.txt_trim_end.Bind(wx.EVT_TEXT, self.on_option_changed)
        grid.Add(self.txt_trim_end, 1, wx.EXPAND)

        # Row 4: Extra Options
        self.chk_faststart = wx.CheckBox(parent, label="Web Faststart (-movflags +faststart)")
        self.chk_faststart.SetValue(True)
        self.chk_faststart.Bind(wx.EVT_CHECKBOX, self.on_option_changed)
        grid.Add(self.chk_faststart, 0, wx.ALIGN_CENTER_VERTICAL)

        sizer.Add(grid, 0, wx.EXPAND | wx.ALL, 12)
        parent.SetSizer(sizer)

    def _init_cmd_tab(self, parent: wx.Panel):
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Top row: Explanatory text & Copy button
        top_row = wx.BoxSizer(wx.HORIZONTAL)
        desc_label = wx.StaticText(
            parent,
            label="This FFmpeg command updates dynamically based on your selections:"
        )
        desc_label.SetForegroundColour(wx.Colour(theme.COLOR_TEXT_MUTED))
        top_row.Add(desc_label, 1, wx.ALIGN_CENTER_VERTICAL)

        btn_copy_cmd = wx.Button(parent, label="📋 Copy Command")
        btn_copy_cmd.Bind(wx.EVT_BUTTON, self.on_copy_command)
        top_row.Add(btn_copy_cmd, 0)
        sizer.Add(top_row, 0, wx.EXPAND | wx.ALL, 8)

        # Command Text Box
        self.txt_command_preview = wx.TextCtrl(
            parent,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_SIMPLE,
            size=(-1, 100)
        )
        self.txt_command_preview.SetMinSize(wx.Size(200, 80))
        self.txt_command_preview.SetBackgroundColour(wx.Colour(theme.COLOR_CONSOLE_BG))
        self.txt_command_preview.SetForegroundColour(wx.Colour(theme.COLOR_CONSOLE_FG))
        font_mono = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.txt_command_preview.SetFont(font_mono)
        sizer.Add(self.txt_command_preview, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Additional Extra Arguments Input
        extra_row = wx.BoxSizer(wx.HORIZONTAL)
        extra_row.Add(wx.StaticText(parent, label="Extra Arguments:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.txt_extra_args = wx.TextCtrl(parent)
        self.txt_extra_args.Bind(wx.EVT_TEXT, self.on_option_changed)
        extra_row.Add(self.txt_extra_args, 1, wx.EXPAND)
        sizer.Add(extra_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Live Console Log Viewer
        sizer.Add(wx.StaticText(parent, label="Live Process Output Log:"), 0, wx.LEFT | wx.TOP, 8)
        self.txt_live_log = wx.TextCtrl(
            parent,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_SIMPLE,
            size=(-1, 120)
        )
        self.txt_live_log.SetMinSize(wx.Size(200, 80))
        self.txt_live_log.SetBackgroundColour(wx.Colour("#111827"))
        self.txt_live_log.SetForegroundColour(wx.Colour("#9CA3AF"))
        self.txt_live_log.SetFont(font_mono)
        sizer.Add(self.txt_live_log, 1, wx.EXPAND | wx.ALL, 8)

        parent.SetSizer(sizer)

    # ================= Event Handlers =================

    def check_ffmpeg_status(self, prompt_if_missing: bool = True, notify_success: bool = False):
        status = FFmpegChecker.check_system()
        self.ffmpeg_installed = status["installed"]

        if self.ffmpeg_installed:
            self.banner_panel.Hide()
            self.banner_panel.GetParent().Layout()
            ver_short = status["version"].split("Copyright")[0].strip() if "Copyright" in status["version"] else status["version"]
            self.lbl_status.SetLabel(f"Ready (FFmpeg: {ver_short or 'Installed'})")
            self.lbl_status.SetForegroundColour(wx.Colour(theme.get_text_primary()))
            if notify_success:
                wx.MessageBox(f"FFmpeg is ready!\n\nPath: {status['ffmpeg_path']}\n{status['version']}",
                                "FFmpeg Verified", wx.OK | wx.ICON_INFORMATION, self)
        else:
            self.banner_panel.Show()
            self.banner_panel.GetParent().Layout()
            self.lbl_status.SetLabel("⚠️ FFmpeg Missing - Installation Required")
            self.lbl_status.SetForegroundColour(wx.Colour(theme.get_danger_color()))
            if prompt_if_missing:
                dlg = FFmpegInstallDialog(self)
                if dlg.ShowModal() == wx.ID_OK:
                    self.check_ffmpeg_status(prompt_if_missing=False, notify_success=True)
                dlg.Destroy()

    def on_copy_install_command(self, event):
        cmd = "sudo apt update && sudo apt install -y ffmpeg"
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(cmd))
            wx.TheClipboard.Close()
            wx.MessageBox(f"Copied command to clipboard:\n\n{cmd}\n\nPaste into terminal to install.",
                            "Command Copied", wx.OK | wx.ICON_INFORMATION, self)

    def on_select_custom_ffmpeg(self, event):
        wildcard = "FFmpeg Executable (ffmpeg*)|ffmpeg*|All files (*.*)|*.*"
        dlg = wx.FileDialog(self, "Select ffmpeg Binary", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            if os.access(path, os.X_OK):
                FFmpegChecker.set_custom_paths(ffmpeg_path=path)
                self.check_ffmpeg_status(prompt_if_missing=False, notify_success=True)
                self.update_command_preview()
            else:
                wx.MessageBox("The selected file is not executable.", "Error", wx.OK | wx.ICON_ERROR, self)
        dlg.Destroy()

    def on_mode_changed(self, event):
        idx = self.mode_combo.GetSelection()
        mode_val = self.mode_choices[idx][1]
        self.builder.mode = mode_val

        # Update labels based on mode
        if mode_val == MergeMode.IMAGE_AUDIO:
            self.lbl_video.SetLabel("Image File:")
        elif mode_val == MergeMode.EXTRACT_AUDIO:
            self.lbl_video.SetLabel("Video File:")
            self.lbl_audio.Disable()
            self.txt_audio.Disable()
        else:
            self.lbl_video.SetLabel("Video File:")
            self.lbl_audio.Enable()
            self.txt_audio.Enable()

        self.update_command_preview()

    def on_browse_video(self, event):
        idx = self.mode_combo.GetSelection()
        mode_val = self.mode_choices[idx][1]

        if mode_val == MergeMode.IMAGE_AUDIO:
            wildcard = "Image files (*.png;*.jpg;*.jpeg;*.bmp;*.webp)|*.png;*.jpg;*.jpeg;*.bmp;*.webp|All files (*.*)|*.*"
            title = "Select Image File"
        else:
            wildcard = "Video files (*.mp4;*.mkv;*.mov;*.avi;*.webm;*.flv;*.m4v;*.ts)|*.mp4;*.mkv;*.mov;*.avi;*.webm;*.flv;*.m4v;*.ts|All files (*.*)|*.*"
            title = "Select Video File"

        dlg = wx.FileDialog(self, title, wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.txt_video.SetValue(dlg.GetPath())
        dlg.Destroy()

    def on_browse_audio(self, event):
        wildcard = "Audio files (*.mp3;*.wav;*.aac;*.m4a;*.flac;*.ogg;*.opus;*.wma)|*.mp3;*.wav;*.aac;*.m4a;*.flac;*.ogg;*.opus;*.wma|All files (*.*)|*.*"
        dlg = wx.FileDialog(self, "Select Audio File", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            self.txt_audio.SetValue(dlg.GetPath())
        dlg.Destroy()

    def on_browse_output(self, event):
        idx = self.mode_combo.GetSelection()
        mode_val = self.mode_choices[idx][1]
        if mode_val == MergeMode.EXTRACT_AUDIO:
            wildcard = "MP3 Audio (*.mp3)|*.mp3|AAC Audio (*.aac;*.m4a)|*.aac;*.m4a|FLAC Audio (*.flac)|*.flac|WAV Audio (*.wav)|*.wav|All files (*.*)|*.*"
            default_name = "extracted_audio.mp3"
        else:
            wildcard = "MP4 Video (*.mp4)|*.mp4|MKV Video (*.mkv)|*.mkv|MOV Video (*.mov)|*.mov|WebM Video (*.webm)|*.webm|All files (*.*)|*.*"
            default_name = "merged_output.mp4"

        dlg = wx.FileDialog(self, "Save Merged Output File", wildcard=wildcard,
                             defaultFile=default_name, style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            self.txt_output.SetValue(dlg.GetPath())
        dlg.Destroy()

    def on_use_video_folder(self, event):
        v_path = self.txt_video.GetValue().strip()
        if not v_path:
            wx.MessageBox("Please select a video file first.", "Notice", wx.OK | wx.ICON_INFORMATION, self)
            return

        v_dir = os.path.dirname(v_path)
        v_base, v_ext = os.path.splitext(os.path.basename(v_path))
        idx = self.mode_combo.GetSelection()
        mode_val = self.mode_choices[idx][1]

        if mode_val == MergeMode.EXTRACT_AUDIO:
            out_file = os.path.join(v_dir, f"{v_base}_audio.mp3")
        else:
            out_ext = v_ext if v_ext else ".mp4"
            out_file = os.path.join(v_dir, f"{v_base}_merged{out_ext}")

        self.txt_output.SetValue(out_file)

    def on_dropped_files(self, filenames):
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if ext in [".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".ts", ".m4v"]:
                self.txt_video.SetValue(f)
            elif ext in [".mp3", ".wav", ".aac", ".m4a", ".flac", ".ogg", ".opus"]:
                self.txt_audio.SetValue(f)
            elif ext in [".png", ".jpg", ".jpeg", ".webp"] and self.builder.mode == MergeMode.IMAGE_AUDIO:
                self.txt_video.SetValue(f)

    def on_video_path_changed(self, event):
        v_path = self.txt_video.GetValue().strip()
        self.builder.video_path = v_path

        # Auto suggest output path if empty
        if v_path and os.path.exists(v_path) and not self.txt_output.GetValue().strip():
            v_dir = os.path.dirname(v_path)
            v_base, v_ext = os.path.splitext(os.path.basename(v_path))
            out_name = f"{v_base}_merged{v_ext or '.mp4'}"
            self.txt_output.SetValue(os.path.join(v_dir, out_name))

        # Probe video
        if v_path and os.path.exists(v_path):
            threading.Thread(target=self._async_probe_video, args=(v_path,), daemon=True).start()
        else:
            self.lbl_video_info.SetLabel("No valid video selected")

        self.update_command_preview()

    def _async_probe_video(self, v_path: str):
        info = MediaProbe.probe_file(v_path)
        self.builder.video_duration = info["duration"]
        parts = []
        if info["resolution"]:
            parts.append(info["resolution"])
        if info["fps"] > 0:
            parts.append(f"{info['fps']} fps")
        if info["video_codec"]:
            parts.append(info["video_codec"])
        if info["duration_str"]:
            parts.append(f"Duration: {info['duration_str']}")
        if info["filesize_str"]:
            parts.append(info["filesize_str"])

        info_text = " | ".join(parts) if parts else "Video loaded"
        def _set_v():
            self.lbl_video_info.SetForegroundColour(wx.Colour(theme.get_text_muted()))
            self.lbl_video_info.SetLabel(f"🎬 {info_text}")
            self.lbl_video_info.Refresh()
        wx.CallAfter(_set_v)
        wx.CallAfter(self.update_command_preview)

    def on_audio_path_changed(self, event):
        a_path = self.txt_audio.GetValue().strip()
        self.builder.audio_path = a_path

        if a_path and os.path.exists(a_path):
            threading.Thread(target=self._async_probe_audio, args=(a_path,), daemon=True).start()
        else:
            self.lbl_audio_info.SetLabel("No valid audio selected")

        self.update_command_preview()

    def _async_probe_audio(self, a_path: str):
        info = MediaProbe.probe_file(a_path)
        self.builder.audio_duration = info["duration"]
        parts = []
        if info["audio_codec"]:
            parts.append(info["audio_codec"].upper())
        if info["sample_rate"] > 0:
            parts.append(f"{info['sample_rate']} Hz")
        if info["audio_channels"] > 0:
            ch_str = "Mono" if info["audio_channels"] == 1 else ("Stereo" if info["audio_channels"] == 2 else f"{info['audio_channels']} ch")
            parts.append(ch_str)
        if info["duration_str"]:
            parts.append(f"Duration: {info['duration_str']}")
        if info["filesize_str"]:
            parts.append(info["filesize_str"])

        info_text = " | ".join(parts) if parts else "Audio loaded"
        def _set_a():
            self.lbl_audio_info.SetForegroundColour(wx.Colour(theme.get_text_muted()))
            self.lbl_audio_info.SetLabel(f"🎵 {info_text}")
            self.lbl_audio_info.Refresh()
        wx.CallAfter(_set_a)
        wx.CallAfter(self.update_command_preview)

    def on_output_path_changed(self, event):
        self.builder.output_path = self.txt_output.GetValue().strip()
        self.update_command_preview()

    def on_vid_vol_changed(self, event):
        val = self.slider_vid_vol.GetValue()
        self.lbl_vid_vol.SetLabel(f"Original Video Audio: {val}%")
        self.builder.video_volume = val / 100.0
        self.update_command_preview()

    def on_aud_vol_changed(self, event):
        val = self.slider_aud_vol.GetValue()
        self.lbl_aud_vol.SetLabel(f"Added Audio Track: {val}%")
        self.builder.audio_volume = val / 100.0
        self.update_command_preview()

    def on_option_changed(self, event):
        # Audio Codec
        a_codec_idx = self.combo_audio_codec.GetSelection()
        self.builder.audio_codec = self.audio_codec_choices[a_codec_idx][1]

        # Audio Bitrate
        b_sel = self.combo_audio_bitrate.GetStringSelection()
        self.builder.audio_bitrate = "auto" if "Auto" in b_sel else b_sel

        # Audio Channels
        ch_sel = self.combo_audio_channels.GetStringSelection()
        if "Stereo" in ch_sel:
            self.builder.audio_channels = "2"
        elif "Mono" in ch_sel:
            self.builder.audio_channels = "1"
        elif "5.1" in ch_sel:
            self.builder.audio_channels = "6"
        else:
            self.builder.audio_channels = "auto"

        # Sample Rate
        sr_sel = self.combo_samplerate.GetStringSelection()
        if "44100" in sr_sel:
            self.builder.audio_samplerate = "44100"
        elif "48000" in sr_sel:
            self.builder.audio_samplerate = "48000"
        elif "96000" in sr_sel:
            self.builder.audio_samplerate = "96000"
        else:
            self.builder.audio_samplerate = "auto"

        # Delay & Loop
        self.builder.audio_delay_ms = self.spin_delay.GetValue()
        self.builder.loop_audio = self.chk_loop.GetValue()

        # Video Codec
        v_codec_idx = self.combo_video_codec.GetSelection()
        self.builder.video_codec = self.video_codec_choices[v_codec_idx][1]

        # Preset & CRF
        self.builder.video_preset = self.combo_preset.GetStringSelection()
        self.builder.video_crf = self.spin_crf.GetValue()

        # Duration Mode
        dur_idx = self.combo_duration.GetSelection()
        self.builder.duration_mode = self.duration_choices[dur_idx][1]

        # Trim
        self.builder.custom_start_time = self.txt_trim_start.GetValue().strip()
        self.builder.custom_end_time = self.txt_trim_end.GetValue().strip()

        # Faststart & Extra
        self.builder.faststart = self.chk_faststart.GetValue()
        self.builder.extra_args = self.txt_extra_args.GetValue().strip()

        self.update_command_preview()

    def update_command_preview(self):
        cmd_str = self.builder.get_command_string(validate=False)
        self.txt_command_preview.SetValue(cmd_str)

    def on_copy_command(self, event):
        cmd_str = self.txt_command_preview.GetValue().strip()
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(cmd_str))
            wx.TheClipboard.Close()
            wx.MessageBox("Command copied to clipboard!", "Copied", wx.OK | wx.ICON_INFORMATION, self)

    # ================= Execution =================

    def on_start_merge(self, event):
        # 1. Verify FFmpeg installation
        if not self.ffmpeg_installed:
            dlg = FFmpegInstallDialog(self)
            res = dlg.ShowModal()
            dlg.Destroy()
            if res == wx.ID_OK:
                self.check_ffmpeg_status(prompt_if_missing=False)
            if not self.ffmpeg_installed:
                return

        # 2. Build and validate command
        try:
            cmd_args = self.builder.build_command_args(validate=True)
        except Exception as e:
            wx.MessageBox(str(e), "Invalid Configuration", wx.OK | wx.ICON_ERROR, self)
            return

        # 3. Check overwrite if file exists
        out_path = self.builder.output_path
        if os.path.exists(out_path):
            resp = wx.MessageBox(f"Output file already exists:\n{out_path}\n\nDo you want to overwrite it?",
                                 "Confirm Overwrite", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION, self)
            if resp != wx.YES:
                return

        # 4. Prepare UI for execution
        self.btn_start.Disable()
        self.btn_cancel.Enable()
        self.gauge.SetValue(0)
        self.lbl_status.SetLabel("⚡ Processing started...")
        self.lbl_status.SetForegroundColour(wx.Colour(theme.get_processing_color()))
        self.lbl_status.Refresh()
        self.txt_live_log.Clear()
        self.txt_live_log.AppendText(f"Starting merge at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # 5. Determine total duration for progress calculation
        total_dur = self.builder.video_duration or self.builder.audio_duration or 0.0

        # 6. Launch merger task
        self.current_task = MergerTask(
            cmd_args=cmd_args,
            total_duration=total_dur,
            output_path=out_path,
            on_progress=self._task_progress,
            on_log=self._task_log,
            on_complete=self._task_complete,
        )
        self.current_task.start()

    def _task_progress(self, pct: float, curr_time: str, speed: str, line: str):
        def _update():
            self.gauge.SetValue(int(pct))
            status_text = f"⚡ Processing: {pct:.1f}% | Time: {curr_time}"
            if speed:
                status_text += f" | Speed: {speed}"
            self.lbl_status.SetLabel(status_text)
            self.lbl_status.SetForegroundColour(wx.Colour(theme.get_processing_color()))
            self.lbl_status.Refresh()
        wx.CallAfter(_update)

    def _task_log(self, line: str):
        def _append():
            self.txt_live_log.AppendText(line + "\n")
        wx.CallAfter(_append)

    def _task_complete(self, success: bool, return_code: int, message: str, output_path: str):
        def _done():
            self.btn_start.Enable()
            self.btn_cancel.Disable()
            if success:
                self.gauge.SetValue(100)
                self.lbl_status.SetLabel("✔ Merge Completed Successfully! 🎉")
                self.lbl_status.SetForegroundColour(wx.Colour(theme.get_success_color()))
                self.lbl_status.Refresh()

                # Success Dialog with actions
                dlg = wx.MessageDialog(
                    self,
                    f"Video & Audio merged successfully!\n\nFile saved to:\n{output_path}\n\nWould you like to open the output folder?",
                    "Merge Complete",
                    wx.YES_NO | wx.ICON_INFORMATION
                )
                dlg.SetYesNoLabels("Open Folder", "Close")
                if dlg.ShowModal() == wx.ID_YES:
                    self._open_folder(output_path)
                dlg.Destroy()
            else:
                self.lbl_status.SetLabel(f"✘ Failed: {message}")
                self.lbl_status.SetForegroundColour(wx.Colour(theme.get_danger_color()))
                self.lbl_status.Refresh()
                wx.MessageBox(f"Processing did not complete:\n\n{message}", "Error", wx.OK | wx.ICON_ERROR, self)

        wx.CallAfter(_done)

    def _open_folder(self, filepath: str):
        folder = os.path.dirname(filepath)
        if os.path.isdir(folder):
            try:
                subprocess.Popen(["xdg-open", folder])
            except Exception as e:
                wx.MessageBox(f"Could not open file manager: {e}", "Notice", wx.OK, self)

    def on_cancel_merge(self, event):
        if self.current_task and self.current_task.is_running:
            self.lbl_status.SetLabel("⏹ Cancelling operation...")
            self.lbl_status.SetForegroundColour(wx.Colour(theme.get_warning_color()))
            self.lbl_status.Refresh()
            self.current_task.cancel()

    def show_install_dialog(self):
        dlg = FFmpegInstallDialog(self)
        if dlg.ShowModal() == wx.ID_OK:
            self.check_ffmpeg_status(prompt_if_missing=False, notify_success=True)
        dlg.Destroy()

    def on_close(self, event):
        if self.current_task and self.current_task.is_running:
            resp = wx.MessageBox("A merge operation is currently running. Cancel and exit?",
                                 "Confirm Exit", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION, self)
            if resp != wx.YES:
                event.Veto()
                return
            self.current_task.cancel()
        event.Skip()


def run_app():
    app = wx.App(False)
    frame = MainWindow()
    frame.Show()
    if not frame.ffmpeg_installed:
        wx.CallAfter(frame.show_install_dialog)
    app.MainLoop()


if __name__ == "__main__":
    run_app()
