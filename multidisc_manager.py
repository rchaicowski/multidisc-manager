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
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # Variables
        self.folder_path = tk.StringVar()
        self.operation_mode = tk.StringVar(value="chd")
        self.m3u_file_type = tk.StringVar(value="all")  # For M3U: all supported formats
        
        # CHD conversion options
        self.delete_after_conversion = tk.BooleanVar(value=False)
        
        self.create_widgets()
        self.update_options_visibility()
        
    def create_widgets(self):
        # Title
        title_label = tk.Label(
            self.root, 
            text="Multi-Disc Manager", 
            font=("Arial", 18, "bold")
        )
        title_label.pack(pady=10)
        
        # Description
        desc_label = tk.Label(
            self.root,
            text="Create M3U playlists and convert disc images to CHD format",
            font=("Arial", 10)
        )
        desc_label.pack(pady=5)
        
        # Folder selection frame
        folder_frame = tk.Frame(self.root)
        folder_frame.pack(pady=15, padx=20, fill="x")
        
        tk.Label(folder_frame, text="Game Folder:", font=("Arial", 10, "bold")).pack(side="left")
        
        folder_entry = tk.Entry(
            folder_frame, 
            textvariable=self.folder_path, 
            width=50,
            font=("Arial", 10)
        )
        folder_entry.pack(side="left", padx=10, fill="x", expand=True)
        
        browse_btn = tk.Button(
            folder_frame, 
            text="Browse", 
            command=self.browse_folder,
            font=("Arial", 10),
            bg="#4CAF50",
            fg="white",
            cursor="hand2",
            padx=15
        )
        browse_btn.pack(side="left")
        
        # Operation mode selection
        mode_frame = tk.LabelFrame(
            self.root,
            text="What do you want to do?",
            font=("Arial", 11, "bold"),
            padx=20,
            pady=15
        )
        mode_frame.pack(pady=10, padx=20, fill="x")
        
        chd_radio = tk.Radiobutton(
            mode_frame,
            text="💾 Convert to CHD (compress disc images)",
            variable=self.operation_mode,
            value="chd",
            font=("Arial", 10),
            command=self.update_options_visibility
        )
        chd_radio.pack(anchor="w", pady=5)
        
        m3u_radio = tk.Radiobutton(
            mode_frame,
            text="📁 Create M3U Playlists (for multi-disc games)",
            variable=self.operation_mode,
            value="m3u",
            font=("Arial", 10),
            command=self.update_options_visibility
        )
        m3u_radio.pack(anchor="w", pady=5)
        
        both_radio = tk.Radiobutton(
            mode_frame,
            text="🔄 Convert to CHD + Create M3U Playlists",
            variable=self.operation_mode,
            value="both",
            font=("Arial", 10),
            command=self.update_options_visibility
        )
        both_radio.pack(anchor="w", pady=5)
        
        # Info button
        info_btn = tk.Button(
            mode_frame,
            text="ℹ️ Help - When to use each?",
            command=self.show_info,
            font=("Arial", 9),
            bg="#2196F3",
            fg="white",
            cursor="hand2"
        )
        info_btn.pack(anchor="w", pady=10)
        
        # Options frame (changes based on mode)
        self.options_frame = tk.LabelFrame(
            self.root,
            text="Options",
            font=("Arial", 10, "bold"),
            padx=20,
            pady=10
        )
        self.options_frame.pack(pady=10, padx=20, fill="x")
        
        # M3U options
        self.m3u_options = tk.Frame(self.options_frame)
        
        tk.Label(self.m3u_options, text="Create M3U playlists for:", font=("Arial", 9, "bold")).pack(anchor="w", pady=5)
        
        tk.Label(
            self.m3u_options,
            text="Scans for: CUE, GDI, CDI, ISO, CHD files",
            font=("Arial", 9),
            fg="gray"
        ).pack(anchor="w", padx=20, pady=5)
        
        info_frame = tk.Frame(self.m3u_options, bg="#e3f2fd", relief="ridge", borderwidth=1)
        info_frame.pack(fill="x", pady=10)
        
        tk.Label(
            info_frame,
            text="ℹ️ Note: All disc files must be in the same folder.\n"
                 "    Works with PSX, PS2, Dreamcast, Saturn, Sega CD, and more!",
            font=("Arial", 8),
            bg="#e3f2fd",
            fg="#1976d2",
            justify="left"
        ).pack(padx=10, pady=8, anchor="w")
        
        # CHD options
        self.chd_options = tk.Frame(self.options_frame)
        
        tk.Label(
            self.chd_options, 
            text="Converts: CUE, GDI, CDI, ISO → CHD format",
            font=("Arial", 9),
            fg="gray"
        ).pack(anchor="w", pady=5)
        
        tk.Checkbutton(
            self.chd_options,
            text="⚠️ Delete original files after successful conversion",
            variable=self.delete_after_conversion,
            font=("Arial", 9),
            fg="red"
        ).pack(anchor="w", pady=5)
        
        tk.Label(
            self.chd_options,
            text="(CHD files are compressed and save 40-60% space)",
            font=("Arial", 8),
            fg="gray"
        ).pack(anchor="w")
        
        # Both options
        self.both_options = tk.Frame(self.options_frame)
        
        tk.Label(
            self.both_options,
            text="Step 1: Convert all disc images to CHD",
            font=("Arial", 9, "bold")
        ).pack(anchor="w", pady=2)
        
        tk.Label(
            self.both_options,
            text="  Converts: CUE, GDI, CDI, ISO → CHD",
            font=("Arial", 8),
            fg="gray"
        ).pack(anchor="w", padx=20)
        
        tk.Label(
            self.both_options,
            text="Step 2: Create M3U playlists for multi-disc games",
            font=("Arial", 9, "bold")
        ).pack(anchor="w", pady=(10,2))
        
        tk.Label(
            self.both_options,
            text="  Groups CHD files into playlists",
            font=("Arial", 8),
            fg="gray"
        ).pack(anchor="w", padx=20)
        
        tk.Checkbutton(
            self.both_options,
            text="⚠️ Delete original files after successful conversion",
            variable=self.delete_after_conversion,
            font=("Arial", 9),
            fg="red"
        ).pack(anchor="w", pady=(10,5))
        
        # Process button
        self.process_btn = tk.Button(
            self.root,
            text="▶ Process Files",
            command=self.run_process,
            font=("Arial", 12, "bold"),
            bg="#2196F3",
            fg="white",
            cursor="hand2",
            height=2,
            padx=30
        )
        self.process_btn.pack(pady=15)
        
        # Progress bar (hidden by default)
        self.progress = ttk.Progressbar(
            self.root,
            mode='indeterminate',
            length=300
        )
        
        # Status/Log area
        log_label = tk.Label(self.root, text="Status Log:", font=("Arial", 10, "bold"))
        log_label.pack(anchor="w", padx=20)
        
        self.log_text = scrolledtext.ScrolledText(
            self.root,
            width=90,
            height=15,
            font=("Consolas", 9),
            bg="#f5f5f5",
            wrap=tk.WORD
        )
        self.log_text.pack(pady=5, padx=20, fill="both", expand=True)
        
        # Footer
        footer_label = tk.Label(
            self.root,
            text="Supports PS1, PS2, Dreamcast, Saturn, and other disc-based systems",
            font=("Arial", 8),
            fg="gray"
        )
        footer_label.pack(pady=5)
        
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
        
        # No validation needed for M3U mode anymore (radio buttons ensure one is selected)
        
        # Clear log
        self.log_text.delete(1.0, tk.END)
        
        # Disable button during processing
        self.process_btn.config(state="disabled", text="Processing...")
        self.progress.pack(pady=5)
        self.progress.start()
        
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
            
            # Check for chdman
            chdman_path = self.find_chdman()
            if not chdman_path:
                self.log("❌ ERROR: chdman not found!")
                self.log("\nchdman is required for CHD conversion.")
                self.log("The tool will be bundled in future releases.")
                self.log("\nFor now, please install MAME (includes chdman):")
                self.log("  Windows: https://www.mamedev.org/release.html")
                self.log("  Linux: sudo apt install mame-tools")
                messagebox.showerror(
                    "chdman Not Found",
                    "chdman is required for CHD conversion.\n\n"
                    "Please install MAME or mame-tools package.\n"
                    "See the log for installation instructions."
                )
                return
            
            self.log(f"✓ Found chdman: {chdman_path}\n")
            
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
                return
            
            self.log(f"\nTotal files to convert: {len(source_files)}\n")
            
            converted = 0
            failed = 0
            
            for source_file in source_files:
                source_path = str(source_file)
                source_ext = source_file.suffix.lower()
                chd_path = str(source_file.with_suffix('.chd'))
                
                # Skip if CHD already exists
                if os.path.exists(chd_path):
                    self.log(f"⏭️  Skipping {source_file.name} (CHD already exists)")
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
            self.log(f"  • Failed: {failed}")
            self.log("=" * 70)
            
            messagebox.showinfo(
                "Conversion Complete",
                f"CHD conversion finished!\n\nConverted: {converted}\nFailed: {failed}"
            )
        
        except Exception as e:
            self.log(f"\n❌ ERROR: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
        
        finally:
            self.progress.stop()
            self.progress.pack_forget()
            self.process_btn.config(state="normal")
            self.update_options_visibility()
    
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
            
            multidisc_games = self.find_multidisc_games(folder)
            
            if not multidisc_games:
                self.log("❌ No multi-disc games found.")
                self.log("\nMake sure your disc files follow naming conventions like:")
                self.log("  • Game Name (Disc 1).cue")
                self.log("  • Game Name (Disc 2).chd")
                self.log("  • Game Name [Disc 1].bin")
                messagebox.showinfo("No Games Found", "No multi-disc games were found.")
            else:
                self.log(f"🎮 Found {len(multidisc_games)} multi-disc game(s)\n")
                
                created_count = 0
                skipped_count = 0
                
                for game_name, disc_files in multidisc_games.items():
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
                
                messagebox.showinfo(
                    "Success!", 
                    f"M3U creation complete!\n\nCreated: {created_count}\nSkipped: {skipped_count}"
                )
        
        except Exception as e:
            self.log(f"\n❌ ERROR: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
        
        finally:
            self.progress.stop()
            self.progress.pack_forget()
            self.process_btn.config(state="normal")
            self.update_options_visibility()
    
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
            
            # Check for chdman
            chdman_path = self.find_chdman()
            if not chdman_path:
                self.log("❌ ERROR: chdman not found!")
                self.log("\nCannot proceed without chdman.")
                messagebox.showerror("chdman Not Found", "chdman is required. See log for details.")
                return
            
            self.log(f"✓ Found chdman: {chdman_path}")
            
            # Find all convertible files
            source_files = []
            for pattern in ["*.cue", "*.gdi", "*.cdi", "*.iso"]:
                found = list(Path(folder).glob(pattern))
                if found:
                    source_files.extend(found)
            
            if source_files:
                self.log(f"Found {len(source_files)} file(s) to convert\n")
                
                converted = 0
                for source_file in source_files:
                    source_path = str(source_file)
                    chd_path = str(source_file.with_suffix('.chd'))
                    
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
            
            multidisc_games = self.find_multidisc_games(folder)
            
            if multidisc_games:
                self.log(f"Found {len(multidisc_games)} multi-disc game(s)\n")
                
                created = 0
                for game_name, disc_files in multidisc_games.items():
                    if self.create_m3u_file(game_name, disc_files, folder):
                        created += 1
                    self.log("")
                
                self.log(f"Created {created} M3U playlist(s)")
            else:
                self.log("No multi-disc games found")
            
            self.log("\n" + "=" * 70)
            self.log("✅ ALL OPERATIONS COMPLETE!")
            self.log("=" * 70)
            
            messagebox.showinfo("Complete!", "CHD conversion and M3U creation finished!")
        
        except Exception as e:
            self.log(f"\n❌ ERROR: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
        
        finally:
            self.progress.stop()
            self.progress.pack_forget()
            self.process_btn.config(state="normal")
            self.update_options_visibility()


if __name__ == "__main__":
    root = tk.Tk()
    app = MultiDiscManagerGUI(root)
    root.mainloop()
