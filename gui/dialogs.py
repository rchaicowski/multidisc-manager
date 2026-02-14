"""Custom dialog windows for RomMate"""

import tkinter as tk
from gui.theme import Theme


def show_format_choice_dialog(parent):
    """Show dialog asking user to choose between CHD and original files
    
    Args:
        parent: Parent tkinter window
        
    Returns:
        str: "chd", "original", or None if cancelled
    """
    choice_dialog = tk.Toplevel(parent)
    choice_dialog.title("Choose Format")
    choice_dialog.geometry("500x250")
    choice_dialog.configure(bg=Theme.BG_DARK)
    choice_dialog.transient(parent)
    choice_dialog.grab_set()
    
    # Center the dialog on parent window
    choice_dialog.update_idletasks()
    parent.update_idletasks()

    # Get parent window position and size
    parent_x = parent.winfo_x()
    parent_y = parent.winfo_y()
    parent_width = parent.winfo_width()
    parent_height = parent.winfo_height()

    # Calculate center position
    dialog_width = 500
    dialog_height = 280
    x = parent_x + (parent_width // 2) - (dialog_width // 2)
    y = parent_y + (parent_height // 2) - (dialog_height // 2)

    choice_dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
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
        bg=Theme.BG_DARK,
        fg=Theme.ACCENT_ORANGE
    ).pack(pady=(20, 10))
    
    # Message
    tk.Label(
        choice_dialog,
        text="Both original disc files and CHD files were found.\nWhich format do you want to use for M3U playlists?",
        font=("Arial", 11),
        bg=Theme.BG_DARK,
        fg=Theme.TEXT_LIGHT,
        justify="center"
    ).pack(pady=(0, 30))
    
    # Buttons frame
    btn_frame = tk.Frame(choice_dialog, bg=Theme.BG_DARK)
    btn_frame.pack(pady=10)
    
    tk.Button(
        btn_frame,
        text="💾 Use CHD Files\n(compressed)",
        command=select_chd,
        font=("Arial", 11, "bold"),
        bg=Theme.ACCENT_BLUE,
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
        bg=Theme.ACCENT_GREEN,
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
        bg=Theme.BG_FRAME,
        fg=Theme.TEXT_LIGHT,
        cursor="hand2",
        padx=15,
        pady=8,
        relief="flat"
    ).pack(pady=(10, 0))
    
    # Wait for dialog to close
    parent.wait_window(choice_dialog)
    
    return selected_format


def show_info_dialog(parent):
    """Show information dialog about when to use each option
    
    Args:
        parent: Parent tkinter window
    """
    from tkinter import scrolledtext
    
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
    
    info_window = tk.Toplevel(parent)
    info_window.title("Help - When to use each option")
    info_window.geometry("600x650")
    info_window.configure(bg=Theme.BG_DARK)
    
    text_widget = scrolledtext.ScrolledText(
        info_window,
        width=70,
        height=35,
        font=("Arial", 10),
        wrap=tk.WORD,
        padx=15,
        pady=15,
        bg=Theme.BG_FRAME,
        fg=Theme.TEXT_LIGHT
    )
    text_widget.pack(fill="both", expand=True, padx=10, pady=10)
    text_widget.insert(1.0, info_text)
    text_widget.config(state="disabled")
    
    close_btn = tk.Button(
        info_window,
        text="Close",
        command=info_window.destroy,
        font=("Arial", 10),
        bg=Theme.ACCENT_GREEN,
        fg="white",
        cursor="hand2",
        padx=20,
        relief="flat"
    )
    close_btn.pack(pady=10)
