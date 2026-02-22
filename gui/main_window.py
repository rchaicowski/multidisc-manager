"""
RomMate - ROM companion tool
Copyright (C) 2026 Rodrigo

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    import tkinter as tk
    DND_AVAILABLE = True
except ImportError:
    import tkinter as tk
    DND_AVAILABLE = False
    print("Warning: tkinterdnd2 not available. Drag & drop disabled.")
from tkinter import filedialog, scrolledtext, messagebox, ttk
import os
import re
from pathlib import Path
import threading
import subprocess
import platform
import shutil
from gui.theme import Theme
from gui.settings_panel import SettingsPanel
from utils.sounds import SoundPlayer
from core.file_utils import normalize_path, detect_available_formats, find_multidisc_games, create_m3u_file
from gui.dialogs import show_format_choice_dialog, show_info_dialog
from core.chd_converter import CHDConverter
from core.m3u_creator import M3UCreator
from core.rom_health import ROMHealthChecker
from utils.config import Config

class RomMateGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("RomMate")
        self.root.geometry("850x1000")
        self.root.resizable(True, True)

        # Use theme colors
        self.bg_dark = Theme.BG_DARK
        self.bg_frame = Theme.BG_FRAME
        self.text_light = Theme.TEXT_LIGHT
        self.text_gray = Theme.TEXT_GRAY
        self.accent_blue = Theme.ACCENT_BLUE
        self.accent_green = Theme.ACCENT_GREEN
        self.accent_red = Theme.ACCENT_RED
        self.accent_orange = Theme.ACCENT_ORANGE

        # Configure root background
        self.root.configure(bg=self.bg_dark)

        # Variables
        self.folder_path = tk.StringVar()
        self.operation_mode = tk.StringVar(value="chd")
        self.m3u_file_type = tk.StringVar(value="all")

        # Load config
        self.config = Config()

        # CHD conversion options
        self.delete_after_conversion = tk.BooleanVar(value=False)

        # Sound player
        self.sound_player = SoundPlayer()
        self.sound_player.volume = self.config.get('sound_volume', 1.0)
        self.sound_player.sounds_enabled = self.config.get('sound_enabled', True)
        self.sounds_enabled = tk.BooleanVar(value=self.sound_player.sounds_enabled)

        # CHD converter
        self.chd_converter = CHDConverter()

        # M3U creator
        self.m3u_creator = M3UCreator()

        # ROM health checker
        self.rom_health = ROMHealthChecker()

        # Processing state
        self.is_processing = False
        self.cancel_requested = False
        self.spinner_running = False
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.spinner_index = 0

        self.create_widgets()

        # Create settings panel
        self.settings_panel = SettingsPanel(
            self.root,
            self.config,
            callbacks={
                'get_sounds_enabled': lambda: self.sounds_enabled.get(),
                'on_sound_toggle': self.on_sound_toggle,
                'get_delete_after_conversion': lambda: self.delete_after_conversion.get(),
                'on_delete_toggle': self.on_delete_toggle,
                'on_volume_change': self.on_volume_change,
                'show_help': self.show_info,
                'on_close': self.hide_settings_panel
            }
        )

        # Enable drag and drop if available
        if DND_AVAILABLE:
            self.setup_drag_and_drop()

    def start_spinner(self):
        """Start the spinner animation"""
        self.spinner_running = True
        self.update_spinner()

    def stop_spinner(self):
        """Stop the spinner animation"""
        self.spinner_running = False

    def update_spinner(self):
        """Update spinner animation"""
        if self.spinner_running:
            spinner = self.spinner_chars[self.spinner_index]
            current_text = self.status_title.cget("text")

            # Remove old spinner if present
            if any(char in current_text for char in self.spinner_chars):
                current_text = (
                    current_text.split()[0] + " " +
                                       " ".join(current_text.split()[1:-1])
                )

            # Add new spinner
            self.status_title.config(text=f"{current_text} {spinner}")

            self.spinner_index = (self.spinner_index +
                                  1) % len(self.spinner_chars)
            self.root.after(100, self.update_spinner)  # Update every 100ms

    def show_main_panel(self):
        """Show the main configuration panel"""
        self.main_container.pack(fill="both", expand=True, padx=30, pady=20)
        self.processing_panel.pack_forget()

    def show_processing_panel(self):
        """Show the processing panel and hide main panel"""
        self.main_container.pack_forget()
        self.processing_panel.pack(fill="both", expand=True, padx=30, pady=20)

        # Reset cancellation flag
        self.cancel_requested = False

        # Reset processing panel
        self.status_title.config(text="Starting", fg=self.text_light)
        self.status_subtitle.config(text="Initializing")
        self.file_counter_label.config(text="0 / 0 files")
        self.current_file_label.config(text="")

        # Clear log
        self.processing_log.config(state="normal")
        self.processing_log.delete(1.0, tk.END)
        self.processing_log.config(state="disabled")

        # Show cancel button, hide completion buttons
        self.cancel_frame.pack(pady=10)
        self.completion_frame.pack_forget()

        # Start spinner
        self.start_spinner()

    def update_processing_status(
        self, title, subtitle, progress=None, total=None, current_file=""
    ):
        """Update the processing panel with current status"""
        # Stop spinner temporarily to update text
        was_spinning = self.spinner_running
        if was_spinning:
            self.stop_spinner()

        self.status_title.config(text=title)
        self.status_subtitle.config(text=subtitle)

        if progress is not None and total is not None and total > 0:
            self.file_counter_label.config(text=f"{progress} / {total} files")

        if current_file:
            self.current_file_label.config(text=f"📄 {current_file}")

        # Restart spinner if it was running
        if was_spinning:
            self.start_spinner()

        self.root.update_idletasks()

    def log_to_processing(self, message):
        """Add a message to the processing log"""
        self.processing_log.config(state="normal")
        self.processing_log.insert(tk.END, message + "\n")
        self.processing_log.see(tk.END)
        self.processing_log.config(state="disabled")
        self.root.update_idletasks()

    def animate_processing_dots(self, text):
        """Update the animation line in the processing log"""
        try:
            # Insert or update animation on its own line
            self.processing_log.config(state='normal')
            
            # Get current content
            current_text = self.processing_log.get("end-2c linestart", "end-1c")
            
            # If last line starts with "   Processing", update it
            if current_text.strip().startswith("Processing"):
                log_position = self.processing_log.index("end-2c linestart")
                self.processing_log.delete(log_position, "end-1c")
                self.processing_log.insert(log_position, text + "\n")
            else:
                # Add new line for animation
                self.processing_log.insert("end", text + "\n")
            
            self.processing_log.config(state='disabled')
            self.processing_log.see("end")
            self.root.update_idletasks()
        except Exception as e:
            # If animation fails, just skip it
            pass

    def setup_drag_and_drop(self):
        """Enable drag and drop for folder selection"""
        # Make the folder entry accept drops
        self.folder_entry.drop_target_register(DND_FILES)
        self.folder_entry.dnd_bind('<<Drop>>', self.on_drop)

    def on_drop(self, event):
        """Handle dropped files/folders"""
        try:
            # Get the dropped path (remove curly braces if present)
            dropped_path = event.data.strip('{}').strip()
            
            # Handle multiple paths (take first one)
            if ' ' in dropped_path and not os.path.exists(dropped_path):
                dropped_path = dropped_path.split()[0].strip('{}')
            
            # Normalize the path
            dropped_path = normalize_path(dropped_path)
            
            # Check if it's a directory
            if os.path.isdir(dropped_path):
                self.update_folder_display(dropped_path)
                self.config.set('last_folder', dropped_path)
            else:
                # If a file was dropped, use its parent directory
                parent_dir = os.path.dirname(dropped_path)
                self.update_folder_display(parent_dir)
                self.config.set('last_folder', parent_dir)
        except Exception as e:
            print(f"Error handling drop: {e}")    

    def add_placeholder_to_entry(self):
        """Add placeholder text to folder entry"""
        placeholder = "⬇️  Drop folder here"
        
        # Center the placeholder text
        self.folder_entry.config(justify='center')
        
        # Set placeholder if empty
        if not self.folder_path.get():
            self.folder_entry.insert(0, placeholder)
            self.folder_entry.config(fg=self.text_gray)
        
        # Remove placeholder on click
        def on_focus_in(event):
            if self.folder_entry.get() == placeholder:
                self.folder_entry.delete(0, tk.END)
                self.folder_entry.config(fg=self.text_light, justify='left')
        
        # Restore placeholder if empty
        def on_focus_out(event):
            if not self.folder_entry.get():
                self.folder_entry.insert(0, placeholder)
                self.folder_entry.config(fg=self.text_gray, justify='center')
        
        self.folder_entry.bind('<FocusIn>', on_focus_in)
        self.folder_entry.bind('<FocusOut>', on_focus_out)

    def update_folder_display(self, folder):
        """Update the folder entry with selected path"""
        self.folder_path.set(folder)
        self.folder_entry.config(fg=self.text_light, justify='left')

    def show_completion(self, success=True, converted=0, skipped=0, failed=0):
        """Show completion state in processing panel"""
        # Stop spinner
        self.stop_spinner()

        # Hide cancel button, show completion buttons
        self.cancel_frame.pack_forget()

        # Play sound
        self.sound_player.play("success" if success else "fail", self.sound_player.volume)

        # Determine the operation type
        mode = self.operation_mode.get()
        
        if mode == "health":
            # ROM Health Check completion
            if success and failed == 0:
                self.status_title.config(
                    text="✅ All ROMs Verified Successfully!", fg=self.accent_green
                )
                self.status_subtitle.config(text="All CHD files passed verification")
                self.processing_panel.config(bg="#1b5e20")
            elif converted > 0:
                self.status_title.config(
                    text="⚠️ Health Check Complete with Issues", fg=self.accent_orange
                )
                self.status_subtitle.config(text="Some files failed verification - check details above")
                self.processing_panel.config(bg="#f57f17")
            else:
                self.status_title.config(
                    text="❌ Health Check Failed", fg=self.accent_red
                )
                self.status_subtitle.config(text="No files verified successfully")
                self.processing_panel.config(bg="#b71c1c")
        else:
            # Existing CHD/M3U completion logic
            if success:
                self.status_title.config(
                    text="✅ Completed Successfully!", fg=self.accent_green
                )
                self.status_subtitle.config(text="All operations finished")
                self.processing_panel.config(bg="#1b5e20")
            else:
                self.status_title.config(
                    text="⚠️ Completed with Errors", fg=self.accent_red)
                self.status_subtitle.config(
                    text="Some operations failed - check details below"
                )
                self.processing_panel.config(bg="#b71c1c")

        # Show completion buttons
        self.completion_frame.pack(pady=20)

        self.root.update_idletasks()

    def reset_and_return(self):
        """Reset state and return to main panel"""
        self.is_processing = False
        self.processing_panel.config(bg=self.bg_frame)
        self.show_main_panel()

    def cancel_processing(self):
        """Cancel the current processing operation"""
        if not self.is_processing:
            return
        
        response = messagebox.askyesno(
            "Cancel Processing",
            "Are you sure you want to cancel?\n\n"
            "Any incomplete CHD files will be deleted.",
            icon='warning'
        )
        
        if response:
            self.cancel_requested = True
            self.log_to_processing("\n⚠️ Cancellation requested...")
            self.log_to_processing("Cleaning up and returning to main screen...")



    def create_widgets(self):
        # Main container (for configuration)
        self.main_container = tk.Frame(self.root, bg=self.bg_dark)

        # Title section with settings button
        title_outer = tk.Frame(self.main_container, bg=self.bg_dark)
        title_outer.pack(fill="x", pady=(10, 5))

        # Settings button (absolute positioned in top right)
        settings_btn = tk.Button(
            title_outer,
            text="⚙️",
            command=self.show_settings_panel,
            font=("Arial", 20),
            bg=self.bg_dark,
            fg=self.text_light,
            cursor="hand2",
            relief="flat",
            activebackground=self.bg_frame,
            bd=0,
            padx=10
        )
        settings_btn.place(relx=1.0, x=-10, y=0, anchor="ne")

        # Title (centered)
        title_label = tk.Label(
            title_outer,
            text="RomMate",
            font=("Arial", 24, "bold"),
            bg=self.bg_dark,
            fg=self.text_light,
        )
        title_label.pack()

        # Description
        desc_label = tk.Label(
            self.main_container,
            text="Your ROM companion - Convert, compress, and organize disc images",
            font=("Arial", 11),
            bg=self.bg_dark,
            fg=self.text_gray,
        )
        desc_label.pack(pady=(0, 30))

        # Folder selection frame
        folder_frame = tk.Frame(self.main_container, bg=self.bg_dark)
        folder_frame.pack(pady=10, fill="x")

        tk.Label(
            folder_frame,
            text="Game Folder:",
            font=("Arial", 11, "bold"),
            bg=self.bg_dark,
            fg=self.text_light,
        ).pack(side="left", padx=(0, 15))

        self.folder_entry = tk.Entry(
            folder_frame,
            textvariable=self.folder_path,
            width=50,
            font=("Arial", 11),
            bg=self.bg_frame,
            fg=self.text_light,
            insertbackground=self.text_light,
            relief="solid",
            bd=1,
            highlightthickness=2,
            highlightbackground=self.bg_dark,
            highlightcolor=self.accent_blue,
        )
        self.folder_entry.pack(side="left", padx=10, fill="x", expand=True, ipady=6)

        # Add placeholder text
        self.add_placeholder_to_entry()

        browse_btn = tk.Button(
            folder_frame,
            text="Browse",
            command=self.browse_folder,
            font=("Arial", 10, "bold"),
            bg=self.accent_green,
            fg="white",
            cursor="hand2",
            padx=20,
            pady=8,
            relief="flat",
            activebackground="#4caf50",
            activeforeground="white",
            bd=0,
        )
        browse_btn.pack(side="left")

        # ===== DISC-BASED ROMS SECTION =====
        disc_frame = tk.Frame(
            self.main_container, bg=self.bg_frame, relief="groove", bd=2
        )
        disc_frame.pack(pady=20, fill="x")

        tk.Label(
            disc_frame,
            text="📀 Disc-Based ROMs",
            font=("Arial", 12, "bold"),
            bg=self.bg_frame,
            fg=self.text_light,
        ).pack(anchor="w", padx=25, pady=(15, 10))

        tk.Radiobutton(
            disc_frame,
            text="💾 Convert to CHD (compress disc images)",
            variable=self.operation_mode,
            value="chd",
            font=("Arial", 11),
            command=self.update_info_section,
            bg=self.bg_frame,
            fg=self.text_light,
            selectcolor=self.bg_dark,
            activebackground=self.bg_frame,
            bd=0,
            highlightthickness=0,
        ).pack(anchor="w", padx=25, pady=8)

        tk.Radiobutton(
            disc_frame,
            text="📁 Create M3U Playlists (for multi-disc games)",
            variable=self.operation_mode,
            value="m3u",
            font=("Arial", 11),
            command=self.update_info_section,
            bg=self.bg_frame,
            fg=self.text_light,
            selectcolor=self.bg_dark,
            activebackground=self.bg_frame,
            bd=0,
            highlightthickness=0,
        ).pack(anchor="w", padx=25, pady=8)

        tk.Radiobutton(
            disc_frame,
            text="🔄 Convert to CHD + Create M3U Playlists",
            variable=self.operation_mode,
            value="both",
            font=("Arial", 11),
            command=self.update_info_section,
            bg=self.bg_frame,
            fg=self.text_light,
            selectcolor=self.bg_dark,
            activebackground=self.bg_frame,
            bd=0,
            highlightthickness=0,
        ).pack(anchor="w", padx=25, pady=8)

        tk.Frame(disc_frame, height=1, bg=self.text_gray).pack(
            fill="x", padx=25, pady=15
        )

        tk.Button(
            disc_frame,
            text="ℹ️  Help - When to use each?",
            command=self.show_info,
            font=("Arial", 10),
            bg=self.accent_blue,
            fg="white",
            cursor="hand2",
            relief="flat",
            padx=15,
            pady=6,
        ).pack(anchor="w", padx=25, pady=(0, 15))

        # ===== ROM TOOLS SECTION =====
        rom_tools_frame = tk.Frame(
            self.main_container, bg=self.bg_frame, relief="groove", bd=2
        )
        rom_tools_frame.pack(pady=20, fill="x")

        tk.Label(
            rom_tools_frame,
            text="🎮 ROM Tools (All ROM Types)",
            font=("Arial", 12, "bold"),
            bg=self.bg_frame,
            fg=self.text_light,
        ).pack(anchor="w", padx=25, pady=(15, 10))

        tk.Radiobutton(
            rom_tools_frame,
            text="🔍 Check ROM Health",
            variable=self.operation_mode,
            value="health",
            font=("Arial", 11),
            command=self.update_info_section,
            bg=self.bg_frame,
            fg=self.text_light,
            selectcolor=self.bg_dark,
            activebackground=self.bg_frame,
            bd=0,
            highlightthickness=0,
        ).pack(anchor="w", padx=25, pady=8)

        tk.Radiobutton(
            rom_tools_frame,
            text="✏️  Validate & Fix ROM Names",
            variable=self.operation_mode,
            value="validate",
            font=("Arial", 11),
            command=self.update_info_section,
            bg=self.bg_frame,
            fg=self.text_light,
            selectcolor=self.bg_dark,
            activebackground=self.bg_frame,
            bd=0,
            highlightthickness=0,
        ).pack(anchor="w", padx=25, pady=(8, 15))

        # ===== INFO SECTION (context-sensitive) =====
        self.info_frame = tk.Frame(
            self.main_container, bg=self.bg_frame, relief="groove", bd=2
        )
        self.info_frame.pack(pady=20, fill="x")

        self.info_title = tk.Label(
            self.info_frame,
            text="ℹ️  Info",
            font=("Arial", 12, "bold"),
            bg=self.bg_frame,
            fg=self.text_light,
        )
        self.info_title.pack(anchor="w", padx=25, pady=(15, 10))

        # Container for dynamic content
        self.info_content = tk.Frame(self.info_frame, bg=self.bg_frame)
        self.info_content.pack(fill="x", padx=25, pady=(0, 15))

        # Create all info sections (hidden by default)
        self.create_info_sections()

        # Process button
        self.process_btn = tk.Button(
            self.main_container,
            text="▶ Start Operation",
            command=self.run_process,
            font=("Arial", 14, "bold"),
            bg=self.accent_blue,
            fg="white",
            cursor="hand2",
            height=2,
            padx=50,
            relief="flat",
        )
        self.process_btn.pack(pady=30)

        # ===== PROCESSING PANEL =====
        self.processing_panel = tk.Frame(
            self.root, bg=self.bg_frame, relief="groove", bd=2
        )

        # Header with status
        status_header = tk.Frame(self.processing_panel, bg=self.bg_frame)
        status_header.pack(fill="x", pady=20, padx=30)

        self.status_title = tk.Label(
            status_header,
            text="Processing...",
            font=("Arial", 20, "bold"),
            bg=self.bg_frame,
            fg=self.text_light,
        )
        self.status_title.pack()

        self.status_subtitle = tk.Label(
            status_header,
            text="Starting operation",
            font=("Arial", 12),
            bg=self.bg_frame,
            fg=self.text_gray,
        )
        self.status_subtitle.pack(pady=(5, 0))

        # Current file being processed
        self.current_file_label = tk.Label(
            self.processing_panel,
            text="",
            font=("Consolas", 11),
            bg=self.bg_frame,
            fg=self.accent_blue,
            wraplength=700,
        )
        self.current_file_label.pack(pady=(10, 20))

        # File counter
        self.file_counter_label = tk.Label(
            self.processing_panel,
            text="0 / 0 files",
            font=("Arial", 13, "bold"),
            bg=self.bg_frame,
            fg=self.text_light,
        )
        self.file_counter_label.pack(pady=(0, 20))

        # Separator
        tk.Frame(self.processing_panel, height=2, bg=self.text_gray).pack(
            fill="x", padx=30, pady=10
        )

        # Details label
        tk.Label(
            self.processing_panel,
            text="Details:",
            font=("Arial", 11, "bold"),
            bg=self.bg_frame,
            fg=self.text_light,
        ).pack(anchor="w", padx=30, pady=(10, 5))

        # Processing log (smaller, for details)
        log_border = tk.Frame(
            self.processing_panel, bg=self.text_gray, relief="solid", bd=1
        )
        log_border.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        self.processing_log = scrolledtext.ScrolledText(
            log_border,
            width=80,
            height=12,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#d4d4d4",
            wrap=tk.WORD,
            state="disabled",
            relief="flat",
            bd=0,
            padx=10,
            pady=8,
        )
        self.processing_log.pack(fill="both", expand=True, padx=1, pady=1)

        # Cancel button (shown during processing)
        self.cancel_frame = tk.Frame(self.processing_panel, bg=self.bg_frame)
        self.cancel_frame.pack(pady=10)

        self.cancel_btn = tk.Button(
            self.cancel_frame,
            text="✖ Cancel",
            command=self.cancel_processing,
            font=("Arial", 11, "bold"),
            bg=self.accent_red,
            fg="white",
            cursor="hand2",
            padx=25,
            pady=10,
            relief="flat",
            activebackground="#d32f2f"
        )
        self.cancel_btn.pack()

        # Completion buttons (hidden until done)
        self.completion_frame = tk.Frame(
            self.processing_panel, bg=self.bg_frame)

        btn_frame = tk.Frame(self.completion_frame, bg=self.bg_frame)
        btn_frame.pack()

        tk.Button(
            btn_frame,
            text="✓ Done - Return to Main",
            command=self.reset_and_return,
            font=("Arial", 12, "bold"),
            bg=self.accent_green,
            fg="white",
            cursor="hand2",
            padx=30,
            pady=12,
            relief="flat",
            activebackground="#4caf50",
            bd=0,
        ).pack(side="left", padx=10)

        tk.Button(
            btn_frame,
            text="🔄 Process Another Folder",
            command=self.reset_and_return,
            font=("Arial", 11),
            bg=self.accent_blue,
            fg="white",
            cursor="hand2",
            padx=20,
            pady=12,
            relief="flat",
            activebackground="#1e88e5",
            bd=0,
        ).pack(side="left", padx=10)

        # Initialize UI
        self.show_main_panel()

    def show_info(self):
        """Show information about when to use each option"""
        show_info_dialog(self.root)

    def create_info_sections(self):
        """Create all info section contents"""
        # CHD Info
        self.chd_info = tk.Frame(self.info_content, bg=self.bg_frame)
        tk.Label(
            self.chd_info,
            text="Converts: CUE, GDI, CDI, ISO → CHD format",
            font=("Arial", 10),
            fg=self.text_gray,
            bg=self.bg_frame,
        ).pack(anchor="w", pady=(0, 5))
        tk.Label(
            self.chd_info,
            text="• CHD files are compressed and save 40-60% space",
            font=("Arial", 9),
            fg=self.text_gray,
            bg=self.bg_frame,
        ).pack(anchor="w", pady=(0, 5))
        tk.Label(
            self.chd_info,
            text="• Supported by RetroArch and most modern emulators",
            font=("Arial", 9),
            fg=self.text_gray,
            bg=self.bg_frame,
        ).pack(anchor="w")

        # M3U Info
        self.m3u_info = tk.Frame(self.info_content, bg=self.bg_frame)
        tk.Label(
            self.m3u_info,
            text="Scans for: CUE, GDI, CDI, ISO, CHD files",
            font=("Arial", 10),
            fg=self.text_gray,
            bg=self.bg_frame,
        ).pack(anchor="w", pady=(0, 10))
        
        info_box = tk.Frame(self.m3u_info, bg="#1a237e", relief="flat")
        info_box.pack(fill="x", pady=(0, 5))
        tk.Label(
            info_box,
            text="ℹ️ Note: All disc files must be in the same folder.\n"
            "    Works with PSX, PS2, Dreamcast, Saturn, Sega CD, and more!\n"
            "    If both CUE and CHD files exist, you'll be asked which to use.",
            font=("Arial", 9),
            bg="#1a237e",
            fg="#90caf9",
            justify="left",
        ).pack(padx=15, pady=12, anchor="w")

        # Both Info
        self.both_info = tk.Frame(self.info_content, bg=self.bg_frame)
        tk.Label(
            self.both_info,
            text="Step 1: Convert all disc images to CHD",
            font=("Arial", 10, "bold"),
            bg=self.bg_frame,
            fg=self.text_light,
        ).pack(anchor="w", pady=(0, 5))
        tk.Label(
            self.both_info,
            text="  Converts: CUE, GDI, CDI, ISO → CHD",
            font=("Arial", 9),
            fg=self.text_gray,
            bg=self.bg_frame,
        ).pack(anchor="w", pady=(0, 10))
        tk.Label(
            self.both_info,
            text="Step 2: Create M3U playlists for multi-disc games",
            font=("Arial", 10, "bold"),
            bg=self.bg_frame,
            fg=self.text_light,
        ).pack(anchor="w", pady=(0, 5))
        tk.Label(
            self.both_info,
            text="  Groups CHD files into playlists",
            font=("Arial", 9),
            fg=self.text_gray,
            bg=self.bg_frame,
        ).pack(anchor="w")

        # Health Check Info
        self.health_info = tk.Frame(self.info_content, bg=self.bg_frame)
        tk.Label(
            self.health_info,
            text="Verifies ROM file integrity:",
            font=("Arial", 10),
            fg=self.text_gray,
            bg=self.bg_frame,
        ).pack(anchor="w", pady=(0, 5))
        tk.Label(
            self.health_info,
            text="• Disc ROMs: Verify CHD integrity, check CUE/BIN matching",
            font=("Arial", 9),
            fg=self.text_gray,
            bg=self.bg_frame,
        ).pack(anchor="w", pady=(0, 3))
        tk.Label(
            self.health_info,
            text="• Cartridge ROMs: Calculate checksums, verify file headers",
            font=("Arial", 9),
            fg=self.text_gray,
            bg=self.bg_frame,
        ).pack(anchor="w", pady=(0, 3))
        tk.Label(
            self.health_info,
            text="• Compare against known good dumps",
            font=("Arial", 9),
            fg=self.text_gray,
            bg=self.bg_frame,
        ).pack(anchor="w")

        # Validate Names Info
        self.validate_info = tk.Frame(self.info_content, bg=self.bg_frame)
        tk.Label(
            self.validate_info,
            text="Checks and fixes ROM filenames:",
            font=("Arial", 10),
            fg=self.text_gray,
            bg=self.bg_frame,
        ).pack(anchor="w", pady=(0, 5))
        tk.Label(
            self.validate_info,
            text="• Compares against No-Intro/Redump databases",
            font=("Arial", 9),
            fg=self.text_gray,
            bg=self.bg_frame,
        ).pack(anchor="w", pady=(0, 3))
        tk.Label(
            self.validate_info,
            text="• Suggests correct naming conventions",
            font=("Arial", 9),
            fg=self.text_gray,
            bg=self.bg_frame,
        ).pack(anchor="w", pady=(0, 3))
        tk.Label(
            self.validate_info,
            text="• Detects region and version information",
            font=("Arial", 9),
            fg=self.text_gray,
            bg=self.bg_frame,
        ).pack(anchor="w")

        # Show CHD by default
        self.update_info_section()

    def update_info_section(self):
        """Update info section based on selected operation"""
        # Hide all
        for frame in [self.chd_info, self.m3u_info, self.both_info, 
                     self.health_info, self.validate_info]:
            frame.pack_forget()
        
        # Get selection (single variable for all operations)
        operation = self.operation_mode.get()
        
        if operation == "health":
            self.health_info.pack(fill="x")
            if hasattr(self, 'process_btn'):
                self.process_btn.config(text="▶ Check ROM Health")
                
        elif operation == "validate":
            self.validate_info.pack(fill="x")
            if hasattr(self, 'process_btn'):
                self.process_btn.config(text="▶ Validate ROM Names")
                
        elif operation == "chd":
            self.chd_info.pack(fill="x")
            if hasattr(self, 'process_btn'):
                self.process_btn.config(text="▶ Convert to CHD")
                
        elif operation == "m3u":
            self.m3u_info.pack(fill="x")
            if hasattr(self, 'process_btn'):
                self.process_btn.config(text="▶ Create M3U Files")
                
        elif operation == "both":
            self.both_info.pack(fill="x")
            if hasattr(self, 'process_btn'):
                self.process_btn.config(text="▶ Convert & Create M3U")

    def browse_folder(self):
        # Determine initial directory based on folder mode
        folder_mode = self.config.get('folder_mode', 'remember_last')
        
        if folder_mode == 'use_default':
            initial_dir = self.config.get('default_folder', str(Path.home()))
        else:
            initial_dir = self.config.get('last_folder', str(Path.home()))
        
        folder = filedialog.askdirectory(
            title="Select Game Folder",
            initialdir=initial_dir
        )
        
        if folder:
            folder = normalize_path(folder)
            self.update_folder_display(folder)
            
            # Always remember last folder (even in default mode)
            self.config.set('last_folder', folder)

    def run_process(self):
        """Handle the main process button"""
        folder = self.folder_path.get()
        
        if not folder:
            messagebox.showwarning("No Folder", "Please select a folder first.")
            return
        
        if not os.path.exists(folder):
            messagebox.showerror(
                "Error", f"Selected folder does not exist!\n\nPath: {folder}"
            )
            return
        
        # Get the operation mode
        mode = self.operation_mode.get()
        
        # Check if ROM tool is selected
        if mode == "health":
            self.check_rom_health()
            return
        elif mode == "validate":
            messagebox.showinfo("Coming Soon", "ROM Name Validator feature is under development!")
            return
        self.is_processing = True

        # Switch to processing panel
        self.show_processing_panel()

        # Run in separate thread
        if mode == "m3u":
            thread = threading.Thread(
                target=self.create_m3u_files, args=(folder,))
        elif mode == "chd":
            thread = threading.Thread(
                target=self.convert_to_chd, args=(folder,))
        else:  # both
            thread = threading.Thread(
                target=self.convert_and_create_m3u, args=(folder,)
            )
        thread.start()

    def convert_to_chd(self, folder):
        """Convert CUE/GDI/CDI/ISO files to CHD format"""
        try:
            self.update_processing_status(
                "CHD Conversion",
                "Checking for chdman tool...",
                0, 1
            )
            
            # Check for chdman
            self.chd_converter.chdman_path = self.chd_converter.find_chdman()
            if not self.chd_converter.chdman_path:
                self.log_to_processing("❌ ERROR: chdman not found!")
                
                # On Linux, offer to install automatically
                if platform.system() == 'Linux':
                    self.log_to_processing("\nOffering automatic installation...")
                    if self.chd_converter.prompt_install_chdman():
                        self.log_to_processing("\n⏳ Installation in progress.")
                        self.log_to_processing("Please complete installation in the terminal, then try again.")
                    else:
                        self.log_to_processing("\n❌ Installation cancelled.")
                else:
                    self.log_to_processing("\nchdman is required for CHD conversion.")
                    self.log_to_processing("It should be in the tools/ folder.")
                    messagebox.showerror(
                        "chdman Not Found",
                        "chdman is required for CHD conversion.\n\n"
                        "It should be bundled in the tools/ folder."
                    )
                
                self.show_completion(success=False)
                return
            
            # Test if chdman actually works
            try:
                test_result = subprocess.run(
                    [self.chd_converter.chdman_path, '--help'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if test_result.returncode != 0 and platform.system() == 'Linux':
                    if 'error while loading shared libraries' in test_result.stderr:
                        self.log_to_processing("❌ ERROR: chdman has missing dependencies!")
                        self.log_to_processing(f"Error: {test_result.stderr[:150]}")
                        
                        if self.chd_converter.prompt_install_chdman():
                            self.log_to_processing("\n⏳ Installation in progress.")
                            self.log_to_processing("Please complete installation in the terminal, then try again.")
                        else:
                            self.log_to_processing("\n❌ Installation cancelled.")
                        
                        self.show_completion(success=False)
                        return
            except Exception as e:
                self.log_to_processing(f"⚠️ Warning: Could not test chdman: {e}")
            
            self.log_to_processing(f"✓ Found chdman: {self.chd_converter.chdman_path}")
            
            self.update_processing_status(
                "CHD Conversion",
                "Scanning for disc images..."
            )
            
            # Convert all files in folder
            converted, skipped, failed = self.chd_converter.convert_folder(
                folder,
                delete_after=self.delete_after_conversion.get(),
                log_callback=self.log_to_processing,
                progress_callback=lambda current, total, filename: self.update_processing_status(
                    "Converting to CHD",
                    f"Processing file {current} of {total}",
                    current,
                    total,
                    filename
                ),
                animation_callback=self.animate_processing_dots,
                cancel_check=lambda: self.cancel_requested
            )
            
            # Check if user cancelled
            if self.cancel_requested:
                self.reset_and_return()
                return
            
            if converted == 0 and skipped == 0 and failed == 0:
                self.log_to_processing("\n❌ No convertible files found.")
                self.log_to_processing("Supported formats: CUE, GDI, CDI, ISO")
                messagebox.showinfo("No Files", "No convertible disc images found.")
                self.show_completion(success=False)
                return
            
            self.log_to_processing("\n" + "=" * 60)
            self.log_to_processing(f"✅ Converted: {converted} | ⏭️ Skipped: {skipped} | ❌ Failed: {failed}")
            self.log_to_processing("=" * 60)
            
            # Check if cancelled before showing success
            if self.cancel_requested:
                self.reset_and_return()
                return
            
            success = failed == 0
            self.show_completion(success=success, converted=converted, skipped=skipped, failed=failed)
            
            messagebox.showinfo(
                "Conversion Complete",
                f"CHD conversion finished!\n\nConverted: {converted}\nSkipped: {skipped}\nFailed: {failed}"
            )
        
        except Exception as e:
            self.log_to_processing(f"\n❌ ERROR: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
            self.show_completion(success=False)

    def create_m3u_files(self, folder):
        """Create M3U playlists for multi-disc games"""
        try:
            self.update_processing_status(
                "M3U Creator",
                "Detecting available disc formats..."
            )
            
            # Use M3U creator with auto-detection
            created, skipped, cancelled = self.m3u_creator.auto_detect_and_create(
                folder,
                log_callback=self.log_to_processing,
                progress_callback=lambda current, total, filename: self.update_processing_status(
                    "Creating M3U Playlists",
                    f"Processing game {current} of {total}",
                    current,
                    total,
                    filename
                ),
                format_choice_callback=lambda: show_format_choice_dialog(self.root)
            )
            
            if cancelled:
                # User cancelled - return to main panel immediately
                self.reset_and_return()
                return
            
            if created == 0 and skipped == 0:
                self.log_to_processing("❌ No multi-disc games found.")
                self.log_to_processing("\nMake sure files follow naming conventions like:")
                self.log_to_processing("  • Game Name (Disc 1).cue")
                self.log_to_processing("  • Game Name (Disc 2).chd")
                messagebox.showinfo("No Games Found", "No multi-disc games were found.")
                self.show_completion(success=False)
            else:
                self.log_to_processing(f"\n{'=' * 60}")
                self.log_to_processing(f"✅ Created: {created} | ⚠️ Skipped: {skipped}")
                self.log_to_processing(f"{'=' * 60}\n")
                self.log_to_processing("✅ ALL OPERATIONS COMPLETE!")
                self.log_to_processing(f"{'=' * 60}")
                
                self.show_completion(success=True, converted=created, skipped=skipped)
                
                messagebox.showinfo(
                    "M3U Creation Complete",
                    f"M3U playlist creation finished!\n\nCreated: {created}\nSkipped: {skipped}"
                )
        
        except Exception as e:
            self.log_to_processing(f"\n❌ ERROR: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
            self.show_completion(success=False)

         
    def convert_and_create_m3u(self, folder):
        """Convert to CHD then create M3U playlists"""
        try:
            self.update_processing_status(
                "CHD + M3U", "Step 1: Checking for chdman..."
            )
            
            # Check for chdman
            self.chd_converter.chdman_path = self.chd_converter.find_chdman()
            if not self.chd_converter.chdman_path:
                self.log_to_processing("❌ ERROR: chdman not found!")
                
                if platform.system() == "Linux":
                    if self.chd_converter.prompt_install_chdman():
                        self.log_to_processing("⏳ Installation in progress.")
                    else:
                        self.log_to_processing("❌ Installation cancelled.")
                else:
                    messagebox.showerror("chdman Not Found", "chdman is required.")
                
                self.show_completion(success=False)
                return
            
            # Test chdman
            try:
                test_result = subprocess.run(
                    [self.chd_converter.chdman_path, "--help"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if test_result.returncode != 0 and platform.system() == "Linux":
                    if "error while loading shared libraries" in test_result.stderr:
                        self.log_to_processing("❌ ERROR: chdman has missing dependencies!")
                        
                        if self.chd_converter.prompt_install_chdman():
                            self.log_to_processing("⏳ Installation in progress.")
                        else:
                            self.log_to_processing("❌ Installation cancelled.")
                        
                        self.show_completion(success=False)
                        return
            except Exception as e:
                self.log_to_processing(f"⚠️ Warning: Could not test chdman: {e}")
            
            self.log_to_processing(f"✓ Found chdman: {self.chd_converter.chdman_path}")
            
            # Step 1: Convert to CHD
            self.log_to_processing(f"\n=== STEP 1: CHD Conversion ===")
            
            converted, skipped, failed = self.chd_converter.convert_folder(
                folder,
                delete_after=self.delete_after_conversion.get(),
                log_callback=self.log_to_processing,
                progress_callback=lambda current, total, filename: self.update_processing_status(
                    "Step 1: Converting to CHD",
                    f"Processing file {current} of {total}",
                    current,
                    total,
                    filename
                ),
                animation_callback=self.animate_processing_dots,
                cancel_check=lambda: self.cancel_requested
            )
            
            if converted > 0 or skipped > 0:
                self.log_to_processing(f"\nStep 1 complete: Converted {converted} file(s)")
            else:
                self.log_to_processing("No files found to convert")
            
            # Step 2: Create M3U
            self.log_to_processing(f"\n=== STEP 2: M3U Creation ===\n")
            
            self.update_processing_status(
                "Step 2: Creating M3U",
                "Scanning for multi-disc games..."
            )
            
            # Only scan for CHD files since we just converted to CHD
            from core.file_utils import find_multidisc_games, create_m3u_file
            
            multidisc_games = find_multidisc_games(
                folder,
                extensions=["*.chd"],
                log_callback=self.log_to_processing
            )
            
            created = 0
            
            if multidisc_games:
                total_games = len(multidisc_games)
                self.log_to_processing(f"Found {total_games} multi-disc game(s)\n")
                
                for index, (game_name, disc_files) in enumerate(multidisc_games.items(), 1):
                    self.update_processing_status(
                        "Step 2: Creating M3U",
                        f"Processing game {index} of {total_games}",
                        index,
                        total_games,
                        f"{game_name}.m3u"
                    )
                    
                    if create_m3u_file(game_name, disc_files, folder, self.log_to_processing):
                        created += 1
                
                self.log_to_processing(f"\nStep 2 complete: Created {created} M3U file(s)")
            else:
                self.log_to_processing("No multi-disc games found")
            
            self.log_to_processing("\n" + "=" * 60)
            self.log_to_processing("✅ ALL OPERATIONS COMPLETE!")
            self.log_to_processing("=" * 60)
            
            # Check if cancelled before showing completion
            if self.cancel_requested:
                self.reset_and_return()
                return
            
            self.show_completion(success=True, converted=converted, skipped=0, failed=0)
        
        except Exception as e:
            self.log_to_processing(f"\n❌ ERROR: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
            self.show_completion(success=False)

    def check_rom_health(self):
        """Run ROM health check"""
        folder = self.folder_path.get()
        
        # Check if chdman is available (only needed for CHD)
        if not self.rom_health.find_chdman():
            response = messagebox.askyesno(
                "chdman Not Found",
                "chdman is required for CHD verification.\n\n"
                "Cartridge ROMs can still be checked.\n\n"
                "Would you like to install chdman now?",
                icon='warning'
            )
            if response:
                self.chd_converter.prompt_install_chdman()
                return
            # Continue without chdman (will skip CHD verification)
        
        # Switch to processing panel
        self.show_processing_panel()
        self.is_processing = True
        
        # Reset log
        self.processing_log.delete(1.0, tk.END)
        self.log_to_processing(f"🔍 ROM Health Check\n")
        self.log_to_processing(f"Folder: {folder}\n")
        self.log_to_processing("=" * 60)
        
        # Start spinner
        self.start_spinner()
        
        # Run health check in thread
        def run_check():
            try:
                results = self.rom_health.check_folder(
                    folder,
                    log_callback=self.log_to_processing,
                    progress_callback=lambda current, total, filename: self.update_processing_status(
                        "Checking ROM Health",
                        f"Verifying file {current} of {total}",
                        current,
                        total,
                        filename
                    ),
                    cancel_check=lambda: self.cancel_requested
                )
                
                # Check if cancelled
                if self.cancel_requested:
                    self.reset_and_return()
                    return
                
                # Calculate totals
                total_verified = (results['chd_verified'] + 
                                results['cue_verified'] + 
                                results['cart_verified'])
                total_issues = (results['chd_failed'] + 
                              results['cue_failed'] + 
                              results['cart_has_header'] + 
                              results['cart_unknown'] +
                              results['cart_failed'])
                total_hacks = results.get('cart_hacks', 0)
                
                # Show summary
                self.log_to_processing("\n" + "=" * 60)
                self.log_to_processing("📊 Summary:")
                self.log_to_processing("=" * 60)
                
                if results['chd_verified'] + results['chd_failed'] > 0:
                    self.log_to_processing(f"CHD Files: ✅ {results['chd_verified']} verified | ❌ {results['chd_failed']} failed")
                
                if results['cue_verified'] + results['cue_failed'] > 0:
                    self.log_to_processing(f"CUE/BIN: ✅ {results['cue_verified']} verified | ❌ {results['cue_failed']} failed")
                
                if (results['cart_verified'] + results['cart_has_header'] + 
                    results.get('cart_hacks', 0) + results['cart_unknown'] + results['cart_failed']) > 0:
                    self.log_to_processing(f"Cartridges: ✅ {results['cart_verified']} verified | "
                                         f"⚠️ {results['cart_has_header']} have headers | "
                                         f"🎨 {results.get('cart_hacks', 0)} ROM hacks | "
                                         f"❓ {results['cart_unknown']} unknown | "
                                         f"❌ {results['cart_failed']} failed")
                
                self.log_to_processing("=" * 60)
                
                # Check if cancelled
                if self.cancel_requested:
                    self.reset_and_return()
                    return
                
                # Offer to fix headers BEFORE showing completion
                if results.get('cart_has_header', 0) > 0:
                    self.root.after(100, lambda: self.offer_header_fix(results))
                
                # Show completion
                if total_issues == 0 and total_verified > 0:
                    # All verified, no issues (hacks are OK!)
                    self.show_completion(success=True, converted=total_verified, skipped=0, failed=0)
                elif total_verified > 0:
                    # Has some issues (unknown or failed)
                    self.show_completion(success=False, converted=total_verified, skipped=0, failed=total_issues)
                else:
                    # Nothing verified
                    self.show_completion(success=False, converted=0, skipped=0, failed=total_issues)
                
            except Exception as e:
                self.log_to_processing(f"\n❌ Error: {str(e)}")
                import traceback
                self.log_to_processing(traceback.format_exc())
                self.show_completion(success=False)
            finally:
                self.is_processing = False
        
        # Start thread
        thread = threading.Thread(target=run_check, daemon=True)
        thread.start()

    def offer_header_fix(self, results):
        """Offer to fix ROMs with external headers
        
        Args:
            results (dict): Health check results
        """
        # Find ROMs with headers
        roms_with_headers = []
        for result in results.get('all_results', []):
            if result.get('status') == 'has_header':
                roms_with_headers.append(result)
        
        if not roms_with_headers:
            return  # No headers to fix
        
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("External Headers Detected")
        dialog.configure(bg=self.bg_dark)
        dialog.transient(self.root)
        dialog.grab_set()

        # Set size and position
        dialog.update_idletasks()
        width = 650
        height = 600  # Increased height
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")

        # Prevent resizing smaller than minimum
        dialog.minsize(650, 600)
        
        # Title
        title_frame = tk.Frame(dialog, bg=self.accent_orange, height=60)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)
        
        tk.Label(
            title_frame,
            text="⚠️ External Copier Headers Detected",
            font=("Arial", 14, "bold"),
            bg=self.accent_orange,
            fg="white"
        ).pack(expand=True)
        
        # Content
        content = tk.Frame(dialog, bg=self.bg_dark, padx=20, pady=20)
        content.pack(fill="both", expand=True)
        
        # Explanation
        tk.Label(
            content,
            text=f"{len(roms_with_headers)} ROM(s) have external copier headers:",
            font=("Arial", 11, "bold"),
            bg=self.bg_dark,
            fg=self.text_light
        ).pack(anchor="w", pady=(0, 10))
        
        # ROM list with checkboxes
        list_frame = tk.Frame(content, bg=self.bg_frame, relief="sunken", bd=1)
        list_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # Scrollbar
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        rom_listbox = tk.Listbox(
            list_frame,
            bg=self.bg_frame,
            fg=self.text_light,
            font=("Arial", 10),
            selectmode=tk.MULTIPLE,
            yscrollcommand=scrollbar.set,
            relief="flat",
            highlightthickness=0
        )
        rom_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        scrollbar.config(command=rom_listbox.yview)
        
        # Populate list
        for rom in roms_with_headers:
            rom_listbox.insert(tk.END, f"• {rom['filename']} ({rom['header_size']} bytes)")
        
        # Select all by default
        rom_listbox.select_set(0, tk.END)
        
        # Info box
        info_frame = tk.Frame(content, bg="#1a237e", relief="flat", padx=15, pady=12)
        info_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(
            info_frame,
            text="ℹ️ What are external headers?\n\n"
                 "These are extra bytes added by old ROM copying devices.\n"
                 "They cause checksum mismatches with databases.\n\n"
                 "• Safe to remove (not part of original ROM)\n"
                 "• Improves compatibility with emulators\n"
                 "• Matches No-Intro standards",
            font=("Arial", 9),
            bg="#1a237e",
            fg="#90caf9",
            justify="left"
        ).pack()
        
        # Options
        backup_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            content,
            text="☑ Create backup before fixing (.backup extension)",
            variable=backup_var,
            font=("Arial", 10),
            bg=self.bg_dark,
            fg=self.text_light,
            selectcolor=self.bg_frame,
            activebackground=self.bg_dark,
            bd=0,
            highlightthickness=0
        ).pack(anchor="w", pady=(0, 15))
        
        # Buttons
        btn_frame = tk.Frame(content, bg=self.bg_dark)
        btn_frame.pack(fill="x")
        
        def fix_headers():
            selected = rom_listbox.curselection()
            if not selected:
                messagebox.showwarning("No Selection", "Please select ROMs to fix.")
                return
            
            # Close dialog first
            dialog.destroy()
            
            # Get folder path
            folder = self.folder_path.get()
            backup_folder = os.path.join(folder, "RomMate_Backups")
            
            # Create backup folder if it doesn't exist
            if backup_var.get():
                os.makedirs(backup_folder, exist_ok=True)
            
            # Fix selected ROMs
            fixed_roms = []
            failed_roms = []
            
            for idx in selected:
                rom = roms_with_headers[idx]
                
                # Create backup in subfolder if requested
                if backup_var.get():
                    import shutil
                    backup_path = os.path.join(backup_folder, os.path.basename(rom['path']))
                    try:
                        shutil.copy2(rom['path'], backup_path)
                    except Exception as e:
                        failed_roms.append((rom['filename'], f"Backup failed: {str(e)}"))
                        continue
                
                # Remove header (without creating .backup since we already backed up)
                success, msg = self.rom_health.cartridge_checker.remove_header(
                    rom['path'],
                    rom['header_size'],
                    create_backup=False  # We already created backup in folder
                )
                
                if success:
                    fixed_roms.append(rom)
                else:
                    failed_roms.append((rom['filename'], msg))
            
            # Re-verify all fixed ROMs
            if fixed_roms:
                verified_roms = []
                still_bad = []
                
                for rom in fixed_roms:
                    # Re-verify
                    result = self.rom_health.cartridge_checker.verify_rom(rom['path'])
                    
                    if result['status'] == 'verified':
                        verified_roms.append(rom['filename'])
                    else:
                        still_bad.append((rom['filename'], result.get('message', 'Unknown status')))
                
                # Show results
                if still_bad:
                    # Some didn't verify - keep backups!
                    msg = f"⚠️ Header removal completed but some ROMs still don't verify:\n\n"
                    msg += f"✅ Successfully verified: {len(verified_roms)}\n"
                    msg += f"❌ Still not verified: {len(still_bad)}\n\n"
                    msg += "Failed ROMs:\n"
                    for filename, status in still_bad:
                        msg += f"• {filename}: {status}\n"
                    msg += f"\n💾 Backups kept in: {backup_folder}"
                    messagebox.showwarning("Partial Success", msg)
                else:
                    # All verified successfully!
                    if backup_var.get():
                        # Offer to delete backups
                        response = messagebox.askyesno(
                            "Headers Removed Successfully!",
                            f"✅ Successfully removed headers from {len(verified_roms)} ROM(s)!\n"
                            f"✅ All ROMs verified as good dumps!\n\n"
                            f"Backups are stored in:\n{backup_folder}\n\n"
                            f"Would you like to delete the backup folder?",
                            icon='question'
                        )
                        
                        if response:
                            # Delete backup folder
                            import shutil
                            try:
                                shutil.rmtree(backup_folder)
                                messagebox.showinfo("Backups Deleted", "✅ Backup folder deleted successfully!")
                            except Exception as e:
                                messagebox.showerror("Error", f"Could not delete backup folder:\n{str(e)}")
                        else:
                            messagebox.showinfo("Backups Kept", f"💾 Backups kept in:\n{backup_folder}")
                    else:
                        messagebox.showinfo(
                            "Headers Removed Successfully!",
                            f"✅ Successfully removed headers from {len(verified_roms)} ROM(s)!\n"
                            f"✅ All ROMs verified as good dumps!"
                        )
            
            if failed_roms:
                msg = "❌ Some ROMs failed to process:\n\n"
                for filename, error in failed_roms:
                    msg += f"• {filename}: {error}\n"
                messagebox.showerror("Errors Occurred", msg)
        
        tk.Button(
            btn_frame,
            text="Learn More",
            command=lambda: messagebox.showinfo(
                "External Copier Headers",
                "External headers are NOT part of the original ROM.\n\n"
                "They were added by devices like:\n"
                "• Super Magicom\n"
                "• Game Doctor\n"
                "• Super Wild Card\n\n"
                "Removing them:\n"
                "✅ Makes ROMs match No-Intro databases\n"
                "✅ Fixes checksum verification\n"
                "✅ Safe - your ROM data is unchanged\n\n"
                "The actual cartridge ROM data starts after the header!"
            ),
            font=("Arial", 10),
            bg=self.bg_frame,
            fg=self.text_light,
            cursor="hand2",
            relief="flat",
            padx=15,
            pady=8
        ).pack(side="left", padx=(0, 10))
        
        tk.Button(
            btn_frame,
            text="Skip",
            command=dialog.destroy,
            font=("Arial", 10),
            bg=self.bg_frame,
            fg=self.text_light,
            cursor="hand2",
            relief="flat",
            padx=15,
            pady=8
        ).pack(side="left", padx=(0, 10))
        
        tk.Button(
            btn_frame,
            text="✂️ Remove Headers",
            command=fix_headers,
            font=("Arial", 10, "bold"),
            bg=self.accent_green,
            fg="white",
            cursor="hand2",
            relief="flat",
            padx=20,
            pady=8
        ).pack(side="right")
        
        # Make ESC close dialog
        dialog.bind('<Escape>', lambda e: dialog.destroy())

    def on_sound_toggle(self, enabled):
        """Handle sound toggle"""
        self.sounds_enabled.set(enabled)
        self.config.set('sound_enabled', enabled)
        # Actually apply to sound player
        self.sound_player.sounds_enabled = enabled

    def on_delete_toggle(self, enabled):
        """Handle delete toggle"""
        self.delete_after_conversion.set(enabled)
        self.config.set('delete_after_conversion', enabled)

    def on_volume_change(self, volume):
        """Handle volume change"""
        self.sound_player.volume = volume
        self.config.set('sound_volume', volume)

    def show_settings_panel(self):
        """Show settings panel"""
        self.main_container.pack_forget()
        self.settings_panel.show()

    def hide_settings_panel(self):
        """Show main panel after settings closes"""
        self.show_main_panel()


