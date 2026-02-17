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
        self.volume = 1.0
        
        # Initialize Windows volume control
        self.windows_volume = None
        if platform.system() == 'Windows':
            try:
                from pycaw.pycaw import AudioUtilities
                
                # Get the default audio output device (new API)
                devices = AudioUtilities.GetSpeakers()
                
                # Access EndpointVolume directly (new pycaw API)
                self.windows_volume = devices.EndpointVolume
                
                print("Windows volume control initialized successfully")
            except Exception as e:
                print(f"Windows volume control not available: {e}")
        
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
    
    def play(self, sound_type, volume=None):
        """Play a sound if enabled and available
        
        Args:
            sound_type (str): "success" or "fail"
            volume (float, optional): Volume level 0.0 to 1.0. Uses self.volume if not provided.
        """
        if not self.sounds_enabled or not self.sounds_available:
            return
        
        # Use provided volume or default to self.volume
        if volume is None:
            volume = self.volume
        
        sound_path = self.success_sound_path if sound_type == "success" else self.fail_sound_path
        
        if not os.path.exists(sound_path):
            return
        
        try:
            if platform.system() == 'Windows':
                import winsound
                
                # Set system volume if we have control
                if self.windows_volume:
                    try:
                        # Set volume (0.0 to 1.0 scale)
                        self.windows_volume.SetMasterVolumeLevelScalar(volume, None)
                    except Exception as e:
                        print(f"Could not set volume: {e}")
                
                # Play sound asynchronously
                winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
                
            elif platform.system() == 'Darwin':  # macOS
                # afplay doesn't have easy volume control
                subprocess.Popen(['afplay', sound_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:  # Linux
                # Try multiple Linux audio players
                for player in ['paplay', 'aplay', 'ffplay']:
                    if shutil.which(player):
                        if player == 'paplay':
                            # paplay supports volume! (0-65536, where 65536 = 100%)
                            volume_int = int(volume * 65536)
                            subprocess.Popen([player, '--volume', str(volume_int), sound_path], 
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        elif player == 'ffplay':
                            # ffplay supports volume with -volume (0-100)
                            volume_percent = int(volume * 100)
                            subprocess.Popen([player, '-nodisp', '-autoexit', '-volume', str(volume_percent), sound_path], 
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        else:
                            # aplay doesn't support volume directly
                            subprocess.Popen([player, sound_path], 
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        break
        except Exception as e:
            print(f"Could not play sound: {e}")
