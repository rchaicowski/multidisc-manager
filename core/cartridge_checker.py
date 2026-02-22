"""
RomMate - ROM companion tool
Copyright (C) 2026 Rodrigo

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
"""

"""Cartridge ROM validation and health checking"""

import os
import hashlib
import zlib
import xml.etree.ElementTree as ET
from pathlib import Path


class CartridgeChecker:
    """Check cartridge ROM integrity and validate against databases"""
    
    # System detection by file extension
    SYSTEM_EXTENSIONS = {
        # Cartridges (No-Intro)
        'nes': ['.nes', '.unf', '.unif'],
        'snes': ['.sfc', '.smc'],
        'n64': ['.n64', '.z64', '.v64'],
        'gb': ['.gb'],
        'gbc': ['.gbc'],
        'gba': ['.gba'],
        'nds': ['.nds'],
        '3ds': ['.3ds', '.cci', '.cia'],
        'genesis': ['.gen', '.md', '.smd'],
        'sms': ['.sms'],
        'gamegear': ['.gg'],
        'sega32x': ['.32x'],
        'a2600': ['.a26'],
        'a7800': ['.a78'],
        'pce': ['.pce'],
        'ngp': ['.ngp', '.ngc'],
        'ws': ['.ws', '.wsc'],
    
        # Disc-based (Redump)
        'ps1': ['.bin', '.img', '.iso'],
        'ps2': ['.iso'],
        'ps3': ['.iso'],
        'psp': ['.iso', '.cso'],
        'gamecube': ['.iso', '.gcm', '.gcz'],
        'wii': ['.iso', '.wbfs'],
        'xbox': ['.iso'],
        'xbox360': ['.iso'],
        'saturn': ['.bin', '.iso'],
        'dreamcast': ['.cdi', '.gdi'],
        'segacd': ['.bin', '.iso'],
        'neogeocd': ['.bin', '.iso'],
    }

    # Which systems use Redump vs No-Intro
    REDUMP_SYSTEMS = [
        'ps1', 'ps2', 'ps3', 'psp',
        'gamecube', 'wii',
        'xbox', 'xbox360',
        'saturn', 'dreamcast', 'segacd', 'neogeocd'
    ]
    
    # Systems that commonly have external headers
    HEADER_SYSTEMS = {
        'snes': 512,  # SMC header
        'nes': 16,    # iNES header (sometimes needed, sometimes not)
        'n64': 0,     # No common headers
        'gb': 0,
        'gbc': 0,
        'gba': 0,
    }
    
    def __init__(self):
        """Initialize cartridge checker"""
        self.databases = {}
        self.no_intro_dir = os.path.join(
            os.path.dirname(__file__), '..', 'databases', 'no-intro'
        )
        self.redump_dir = os.path.join(
            os.path.dirname(__file__), '..', 'databases', 'redump'
        )
    
    def detect_system(self, rom_file):
        """Detect system from file extension
        
        Args:
            rom_file (str): Path to ROM file
            
        Returns:
            str: System name or None
        """
        ext = os.path.splitext(rom_file)[1].lower()
        
        for system, extensions in self.SYSTEM_EXTENSIONS.items():
            if ext in extensions:
                return system
        
        return None
    
    def calculate_checksums(self, rom_file, skip_bytes=0):
        """Calculate CRC32, MD5, and SHA1 checksums
        
        Args:
            rom_file (str): Path to ROM file
            skip_bytes (int): Number of bytes to skip (for header removal)
            
        Returns:
            tuple: (crc32_hex, md5_hex, sha1_hex)
        """
        crc32 = 0
        md5 = hashlib.md5()
        sha1 = hashlib.sha1()
        
        try:
            with open(rom_file, 'rb') as f:
                # Skip header if needed
                if skip_bytes > 0:
                    f.seek(skip_bytes)
                
                # Read in chunks for large files
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    crc32 = zlib.crc32(chunk, crc32)
                    md5.update(chunk)
                    sha1.update(chunk)
            
            # Format as hex strings
            crc32_hex = format(crc32 & 0xFFFFFFFF, '08x').upper()
            md5_hex = md5.hexdigest().upper()
            sha1_hex = sha1.hexdigest().upper()
            
            return crc32_hex, md5_hex, sha1_hex
            
        except Exception as e:
            return None, None, None
    
    def load_database(self, system):
        """Load database for a system
        
        Args:
            system (str): System name
            
        Returns:
            dict: Database dictionary {crc32: game_info}
        """
        # Check if already loaded
        if system in self.databases:
            return self.databases[system]
        
        # Determine which database directory to use
        if system in self.REDUMP_SYSTEMS:
            db_file = os.path.join(self.redump_dir, f"{system}.dat")
        else:
            db_file = os.path.join(self.no_intro_dir, f"{system}.dat")
        
        if not os.path.exists(db_file):
            # Database not found - return empty
            return {}
        
        # Parse database
        database = {}
        try:
            tree = ET.parse(db_file)
            root = tree.getroot()
            
            for game in root.findall('game'):
                game_name = game.get('name', 'Unknown')
                
                for rom in game.findall('rom'):
                    crc = rom.get('crc', '').upper()
                    if crc:
                        database[crc] = {
                            'name': game_name,
                            'size': rom.get('size', '0'),
                            'md5': rom.get('md5', '').upper(),
                            'sha1': rom.get('sha1', '').upper(),
                        }
            
            # Cache the database
            self.databases[system] = database
            
        except Exception as e:
            print(f"Error loading database for {system}: {e}")
            return {}
        
        return database
    
    def has_external_header(self, rom_file, system):
        """Check if ROM likely has an external copier header
        
        Args:
            rom_file (str): Path to ROM file
            system (str): System name
            
        Returns:
            bool: True if likely has header
        """
        if system not in self.HEADER_SYSTEMS:
            return False
        
        header_size = self.HEADER_SYSTEMS[system]
        if header_size == 0:
            return False
        
        file_size = os.path.getsize(rom_file)
        
        if system == 'snes':
            # SNES ROMs should be multiples of 1024
            # If size % 1024 == 512, likely has SMC header
            return (file_size % 1024) == 512
        
        elif system == 'nes':
            # Check for iNES header signature
            try:
                with open(rom_file, 'rb') as f:
                    signature = f.read(4)
                    return signature == b'NES\x1a'
            except:
                return False
        
        return False
    
    def fuzzy_name_match(self, filename, database_name, threshold=0.8):
        """Check if filename fuzzy matches database name
        
        Args:
            filename (str): ROM filename
            database_name (str): Name from database
            threshold (float): Similarity threshold (0.0 to 1.0)
            
        Returns:
            float: Similarity score (0.0 to 1.0)
        """
        import difflib
        
        # Normalize both names
        file_clean = filename.lower()
        db_clean = database_name.lower()
        
        # Remove extensions
        file_clean = file_clean.rsplit('.', 1)[0]
        
        # Remove common patterns
        for pattern in ['(usa)', '(europe)', '(japan)', '(world)', 
                        '[!]', '[a]', '[b]', '(rev ', '(v1.']:
            file_clean = file_clean.replace(pattern, '')
            db_clean = db_clean.replace(pattern, '')
        
        # Calculate similarity
        similarity = difflib.SequenceMatcher(None, file_clean, db_clean).ratio()
        
        return similarity
    
    def detect_rom_hack(self, filename):
        """Detect if ROM is likely a hack or translation
        
        Args:
            filename (str): ROM filename
            
        Returns:
            tuple: (is_hack: bool, hack_type: str, confidence: str)
        """
        filename_lower = filename.lower()
        
        # Translation patterns
        translation_patterns = [
            '[t+', '[t-', '(t+', '(t-',
            'translation', 'translated'
        ]
        
        # Hack patterns
        hack_patterns = [
            '[hack]', '[h]', '(hack)', '(h)',
            'improved', 'enhanced', 'redux', 'remastered',
            'fixed', 'bugfix', 'difficulty',
            'hack by', 'rom hack'
        ]
        
        # Version/beta patterns (strong indicators)
        version_patterns = [
            'v1.', 'v2.', 'v3.', 'v4.', 'v5.',
            'beta', 'alpha', 'demo', 'proto',
            'preview', 'test'
        ]
        
        # Check for translations
        for pattern in translation_patterns:
            if pattern in filename_lower:
                return True, 'translation', '95%'
        
        # Check for explicit hack markers
        for pattern in hack_patterns:
            if pattern in filename_lower:
                return True, 'hack', '90%'
        
        # Check for version numbers (weaker signal)
        for pattern in version_patterns:
            if pattern in filename_lower:
                # Only if it's not an official release pattern
                if 'rev' not in filename_lower and 'prototype' not in filename_lower:
                    return True, 'modified', '80%'
        
        return False, None, None
    
    def remove_header(self, rom_file, header_size, create_backup=True):
        """Remove external header from ROM file
        
        Args:
            rom_file (str): Path to ROM file
            header_size (int): Size of header in bytes
            create_backup (bool): Create .backup file before modifying
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Create backup if requested
            if create_backup:
                import shutil
                backup_path = rom_file + '.backup'
                shutil.copy2(rom_file, backup_path)
            
            # Read file without header
            with open(rom_file, 'rb') as f:
                f.seek(header_size)  # Skip header
                clean_data = f.read()
            
            # Write back without header
            with open(rom_file, 'wb') as f:
                f.write(clean_data)
            
            return True, f"Header removed successfully ({header_size} bytes)"
            
        except Exception as e:
            return False, f"Error removing header: {str(e)}"
    
    def verify_rom(self, rom_file):
        """Verify a single ROM file with multi-level verification
        
        Args:
            rom_file (str): Path to ROM file
            
        Returns:
            dict: Verification result with status, message, details
        """
        filename = os.path.basename(rom_file)
        
        # Detect system
        system = self.detect_system(rom_file)
        if not system:
            return {
                'status': 'unknown',
                'message': 'Unknown file type',
                'filename': filename,
                'path': rom_file,  # Added
                'system': None
            }
        
        # Check if it's a ROM hack/translation FIRST
        is_hack, hack_type, hack_confidence = self.detect_rom_hack(filename)
        if is_hack:
            hack_label = {
                'translation': '🌍 Translation Patch',
                'hack': '🎨 ROM Hack',
                'modified': '📝 Modified ROM'
            }.get(hack_type, '🎨 Modified')
            
            return {
                'status': 'hack',
                'message': f'{hack_label} Detected',
                'filename': filename,
                'path': rom_file,  # Added
                'system': system,
                'hack_type': hack_type,
                'confidence': hack_confidence
            }
        
        # Load database
        database = self.load_database(system)
        if not database:
            return {
                'status': 'no_database',
                'message': f'No database available for {system.upper()}',
                'filename': filename,
                'path': rom_file,  # Added
                'system': system
            }
        
        # Get file size
        file_size = os.path.getsize(rom_file)
        
        # Calculate checksums
        crc32, md5, sha1 = self.calculate_checksums(rom_file)
        
        if not crc32:
            return {
                'status': 'error',
                'message': 'Could not read ROM file',
                'filename': filename,
                'path': rom_file,  # Added
                'system': system
            }
        
        # LEVEL 1: EXACT checksum match (100% certain)
        # Check all matches to find multiple regions
        all_matches = []
        for db_crc, entry in database.items():
            if crc32 == db_crc:
                expected_size = int(entry.get('size', '0'))
                if expected_size == file_size:
                    all_matches.append(entry['name'])
        
        if all_matches:
            if len(all_matches) > 1:
                return {
                    'status': 'verified',
                    'message': 'Verified Good Dump',
                    'filename': filename,
                    'path': rom_file,  # Added
                    'system': system,
                    'game_name': all_matches[0],  # Primary match
                    'all_regions': all_matches,
                    'crc32': crc32,
                    'confidence': '100%'
                }
            else:
                return {
                    'status': 'verified',
                    'message': 'Verified Good Dump',
                    'filename': filename,
                    'path': rom_file,  # Added
                    'system': system,
                    'game_name': all_matches[0],
                    'crc32': crc32,
                    'confidence': '100%'
                }
        
        # Check if has external header and try without it
        if self.has_external_header(rom_file, system):
            header_size = self.HEADER_SYSTEMS[system]
            crc32_clean, md5_clean, sha1_clean = self.calculate_checksums(rom_file, header_size)
            
            # Check all matches for headerless version
            all_matches_clean = []
            for db_crc, entry in database.items():
                if crc32_clean == db_crc:
                    all_matches_clean.append(entry['name'])
            
            if all_matches_clean:
                if len(all_matches_clean) > 1:
                    return {
                        'status': 'has_header',
                        'message': 'Has External Header (fixable)',
                        'filename': filename,
                        'path': rom_file,  # Added
                        'system': system,
                        'game_name': all_matches_clean[0],
                        'all_regions': all_matches_clean,
                        'crc32': crc32_clean,
                        'header_size': header_size,
                        'confidence': '100%'
                    }
                else:
                    return {
                        'status': 'has_header',
                        'message': 'Has External Header (fixable)',
                        'filename': filename,
                        'path': rom_file,  # Added
                        'system': system,
                        'game_name': all_matches_clean[0],
                        'crc32': crc32_clean,
                        'header_size': header_size,
                        'confidence': '100%'
                    }
        
        # LEVEL 2: Multiple checksums match (99% certain)
        for db_crc, entry in database.items():
            matches = 0
            if crc32 == db_crc:
                matches += 1
            if md5 and md5 == entry.get('md5', ''):
                matches += 1
            if sha1 and sha1 == entry.get('sha1', ''):
                matches += 1
            
            if matches >= 2:
                return {
                    'status': 'probable',
                    'message': f'Probable Good Dump ({matches}/3 checksums match)',
                    'filename': filename,
                    'path': rom_file,  # Added
                    'system': system,
                    'game_name': entry['name'],
                    'confidence': '99%'
                }
        
        # LEVEL 3: Filename + size match (95% certain)
        best_match = None
        best_similarity = 0
        
        for db_crc, entry in database.items():
            # Check file size
            expected_size = int(entry.get('size', '0'))
            size_diff = abs(file_size - expected_size)
            
            # Allow small size differences (headers)
            if size_diff <= 512:  # Within 512 bytes
                # Check filename similarity
                similarity = self.fuzzy_name_match(filename, entry['name'])
                
                if similarity > best_similarity and similarity >= 0.8:
                    best_similarity = similarity
                    best_match = entry
        
        if best_match:
            return {
                'status': 'likely',
                'message': f'Likely Match - Name & Size Match ({int(best_similarity * 100)}% similar)',
                'filename': filename,
                'path': rom_file,  # Added
                'system': system,
                'game_name': best_match['name'],
                'confidence': '95%'
            }
        
        # LEVEL 4: Filename only (80% certain)
        for db_crc, entry in database.items():
            similarity = self.fuzzy_name_match(filename, entry['name'])
            if similarity >= 0.7:
                return {
                    'status': 'name_match',
                    'message': f'Name Match - Checksum Differs ({int(similarity * 100)}% similar)',
                    'filename': filename,
                    'path': rom_file,  # Added
                    'system': system,
                    'game_name': entry['name'],
                    'confidence': '80%'
                }
        
        # LEVEL 5: Unknown
        return {
            'status': 'unknown',
            'message': 'Unknown ROM (not in database)',
            'filename': filename,
            'path': rom_file,  # Added
            'system': system,
            'crc32': crc32
        }
    
    def check_folder(self, folder, log_callback=None, progress_callback=None, cancel_check=None):
        """Check all cartridge ROMs in a folder
        
        Args:
            folder (str): Folder path to scan
            log_callback (function): Callback for logging messages
            progress_callback (function): Callback for progress updates
            cancel_check (function): Function that returns True if cancelled
            
        Returns:
            tuple: (verified, has_header, rom_hacks, unknown, failed, results)
        """
        verified = 0
        has_header = 0
        rom_hacks = 0
        unknown = 0
        failed = 0
        results = []
        
        # First, find all CUE files to exclude their BINs from cartridge checking
        cue_bin_files = set()
        for root, dirs, files in os.walk(folder):
            for file in files:
                if file.lower().endswith('.cue'):
                    cue_path = os.path.join(root, file)
                    cue_dir = os.path.dirname(cue_path)
                    try:
                        with open(cue_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for line in f:
                                if 'FILE' in line.upper():
                                    parts = line.split('"')
                                    if len(parts) >= 2:
                                        bin_file = parts[1]
                                        bin_path = os.path.join(cue_dir, bin_file)
                                        cue_bin_files.add(os.path.normpath(bin_path))
                    except:
                        pass
        
        # Find all cartridge ROM files, excluding CUE/BIN files
        rom_files = []
        for root, dirs, files in os.walk(folder):
            for file in files:
                full_path = os.path.join(root, file)
                
                # Skip if it's part of a CUE/BIN set
                if os.path.normpath(full_path) in cue_bin_files:
                    continue
                
                ext = os.path.splitext(file)[1].lower()
                # Check if extension is in any system
                for system, extensions in self.SYSTEM_EXTENSIONS.items():
                    if ext in extensions:
                        rom_files.append(full_path)
                        break
        
        if not rom_files:
            if log_callback:
                log_callback("❌ No cartridge ROM files found in folder")
            return 0, 0, 0, 0, 0, []
        
        if log_callback:
            log_callback(f"\n🎮 Found {len(rom_files)} cartridge ROM(s) to verify\n")
        
        # Verify each ROM
        for index, rom_file in enumerate(rom_files, 1):
            # Check for cancellation
            if cancel_check and cancel_check():
                if log_callback:
                    log_callback("\n⚠️ Health check cancelled by user")
                break
            
            filename = os.path.basename(rom_file)
            
            if progress_callback:
                progress_callback(index, len(rom_files), filename)
            
            if log_callback:
                log_callback(f"🔎 Verifying: {filename}")
            
            # Verify the ROM
            result = self.verify_rom(rom_file)
            results.append(result)
            
            # Log result
            if result['status'] == 'verified':
                verified += 1
                if log_callback:
                    log_callback(f"   ✅ {result['message']}")
                    if result.get('all_regions'):
                        log_callback(f"      Matches: {', '.join(result['all_regions'])}")
                    else:
                        log_callback(f"      Game: {result['game_name']}")
                    log_callback(f"      Confidence: {result['confidence']}")
                    
            elif result['status'] == 'has_header':
                has_header += 1
                if log_callback:
                    log_callback(f"   ⚠️ {result['message']}")
                    if result.get('all_regions'):
                        log_callback(f"      Matches: {', '.join(result['all_regions'])}")
                    else:
                        log_callback(f"      Game: {result['game_name']}")
                    log_callback(f"      Header Size: {result['header_size']} bytes")
                    
            elif result['status'] == 'probable':
                verified += 1  # Count as verified
                if log_callback:
                    log_callback(f"   ✅ {result['message']}")
                    log_callback(f"      Game: {result['game_name']}")
                    log_callback(f"      Confidence: {result['confidence']}")
                    
            elif result['status'] == 'likely':
                verified += 1  # Count as verified
                if log_callback:
                    log_callback(f"   📝 {result['message']}")
                    log_callback(f"      Game: {result['game_name']}")
                    log_callback(f"      Confidence: {result['confidence']}")
                    
            elif result['status'] == 'hack':
                rom_hacks += 1
                if log_callback:
                    log_callback(f"   🎨 {result['message']}")
                    log_callback(f"      Type: {result['hack_type'].title()}")
                    log_callback(f"      Confidence: {result['confidence']}")
                    
            elif result['status'] == 'name_match':
                unknown += 1
                if log_callback:
                    log_callback(f"   🔍 {result['message']}")
                    log_callback(f"      Possible: {result['game_name']}")
                    log_callback(f"      Confidence: {result['confidence']}")
                    
            elif result['status'] == 'unknown':
                unknown += 1
                if log_callback:
                    log_callback(f"   ❓ {result['message']}")
                    
            elif result['status'] == 'no_database':
                unknown += 1
                if log_callback:
                    log_callback(f"   ⚠️ {result['message']}")
                    
            else:
                failed += 1
                if log_callback:
                    log_callback(f"   ❌ {result['message']}")
        
        return verified, has_header, rom_hacks, unknown, failed, results
