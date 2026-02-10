"""M3U playlist creation functionality for RomMate"""

from core.file_utils import detect_available_formats, find_multidisc_games, create_m3u_file


class M3UCreator:
    """Handles creation of M3U playlist files for multi-disc games"""
    
    def __init__(self):
        """Initialize M3U creator"""
        pass
    
    def create_playlists(self, folder, extensions=None, log_callback=None, progress_callback=None):
        """Create M3U playlists for all multi-disc games in a folder
        
        Args:
            folder (str): Folder containing disc images
            extensions (list, optional): List of file patterns to scan (e.g., ["*.chd"])
                                        If None, scans all formats
            log_callback (callable): Function to call with log messages
            progress_callback (callable): Function to call with progress updates
                                        Should accept (current, total, filename) args
        
        Returns:
            tuple: (created, skipped) - counts of playlists created/skipped
        """
        # Find multi-disc games
        multidisc_games = find_multidisc_games(folder, extensions, log_callback)
        
        if not multidisc_games:
            return 0, 0
        
        if log_callback:
            log_callback(f"🎮 Found {len(multidisc_games)} multi-disc game(s)\n")
        
        total_games = len(multidisc_games)
        created_count = 0
        skipped_count = 0
        
        for index, (game_name, disc_files) in enumerate(multidisc_games.items(), 1):
            if progress_callback:
                progress_callback(index, total_games, f"{game_name}.m3u")
            
            was_created = create_m3u_file(game_name, disc_files, folder, log_callback)
            
            if was_created:
                created_count += 1
            else:
                skipped_count += 1
        
        return created_count, skipped_count
    
    def auto_detect_and_create(self, folder, log_callback=None, 
                               progress_callback=None, format_choice_callback=None):
        """Auto-detect available formats and create M3U playlists
        
        If both original and CHD files exist, calls format_choice_callback to ask user.
        
        Args:
            folder (str): Folder containing disc images
            log_callback (callable): Function to call with log messages
            progress_callback (callable): Function to call with progress updates
            format_choice_callback (callable): Function to call when both formats exist
                                             Should return "chd", "original", or None (cancel)
        
        Returns:
            tuple: (created, skipped, cancelled) - counts of outcomes
        """
        # Detect what formats are available
        has_original, has_chd = detect_available_formats(folder)
        
        # Determine which extensions to use
        extensions = None
        
        if has_original and has_chd:
            # Both formats exist - ask user which to use
            if log_callback:
                log_callback("⚠️ Found both original files (CUE/GDI/CDI/ISO) and CHD files")
            
            if format_choice_callback:
                choice = format_choice_callback()
                
                if choice is None:  # User cancelled
                    if log_callback:
                        log_callback("❌ Operation cancelled by user")
                    return 0, 0, True
                elif choice == "chd":
                    extensions = ["*.chd"]
                    if log_callback:
                        log_callback("✓ User selected: CHD files")
                else:  # original
                    extensions = ["*.cue", "*.gdi", "*.cdi", "*.iso"]
                    if log_callback:
                        log_callback("✓ User selected: Original disc files")
            else:
                # No callback - default to CHD
                extensions = ["*.chd"]
        
        elif has_chd:
            # Only CHD files
            extensions = ["*.chd"]
            if log_callback:
                log_callback("✓ Auto-detected: CHD files only")
        
        elif has_original:
            # Only original files
            extensions = ["*.cue", "*.gdi", "*.cdi", "*.iso"]
            if log_callback:
                log_callback("✓ Auto-detected: Original disc files only")
        
        else:
            # No disc files found
            if log_callback:
                log_callback("❌ No disc files found")
            return 0, 0, False
        
        # Create playlists
        created, skipped = self.create_playlists(
            folder, 
            extensions=extensions,
            log_callback=log_callback,
            progress_callback=progress_callback
        )
        
        return created, skipped, False
