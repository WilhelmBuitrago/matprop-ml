import os
import json
import tempfile
import shutil
from pathlib import Path
from typing import Optional
import logging
import sys
import os

# Add the parent directory to the path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import using absolute paths
from config_schema import ConfigSchema

logger = logging.getLogger(__name__)

class ConfigPersistence:
    """Handles persistence operations for configuration with atomic writes and backup management"""
    
    def __init__(self, config_dir: str = "./config_store"):
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "config.json"
        self.backup_dir = self.config_dir / "backups"
        self._ensure_directories_exist()
    
    def _ensure_directories_exist(self):
        """Ensure that the configuration directory and backup directory exist"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            logger.error(f"Permission denied when creating directories: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating directories: {e}")
            raise
    
    def _atomic_write(self, data: str, target_file: Path):
        """Perform atomic write operation using temp file -> fsync -> rename pattern"""
        try:
            # Create temporary file in the same directory as target
            temp_file = None
            
            try:
                # Create temp file
                temp_fd, temp_path = tempfile.mkstemp(
                    dir=target_file.parent, 
                    prefix=".tmp_", 
                    suffix=target_file.suffix
                )
                temp_file = Path(temp_path)
                
                # Write data to temp file
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(data)
                
                # Close the file to ensure data is written
                os.close(temp_fd)
                
                # Atomically rename temp file to target
                temp_file.replace(target_file)
                
            except Exception as e:
                # Clean up temp file if something went wrong
                if temp_file and temp_file.exists():
                    try:
                        temp_file.unlink()
                    except:
                        pass
                raise e
                
        except Exception as e:
            logger.error(f"Atomic write failed: {e}")
            raise
    
    def _create_backup(self):
        """Create a backup of the current configuration file"""
        if self.config_file.exists():
            try:
                # Create timestamp for backup
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = self.backup_dir / f"config_backup_{timestamp}.json"
                
                # Copy current config to backup location
                shutil.copy2(self.config_file, backup_file)
                logger.info(f"Backup created: {backup_file}")
                
                # Clean up old backups (keep only last 5)
                self._cleanup_old_backups()
                
            except Exception as e:
                logger.error(f"Backup creation failed: {e}")
                # Don't raise exception for backup failures, as the main operation should continue
    
    def _cleanup_old_backups(self):
        """Remove old backup files, keeping only the 5 most recent"""
        try:
            backup_files = list(self.backup_dir.glob("config_backup_*.json"))
            if len(backup_files) > 5:
                # Sort by modification time and remove oldest
                backup_files.sort(key=lambda x: x.stat().st_mtime)
                for old_backup in backup_files[:-5]:
                    old_backup.unlink()
        except Exception as e:
            logger.warning(f"Failed to cleanup old backups: {e}")
    
    def save_config(self, config: ConfigSchema):
        """Save configuration with atomic write and backup"""
        try:
            # Create backup of existing config
            if self.config_file.exists():
                self._create_backup()
            
            # Convert config to JSON
            config_dict = config.dict()
            config_json = json.dumps(config_dict, indent=2, ensure_ascii=False)
            
            # Perform atomic write
            self._atomic_write(config_json, self.config_file)
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            raise
    
    def load_config(self) -> Optional[ConfigSchema]:
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_dict = json.load(f)
                return ConfigSchema(**config_dict)
            return None
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return None
    
    def get_backups(self) -> list:
        """Get list of available backup files"""
        try:
            backup_files = list(self.backup_dir.glob("config_backup_*.json"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return [str(f) for f in backup_files]
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []
    
    def restore_backup(self, backup_file: str) -> bool:
        """Restore configuration from a backup file"""
        try:
            backup_path = Path(backup_file)
            if not backup_path.exists():
                logger.error(f"Backup file does not exist: {backup_file}")
                return False
            
            # Create backup of current config before restoring
            if self.config_file.exists():
                self._create_backup()
            
            # Copy backup to config file
            shutil.copy2(backup_path, self.config_file)
            return True
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False