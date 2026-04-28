import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from threading import Lock


@dataclass
class AuditEntry:
    """Represents a single audit log entry"""
    timestamp: str
    user: str
    action: str
    resource: str
    changes: Dict[str, Any]
    validation_result: Dict[str, Any]
    id: str = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = datetime.now().strftime("%Y%m%d%H%M%S%f")


class AuditLogger:
    """Audit logger for configuration changes"""
    
    def __init__(self, log_file: str = "./config_store/config_audit.log"):
        self.log_file = Path(log_file)
        self.lock = Lock()
        self._ensure_log_file_exists()
    
    def _ensure_log_file_exists(self):
        """Ensure the log file exists"""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_file.exists():
            self.log_file.write_text("[]")
    
    def log_change(self, user: str, changes: Dict[str, Any], validation_result: Dict[str, Any]):
        """Log a configuration change"""
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            user=user or "system",
            action="CONFIG_UPDATE",
            resource="config",
            changes=changes,
            validation_result=validation_result
        )
        
        with self.lock:
            # Read existing entries
            if self.log_file.exists():
                try:
                    with open(self.log_file, 'r') as f:
                        entries = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    entries = []
            else:
                entries = []
            
            # Append new entry
            entries.append(asdict(entry))
            
            # Write back to file
            with open(self.log_file, 'w') as f:
                json.dump(entries, f, indent=2)
    
    def get_history(self, limit: int = 50, offset: int = 0, 
                    start_date: Optional[str] = None, 
                    end_date: Optional[str] = None,
                    config_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get audit history with optional filtering"""
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    entries = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                entries = []
        else:
            entries = []
        
        # Apply filters
        filtered_entries = entries
        
        # Filter by date range
        if start_date:
            filtered_entries = [
                entry for entry in filtered_entries 
                if entry['timestamp'] >= start_date
            ]
        
        if end_date:
            filtered_entries = [
                entry for entry in filtered_entries 
                if entry['timestamp'] <= end_date
            ]
        
        # Filter by config key
        if config_key:
            filtered_entries = [
                entry for entry in filtered_entries 
                if config_key in json.dumps(entry.get('changes', {}))
            ]
        
        # Apply pagination
        filtered_entries = filtered_entries[offset:offset + limit]
        
        return filtered_entries
    
    def get_entry_count(self) -> int:
        """Get total number of audit entries"""
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    entries = json.load(f)
                return len(entries)
            except (json.JSONDecodeError, FileNotFoundError):
                return 0
        return 0