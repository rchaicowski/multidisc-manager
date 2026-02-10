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
                current_text = current_text.split()[0] + " " + " ".join(current_text.split()[1:-1])
            
            # Add new spinner
            self.status_title.config(text=f"{current_text} {spinner}")
            
            self.spinner_index = (self.spinner_index + 1) % len(self.spinner_chars)
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
        self.processing_log.config(state='normal')
        self.processing_log.delete(1.0, tk.END)
        self.processing_log.config(state='disabled')
        
        # Hide completion buttons
        self.completion_frame.pack_forget()
        
        # Start spinner
        self.start_spinner()
    
    def update_processing_status(self, title, subtitle, progress=None, total=None, current_file=""):
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
        self.processing_log.config(state='normal')
        self.processing_log.insert(tk.END, message + "\n")
        self.processing_log.see(tk.END)
        self.processing_log.config(state='disabled')
        self.root.update_idletasks()
    
    def show_completion(self, success=True, converted=0, skipped=0, failed=0):
        """Show completion state in processing panel"""
        # Stop spinner
        self.stop_spinner()
        
        # Play sound
        self.sound_player.play("success" if success else "fail")
        
        if success:
            self.status_title.config(text="✅ Completed Successfully!", fg=self.accent_green)
            self.status_subtitle.config(text="All operations finished")
            self.processing_panel.config(bg="#1b5e20")
        else:
            self.status_title.config(text="⚠️ Completed with Errors", fg=self.accent_red)
            self.status_subtitle.config(text="Some operations failed - check details below")
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
            fg=self.text_light
        )
        title_label.pack(pady=(10, 5))
        
        # Description
        desc_label = tk.Label(
            self.main_container,
            text="Your ROM companion - Convert, compress, and organize disc images",
            font=("Arial", 11),
            bg=self.bg_dark,
            fg=self.text_gray
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
            fg=self.text_light
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
            highlightcolor=self.accent_blue
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
            bd=0
        )
        browse_btn.pack(side="left")
        
        # Operation mode selection
        mode_frame = tk.Frame(
            self.main_container,
            bg=self.bg_frame,
            relief="groove",
            bd=2
        )
        mode_frame.pack(pady=20, fill="x")
        
        tk.Label(
            mode_frame,
            text="What do you want to do?",
            font=("Arial", 12, "bold"),
            bg=self.bg_frame,
            fg=self.text_light
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
            highlightthickness=0
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
            highlightthickness=0
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
            highlightthickness=0
        )
        both_radio.pack(anchor="w", padx=25, pady=8)
        
        tk.Frame(mode_frame, height=1, bg=self.text_gray).pack(fill="x", padx=25, pady=15)
        
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
            bd=0
        )
        info_btn.pack(anchor="w", padx=25, pady=(0, 15))
        
        # Options frame
        self.options_frame = tk.Frame(
            self.main_container,
            bg=self.bg_frame,
            relief="groove",
            bd=2
        )
        self.options_frame.pack(pady=20, fill="x")
        
        self.options_title = tk.Label(
            self.options_frame,
            text="Options",
            font=("Arial", 12, "bold"),
            bg=self.bg_frame,
            fg=self.text_light
        )
        self.options_title.pack(anchor="w", padx=25, pady=(15, 10))
        
        # M3U options
        self.m3u_options = tk.Frame(self.options_frame, bg=self.bg_frame)
        
        tk.Label(
            self.m3u_options,
            text="Scans for: CUE, GDI, CDI, ISO, CHD files",
            font=("Arial", 10),
            fg=self.text_gray,
            bg=self.bg_frame
        ).pack(anchor="w", padx=25, pady=(0, 10))
        
        info_frame = tk.Frame(self.m3u_options, bg="#1a237e", relief="flat", borderwidth=1)
        info_frame.pack(fill="x", padx=25, pady=(0, 15))
        
        tk.Label(
            info_frame,
            text="ℹ️ Note: All disc files must be in the same folder.\n"
                 "    Works with PSX, PS2, Dreamcast, Saturn, Sega CD, and more!\n"
                 "    If both CUE and CHD files exist, you'll be asked which to use.",
            font=("Arial", 9),
            bg="#1a237e",
            fg="#90caf9",
            justify="left"
        ).pack(padx=15, pady=12, anchor="w")
        
        # CHD options
        self.chd_options = tk.Frame(self.options_frame, bg=self.bg_frame)
        
        tk.Label(
            self.chd_options, 
            text="Converts: CUE, GDI, CDI, ISO → CHD format",
            font=("Arial", 10),
            fg=self.text_gray,
            bg=self.bg_frame
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
            highlightthickness=0
        ).pack(anchor="w", padx=25, pady=(0, 10))
        
        tk.Label(
            self.chd_options,
            text="(CHD files are compressed and save 40-60% space)",
            font=("Arial", 9),
            fg=self.text_gray,
            bg=self.bg_frame
        ).pack(anchor="w", padx=25, pady=(0, 15))
        
        # Both options
        self.both_options = tk.Frame(self.options_frame, bg=self.bg_frame)
        
        tk.Label(
            self.both_options,
            text="Step 1: Convert all disc images to CHD",
            font=("Arial", 10, "bold"),
            bg=self.bg_frame,
            fg=self.text_light
        ).pack(anchor="w", padx=25, pady=(0, 5))
        
        tk.Label(
            self.both_options,
            text="  Converts: CUE, GDI, CDI, ISO → CHD",
            font=("Arial", 9),
            fg=self.text_gray,
            bg=self.bg_frame
        ).pack(anchor="w", padx=25)
        
        tk.Label(
            self.both_options,
            text="Step 2: Create M3U playlists for multi-disc games",
            font=("Arial", 10, "bold"),
            bg=self.bg_frame,
            fg=self.text_light
        ).pack(anchor="w", padx=25, pady=(15, 5))
        
        tk.Label(
            self.both_options,
            text="  Groups CHD files into playlists",
            font=("Arial", 9),
            fg=self.text_gray,
            bg=self.bg_frame
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
            highlightthickness=0
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
            bd=0
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
            text="🔔 Enable sounds" + ("" if self.sound_player.sounds_available else " (sounds not found)"),
            variable=self.sounds_enabled,
            command=test_sound,
            font=("Arial", 9),
            bg=self.bg_dark,
            fg=self.text_gray if self.sound_player.sounds_available else self.accent_red,
            selectcolor=self.bg_dark,
            activebackground=self.bg_dark,
            activeforeground=self.text_light,
            bd=0,
            highlightthickness=0
        )
        sound_check.pack(side="left", padx=(0, 15))
        
        footer_label = tk.Label(
            footer_frame,
            text="Supports PS1, PS2, Dreamcast, Saturn, and other disc-based systems",
            font=("Arial", 9),
            fg=self.text_gray,
            bg=self.bg_dark
        )
        footer_label.pack(side="left")
        
        # ===== PROCESSING PANEL =====
        self.processing_panel = tk.Frame(self.root, bg=self.bg_frame, relief="groove", bd=2)
        
        # Header with status
        status_header = tk.Frame(self.processing_panel, bg=self.bg_frame)
        status_header.pack(fill="x", pady=20, padx=30)
        
        self.status_title = tk.Label(
            status_header,
            text="Processing...",
            font=("Arial", 20, "bold"),
            bg=self.bg_frame,
            fg=self.text_light
        )
        self.status_title.pack()
        
        self.status_subtitle = tk.Label(
            status_header,
            text="Starting operation",
            font=("Arial", 12),
            bg=self.bg_frame,
            fg=self.text_gray
        )
        self.status_subtitle.pack(pady=(5, 0))
        
        # Current file being processed
        self.current_file_label = tk.Label(
            self.processing_panel,
            text="",
            font=("Consolas", 11),
            bg=self.bg_frame,
            fg=self.accent_blue,
            wraplength=700
        )
        self.current_file_label.pack(pady=(10, 20))
        
        # File counter
        self.file_counter_label = tk.Label(
            self.processing_panel,
            text="0 / 0 files",
            font=("Arial", 13, "bold"),
            bg=self.bg_frame,
            fg=self.text_light
        )
        self.file_counter_label.pack(pady=(0, 20))
        
        # Separator
        tk.Frame(self.processing_panel, height=2, bg=self.text_gray).pack(fill="x", padx=30, pady=10)
        
        # Details label
        tk.Label(
            self.processing_panel,
            text="Details:",
            font=("Arial", 11, "bold"),
            bg=self.bg_frame,
            fg=self.text_light
        ).pack(anchor="w", padx=30, pady=(10, 5))
        
        # Processing log (smaller, for details)
        log_border = tk.Frame(self.processing_panel, bg=self.text_gray, relief="solid", bd=1)
        log_border.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        
        self.processing_log = scrolledtext.ScrolledText(
            log_border,
            width=80,
            height=12,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#d4d4d4",
            wrap=tk.WORD,
            state='disabled',
            relief="flat",
            bd=0,
            padx=10,
            pady=8
        )
        self.processing_log.pack(fill="both", expand=True, padx=1, pady=1)
        
        # Completion buttons (hidden until done)
        self.completion_frame = tk.Frame(self.processing_panel, bg=self.bg_frame)
        
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
            bd=0
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
            bd=0
        ).pack(side="left", padx=10)
        
        # Initialize UI
        self.update_options_visibility()
        self.show_main_panel()
    
    def show_info(self):
        """Show information about when to use each option"""
        info_text = """
📁 CREATE M3U PLAYLISTS

Use this when you have multi-disc games (games with Disc 1, Disc 2, etc.)

What it does:
• Creates playlist files (.m3u) that list all discs for each game
• Allows you to switch discs in your emulator during gameplay
• Keeps your game library organized

Best for:
• PS1 multi-disc games
• PS2 multi-disc games
• Dreamcast multi-disc games
• Sega Saturn multi-disc games

Example: If you have:
  - Final Fantasy VII (Disc 1).cue
  - Final Fantasy VII (Disc 2).cue
  - Final Fantasy VII (Disc 3).cue
  
It creates: Final Fantasy VII.m3u

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💾 CONVERT TO CHD

Use this to compress your disc images and save space

What it does:
• Converts CUE/BIN files to CHD (Compressed Hunks of Data)
• Reduces file size by 40-60%
• Improves loading times in some emulators
• Preserves all game data perfectly

Best for:
• Saving hard drive space
• Faster game loading
• RetroArch and most modern emulators support CHD

Example: 
  Game.cue (1 KB) + Game.bin (700 MB)
  → Game.chd (300-400 MB)

⚠️ Note: Always keep backups before converting!
        """
        
        info_window = tk.Toplevel(self.root)
        info_window.title("Help - When to use each option")
        info_window.geometry("600x650")
        info_window.configure(bg=self.bg_dark)
        
        text_widget = scrolledtext.ScrolledText(
            info_window,
            width=70,
            height=35,
            font=("Arial", 10),
            wrap=tk.WORD,
            padx=15,
            pady=15,
            bg=self.bg_frame,
            fg=self.text_light
        )
        text_widget.pack(fill="both", expand=True, padx=10, pady=10)
        text_widget.insert(1.0, info_text)
        text_widget.config(state="disabled")
        
        close_btn = tk.Button(
            info_window,
            text="Close",
            command=info_window.destroy,
            font=("Arial", 10),
            bg=self.accent_green,
            fg="white",
            cursor="hand2",
            padx=20,
            relief="flat"
        )
        close_btn.pack(pady=10)
    
    def browse_folder(self):
        folder = filedialog.askdirectory(title="Select Game Folder")
        if folder:
            # Strip any leading/trailing whitespace
            folder = folder.strip()
            
            # Additional check: if folder doesn't exist, try with trailing space
            # (Linux file dialog sometimes strips trailing spaces from folder names)
            if not os.path.exists(folder):
                folder_with_space = folder + " "
                if os.path.exists(folder_with_space):
                    folder = folder_with_space
            
            self.folder_path.set(folder)
    
    def run_process(self):
        folder = self.folder_path.get()
        
        if not folder:
            messagebox.showwarning("No Folder", "Please select a game folder first!")
            return
        
        if not os.path.exists(folder):
            messagebox.showerror("Error", f"Selected folder does not exist!\n\nPath: {folder}")
            return
        
        mode = self.operation_mode.get()
        self.is_processing = True
        
        # Switch to processing panel
        self.show_processing_panel()
        
        # Run in separate thread
        if mode == "m3u":
            thread = threading.Thread(target=self.create_m3u_files, args=(folder,))
        elif mode == "chd":
            thread = threading.Thread(target=self.convert_to_chd, args=(folder,))
        else:  # both
            thread = threading.Thread(target=self.convert_and_create_m3u, args=(folder,))
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
            chdman_path = self.find_chdman()
            if not chdman_path:
                self.log_to_processing("❌ ERROR: chdman not found!")
                
                # On Linux, offer to install automatically
                if platform.system() == 'Linux':
                    if self.prompt_install_chdman():
                        self.log_to_processing("⏳ Installation in progress.")
                        self.log_to_processing("Please complete installation in the terminal, then try again.")
                    else:
                        self.log_to_processing("❌ Installation cancelled.")
                else:
                    self.log_to_processing("chdman is required for CHD conversion.")
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
                    [chdman_path, '--help'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if test_result.returncode != 0 and platform.system() == 'Linux':
                    if 'error while loading shared libraries' in test_result.stderr:
                        self.log_to_processing("❌ ERROR: chdman has missing dependencies!")
                        
                        if self.prompt_install_chdman():
                            self.log_to_processing("⏳ Installation in progress.")
                        else:
                            self.log_to_processing("❌ Installation cancelled.")
                        
                        self.show_completion(success=False)
                        return
            except Exception as e:
                self.log_to_processing(f"⚠️ Warning: Could not test chdman: {e}")
            
            self.log_to_processing(f"✓ Found chdman: {chdman_path}")
            
            self.update_processing_status(
                "CHD Conversion",
                "Scanning for disc images..."
            )
            
            # Find all convertible files
            source_files = []
            for pattern in ["*.cue", "*.gdi", "*.cdi", "*.iso"]:
                found = list(Path(folder).glob(pattern))
                if found:
                    self.log_to_processing(f"Found {len(found)} {pattern} file(s)")
                    source_files.extend(found)
            
            if not source_files:
                self.log_to_processing("❌ No convertible files found.")
                self.log_to_processing("Supported formats: CUE, GDI, CDI, ISO")
                messagebox.showinfo("No Files", "No convertible disc images found.")
                self.show_completion(success=False)
                return
            
            total_files = len(source_files)
            self.log_to_processing(f"\nTotal files to convert: {total_files}\n")
            
            converted = 0
            failed = 0
            skipped = 0
            
            for index, source_file in enumerate(source_files, 1):
                source_path = str(source_file)
                source_ext = source_file.suffix.lower()
                chd_path = str(source_file.with_suffix('.chd'))
                
                # Update status
                self.update_processing_status(
                    "Converting to CHD",
                    f"Processing file {index} of {total_files}",
                    index,
                    total_files,
                    source_file.name
                )
                
                # Skip if CHD already exists
                if os.path.exists(chd_path):
                    self.log_to_processing(f"⏭️  Skipped: {source_file.name} (CHD already exists)")
                    skipped += 1
                    continue
                
                self.log_to_processing(f"🔄 Converting: {source_file.name}")
                
                # Add a processing indicator that updates
                processing_msg = "   Processing"
                self.log_to_processing(processing_msg)
                
                # Keep track of log position for updating
                log_position = self.processing_log.index("end-2c linestart")
                
                try:
                    import time
                    cmd = [chdman_path, 'createcd', '-i', source_path, '-o', chd_path]
                    
                    # Start conversion process
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    # Animate dots while waiting
                    dots = 0
                    while process.poll() is None:
                        dots = (dots + 1) % 4
                        dot_str = "." * dots
                        self.processing_log.config(state='normal')
                        self.processing_log.delete(log_position, f"{log_position} lineend")
                        self.processing_log.insert(log_position, f"   Processing{dot_str}")
                        self.processing_log.config(state='disabled')
                        self.root.update_idletasks()
                        time.sleep(0.3)  # Just wait for animation, not the process!
                    
                    # Get final result
                    stdout, stderr = process.communicate()
                    
                    # Remove processing line
                    self.processing_log.config(state='normal')
                    self.processing_log.delete(f"{log_position} linestart", f"{log_position} lineend+1c")
                    self.processing_log.config(state='disabled')
                    
                    if process.returncode == 0:
                        self.log_to_processing(f"   ✓ Success: {os.path.basename(chd_path)}")
                        converted += 1
                        
                        # Delete original files if option is enabled
                        if self.delete_after_conversion.get():
                            try:
                                os.remove(source_path)
                                if source_ext == '.cue':
                                    bin_file = source_path.rsplit('.', 1)[0] + '.bin'
                                    if os.path.exists(bin_file):
                                        os.remove(bin_file)
                                self.log_to_processing(f"   🗑️  Deleted original files")
                            except Exception as e:
                                self.log_to_processing(f"   ⚠️  Could not delete originals: {e}")
                    else:
                        self.log_to_processing(f"   ❌ Failed: {stderr[:100]}")
                        failed += 1
                
                except Exception as e:
                    # Remove processing line if error
                    try:
                        self.processing_log.config(state='normal')
                        self.processing_log.delete(f"{log_position} linestart", f"{log_position} lineend+1c")
                        self.processing_log.config(state='disabled')
                    except:
                        pass
                    self.log_to_processing(f"   ❌ Error: {str(e)}")
                    failed += 1
            
            self.log_to_processing("\n" + "=" * 60)
            self.log_to_processing(f"✅ Converted: {converted} | ⏭️ Skipped: {skipped} | ❌ Failed: {failed}")
            self.log_to_processing("=" * 60)
            
            success = failed == 0
            self.show_completion(success=success, converted=converted, skipped=skipped, failed=failed)
            
        except Exception as e:
            self.log_to_processing(f"\n❌ ERROR: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
            self.show_completion(success=False)
    
    def find_chdman(self):
        """Try to find chdman executable"""
        bundled_path = os.path.join(os.path.dirname(__file__), 'tools', 
                                    'chdman.exe' if platform.system() == 'Windows' else 'chdman')
        if os.path.exists(bundled_path):
            return bundled_path
        
        chdman_name = 'chdman.exe' if platform.system() == 'Windows' else 'chdman'
        chdman_path = shutil.which(chdman_name)
        if chdman_path:
            return chdman_path
        
        return None
    
    def get_install_command(self):
        """Get the correct package manager command for this Linux distro"""
        if platform.system() != 'Linux':
            return None
        
        try:
            with open('/etc/os-release', 'r') as f:
                os_info = f.read().lower()
            
            if 'ubuntu' in os_info or 'debian' in os_info or 'mint' in os_info:
                return "sudo apt install mame-tools"
            elif 'fedora' in os_info or 'rhel' in os_info or 'centos' in os_info:
                return "sudo dnf install mame"
            elif 'arch' in os_info or 'manjaro' in os_info:
                return "sudo pacman -S mame-tools"
            elif 'opensuse' in os_info:
                return "sudo zypper install mame-tools"
            else:
                return "sudo apt install mame-tools"
        except:
            return "sudo apt install mame-tools"
    
    def prompt_install_chdman(self):
        """Prompt user to install chdman automatically"""
        install_cmd = self.get_install_command()
        
        if not install_cmd:
            return False
        
        response = messagebox.askyesno(
            "First-Time Setup Required",
            f"CHD conversion requires chdman.\n\n"
            f"Would you like to install it now?\n"
            f"(This will open a terminal and require your password)\n\n"
            f"Command: {install_cmd}\n\n"
            f"This is a one-time setup.",
            icon='question'
        )
        
        if response:
            try:
                terminals = [
                    ['gnome-terminal', '--'],
                    ['konsole', '-e'],
                    ['xfce4-terminal', '-e'],
                    ['xterm', '-e'],
                ]
                
                install_script = f'{install_cmd}; echo "\n✅ Installation complete! Press Enter to close."; read'
                
                terminal_opened = False
                for terminal in terminals:
                    try:
                        subprocess.Popen(terminal + ['bash', '-c', install_script])
                        terminal_opened = True
                        break
                    except FileNotFoundError:
                        continue
                
                if terminal_opened:
                    messagebox.showinfo(
                        "Installing...",
                        "Please complete the installation in the terminal window.\n\n"
                        "After installation, try CHD conversion again."
                    )
                    return True
                else:
                    messagebox.showwarning(
                        "Manual Installation Required",
                        f"Could not open terminal automatically.\n\n"
                        f"Please run this command manually:\n{install_cmd}\n\n"
                        f"Then try CHD conversion again."
                    )
                    return False
            except Exception as e:
                messagebox.showerror(
                    "Installation Error",
                    f"Could not start installation.\n\n"
                    f"Please run manually:\n{install_cmd}"
                )
                return False
        
        return False
    
    def detect_available_formats(self, folder):
        """Detect which disc formats are available in the folder"""
        has_cue = len(list(Path(folder).glob("*.cue"))) > 0
        has_gdi = len(list(Path(folder).glob("*.gdi"))) > 0
        has_cdi = len(list(Path(folder).glob("*.cdi"))) > 0
        has_iso = len(list(Path(folder).glob("*.iso"))) > 0
        has_chd = len(list(Path(folder).glob("*.chd"))) > 0
        
        has_original_formats = has_cue or has_gdi or has_cdi or has_iso
        
        return has_original_formats, has_chd
    
    def extract_game_info(self, filename):
        """Extract game name and disc number from filename."""
        name_without_ext = os.path.splitext(filename)[0]
        
        patterns = [
            r'(.*?)[\s\-_]*\(Dis[ck]\s*(\d+)\)',
            r'(.*?)[\s\-_]*\[Dis[ck]\s*(\d+)\]',
            r'(.*?)[\s\-_]*Dis[ck]\s*(\d+)',
            r'(.*?)[\s\-_]*\(CD\s*(\d+)\)',
            r'(.*?)[\s\-_]*\[CD\s*(\d+)\]',
            r'(.*?)[\s\-_]*CD\s*(\d+)',
            r'(.*?)[\s\-_]*\((?:Side|Dis[ck])\s*([A-Z])\)',
            r'(.*?)[\s\-_]*\[(?:Side|Dis[ck])\s*([A-Z])\]',
        ]
        
        for i, pattern in enumerate(patterns):
            match = re.match(pattern, name_without_ext, re.IGNORECASE)
            if match:
                game_name = match.group(1).strip()
                disc_identifier = match.group(2)
                
                if i >= 6:
                    disc_num = ord(disc_identifier.upper()) - ord('A') + 1
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
                self.log_to_processing(f"Found {len(files)} {ext_pattern} file(s)")
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
                extensions_used = set(os.path.splitext(f[1])[1].lower() for f in files)
                if len(extensions_used) == 1:
                    multidisc_games[name] = files
                else:
                    self.log_to_processing(f"⚠️  Skipping '{name}' - mixed formats")
        
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
        
        with open(m3u_filename, 'w', encoding='utf-8') as f:
            for disc_num, disc_file in disc_files:
                f.write(f"{disc_file}\n")
        
        self.log_to_processing(f"  ✓ Created: {game_name}.m3u ({len(disc_files)} discs)")
        for disc_num, disc_file in disc_files:
            self.log_to_processing(f"      • Disc {disc_num}: {disc_file}")
        
        return True
    
    def create_m3u_files(self, folder):
        try:
            self.update_processing_status(
                "M3U Creator",
                "Detecting available disc formats..."
            )
            
            # Detect what formats are available
            has_original, has_chd = self.detect_available_formats(folder)
            
            # Determine which extensions to use
            extensions = None
            
            if has_original and has_chd:
                # Both formats exist - ask user which to use
                self.log_to_processing("⚠️ Found both original files (CUE/GDI/CDI/ISO) and CHD files")
                
                # Create custom dialog
                choice_dialog = tk.Toplevel(self.root)
                choice_dialog.title("Choose Format")
                choice_dialog.geometry("500x250")
                choice_dialog.configure(bg=self.bg_dark)
                choice_dialog.transient(self.root)
                choice_dialog.grab_set()
                
                # Center the dialog
                choice_dialog.update_idletasks()
                x = (choice_dialog.winfo_screenwidth() // 2) - (500 // 2)
                y = (choice_dialog.winfo_screenheight() // 2) - (250 // 2)
                choice_dialog.geometry(f"500x250+{x}+{y}")
                
                selected_format = None
                
                def select_chd():
                    nonlocal selected_format
                    selected_format = "chd"
                    choice_dialog.destroy()
                
                def select_original():
                    nonlocal selected_format
                    selected_format = "original"
                    choice_dialog.destroy()
                
                def cancel():
                    nonlocal selected_format
                    selected_format = None
                    choice_dialog.destroy()
                
                # Title
                tk.Label(
                    choice_dialog,
                    text="⚠️ Multiple Disc Formats Found",
                    font=("Arial", 16, "bold"),
                    bg=self.bg_dark,
                    fg=self.accent_orange
                ).pack(pady=(20, 10))
                
                # Message
                tk.Label(
                    choice_dialog,
                    text="Both original disc files and CHD files were found.\nWhich format do you want to use for M3U playlists?",
                    font=("Arial", 11),
                    bg=self.bg_dark,
                    fg=self.text_light,
                    justify="center"
                ).pack(pady=(0, 30))
                
                # Buttons frame
                btn_frame = tk.Frame(choice_dialog, bg=self.bg_dark)
                btn_frame.pack(pady=10)
                
                tk.Button(
                    btn_frame,
                    text="💾 Use CHD Files\n(compressed)",
                    command=select_chd,
                    font=("Arial", 11, "bold"),
                    bg=self.accent_blue,
                    fg="white",
                    cursor="hand2",
                    padx=20,
                    pady=15,
                    relief="flat",
                    width=15
                ).pack(side="left", padx=10)
                
                tk.Button(
                    btn_frame,
                    text="📀 Use Original Files\n(CUE/BIN/etc)",
                    command=select_original,
                    font=("Arial", 11, "bold"),
                    bg=self.accent_green,
                    fg="white",
                    cursor="hand2",
                    padx=20,
                    pady=15,
                    relief="flat",
                    width=15
                ).pack(side="left", padx=10)
                
                # Cancel button
                tk.Button(
                    choice_dialog,
                    text="Cancel",
                    command=cancel,
                    font=("Arial", 10),
                    bg=self.bg_frame,
                    fg=self.text_light,
                    cursor="hand2",
                    padx=15,
                    pady=8,
                    relief="flat"
                ).pack(pady=(10, 0))
                
                # Wait for dialog to close
                self.root.wait_window(choice_dialog)
                
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
                self.log_to_processing("✓ Auto-detected: Original disc files only")
            
            else:
                # No disc files found
                self.log_to_processing("❌ No disc files found")
                messagebox.showerror("No Files", "No disc image files found in the selected folder.")
                self.show_completion(success=False)
                return
            
            self.update_processing_status(
                "M3U Creator",
                "Scanning for multi-disc games..."
            )
            
            multidisc_games = self.find_multidisc_games(folder, extensions=extensions)
            
            if not multidisc_games:
                self.log_to_processing("❌ No multi-disc games found.")
                self.log_to_processing("\nMake sure files follow naming conventions like:")
                self.log_to_processing("  • Game Name (Disc 1).cue")
                self.log_to_processing("  • Game Name (Disc 2).chd")
                messagebox.showinfo("No Games Found", "No multi-disc games were found.")
                self.show_completion(success=False)
            else:
                self.log_to_processing(f"🎮 Found {len(multidisc_games)} multi-disc game(s)\n")
                
                total_games = len(multidisc_games)
                created_count = 0
                skipped_count = 0
                
                for index, (game_name, disc_files) in enumerate(multidisc_games.items(), 1):
                    self.update_processing_status(
                        "Creating M3U Playlists",
                        f"Processing game {index} of {total_games}",
                        index,
                        total_games,
                        f"{game_name}.m3u"
                    )
                    
                    if self.create_m3u_file(game_name, disc_files, folder):
                        created_count += 1
                    else:
                        skipped_count += 1
                
                self.log_to_processing("\n" + "=" * 60)
                self.log_to_processing(f"✅ Created: {created_count} | ⏭️ Skipped: {skipped_count}")
                self.log_to_processing("=" * 60)
                
                self.show_completion(success=True, converted=created_count, skipped=skipped_count)
        
        except Exception as e:
            self.log_to_processing(f"\n❌ ERROR: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
            self.show_completion(success=False)
    
    def convert_and_create_m3u(self, folder):
        """Convert to CHD then create M3U playlists"""
        try:
            self.update_processing_status(
                "CHD + M3U",
                "Step 1: Checking for chdman..."
            )
            
            # Check for chdman
            chdman_path = self.find_chdman()
            if not chdman_path:
                self.log_to_processing("❌ ERROR: chdman not found!")
                
                if platform.system() == 'Linux':
                    if self.prompt_install_chdman():
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
                    [chdman_path, '--help'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if test_result.returncode != 0 and platform.system() == 'Linux':
                    if 'error while loading shared libraries' in test_result.stderr:
                        self.log_to_processing("❌ ERROR: chdman has missing dependencies!")
                        
                        if self.prompt_install_chdman():
                            self.log_to_processing("⏳ Installation in progress.")
                        else:
                            self.log_to_processing("❌ Installation cancelled.")
                        
                        self.show_completion(success=False)
                        return
            except Exception as e:
                self.log_to_processing(f"⚠️ Warning: Could not test chdman: {e}")
            
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
                self.log_to_processing(f"Found {total_files} file(s) to convert\n")
                
                for index, source_file in enumerate(source_files, 1):
                    source_path = str(source_file)
                    chd_path = str(source_file.with_suffix('.chd'))
                    
                    self.update_processing_status(
                        "Step 1: Converting to CHD",
                        f"Processing file {index} of {total_files}",
                        index,
                        total_files,
                        source_file.name
                    )
                    
                    if os.path.exists(chd_path):
                        self.log_to_processing(f"⏭️  {source_file.name} (CHD exists)")
                        continue
                    
                    self.log_to_processing(f"🔄 {source_file.name}")
                    
                    # Add a processing indicator
                    processing_msg = "   Processing"
                    self.log_to_processing(processing_msg)
                    log_position = self.processing_log.index("end-2c linestart")
                    
                    try:
                        import time
                        # Start conversion process
                        process = subprocess.Popen(
                            [chdman_path, 'createcd', '-i', source_path, '-o', chd_path],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                        
                        # Animate dots while waiting
                        dots = 0
                        while process.poll() is None:
                            dots = (dots + 1) % 4
                            dot_str = "." * dots
                            self.processing_log.config(state='normal')
                            self.processing_log.delete(log_position, f"{log_position} lineend")
                            self.processing_log.insert(log_position, f"   Processing{dot_str}")
                            self.processing_log.config(state='disabled')
                            self.root.update_idletasks()
                            time.sleep(0.3)  # Just wait for animation, not the process!
                        
                        stdout, stderr = process.communicate()
                        
                        # Remove processing line
                        self.processing_log.config(state='normal')
                        self.processing_log.delete(f"{log_position} linestart", f"{log_position} lineend+1c")
                        self.processing_log.config(state='disabled')
                        
                        if process.returncode == 0:
                            self.log_to_processing(f"   ✓ Converted to CHD")
                            converted += 1
                            
                            if self.delete_after_conversion.get():
                                try:
                                    os.remove(source_path)
                                    if source_file.suffix.lower() == '.cue':
                                        bin_file = str(source_file.with_suffix('.bin'))
                                        if os.path.exists(bin_file):
                                            os.remove(bin_file)
                                    self.log_to_processing(f"   🗑️  Deleted originals")
                                except:
                                    pass
                        else:
                            self.log_to_processing(f"   ❌ Conversion failed")
                    except:
                        # Remove processing line if error
                        try:
                            self.processing_log.config(state='normal')
                            self.processing_log.delete(f"{log_position} linestart", f"{log_position} lineend+1c")
                            self.processing_log.config(state='disabled')
                        except:
                            pass
                        self.log_to_processing(f"   ❌ Error during conversion")
                
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
            multidisc_games = self.find_multidisc_games(folder, extensions=["*.chd"])
            
            created = 0
            
            if multidisc_games:
                total_games = len(multidisc_games)
                self.log_to_processing(f"Found {total_games} multi-disc game(s)\n")
                
                for index, (game_name, disc_files) in enumerate(multidisc_games, 1):
                    self.update_processing_status(
                        "Step 2: Creating M3U",
                        f"Processing game {index} of {total_games}",
                        index,
                        total_games,
                        f"{game_name}.m3u"
                    )
                    
                    if self.create_m3u_file(game_name, disc_files, folder):
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


if __name__ == "__main__":
    root = tk.Tk()
    app = RomMateGUI(root)
    root.mainloop()
