"""File utilities for RomMate - game detection, path handling, and validation"""

import os
import re
from pathlib import Path


def normalize_path(path):
    """Normalize a file path by stripping whitespace and handling trailing spaces
    
    Args:
        path (str): The path to normalize
        
    Returns:
        str: Normalized path that actually exists, or original path if not found
    """
    # Strip any leading/trailing whitespace
    path = path.strip()
    
    # Additional check: if folder doesn't exist, try with trailing space
    # (Linux file dialog sometimes strips trailing spaces from folder names)
    if not os.path.exists(path):
        path_with_space = path + " "
        if os.path.exists(path_with_space):
            return path_with_space
    
    return path


def detect_available_formats(folder):
    """Detect which disc formats are available in the folder
    
    Args:
        folder (str): Path to folder to scan
        
    Returns:
        tuple: (has_original_formats, has_chd) - booleans indicating presence
    """
    has_cue = len(list(Path(folder).glob("*.cue"))) > 0
    has_gdi = len(list(Path(folder).glob("*.gdi"))) > 0
    has_cdi = len(list(Path(folder).glob("*.cdi"))) > 0
    has_iso = len(list(Path(folder).glob("*.iso"))) > 0
    has_chd = len(list(Path(folder).glob("*.chd"))) > 0
    
    has_original_formats = has_cue or has_gdi or has_cdi or has_iso
    
    return has_original_formats, has_chd


def extract_game_info(filename):
    """Extract game name and disc number from filename
    
    Supports various naming patterns like:
    - Game Name (Disc 1).cue
    - Game Name [Disc 2].chd
    - Game Name CD1.bin
    - Game Name (Side A).cue
    
    Args:
        filename (str): The filename to parse
        
    Returns:
        tuple: (game_name, disc_num) or (None, None) if not a multi-disc file
    """
    name_without_ext = os.path.splitext(filename)[0]
    
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
            
            # Convert letter to number (A=1, B=2, etc.) for letter patterns
            if i >= 6:  # Letter-based patterns
                disc_num = ord(disc_identifier.upper()) - ord('A') + 1
            else:
                disc_num = int(disc_identifier)
            
            return game_name, disc_num
    
    return None, None


def find_multidisc_games(folder, extensions=None, log_callback=None):
    """Scan folder for multi-disc games and group them
    
    Args:
        folder (str): Path to folder to scan
        extensions (list, optional): List of file patterns to scan (e.g., ["*.chd"])
        log_callback (callable, optional): Function to call with log messages
        
    Returns:
        dict: Dictionary mapping game names to list of (disc_num, filename) tuples
    """
    if extensions is None:
        extensions = ["*.cue", "*.gdi", "*.cdi", "*.iso", "*.chd"]
    
    games = {}
    
    if log_callback:
        log_callback(f"Scanning for: {', '.join(extensions)}")
    
    all_files = []
    for ext_pattern in extensions:
        files = list(Path(folder).glob(ext_pattern))
        if files:
            if log_callback:
                log_callback(f"Found {len(files)} {ext_pattern} file(s)")
            all_files.extend(files)
    
    for file in all_files:
        filename = file.name
        game_name, disc_num = extract_game_info(filename)
        
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
                if log_callback:
                    log_callback(f"⚠️  Skipping '{name}' - mixed formats")
    
    # Sort by disc number
    for game_name in multidisc_games:
        multidisc_games[game_name].sort(key=lambda x: x[0])
    
    return multidisc_games


def create_m3u_file(game_name, disc_files, folder, log_callback=None):
    """Create an .m3u file for a multi-disc game
    
    Args:
        game_name (str): Name of the game
        disc_files (list): List of (disc_num, filename) tuples
        folder (str): Folder to create the M3U file in
        log_callback (callable, optional): Function to call with log messages
        
    Returns:
        bool: True if M3U was created, False if it already existed
    """
    m3u_filename = os.path.join(folder, f"{game_name}.m3u")
    
    if os.path.exists(m3u_filename):
        if log_callback:
            log_callback(f"  ⚠️ Already exists: {game_name}.m3u")
        return False
    
    with open(m3u_filename, 'w', encoding='utf-8') as f:
        for disc_num, disc_file in disc_files:
            f.write(f"{disc_file}\n")
    
    if log_callback:
        log_callback(f"  ✓ Created: {game_name}.m3u ({len(disc_files)} discs)")
        for disc_num, disc_file in disc_files:
            log_callback(f"      • Disc {disc_num}: {disc_file}")
    
    return True
