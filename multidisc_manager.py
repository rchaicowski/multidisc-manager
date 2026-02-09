import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, ttk
import os
import re
from pathlib import Path
import threading
import subprocess
import platform
import shutil


class MultiDiscManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Multi-Disc Manager")
        self.root.geometry("850x850")  # Increased height
        self.root.resizable(True, True)
        
        # Dark mode colors
        self.bg_dark = "#2b2b2b"
        self.bg_frame = "#3c3c3c"
        self.text_light = "#e0e0e0"
        self.text_gray = "#9e9e9e"
        self.accent_blue = "#42a5f5"
        self.accent_green = "#66bb6a"
        self.accent_red = "#ef5350"
        self.accent_orange = "#ff9800"
        
        # Configure root background
        self.root.configure(bg=self.bg_dark)
        
        # Variables
        self.folder_path = tk.StringVar()
        self.operation_mode = tk.StringVar(value="chd")
        self.m3u_file_type = tk.StringVar(value="all")
        
        # CHD conversion options
        self.delete_after_conversion = tk.BooleanVar(value=False)
        
        # Sound options
        self.sounds_enabled = tk.BooleanVar(value=True)
        self.load_sounds()
        
        self.create_widgets()
    
    def load_sounds(self):
        """Check if sound files exist"""
        sounds_dir = os.path.join(os.path.dirname(__file__), 'sounds')
        self.success_sound_path = os.path.join(sounds_dir, 'success.wav')
        self.fail_sound_path = os.path.join(sounds_dir, 'fail.wav')
    
    def play_sound(self, sound_type):
        """Play a sound if enabled using OS commands"""
        if not self.sounds_enabled.get():
            return
        
        sound_path = self.success_sound_path if sound_type == "success" else self.fail_sound_path
        
        if not os.path.exists(sound_path):
            return
        
        try:
            if platform.system() == 'Windows':
                import winsound
                winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                # Linux: Just fire and forget with &
                os.system(f'aplay "{sound_path}" >/dev/null 2>&1 &')
        except Exception as e:
            pass
    
    def update_status(self, message, progress=None, total=None):
        """Update the status label and progress bar"""
        self.status_label.config(text=message)
        
        if progress is not None and total is not None and total > 0:
            percentage = int((progress / total) * 100)
            self.progress['value'] = percentage
            self.progress_text.config(text=f"{percentage}% ({progress}/{total})")
        
        self.root.update_idletasks()
    
    def show_processing_ui(self):
        """Show status and progress during processing"""
        self.status_frame.pack(pady=10, padx=20, fill="x")
        self.progress_frame.pack(pady=5)
        self.progress['value'] = 0
        self.progress_text.config(text="0%")
    
    def hide_processing_ui(self):
        """Hide status and progress"""
        self.status_frame.pack_forget()
        self.progress_frame.pack_forget()
    
    def show_finished_state(self, success=True):
        """Show completion state"""
        if success:
            self.status_label.config(
                text="✅ All operations completed successfully!",
                bg="#1b5e20",
                fg="#a5d6a7"
            )
            self.process_btn.config(
                text="✅ Finished - Process More?",
                bg=self.accent_green,
                state="normal"
            )
            # Play success sound - schedule in main thread
            self.root.after(100, lambda: self.play_sound("success"))
        else:
            self.status_label.config(
                text="⚠️ Completed with errors - check log",
                bg="#b71c1c",
                fg="#ffcdd2"
            )
            self.process_btn.config(
                text="⚠️ Finished - Try Again?",
                bg=self.accent_red,
                state="normal"
            )
            # Play fail sound - schedule in main thread
            self.root.after(100, lambda: self.play_sound("fail"))
        
        # Keep status visible but hide progress
        self.progress_frame.pack_forget()
    
    def reset_ui_state(self):
        """Reset UI to initial state"""
        self.status_label.config(
            text="Ready to process",
            bg="#1b5e20",
            fg="#a5d6a7"
        )
        self.hide_processing_ui()
        mode = self.operation_mode.get()
        if mode == "chd":
            self.process_btn.config(text="▶ Convert to CHD", bg=self.accent_blue)
        elif mode == "m3u":
            self.process_btn.config(text="▶ Create M3U Files", bg=self.accent_blue)
        else:
            self.process_btn.config(text="▶ Convert & Create M3U", bg=self.accent_blue)
    
    def update_options_visibility(self):
        """Show/hide options based on selected mode"""
        self.m3u_options.pack_forget()
        self.chd_options.pack_forget()
        self.both_options.pack_forget()
        
        # Reset UI when changing modes
        self.reset_ui_state()
        
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
        # Add top padding
        tk.Frame(self.root, height=10, bg=self.bg_dark).pack()
        
        # Title
        title_label = tk.Label(
            self.root, 
            text="Multi-Disc Manager", 
            font=("Arial", 20, "bold"),
            bg=self.bg_dark,
            fg=self.text_light
        )
        title_label.pack(pady=15)
        
        # Description
        desc_label = tk.Label(
            self.root,
            text="Create M3U playlists and convert disc images to CHD format",
            font=("Arial", 10),
            bg=self.bg_dark,
            fg=self.text_gray
        )
        desc_label.pack(pady=(0, 20))
        
        # Folder selection frame
        folder_frame = tk.Frame(self.root, bg=self.bg_dark)
        folder_frame.pack(pady=10, padx=30, fill="x")
        
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
            self.root,
            bg=self.bg_frame,
            relief="groove",
            bd=2
        )
        mode_frame.pack(pady=15, padx=30, fill="x")
        
        # Title inside the frame
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
        
        # Add separator
        tk.Frame(mode_frame, height=1, bg=self.text_gray).pack(fill="x", padx=25, pady=15)
        
        # Info button
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
        
        # Options frame (changes based on mode)
        self.options_frame = tk.Frame(
            self.root,
            bg=self.bg_frame,
            relief="groove",
            bd=2
        )
        self.options_frame.pack(pady=15, padx=30, fill="x")
        
        # Title will be added by each option frame
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
                 "    Works with PSX, PS2, Dreamcast, Saturn, Sega CD, and more!",
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
            self.root,
            text="▶ Process Files",
            command=self.run_process,
            font=("Arial", 13, "bold"),
            bg=self.accent_blue,
            fg="white",
            cursor="hand2",
            height=2,
            padx=40,
            relief="flat",
            activebackground="#1e88e5",
            activeforeground="white",
            bd=0
        )
        self.process_btn.pack(pady=20)
        
        # Status frame (shows current operation)
        self.status_frame = tk.Frame(self.root, bg="#1b5e20", relief="groove", borderwidth=2)
        
        self.status_label = tk.Label(
            self.status_frame,
            text="Ready to process",
            font=("Arial", 12, "bold"),
            bg="#1b5e20",
            fg="#a5d6a7"
        )
        self.status_label.pack(pady=15, padx=25)
        
        # Progress bar with percentage
        self.progress_frame = tk.Frame(self.root, bg=self.bg_dark)
        
        self.progress = ttk.Progressbar(
            self.progress_frame,
            mode='determinate',
            length=450
        )
        self.progress.pack(side="left", padx=(0, 15))
        
        self.progress_text = tk.Label(
            self.progress_frame,
            text="0%",
            font=("Arial", 10, "bold"),
            bg=self.bg_dark,
            fg=self.text_light
        )
        self.progress_text.pack(side="left")
        
        # Status/Log area
        log_frame = tk.Frame(self.root, bg=self.bg_dark)
        log_frame.pack(pady=(15, 5), padx=30, fill="both", expand=True)
        
        log_label = tk.Label(
            log_frame, 
            text="Status Log:", 
            font=("Arial", 11, "bold"),
            bg=self.bg_dark,
            fg=self.text_light
        )
        log_label.pack(anchor="w", pady=(0, 8))
        
        # Scrolled text with border frame for better visibility
        log_border = tk.Frame(log_frame, bg=self.text_gray, relief="solid", bd=1)
        log_border.pack(fill="both", expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            log_border,
            width=90,
            height=10,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#d4d4d4",
            wrap=tk.WORD,
            insertbackground=self.text_light,
            selectbackground=self.accent_blue,
            selectforeground="white",
            relief="flat",
            bd=0,
            padx=10,
            pady=8
        )
        self.log_text.pack(fill="both", expand=True, padx=1, pady=1)
        
        # Footer with sound toggle
        footer_frame = tk.Frame(self.root, bg=self.bg_dark)
        footer_frame.pack(pady=(10, 15))
        
        def test_sound():
            """Test sound when checkbox is toggled"""
            if self.sounds_enabled.get():
                self.play_sound("success")
        
        sound_check = tk.Checkbutton(
            footer_frame,
            text="🔔 Enable sounds",
            variable=self.sounds_enabled,
            command=test_sound,  # Play sound when toggled
            font=("Arial", 9),
            bg=self.bg_dark,
            fg=self.text_gray,
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
        
        # Initialize UI state
        self.update_options_visibility()
        
    def update_status(self, message, progress=None, total=None):
        """Update the status label and progress bar"""
        self.status_label.config(text=message)
        
        if progress is not None and total is not None and total > 0:
            percentage = int((progress / total) * 100)
            self.progress['value'] = percentage
            self.progress_text.config(text=f"{percentage}% ({progress}/{total})")
        
        self.root.update_idletasks()
    
    def show_processing_ui(self):
        """Show status and progress during processing"""
        self.status_frame.pack(pady=10, padx=20, fill="x")
        self.progress_frame.pack(pady=5)
        self.progress['value'] = 0
        self.progress_text.config(text="0%")
    
    def hide_processing_ui(self):
        """Hide status and progress"""
        self.status_frame.pack_forget()
        self.progress_frame.pack_forget()
    
    def show_finished_state(self, success=True):
        """Show completion state"""
        if success:
            self.status_label.config(
                text="✅ All operations completed successfully!",
                bg="#c8e6c9",
                fg="#1b5e20"
            )
            self.process_btn.config(
                text="✅ Finished - Process More?",
                bg="#4CAF50",
                state="normal"
            )
        else:
            self.status_label.config(
                text="⚠️ Completed with errors - check log",
                bg="#ffccbc",
                fg="#bf360c"
            )
            self.process_btn.config(
                text="⚠️ Finished - Try Again?",
                bg="#FF5722",
                state="normal"
            )
        
        # Keep status visible but hide progress
        self.progress_frame.pack_forget()
    
    def reset_ui_state(self):
        """Reset UI to initial state"""
        self.status_label.config(
            text="Ready to process",
            bg="#e8f5e9",
            fg="#2e7d32"
        )
        self.hide_processing_ui()
        mode = self.operation_mode.get()
        if mode == "chd":
            self.process_btn.config(text="▶ Convert to CHD", bg="#2196F3")
        elif mode == "m3u":
            self.process_btn.config(text="▶ Create M3U Files", bg="#2196F3")
        else:
            self.process_btn.config(text="▶ Convert & Create M3U", bg="#2196F3")
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
• PS1 games like Final Fantasy VII, VIII, IX
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
        
        text_widget = scrolledtext.ScrolledText(
            info_window,
            width=70,
            height=35,
            font=("Arial", 10),
            wrap=tk.WORD,
            padx=15,
            pady=15
        )
        text_widget.pack(fill="both", expand=True, padx=10, pady=10)
        text_widget.insert(1.0, info_text)
        text_widget.config(state="disabled")
        
        close_btn = tk.Button(
            info_window,
            text="Close",
            command=info_window.destroy,
            font=("Arial", 10),
            bg="#4CAF50",
            fg="white",
            cursor="hand2",
            padx=20
        )
        close_btn.pack(pady=10)
    
    def browse_folder(self):
        folder = filedialog.askdirectory(title="Select Game Folder")
        if folder:
            self.folder_path.set(folder)
            self.log(f"✓ Selected folder: {folder}\n")
    
    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def run_process(self):
        folder = self.folder_path.get()
        
        if not folder:
            messagebox.showwarning("No Folder", "Please select a game folder first!")
            return
        
        if not os.path.exists(folder):
            messagebox.showerror("Error", "Selected folder does not exist!")
            return
        
        mode = self.operation_mode.get()
        
        # Clear log
        self.log_text.delete(1.0, tk.END)
        
        # Show processing UI
        self.show_processing_ui()
        self.update_status("Initializing...", 0, 100)
        
        # Disable button during processing
        self.process_btn.config(state="disabled", text="Processing...")
        
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
            self.log("=" * 70)
            self.log("CHD CONVERTER - STARTING")
            self.log("=" * 70)
            self.log(f"Target folder: {folder}\n")
            
            self.update_status("Checking for chdman...", 5, 100)
            
            # Check for chdman
            chdman_path = self.find_chdman()
            if not chdman_path:
                self.log("❌ ERROR: chdman not found!")
                
                # On Linux, offer to install automatically
                if platform.system() == 'Linux':
                    self.log("\nOffering automatic installation...")
                    if self.prompt_install_chdman():
                        self.log("\n⏳ Installation in progress.")
                        self.log("Please complete installation in the terminal, then try again.")
                    else:
                        self.log("\n❌ Installation cancelled.")
                else:
                    self.log("\nchdman is required for CHD conversion.")
                    self.log("It should be in the tools/ folder.")
                    messagebox.showerror(
                        "chdman Not Found",
                        "chdman is required for CHD conversion.\n\n"
                        "It should be bundled in the tools/ folder."
                    )
                
                self.show_finished_state(success=False)
                return
            
            # Test if chdman actually works (check for dependency issues)
            try:
                test_result = subprocess.run(
                    [chdman_path, '--help'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                # If it fails with library error on Linux, offer to install
                if test_result.returncode != 0 and platform.system() == 'Linux':
                    if 'error while loading shared libraries' in test_result.stderr:
                        self.log("❌ ERROR: chdman has missing dependencies!")
                        self.log(f"Error: {test_result.stderr[:150]}")
                        
                        if self.prompt_install_chdman():
                            self.log("\n⏳ Installation in progress.")
                            self.log("Please complete installation in the terminal, then try again.")
                        else:
                            self.log("\n❌ Installation cancelled.")
                        
                        self.show_finished_state(success=False)
                        return
            except Exception as e:
                self.log(f"⚠️ Warning: Could not test chdman: {e}")
            
            self.log(f"✓ Found chdman: {chdman_path}\n")
            
            self.update_status("Scanning for disc images...", 10, 100)
            
            # Find all convertible files
            source_files = []
            for pattern in ["*.cue", "*.gdi", "*.cdi", "*.iso"]:
                found = list(Path(folder).glob(pattern))
                if found:
                    self.log(f"Found {len(found)} {pattern} file(s)")
                    source_files.extend(found)
            
            if not source_files:
                self.log("\n❌ No convertible files found.")
                self.log("Supported formats: CUE, GDI, CDI, ISO")
                messagebox.showinfo("No Files", "No convertible disc images found.")
                self.show_finished_state(success=False)
                return
            
            total_files = len(source_files)
            self.log(f"\nTotal files to convert: {total_files}\n")
            
            converted = 0
            failed = 0
            skipped = 0
            
            for index, source_file in enumerate(source_files, 1):
                source_path = str(source_file)
                source_ext = source_file.suffix.lower()
                chd_path = str(source_file.with_suffix('.chd'))
                
                # Update status
                self.update_status(
                    f"Converting: {source_file.name}",
                    index,
                    total_files
                )
                
                # Skip if CHD already exists
                if os.path.exists(chd_path):
                    self.log(f"⏭️  Skipping {source_file.name} (CHD already exists)")
                    skipped += 1
                    continue
                
                self.log(f"🔄 Converting: {source_file.name}")
                
                try:
                    # Different chdman commands for different formats
                    if source_ext in ['.cue', '.gdi', '.cdi']:
                        cmd = [chdman_path, 'createcd', '-i', source_path, '-o', chd_path]
                    else:  # .iso
                        cmd = [chdman_path, 'createcd', '-i', source_path, '-o', chd_path]
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    
                    if result.returncode == 0:
                        self.log(f"   ✓ Success: {os.path.basename(chd_path)}")
                        converted += 1
                        
                        # Delete original files if option is enabled
                        if self.delete_after_conversion.get():
                            try:
                                os.remove(source_path)
                                # For CUE files, also remove associated BIN files
                                if source_ext == '.cue':
                                    bin_file = source_path.rsplit('.', 1)[0] + '.bin'
                                    if os.path.exists(bin_file):
                                        os.remove(bin_file)
                                self.log(f"   🗑️  Deleted original files")
                            except Exception as e:
                                self.log(f"   ⚠️  Could not delete originals: {e}")
                    else:
                        self.log(f"   ❌ Failed: {result.stderr[:150]}")
                        failed += 1
                
                except subprocess.TimeoutExpired:
                    self.log(f"   ❌ Timeout - conversion took too long")
                    failed += 1
                except Exception as e:
                    self.log(f"   ❌ Error: {str(e)}")
                    failed += 1
                
                self.log("")
            
            self.log("=" * 70)
            self.log("✅ CONVERSION COMPLETE!")
            self.log(f"  • Successfully converted: {converted}")
            self.log(f"  • Skipped (already exist): {skipped}")
            self.log(f"  • Failed: {failed}")
            self.log("=" * 70)
            
            success = failed == 0
            self.show_finished_state(success=success)
            
            messagebox.showinfo(
                "Conversion Complete",
                f"CHD conversion finished!\n\nConverted: {converted}\nSkipped: {skipped}\nFailed: {failed}"
            )
        
        except Exception as e:
            self.log(f"\n❌ ERROR: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
            self.show_finished_state(success=False)
        
        finally:
            pass
    
    def find_chdman(self):
        """Try to find chdman executable"""
        # Check if bundled with app (future)
        bundled_path = os.path.join(os.path.dirname(__file__), 'tools', 
                                    'chdman.exe' if platform.system() == 'Windows' else 'chdman')
        if os.path.exists(bundled_path):
            return bundled_path
        
        # Check if in system PATH
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
                return "sudo apt install mame-tools"  # Default to apt
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
                # Try different terminal emulators (Linux has many)
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
    
    def extract_game_info(self, filename):
        """Extract game name and disc number from filename."""
        name_without_ext = os.path.splitext(filename)[0]
        
        # Expanded patterns to handle more variations
        patterns = [
            # Standard disc patterns
            r'(.*?)[\s\-_]*\(Dis[ck]\s*(\d+)\)',      # (Disc 1) or (Disk 1)
            r'(.*?)[\s\-_]*\[Dis[ck]\s*(\d+)\]',      # [Disc 1] or [Disk 1]
            r'(.*?)[\s\-_]*Dis[ck]\s*(\d+)',          # Disc 1 or Disk 1
            # CD patterns
            r'(.*?)[\s\-_]*\(CD\s*(\d+)\)',           # (CD1) or (CD 1)
            r'(.*?)[\s\-_]*\[CD\s*(\d+)\]',           # [CD1] or [CD 1]
            r'(.*?)[\s\-_]*CD\s*(\d+)',               # CD1 or CD 1
            # Side/Disk letter patterns (A=1, B=2, etc.)
            r'(.*?)[\s\-_]*\((?:Side|Dis[ck])\s*([A-Z])\)',  # (Side A) or (Disk A)
            r'(.*?)[\s\-_]*\[(?:Side|Dis[ck])\s*([A-Z])\]',  # [Side A] or [Disk A]
        ]
        
        for i, pattern in enumerate(patterns):
            match = re.match(pattern, name_without_ext, re.IGNORECASE)
            if match:
                game_name = match.group(1).strip()
                disc_identifier = match.group(2)
                
                # Convert letter to number (A=1, B=2, etc.) for last two patterns
                if i >= 6:  # Letter-based patterns
                    disc_num = ord(disc_identifier.upper()) - ord('A') + 1
                else:
                    disc_num = int(disc_identifier)
                
                return game_name, disc_num
        
        return None, None
    
    def find_multidisc_games(self, folder):
        """Scan folder for multi-disc games and group them."""
        games = {}
        
        # All supported disc image formats
        extensions = ["*.cue", "*.gdi", "*.cdi", "*.iso", "*.chd"]
        
        self.log(f"Scanning for all supported formats: {', '.join(extensions)}")
        self.log("-" * 60)
        
        all_files = []
        for ext_pattern in extensions:
            files = list(Path(folder).glob(ext_pattern))
            if files:
                self.log(f"Found {len(files)} {ext_pattern} file(s)")
                all_files.extend(files)
        
        for file in all_files:
            filename = file.name
            game_name, disc_num = self.extract_game_info(filename)
            
            if game_name and disc_num:
                if game_name not in games:
                    games[game_name] = []
                games[game_name].append((disc_num, filename))
        
        self.log("-" * 60 + "\n")
        
        # Filter only games with multiple discs and verify all discs use same format
        multidisc_games = {}
        for name, files in games.items():
            if len(files) > 1:
                # Check if all files have the same extension
                extensions_used = set(os.path.splitext(f[1])[1].lower() for f in files)
                if len(extensions_used) == 1:
                    multidisc_games[name] = files
                else:
                    self.log(f"⚠️  Skipping '{name}' - mixed formats detected")
                    self.log(f"    Formats found: {', '.join(extensions_used)}")
        
        # Sort disc files by disc number
        for game_name in multidisc_games:
            multidisc_games[game_name].sort(key=lambda x: x[0])
        
        return multidisc_games
    
    def create_m3u_file(self, game_name, disc_files, folder):
        """Create an .m3u file for a multi-disc game."""
        m3u_filename = os.path.join(folder, f"{game_name}.m3u")
        
        if os.path.exists(m3u_filename):
            self.log(f"  ⚠ M3U already exists: {game_name}.m3u")
            return False
        
        with open(m3u_filename, 'w', encoding='utf-8') as f:
            for disc_num, disc_file in disc_files:
                f.write(f"{disc_file}\n")
        
        self.log(f"  ✓ Created: {game_name}.m3u")
        self.log(f"    Total discs: {len(disc_files)}")
        for disc_num, disc_file in disc_files:
            self.log(f"      • Disc {disc_num}: {disc_file}")
        
        return True
    
    def create_m3u_files(self, folder):
        try:
            self.log("=" * 70)
            self.log("M3U CREATOR - STARTING")
            self.log("=" * 70)
            self.log(f"Target folder: {folder}\n")
            
            self.update_status("Scanning for multi-disc games...", 20, 100)
            
            multidisc_games = self.find_multidisc_games(folder)
            
            if not multidisc_games:
                self.log("❌ No multi-disc games found.")
                self.log("\nMake sure your disc files follow naming conventions like:")
                self.log("  • Game Name (Disc 1).cue")
                self.log("  • Game Name (Disc 2).chd")
                self.log("  • Game Name [Disc 1].bin")
                messagebox.showinfo("No Games Found", "No multi-disc games were found.")
                self.show_finished_state(success=False)
            else:
                self.log(f"🎮 Found {len(multidisc_games)} multi-disc game(s)\n")
                
                total_games = len(multidisc_games)
                created_count = 0
                skipped_count = 0
                
                for index, (game_name, disc_files) in enumerate(multidisc_games.items(), 1):
                    self.update_status(
                        f"Creating M3U: {game_name}",
                        index,
                        total_games
                    )
                    
                    if self.create_m3u_file(game_name, disc_files, folder):
                        created_count += 1
                    else:
                        skipped_count += 1
                    self.log("")
                
                self.log("=" * 70)
                self.log("✅ COMPLETED SUCCESSFULLY!")
                self.log(f"  • M3U files created: {created_count}")
                self.log(f"  • Already existed (skipped): {skipped_count}")
                self.log("=" * 70)
                
                self.show_finished_state(success=True)
                
                messagebox.showinfo(
                    "Success!", 
                    f"M3U creation complete!\n\nCreated: {created_count}\nSkipped: {skipped_count}"
                )
        
        except Exception as e:
            self.log(f"\n❌ ERROR: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
            self.show_finished_state(success=False)
        
        finally:
            pass
    
    def convert_and_create_m3u(self, folder):
        """Convert to CHD then create M3U playlists"""
        try:
            self.log("=" * 70)
            self.log("CONVERT TO CHD + CREATE M3U - STARTING")
            self.log("=" * 70)
            self.log(f"Target folder: {folder}\n")
            
            # Step 1: Convert to CHD
            self.log("STEP 1: Converting disc images to CHD")
            self.log("-" * 70)
            
            self.update_status("Step 1: Checking for chdman...", 5, 100)
            
            # Check for chdman
            chdman_path = self.find_chdman()
            if not chdman_path:
                self.log("❌ ERROR: chdman not found!")
                
                # On Linux, offer to install automatically
                if platform.system() == 'Linux':
                    self.log("\nOffering automatic installation...")
                    if self.prompt_install_chdman():
                        self.log("\n⏳ Installation in progress.")
                        self.log("Please complete installation in the terminal, then try again.")
                    else:
                        self.log("\n❌ Installation cancelled.")
                else:
                    messagebox.showerror("chdman Not Found", "chdman is required. See log for details.")
                
                self.show_finished_state(success=False)
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
                        self.log("❌ ERROR: chdman has missing dependencies!")
                        self.log(f"Error: {test_result.stderr[:150]}")
                        
                        if self.prompt_install_chdman():
                            self.log("\n⏳ Installation in progress.")
                            self.log("Please complete installation in the terminal, then try again.")
                        else:
                            self.log("\n❌ Installation cancelled.")
                        
                        self.show_finished_state(success=False)
                        return
            except Exception as e:
                self.log(f"⚠️ Warning: Could not test chdman: {e}")
            
            self.log(f"✓ Found chdman: {chdman_path}")
            
            self.update_status("Step 1: Scanning for disc images...", 10, 100)
            
            # Find all convertible files
            source_files = []
            for pattern in ["*.cue", "*.gdi", "*.cdi", "*.iso"]:
                found = list(Path(folder).glob(pattern))
                if found:
                    source_files.extend(found)
            
            if source_files:
                total_files = len(source_files)
                self.log(f"Found {total_files} file(s) to convert\n")
                
                converted = 0
                for index, source_file in enumerate(source_files, 1):
                    source_path = str(source_file)
                    chd_path = str(source_file.with_suffix('.chd'))
                    
                    # Calculate progress (0-50% for CHD conversion)
                    progress = 10 + int((index / total_files) * 40)
                    self.update_status(
                        f"Step 1: Converting {source_file.name}",
                        progress,
                        100
                    )
                    
                    if os.path.exists(chd_path):
                        self.log(f"⏭️  {source_file.name} (CHD exists)")
                        continue
                    
                    self.log(f"🔄 {source_file.name}")
                    
                    try:
                        result = subprocess.run(
                            [chdman_path, 'createcd', '-i', source_path, '-o', chd_path],
                            capture_output=True,
                            text=True,
                            timeout=300
                        )
                        
                        if result.returncode == 0:
                            self.log(f"   ✓ Converted to CHD")
                            converted += 1
                            
                            if self.delete_after_conversion.get():
                                try:
                                    os.remove(source_path)
                                    if source_file.suffix.lower() == '.cue':
                                        bin_file = str(source_file.with_suffix('.bin'))
                                        if os.path.exists(bin_file):
                                            os.remove(bin_file)
                                    self.log(f"   🗑️  Deleted originals")
                                except:
                                    pass
                        else:
                            self.log(f"   ❌ Conversion failed")
                    except:
                        self.log(f"   ❌ Error during conversion")
                
                self.log(f"\nConverted {converted} file(s) to CHD")
            else:
                self.log("No files found to convert")
            
            # Step 2: Create M3U playlists
            self.log("\n" + "=" * 70)
            self.log("STEP 2: Creating M3U playlists")
            self.log("-" * 70 + "\n")
            
            self.update_status("Step 2: Scanning for multi-disc games...", 55, 100)
            
            multidisc_games = self.find_multidisc_games(folder)
            
            if multidisc_games:
                total_games = len(multidisc_games)
                self.log(f"Found {total_games} multi-disc game(s)\n")
                
                created = 0
                for index, (game_name, disc_files) in enumerate(multidisc_games.items(), 1):
                    # Calculate progress (50-100% for M3U creation)
                    progress = 55 + int((index / total_games) * 45)
                    self.update_status(
                        f"Step 2: Creating M3U for {game_name}",
                        progress,
                        100
                    )
                    
                    if self.create_m3u_file(game_name, disc_files, folder):
                        created += 1
                    self.log("")
                
                self.log(f"Created {created} M3U playlist(s)")
            else:
                self.log("No multi-disc games found")
            
            self.log("\n" + "=" * 70)
            self.log("✅ ALL OPERATIONS COMPLETE!")
            self.log("=" * 70)
            
            self.show_finished_state(success=True)
            
            messagebox.showinfo("Complete!", "CHD conversion and M3U creation finished!")
        
        except Exception as e:
            self.log(f"\n❌ ERROR: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
            self.show_finished_state(success=False)
        
        finally:
            pass


if __name__ == "__main__":
    root = tk.Tk()
    app = MultiDiscManagerGUI(root)
    root.mainloop()
