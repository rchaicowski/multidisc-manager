"""CHD conversion functionality for RomMate"""

import os
import subprocess
import platform
import shutil
import time
from pathlib import Path
from tkinter import messagebox


class CHDConverter:
    """Handles conversion of disc images to CHD format"""
    
    def __init__(self):
        """Initialize CHD converter"""
        self.chdman_path = None
    
    def find_chdman(self):
        """Try to find chdman executable
        
        Returns:
            str: Path to chdman or None if not found
        """
        # Check if bundled with app
        bundled_path = os.path.join(os.path.dirname(__file__), '..', 'tools', 
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
        """Get the correct package manager command for this Linux distro
        
        Returns:
            str: Installation command or None if not Linux
        """
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
        """Prompt user to install chdman automatically (Linux only)
        
        Returns:
            bool: True if installation was attempted, False otherwise
        """
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
    
    def convert_file(self, source_file, delete_after=False, 
                    log_callback=None, animation_callback=None):
        """Convert a single file to CHD
        
        Args:
            source_file (Path): Source file to convert
            delete_after (bool): Delete original after successful conversion
            log_callback (callable): Function to call with log messages
            animation_callback (callable): Function to call for animation updates
                                         Should accept (position, text) args
        
        Returns:
            tuple: (success, chd_path) - success is bool, chd_path is str or None
        """
        source_path = str(source_file)
        source_ext = source_file.suffix.lower()
        chd_path = str(source_file.with_suffix('.chd'))
        
        # Skip if CHD already exists
        if os.path.exists(chd_path):
            return True, chd_path
        
        try:
            cmd = [self.chdman_path, 'createcd', '-i', source_path, '-o', chd_path]
            
            # Start conversion process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Animate dots while waiting (if callback provided)
            if animation_callback:
                dots = 0
                while process.poll() is None:
                    dots = (dots + 1) % 4
                    dot_str = "." * dots
                    animation_callback(f"   Processing{dot_str}")
                    time.sleep(0.3)
            else:
                # Just wait without animation
                process.wait()
            
            # Get final result
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                # Success - delete originals if requested
                if delete_after:
                    try:
                        os.remove(source_path)
                        if source_ext == '.cue':
                            bin_file = source_path.rsplit('.', 1)[0] + '.bin'
                            if os.path.exists(bin_file):
                                os.remove(bin_file)
                        if log_callback:
                            log_callback(f"   🗑️  Deleted original files")
                    except Exception as e:
                        if log_callback:
                            log_callback(f"   ⚠️  Could not delete originals: {e}")
                
                return True, chd_path
            else:
                if log_callback:
                    log_callback(f"   ❌ Failed: {stderr[:100]}")
                return False, None
        
        except Exception as e:
            if log_callback:
                log_callback(f"   ❌ Error: {str(e)}")
            return False, None
    
    def convert_folder(self, folder, delete_after=False, 
                      log_callback=None, progress_callback=None, animation_callback=None, cancel_check=None):
        """Convert all disc images in a folder to CHD
        
        Args:
            folder (str): Folder containing disc images
            delete_after (bool): Delete originals after successful conversion
            log_callback (callable): Function to call with log messages
            progress_callback (callable): Function to call with progress updates
                                        Should accept (current, total, filename) args
            cancel_check (callable): Function to call to check if cancellation was requested
        
        Returns:
            tuple: (converted, skipped, failed) - counts of each outcome
        """
        # Make sure chdman_path is set
        if not self.chdman_path:
            self.chdman_path = self.find_chdman()
            if not self.chdman_path:
                return 0, 0, 0
        
        # Find all convertible files
        source_files = []
        for pattern in ["*.cue", "*.gdi", "*.cdi", "*.iso"]:
            found = list(Path(folder).glob(pattern))
            if found:
                if log_callback:
                    log_callback(f"Found {len(found)} {pattern} file(s)")
                source_files.extend(found)
        
        if not source_files:
            return 0, 0, 0
        
        total_files = len(source_files)
        if log_callback:
            log_callback(f"\nTotal files to convert: {total_files}\n")
        
        converted = 0
        skipped = 0
        failed = 0
        
        for index, source_file in enumerate(source_files, 1):
            # Check if cancellation was requested
            if cancel_check and cancel_check():
                if log_callback:
                    log_callback("❌ Conversion cancelled by user")
                return converted, skipped, failed
            
            if progress_callback:
                progress_callback(index, total_files, source_file.name)
            
            # Check if already exists
            chd_path = str(source_file.with_suffix('.chd'))
            if os.path.exists(chd_path):
                if log_callback:
                    log_callback(f"⏭️  Skipped: {source_file.name} (CHD already exists)")
                skipped += 1
                continue
            
            if log_callback:
                log_callback(f"🔄 Converting: {source_file.name}")
            
            success, chd_path = self.convert_file(
                source_file, 
                delete_after=delete_after,
                log_callback=log_callback,
                animation_callback=animation_callback
            )
            
            # If conversion was cancelled mid-file, delete the partial CHD
            if cancel_check and cancel_check():
                if chd_path and os.path.exists(chd_path):
                    try:
                        os.remove(chd_path)
                        if log_callback:
                            log_callback(f"   🗑️ Deleted incomplete: {os.path.basename(chd_path)}")
                    except:
                        pass
                if log_callback:
                    log_callback("❌ Conversion cancelled by user")
                return converted, skipped, failed
            
            if success:
                if log_callback:
                    log_callback(f"   ✓ Converted to CHD")
                converted += 1
            else:
                # Error already logged in convert_file
                failed += 1
        
        return converted, skipped, failed
