import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import os
import re
from pathlib import Path
import threading


class M3UCreatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("M3U Creator")
        self.root.geometry("750x600")
        self.root.resizable(True, True)
        
        # Variables
        self.folder_path = tk.StringVar()
        self.include_cue = tk.BooleanVar(value=True)
        self.include_chd = tk.BooleanVar(value=True)
        self.include_bin = tk.BooleanVar(value=False)
        
        self.create_widgets()
        
    def create_widgets(self):
        # Title
        title_label = tk.Label(
            self.root, 
            text="M3U Creator for Multi-Disc Games", 
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=10)
        
        # Description
        desc_label = tk.Label(
            self.root,
            text="Automatically create M3U playlist files for multi-disc PS1, PS2, Dreamcast, Saturn games",
            font=("Arial", 9)
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
        
        # File type selection frame
        filetype_frame = tk.LabelFrame(
            self.root,
            text="File Types to Include",
            font=("Arial", 10, "bold"),
            padx=20,
            pady=10
        )
        filetype_frame.pack(pady=10, padx=20, fill="x")
        
        cue_check = tk.Checkbutton(
            filetype_frame,
            text="CUE files (.cue)",
            variable=self.include_cue,
            font=("Arial", 10)
        )
        cue_check.pack(anchor="w", pady=2)
        
        chd_check = tk.Checkbutton(
            filetype_frame,
            text="CHD files (.chd) - Compressed disc format",
            variable=self.include_chd,
            font=("Arial", 10)
        )
        chd_check.pack(anchor="w", pady=2)
        
        bin_check = tk.Checkbutton(
            filetype_frame,
            text="BIN files (.bin) - Standalone disc images",
            variable=self.include_bin,
            font=("Arial", 10)
        )
        bin_check.pack(anchor="w", pady=2)
        
        # Info label
        info_label = tk.Label(
            self.root,
            text="💡 Tip: Most users should keep CUE and CHD enabled",
            font=("Arial", 9),
            fg="gray"
        )
        info_label.pack(pady=5)
        
        # Create button
        self.create_btn = tk.Button(
            self.root,
            text="▶ Create M3U Files",
            command=self.run_creator,
            font=("Arial", 12, "bold"),
            bg="#2196F3",
            fg="white",
            cursor="hand2",
            height=2,
            padx=20
        )
        self.create_btn.pack(pady=15)
        
        # Status/Log area
        log_label = tk.Label(self.root, text="Status Log:", font=("Arial", 10, "bold"))
        log_label.pack(anchor="w", padx=20)
        
        self.log_text = scrolledtext.ScrolledText(
            self.root,
            width=85,
            height=15,
            font=("Consolas", 9),
            bg="#f5f5f5",
            wrap=tk.WORD
        )
        self.log_text.pack(pady=5, padx=20, fill="both", expand=True)
        
        # Footer
        footer_label = tk.Label(
            self.root,
            text="Works with PlayStation, Dreamcast, Saturn, and other multi-disc systems",
            font=("Arial", 8),
            fg="gray"
        )
        footer_label.pack(pady=5)
        
    def browse_folder(self):
        folder = filedialog.askdirectory(title="Select Game Folder")
        if folder:
            self.folder_path.set(folder)
            self.log(f"✓ Selected folder: {folder}\n")
    
    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def run_creator(self):
        folder = self.folder_path.get()
        
        if not folder:
            messagebox.showwarning("No Folder", "Please select a game folder first!")
            return
        
        if not os.path.exists(folder):
            messagebox.showerror("Error", "Selected folder does not exist!")
            return
        
        if not self.include_cue.get() and not self.include_chd.get() and not self.include_bin.get():
            messagebox.showwarning("No File Types", "Please select at least one file type to include!")
            return
        
        # Clear log
        self.log_text.delete(1.0, tk.END)
        
        # Disable button during processing
        self.create_btn.config(state="disabled", text="Processing...")
        
        # Run in separate thread
        thread = threading.Thread(target=self.create_m3u_files, args=(folder,))
        thread.start()
    
    def extract_game_info(self, filename):
        """Extract game name and disc number from filename."""
        name_without_ext = os.path.splitext(filename)[0]
        
        patterns = [
            r'(.*?)[\s\-_]*\(Dis[ck]\s*(\d+)\)',
            r'(.*?)[\s\-_]*\[Dis[ck]\s*(\d+)\]',
            r'(.*?)[\s\-_]*Dis[ck]\s*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, name_without_ext, re.IGNORECASE)
            if match:
                game_name = match.group(1).strip()
                disc_num = int(match.group(2))
                return game_name, disc_num
        
        return None, None
    
    def find_multidisc_games(self, folder):
        """Scan folder for multi-disc games and group them."""
        games = {}
        extensions = []
        
        if self.include_cue.get():
            extensions.append("*.cue")
        if self.include_chd.get():
            extensions.append("*.chd")
        if self.include_bin.get():
            extensions.append("*.bin")
        
        self.log(f"Scanning for file types: {', '.join(extensions)}")
        self.log("-" * 60)
        
        for ext_pattern in extensions:
            files = list(Path(folder).glob(ext_pattern))
            self.log(f"Found {len(files)} {ext_pattern} file(s)")
            
            for file in files:
                filename = file.name
                game_name, disc_num = self.extract_game_info(filename)
                
                if game_name and disc_num:
                    if game_name not in games:
                        games[game_name] = []
                    games[game_name].append((disc_num, filename))
        
        self.log("-" * 60 + "\n")
        
        # Filter only games with multiple discs
        multidisc_games = {name: files for name, files in games.items() if len(files) > 1}
        
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
            self.log("=" * 60)
            self.log("M3U CREATOR - STARTING")
            self.log("=" * 60)
            self.log(f"Target folder: {folder}\n")
            
            multidisc_games = self.find_multidisc_games(folder)
            
            if not multidisc_games:
                self.log("❌ No multi-disc games found.")
                self.log("\nMake sure your disc files follow naming conventions like:")
                self.log("  • Game Name (Disc 1).cue")
                self.log("  • Game Name (Disc 2).chd")
                self.log("  • Game Name [Disc 1].bin")
                messagebox.showinfo("No Games Found", "No multi-disc games were found in the selected folder.")
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
                
                self.log("=" * 60)
                self.log("✅ COMPLETED SUCCESSFULLY!")
                self.log(f"  • M3U files created: {created_count}")
                self.log(f"  • Already existed (skipped): {skipped_count}")
                self.log("=" * 60)
                
                messagebox.showinfo(
                    "Success!", 
                    f"M3U creation complete!\n\nCreated: {created_count}\nSkipped: {skipped_count}"
                )
        
        except Exception as e:
            self.log(f"\n❌ ERROR: {str(e)}")
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
        
        finally:
            self.create_btn.config(state="normal", text="▶ Create M3U Files")


if __name__ == "__main__":
    root = tk.Tk()
    app = M3UCreatorGUI(root)
    root.mainloop()
