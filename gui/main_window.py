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
from utils.sounds import SoundPlayer
from core.file_utils import normalize_path, detect_available_formats, find_multidisc_games, create_m3u_file
from gui.dialogs import show_format_choice_dialog, show_info_dialog
from core.chd_converter import CHDConverter
from core.m3u_creator import M3UCreator
from utils.config import Config

class RomMateGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("RomMate")
        self.root.geometry("850x870")
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
        self.sounds_enabled = tk.BooleanVar(value=self.sound_player.sounds_enabled)

        # CHD converter
        self.chd_converter = CHDConverter()

        # M3U creator
        self.m3u_creator = M3UCreator()

        # Processing state
        self.is_processing = False
        self.spinner_running = False
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.spinner_index = 0

        self.create_widgets()

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

        # Reset processing panel
        self.status_title.config(text="Starting", fg=self.text_light)
        self.status_subtitle.config(text="Initializing")
        self.file_counter_label.config(text="0 / 0 files")
        self.current_file_label.config(text="")

        # Clear log
        self.processing_log.config(state="normal")
        self.processing_log.delete(1.0, tk.END)
        self.processing_log.config(state="disabled")

        # Hide completion buttons
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

        # Play sound
        self.sound_player.play("success" if success else "fail")

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

    def update_options_visibility(self):
        """Show/hide options based on selected mode"""
        self.m3u_options.pack_forget()
        self.chd_options.pack_forget()
        self.both_options.pack_forget()

        mode = self.operation_mode.get()

        if mode == "chd":
            self.chd_options.pack(fill="x")
            self.process_btn.config(text="▶ Convert to CHD")
        elif mode == "m3u":
            self.m3u_options.pack(fill="x")
            self.process_btn.config(text="▶ Create M3U Files")
        else:  # both
            self.both_options.pack(fill="x")
            self.process_btn.config(text="▶ Convert & Create M3U")

    def create_widgets(self):
        # Main container (for configuration)
        self.main_container = tk.Frame(self.root, bg=self.bg_dark)

        # Title
        title_label = tk.Label(
            self.main_container,
            text="RomMate",
            font=("Arial", 24, "bold"),
            bg=self.bg_dark,
            fg=self.text_light,
        )
        title_label.pack(pady=(10, 5))

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

        # Operation mode selection
        mode_frame = tk.Frame(
            self.main_container, bg=self.bg_frame, relief="groove", bd=2
        )
        mode_frame.pack(pady=20, fill="x")

        tk.Label(
            mode_frame,
            text="What do you want to do?",
            font=("Arial", 12, "bold"),
            bg=self.bg_frame,
            fg=self.text_light,
        ).pack(anchor="w", padx=25, pady=(15, 10))

        chd_radio = tk.Radiobutton(
            mode_frame,
            text="💾 Convert to CHD (compress disc images)",
            variable=self.operation_mode,
            value="chd",
            font=("Arial", 11),
            command=self.update_options_visibility,
            bg=self.bg_frame,
            fg=self.text_light,
            selectcolor=self.bg_dark,
            activebackground=self.bg_frame,
            activeforeground=self.text_light,
            bd=0,
            highlightthickness=0,
        )
        chd_radio.pack(anchor="w", padx=25, pady=8)

        m3u_radio = tk.Radiobutton(
            mode_frame,
            text="📁 Create M3U Playlists (for multi-disc games)",
            variable=self.operation_mode,
            value="m3u",
            font=("Arial", 11),
            command=self.update_options_visibility,
            bg=self.bg_frame,
            fg=self.text_light,
            selectcolor=self.bg_dark,
            activebackground=self.bg_frame,
            activeforeground=self.text_light,
            bd=0,
            highlightthickness=0,
        )
        m3u_radio.pack(anchor="w", padx=25, pady=8)

        both_radio = tk.Radiobutton(
            mode_frame,
            text="🔄 Convert to CHD + Create M3U Playlists",
            variable=self.operation_mode,
            value="both",
            font=("Arial", 11),
            command=self.update_options_visibility,
            bg=self.bg_frame,
            fg=self.text_light,
            selectcolor=self.bg_dark,
            activebackground=self.bg_frame,
            activeforeground=self.text_light,
            bd=0,
            highlightthickness=0,
        )
        both_radio.pack(anchor="w", padx=25, pady=8)

        tk.Frame(mode_frame, height=1, bg=self.text_gray).pack(
            fill="x", padx=25, pady=15
        )

        info_btn = tk.Button(
            mode_frame,
            text="ℹ️  Help - When to use each?",
            command=self.show_info,
            font=("Arial", 10),
            bg=self.accent_blue,
            fg="white",
            cursor="hand2",
            relief="flat",
            activebackground="#1e88e5",
            activeforeground="white",
            padx=15,
            pady=6,
            bd=0,
        )
        info_btn.pack(anchor="w", padx=25, pady=(0, 15))

        # Options frame
        self.options_frame = tk.Frame(
            self.main_container, bg=self.bg_frame, relief="groove", bd=2
        )
        self.options_frame.pack(pady=20, fill="x")

        self.options_title = tk.Label(
            self.options_frame,
            text="Options",
            font=("Arial", 12, "bold"),
            bg=self.bg_frame,
            fg=self.text_light,
        )
        self.options_title.pack(anchor="w", padx=25, pady=(15, 10))

        # M3U options
        self.m3u_options = tk.Frame(self.options_frame, bg=self.bg_frame)

        tk.Label(
            self.m3u_options,
            text="Scans for: CUE, GDI, CDI, ISO, CHD files",
            font=("Arial", 10),
            fg=self.text_gray,
            bg=self.bg_frame,
        ).pack(anchor="w", padx=25, pady=(0, 10))

        info_frame = tk.Frame(
            self.m3u_options, bg="#1a237e", relief="flat", borderwidth=1
        )
        info_frame.pack(fill="x", padx=25, pady=(0, 15))

        tk.Label(
            info_frame,
            text="ℹ️ Note: All disc files must be in the same folder.\n"
            "    Works with PSX, PS2, Dreamcast, Saturn, Sega CD, and more!\n"
            "    If both CUE and CHD files exist, you'll be asked which to use.",
            font=("Arial", 9),
            bg="#1a237e",
            fg="#90caf9",
            justify="left",
        ).pack(padx=15, pady=12, anchor="w")

        # CHD options
        self.chd_options = tk.Frame(self.options_frame, bg=self.bg_frame)

        tk.Label(
            self.chd_options,
            text="Converts: CUE, GDI, CDI, ISO → CHD format",
            font=("Arial", 10),
            fg=self.text_gray,
            bg=self.bg_frame,
        ).pack(anchor="w", padx=25, pady=(0, 15))

        tk.Checkbutton(
            self.chd_options,
            text="⚠️ Delete original files after successful conversion",
            variable=self.delete_after_conversion,
            font=("Arial", 10),
            fg=self.accent_red,
            bg=self.bg_frame,
            selectcolor=self.bg_dark,
            activebackground=self.bg_frame,
            activeforeground=self.accent_red,
            bd=0,
            highlightthickness=0,
        ).pack(anchor="w", padx=25, pady=(0, 10))

        tk.Label(
            self.chd_options,
            text="(CHD files are compressed and save 40-60% space)",
            font=("Arial", 9),
            fg=self.text_gray,
            bg=self.bg_frame,
        ).pack(anchor="w", padx=25, pady=(0, 15))

        # Both options
        self.both_options = tk.Frame(self.options_frame, bg=self.bg_frame)

        tk.Label(
            self.both_options,
            text="Step 1: Convert all disc images to CHD",
            font=("Arial", 10, "bold"),
            bg=self.bg_frame,
            fg=self.text_light,
        ).pack(anchor="w", padx=25, pady=(0, 5))

        tk.Label(
            self.both_options,
            text="  Converts: CUE, GDI, CDI, ISO → CHD",
            font=("Arial", 9),
            fg=self.text_gray,
            bg=self.bg_frame,
        ).pack(anchor="w", padx=25)

        tk.Label(
            self.both_options,
            text="Step 2: Create M3U playlists for multi-disc games",
            font=("Arial", 10, "bold"),
            bg=self.bg_frame,
            fg=self.text_light,
        ).pack(anchor="w", padx=25, pady=(15, 5))

        tk.Label(
            self.both_options,
            text="  Groups CHD files into playlists",
            font=("Arial", 9),
            fg=self.text_gray,
            bg=self.bg_frame,
        ).pack(anchor="w", padx=25)

        tk.Checkbutton(
            self.both_options,
            text="⚠️ Delete original files after successful conversion",
            variable=self.delete_after_conversion,
            font=("Arial", 10),
            fg=self.accent_red,
            bg=self.bg_frame,
            selectcolor=self.bg_dark,
            activebackground=self.bg_frame,
            activeforeground=self.accent_red,
            bd=0,
            highlightthickness=0,
        ).pack(anchor="w", padx=25, pady=(15, 15))

        # Process button
        self.process_btn = tk.Button(
            self.main_container,
            text="▶ Process Files",
            command=self.run_process,
            font=("Arial", 14, "bold"),
            bg=self.accent_blue,
            fg="white",
            cursor="hand2",
            height=2,
            padx=50,
            relief="flat",
            activebackground="#1e88e5",
            activeforeground="white",
            bd=0,
        )
        self.process_btn.pack(pady=30)

        # Footer
        footer_frame = tk.Frame(self.main_container, bg=self.bg_dark)
        footer_frame.pack(pady=(0, 10))

        def test_sound():
            if self.sounds_enabled.get():
                self.sound_player.play("success")

        sound_check = tk.Checkbutton(
            footer_frame,
            text="🔔 Enable sounds"
            + ("" if self.sound_player.sounds_available else " (sounds not found)"),
            variable=self.sounds_enabled,
            command=test_sound,
            font=("Arial", 9),
            bg=self.bg_dark,
            fg=(
                self.text_gray
                if self.sound_player.sounds_available
                else self.accent_red
            ),
            selectcolor=self.bg_dark,
            activebackground=self.bg_dark,
            activeforeground=self.text_light,
            bd=0,
            highlightthickness=0,
        )
        sound_check.pack(side="left", padx=(0, 15))

        footer_label = tk.Label(
            footer_frame,
            text="Supports PS1, PS2, Dreamcast, Saturn, and other disc-based systems",
            font=("Arial", 9),
            fg=self.text_gray,
            bg=self.bg_dark,
        )
        footer_label.pack(side="left")

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
        self.update_options_visibility()
        self.show_main_panel()

    def show_info(self):
        """Show information about when to use each option"""
        show_info_dialog(self.root)

    def browse_folder(self):
        # Start from last used folder
        initial_dir = self.config.get('last_folder', str(Path.home()))
        
        folder = filedialog.askdirectory(
            title="Select Game Folder",
            initialdir=initial_dir
        )
        
        if folder:
            folder = normalize_path(folder)
            self.update_folder_display(folder)
            
            # Remember this folder for next time
            self.config.set('last_folder', folder)

    def run_process(self):
        folder = self.folder_path.get()

        if not folder:
            messagebox.showwarning(
                "No Folder", "Please select a game folder first!")
            return

        if not os.path.exists(folder):
            messagebox.showerror(
                "Error", f"Selected folder does not exist!\n\nPath: {folder}"
            )
            return

        mode = self.operation_mode.get()
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
                animation_callback=self.animate_processing_dots
            )
            
            if converted == 0 and skipped == 0 and failed == 0:
                self.log_to_processing("\n❌ No convertible files found.")
                self.log_to_processing("Supported formats: CUE, GDI, CDI, ISO")
                messagebox.showinfo("No Files", "No convertible disc images found.")
                self.show_completion(success=False)
                return
            
            self.log_to_processing("\n" + "=" * 60)
            self.log_to_processing(f"✅ Converted: {converted} | ⏭️ Skipped: {skipped} | ❌ Failed: {failed}")
            self.log_to_processing("=" * 60)
            
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
                animation_callback=self.animate_processing_dots
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
            
            self.show_completion(success=True, converted=converted, skipped=0, failed=0)
        
        except Exception as e:
            self.log_to_processing(f"\n❌ ERROR: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
            self.show_completion(success=False)


