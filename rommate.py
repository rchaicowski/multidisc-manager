import tkinter as tk
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
from core.file_utils import normalize_path, detect_available_formats
from gui.dialogs import show_format_choice_dialog, show_info_dialog
from core.chd_converter import CHDConverter 

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

        # CHD conversion options
        self.delete_after_conversion = tk.BooleanVar(value=False)

        # Sound player
        self.sound_player = SoundPlayer()
        self.sounds_enabled = tk.BooleanVar(value=self.sound_player.sounds_enabled)

        # CHD converter  ← Add these 2 lines
        self.chd_converter = CHDConverter()

        # Processing state
        self.is_processing = False
        self.spinner_running = False
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.spinner_index = 0

        self.create_widgets()

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

        folder_entry = tk.Entry(
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
        folder_entry.pack(side="left", padx=10, fill="x", expand=True, ipady=6)

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
        folder = filedialog.askdirectory(title="Select Game Folder")
        if folder:
            folder = normalize_path(folder)
            self.folder_path.set(folder)

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
                )
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

    def extract_game_info(self, filename):
        """Extract game name and disc number from filename."""
        name_without_ext = os.path.splitext(filename)[0]

        patterns = [
            r"(.*?)[\s\-_]*\(Dis[ck]\s*(\d+)\)",
            r"(.*?)[\s\-_]*\[Dis[ck]\s*(\d+)\]",
            r"(.*?)[\s\-_]*Dis[ck]\s*(\d+)",
            r"(.*?)[\s\-_]*\(CD\s*(\d+)\)",
            r"(.*?)[\s\-_]*\[CD\s*(\d+)\]",
            r"(.*?)[\s\-_]*CD\s*(\d+)",
            r"(.*?)[\s\-_]*\((?:Side|Dis[ck])\s*([A-Z])\)",
            r"(.*?)[\s\-_]*\[(?:Side|Dis[ck])\s*([A-Z])\]",
        ]

        for i, pattern in enumerate(patterns):
            match = re.match(pattern, name_without_ext, re.IGNORECASE)
            if match:
                game_name = match.group(1).strip()
                disc_identifier = match.group(2)

                if i >= 6:
                    disc_num = ord(disc_identifier.upper()) - ord("A") + 1
                else:
                    disc_num = int(disc_identifier)

                return game_name, disc_num

        return None, None

    def find_multidisc_games(self, folder, extensions=None):
        """Scan folder for multi-disc games and group them."""
        if extensions is None:
            extensions = ["*.cue", "*.gdi", "*.cdi", "*.iso", "*.chd"]

        games = {}

        self.log_to_processing(f"Scanning for: {', '.join(extensions)}")

        all_files = []
        for ext_pattern in extensions:
            files = list(Path(folder).glob(ext_pattern))
            if files:
                self.log_to_processing(
                    f"Found {len(files)} {ext_pattern} file(s)")
                all_files.extend(files)

        for file in all_files:
            filename = file.name
            game_name, disc_num = self.extract_game_info(filename)

            if game_name and disc_num:
                if game_name not in games:
                    games[game_name] = []
                games[game_name].append((disc_num, filename))

        # Filter only games with multiple discs
        multidisc_games = {}
        for name, files in games.items():
            if len(files) > 1:
                extensions_used = set(os.path.splitext(
                    f[1])[1].lower() for f in files)
                if len(extensions_used) == 1:
                    multidisc_games[name] = files
                else:
                    self.log_to_processing(
                        f"⚠️  Skipping '{name}' - mixed formats")

        # Sort by disc number
        for game_name in multidisc_games:
            multidisc_games[game_name].sort(key=lambda x: x[0])

        return multidisc_games

    def create_m3u_file(self, game_name, disc_files, folder):
        """Create an .m3u file for a multi-disc game."""
        m3u_filename = os.path.join(folder, f"{game_name}.m3u")

        if os.path.exists(m3u_filename):
            self.log_to_processing(f"  ⚠️ Already exists: {game_name}.m3u")
            return False

        with open(m3u_filename, "w", encoding="utf-8") as f:
            for disc_num, disc_file in disc_files:
                f.write(f"{disc_file}\n")

        self.log_to_processing(
            f"  ✓ Created: {game_name}.m3u ({len(disc_files)} discs)"
        )
        for disc_num, disc_file in disc_files:
            self.log_to_processing(f"      • Disc {disc_num}: {disc_file}")

        return True

    def create_m3u_files(self, folder):
        try:
            self.update_processing_status(
                "M3U Creator", "Detecting available disc formats..."
            )

            # Detect what formats are available
            has_original, has_chd = detect_available_formats(folder)

            # Determine which extensions to use
            extensions = None

            if has_original and has_chd:
                # Both formats exist - ask user which to use
                self.log_to_processing(
                    "⚠️ Found both original files (CUE/GDI/CDI/ISO) and CHD files")

                selected_format = show_format_choice_dialog(self.root)

                if selected_format is None:  # Cancel
                    self.log_to_processing("❌ Operation cancelled by user")
                    self.show_completion(success=False)
                    return
                elif selected_format == "chd":
                    extensions = ["*.chd"]
                    self.log_to_processing("✓ User selected: CHD files")
                else:  # original
                    extensions = ["*.cue", "*.gdi", "*.cdi", "*.iso"]
                    self.log_to_processing("✓ User selected: Original disc files")

            elif has_chd:
                # Only CHD files
                extensions = ["*.chd"]
                self.log_to_processing("✓ Auto-detected: CHD files only")

            elif has_original:
                # Only original files
                extensions = ["*.cue", "*.gdi", "*.cdi", "*.iso"]
                self.log_to_processing(
                    "✓ Auto-detected: Original disc files only")

            else:
                # No disc files found
                self.log_to_processing("❌ No disc files found")
                messagebox.showerror(
                    "No Files", "No disc image files found in the selected folder."
                )
                self.show_completion(success=False)
                return

            self.update_processing_status(
                "M3U Creator", "Scanning for multi-disc games..."
            )

            multidisc_games = self.find_multidisc_games(
                folder, extensions=extensions)

            if not multidisc_games:
                self.log_to_processing("❌ No multi-disc games found.")
                self.log_to_processing(
                    "\nMake sure files follow naming conventions like:"
                )
                self.log_to_processing("  • Game Name (Disc 1).cue")
                self.log_to_processing("  • Game Name (Disc 2).chd")
                messagebox.showinfo(
                    "No Games Found", "No multi-disc games were found.")
                self.show_completion(success=False)
            else:
                self.log_to_processing(
                    f"🎮 Found {len(multidisc_games)} multi-disc game(s)\n"
                )

                total_games = len(multidisc_games)
                created_count = 0
                skipped_count = 0

                for index, (game_name, disc_files) in enumerate(
                    multidisc_games.items(), 1
                ):
                    self.update_processing_status(
                        "Creating M3U Playlists",
                        f"Processing game {index} of {total_games}",
                        index,
                        total_games,
                        f"{game_name}.m3u",
                    )

                    if self.create_m3u_file(game_name, disc_files, folder):
                        created_count += 1
                    else:
                        skipped_count += 1

                self.log_to_processing("\n" + "=" * 60)
                self.log_to_processing(
                    f"✅ Created: {created_count} | ⏭️ Skipped: {skipped_count}"
                )
                self.log_to_processing("=" * 60)

                self.show_completion(
                    success=True, converted=created_count, skipped=skipped_count
                )

        except Exception as e:
            self.log_to_processing(f"\n❌ ERROR: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
            self.show_completion(success=False)

    def convert_and_create_m3u(self, folder):
        """Convert to CHD then create M3U playlists"""
        try:
            self.update_processing_status(
                "CHD + M3U", "Step 1: Checking for chdman...")

            # Check for chdman
            chdman_path = self.find_chdman()
            if not chdman_path:
                self.log_to_processing("❌ ERROR: chdman not found!")

                if platform.system() == "Linux":
                    if self.prompt_install_chdman():
                        self.log_to_processing("⏳ Installation in progress.")
                    else:
                        self.log_to_processing("❌ Installation cancelled.")
                else:
                    messagebox.showerror(
                        "chdman Not Found", "chdman is required.")

                self.show_completion(success=False)
                return

            # Test chdman
            try:
                test_result = subprocess.run(
                    [chdman_path, "--help"], capture_output=True, text=True, timeout=5
                )

                if test_result.returncode != 0 and platform.system() == "Linux":
                    if "error while loading shared libraries" in test_result.stderr:
                        self.log_to_processing(
                            "❌ ERROR: chdman has missing dependencies!"
                        )

                        if self.prompt_install_chdman():
                            self.log_to_processing(
                                "⏳ Installation in progress.")
                        else:
                            self.log_to_processing("❌ Installation cancelled.")

                        self.show_completion(success=False)
                        return
            except Exception as e:
                self.log_to_processing(
                    f"⚠️ Warning: Could not test chdman: {e}")

            self.log_to_processing(f"✓ Found chdman: {chdman_path}")

            # Find convertible files
            source_files = []
            for pattern in ["*.cue", "*.gdi", "*.cdi", "*.iso"]:
                found = list(Path(folder).glob(pattern))
                if found:
                    source_files.extend(found)

            converted = 0

            if source_files:
                total_files = len(source_files)
                self.log_to_processing(f"\n=== STEP 1: CHD Conversion ===")
                self.log_to_processing(
                    f"Found {total_files} file(s) to convert\n")

                for index, source_file in enumerate(source_files, 1):
                    source_path = str(source_file)
                    chd_path = str(source_file.with_suffix(".chd"))

                    self.update_processing_status(
                        "Step 1: Converting to CHD",
                        f"Processing file {index} of {total_files}",
                        index,
                        total_files,
                        source_file.name,
                    )

                    if os.path.exists(chd_path):
                        self.log_to_processing(
                            f"⏭️  {source_file.name} (CHD exists)")
                        continue

                    self.log_to_processing(f"🔄 {source_file.name}")

                    # Add a processing indicator
                    processing_msg = "   Processing"
                    self.log_to_processing(processing_msg)
                    log_position = self.processing_log.index(
                        "end-2c linestart")

                    try:
                        import time

                        # Start conversion process
                        process = subprocess.Popen(
                            [
                                chdman_path,
                                "createcd",
                                "-i",
                                source_path,
                                "-o",
                                chd_path,
                            ],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                        )

                        # Animate dots while waiting
                        dots = 0
                        while process.poll() is None:
                            dots = (dots + 1) % 4
                            dot_str = "." * dots
                            self.processing_log.config(state="normal")
                            self.processing_log.delete(
                                log_position, f"{log_position} lineend"
                            )
                            self.processing_log.insert(
                                log_position, f"   Processing{dot_str}"
                            )
                            self.processing_log.config(state="disabled")
                            self.root.update_idletasks()
                            # Just wait for animation, not the process!
                            time.sleep(0.3)

                        stdout, stderr = process.communicate()

                        # Remove processing line
                        self.processing_log.config(state="normal")
                        self.processing_log.delete(
                            f"{log_position} linestart", f"{log_position} lineend+1c"
                        )
                        self.processing_log.config(state="disabled")

                        if process.returncode == 0:
                            self.log_to_processing(f"   ✓ Converted to CHD")
                            converted += 1

                            if self.delete_after_conversion.get():
                                try:
                                    os.remove(source_path)
                                    if source_file.suffix.lower() == ".cue":
                                        bin_file = str(
                                            source_file.with_suffix(".bin"))
                                        if os.path.exists(bin_file):
                                            os.remove(bin_file)
                                    self.log_to_processing(
                                        f"   🗑️  Deleted originals")
                                except:
                                    pass
                        else:
                            self.log_to_processing(f"   ❌ Conversion failed")
                    except:
                        # Remove processing line if error
                        try:
                            self.processing_log.config(state="normal")
                            self.processing_log.delete(
                                f"{log_position} linestart",
                                f"{log_position} lineend+1c",
                            )
                            self.processing_log.config(state="disabled")
                        except:
                            pass
                        self.log_to_processing(f"   ❌ Error during conversion")

                self.log_to_processing(
                    f"\nStep 1 complete: Converted {converted} file(s)"
                )
            else:
                self.log_to_processing("No files found to convert")

            # Step 2: Create M3U
            self.log_to_processing(f"\n=== STEP 2: M3U Creation ===\n")

            self.update_processing_status(
                "Step 2: Creating M3U", "Scanning for multi-disc games..."
            )

            # Only scan for CHD files since we just converted to CHD
            multidisc_games = self.find_multidisc_games(
                folder, extensions=["*.chd"])

            created = 0

            if multidisc_games:
                total_games = len(multidisc_games)
                self.log_to_processing(
                    f"Found {total_games} multi-disc game(s)\n")

                for index, (game_name, disc_files) in enumerate(multidisc_games, 1):
                    self.update_processing_status(
                        "Step 2: Creating M3U",
                        f"Processing game {index} of {total_games}",
                        index,
                        total_games,
                        f"{game_name}.m3u",
                    )

                    if self.create_m3u_file(game_name, disc_files, folder):
                        created += 1

                self.log_to_processing(
                    f"\nStep 2 complete: Created {created} M3U file(s)"
                )
            else:
                self.log_to_processing("No multi-disc games found")

            self.log_to_processing("\n" + "=" * 60)
            self.log_to_processing("✅ ALL OPERATIONS COMPLETE!")
            self.log_to_processing("=" * 60)

            self.show_completion(
                success=True, converted=converted, skipped=0, failed=0)

        except Exception as e:
            self.log_to_processing(f"\n❌ ERROR: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
            self.show_completion(success=False)


if __name__ == "__main__":
    root = tk.Tk()
    app = RomMateGUI(root)
    root.mainloop()
