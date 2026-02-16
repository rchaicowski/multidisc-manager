"""Settings panel for RomMate"""

import tkinter as tk
from tkinter import filedialog
from gui.theme import Theme


class SettingsPanel:
    """Settings panel with all user preferences"""
    
    def __init__(self, parent, config, callbacks):
        """Initialize settings panel
        
        Args:
            parent: Parent tkinter window
            config: Config object for saving/loading settings
            callbacks: Dictionary of callback functions
        """
        self.parent = parent
        self.config = config
        self.callbacks = callbacks
        
        # Theme colors
        self.bg_dark = Theme.BG_DARK
        self.bg_frame = Theme.BG_FRAME
        self.text_light = Theme.TEXT_LIGHT
        self.text_gray = Theme.TEXT_GRAY
        self.accent_blue = Theme.ACCENT_BLUE
        self.accent_red = Theme.ACCENT_RED
        
        # Create the panel
        self.create_panel()
    
    def create_panel(self):
        """Create the settings panel UI"""
        self.panel = tk.Frame(self.parent, bg=self.bg_dark)
        
        # Header with title and close button
        header_frame = tk.Frame(self.panel, bg=self.bg_dark)
        header_frame.pack(fill="x", padx=30, pady=20)
        
        # Center the title
        title_label = tk.Label(
            header_frame,
            text="⚙️ Settings",
            font=("Arial", 24, "bold"),
            bg=self.bg_dark,
            fg=self.text_light
        )
        title_label.pack(expand=True)
        
        # Close button (positioned absolutely in top right)
        close_btn = tk.Button(
            header_frame,
            text="✖",
            command=self.hide,
            font=("Arial", 16, "bold"),
            bg=self.bg_dark,
            fg=self.text_light,
            cursor="hand2",
            relief="flat",
            activebackground=self.accent_red,
            bd=0,
            padx=10
        )
        close_btn.place(relx=1.0, x=-10, rely=0.5, anchor="e")
        
        # Content area
        content_frame = tk.Frame(self.panel, bg=self.bg_dark)
        content_frame.pack(fill="both", expand=True, padx=50, pady=20)
        
        # Create settings sections
        self.create_sound_settings(content_frame)
        self.create_folder_settings(content_frame)
        self.create_conversion_settings(content_frame)
        self.create_language_settings(content_frame)
        self.create_about_section(content_frame)
    
    def create_sound_settings(self, parent):
        """Create sound settings section"""
        # Section frame
        section = tk.Frame(parent, bg=self.bg_frame, relief="solid", bd=1)
        section.pack(fill="x", pady=(0, 20))
        
        # Header
        tk.Label(
            section,
            text="🔊 Sound",
            font=("Arial", 14, "bold"),
            bg=self.bg_frame,
            fg=self.text_light
        ).pack(anchor="w", padx=20, pady=(15, 10))
        
        # Content
        content = tk.Frame(section, bg=self.bg_frame)
        content.pack(fill="x", padx=20, pady=(0, 15))
        
        # Enable sounds checkbox
        sounds_enabled = self.callbacks.get('get_sounds_enabled')()
        self.sound_var = tk.BooleanVar(value=sounds_enabled)
        
        tk.Checkbutton(
            content,
            text="Enable sounds",
            variable=self.sound_var,
            font=("Arial", 11),
            bg=self.bg_frame,
            fg=self.text_light,
            selectcolor=self.bg_dark,
            activebackground=self.bg_frame,
            command=lambda: self.callbacks.get('on_sound_toggle')(self.sound_var.get())
        ).pack(anchor="w", pady=5)
        
        # Volume slider
        volume_frame = tk.Frame(content, bg=self.bg_frame)
        volume_frame.pack(fill="x", pady=10)
        
        tk.Label(
            volume_frame,
            text="Volume:",
            font=("Arial", 11),
            bg=self.bg_frame,
            fg=self.text_light
        ).pack(side="left", padx=(0, 10))
        
        self.volume_var = tk.DoubleVar(value=self.config.get('sound_volume', 1.0) * 100)
        
        volume_slider = tk.Scale(
            volume_frame,
            from_=0,
            to=100,
            orient="horizontal",
            variable=self.volume_var,
            command=self.on_volume_change,
            bg=self.bg_frame,
            fg=self.text_light,
            highlightthickness=0,
            troughcolor=self.bg_dark,
            activebackground=self.accent_blue,
            length=250,
            showvalue=0
        )
        volume_slider.pack(side="left", fill="x", expand=True, padx=5)
        
        self.volume_label = tk.Label(
            volume_frame,
            text=f"{int(self.volume_var.get())}%",
            font=("Arial", 11),
            bg=self.bg_frame,
            fg=self.text_light,
            width=5
        )
        self.volume_label.pack(side="left")
    
    def create_folder_settings(self, parent):
        """Create folder settings section"""
        section = tk.Frame(parent, bg=self.bg_frame, relief="solid", bd=1)
        section.pack(fill="x", pady=(0, 20))
        
        # Header
        tk.Label(
            section,
            text="📁 Folders",
            font=("Arial", 14, "bold"),
            bg=self.bg_frame,
            fg=self.text_light
        ).pack(anchor="w", padx=20, pady=(15, 10))
        
        # Content
        content = tk.Frame(section, bg=self.bg_frame)
        content.pack(fill="x", padx=20, pady=(0, 15))
        
        # Default ROM folder
        folder_frame = tk.Frame(content, bg=self.bg_frame)
        folder_frame.pack(fill="x", pady=5)
        
        tk.Label(
            folder_frame,
            text="Default ROM folder:",
            font=("Arial", 11),
            bg=self.bg_frame,
            fg=self.text_light
        ).pack(anchor="w", pady=(0, 5))
        
        entry_frame = tk.Frame(folder_frame, bg=self.bg_frame)
        entry_frame.pack(fill="x")
        
        self.default_folder_var = tk.StringVar(
            value=self.config.get('default_rom_folder', 'Not set')
        )
        
        tk.Entry(
            entry_frame,
            textvariable=self.default_folder_var,
            font=("Arial", 10),
            bg=self.bg_dark,
            fg=self.text_light,
            insertbackground=self.text_light,
            state='readonly',
            relief="solid",
            bd=1
        ).pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        tk.Button(
            entry_frame,
            text="Browse",
            command=self.set_default_folder,
            font=("Arial", 10),
            bg=self.accent_blue,
            fg="white",
            cursor="hand2",
            relief="flat",
            padx=20,
            pady=5
        ).pack(side="left")
    
    def create_conversion_settings(self, parent):
        """Create conversion settings section"""
        section = tk.Frame(parent, bg=self.bg_frame, relief="solid", bd=1)
        section.pack(fill="x", pady=(0, 20))
        
        # Header
        tk.Label(
            section,
            text="🗑️ Conversion",
            font=("Arial", 14, "bold"),
            bg=self.bg_frame,
            fg=self.text_light
        ).pack(anchor="w", padx=20, pady=(15, 10))
        
        # Content
        content = tk.Frame(section, bg=self.bg_frame)
        content.pack(fill="x", padx=20, pady=(0, 15))
        
        delete_enabled = self.callbacks.get('get_delete_after_conversion')()
        self.delete_var = tk.BooleanVar(value=delete_enabled)
        
        tk.Checkbutton(
            content,
            text="Delete original files after successful CHD conversion",
            variable=self.delete_var,
            font=("Arial", 11),
            bg=self.bg_frame,
            fg=self.text_light,
            selectcolor=self.bg_dark,
            activebackground=self.bg_frame,
            command=lambda: self.callbacks.get('on_delete_toggle')(self.delete_var.get())
        ).pack(anchor="w", pady=5)
        
        tk.Label(
            content,
            text="(CHD files are compressed and save 40-60% space)",
            font=("Arial", 9),
            bg=self.bg_frame,
            fg=self.text_gray
        ).pack(anchor="w", padx=(25, 0))
    
    def create_language_settings(self, parent):
        """Create language settings section"""
        section = tk.Frame(parent, bg=self.bg_frame, relief="solid", bd=1)
        section.pack(fill="x", pady=(0, 20))
        
        # Header
        tk.Label(
            section,
            text="🌍 Language",
            font=("Arial", 14, "bold"),
            bg=self.bg_frame,
            fg=self.text_light
        ).pack(anchor="w", padx=20, pady=(15, 10))
        
        # Content
        content = tk.Frame(section, bg=self.bg_frame)
        content.pack(fill="x", padx=20, pady=(0, 15))
        
        tk.Label(
            content,
            text="Language: English (More languages coming soon)",
            font=("Arial", 11),
            bg=self.bg_frame,
            fg=self.text_gray
        ).pack(anchor="w", pady=5)
    
    def create_about_section(self, parent):
        """Create about section"""
        section = tk.Frame(parent, bg=self.bg_frame, relief="solid", bd=1)
        section.pack(fill="x", pady=(0, 20))
        
        # Header
        tk.Label(
            section,
            text="ℹ️ About",
            font=("Arial", 14, "bold"),
            bg=self.bg_frame,
            fg=self.text_light
        ).pack(anchor="w", padx=20, pady=(15, 10))
        
        # Content
        content = tk.Frame(section, bg=self.bg_frame)
        content.pack(fill="x", padx=20, pady=(0, 15))
        
        tk.Label(
            content,
            text="RomMate v1.0.0",
            font=("Arial", 12, "bold"),
            bg=self.bg_frame,
            fg=self.text_light
        ).pack(anchor="w", pady=(0, 5))
        
        tk.Label(
            content,
            text="Your ROM companion - Convert, compress, and organize disc images",
            font=("Arial", 10),
            bg=self.bg_frame,
            fg=self.text_gray,
            wraplength=500,
            justify="left"
        ).pack(anchor="w", pady=(0, 10))
        
        tk.Button(
            content,
            text="📖 View Documentation",
            command=self.callbacks.get('show_help'),
            font=("Arial", 10),
            bg=self.accent_blue,
            fg="white",
            cursor="hand2",
            relief="flat",
            padx=20,
            pady=8
        ).pack(anchor="w")
    
    def on_volume_change(self, value):
        """Handle volume slider change"""
        volume = float(value) / 100
        self.config.set('sound_volume', volume)
        self.volume_label.config(text=f"{int(float(value))}%")
        
        if 'on_volume_change' in self.callbacks:
            self.callbacks['on_volume_change'](volume)
    
    def set_default_folder(self):
        """Set default ROM folder"""
        folder = filedialog.askdirectory(title="Select Default ROM Folder")
        if folder:
            self.default_folder_var.set(folder)
            self.config.set('default_rom_folder', folder)
    
    def show(self):
        """Show the settings panel"""
        self.panel.pack(fill="both", expand=True)
    
    def hide(self):
        """Hide the settings panel"""
        self.panel.pack_forget()
        # Call the callback to show main panel
        if 'on_close' in self.callbacks:
            self.callbacks['on_close']()
