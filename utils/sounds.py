"""Sound playback utilities for RomMate"""

import os
import subprocess
import platform
import shutil


class SoundPlayer:
    """Handles sound playback across different platforms"""
    
    def __init__(self):
        """Initialize sound player and check for sound files"""
        self.sounds_enabled = True
        
        # Sound files are in the sounds/ directory at project root
        sounds_dir = os.path.join(os.path.dirname(__file__), '..', 'sounds')
        self.success_sound_path = os.path.join(sounds_dir, 'success.wav')
        self.fail_sound_path = os.path.join(sounds_dir, 'fail.wav')
        
        # Check if sounds are actually available
        self.sounds_available = (
            os.path.exists(self.success_sound_path) and 
            os.path.exists(self.fail_sound_path)
        )
        
        if not self.sounds_available:
            print(f"Warning: Sound files not found in {sounds_dir}")
    
    def play(self, sound_type):
        """Play a sound if enabled and available
        
        Args:
            sound_type (str): "success" or "fail"
        """
        if not self.sounds_enabled or not self.sounds_available:
            return
        
        sound_path = self.success_sound_path if sound_type == "success" else self.fail_sound_path
        
        if not os.path.exists(sound_path):
            return
        
        try:
            if platform.system() == 'Windows':
                import winsound
                # Play sound asynchronously without blocking
                winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
            elif platform.system() == 'Darwin':  # macOS
                # Use afplay on macOS
                subprocess.Popen(['afplay', sound_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:  # Linux
                # Try multiple Linux audio players
                for player in ['aplay', 'paplay', 'ffplay']:
                    if shutil.which(player):
                        if player == 'ffplay':
                            subprocess.Popen([player, '-nodisp', '-autoexit', sound_path], 
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        else:
                            subprocess.Popen([player, sound_path], 
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        break
        except Exception as e:
            print(f"Could not play sound: {e}")
