import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

class UXTConfig:
    """Configuration management for UXT."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or str(Path.home() / ".uxt" / "config.json")
        self._config = self._load_default_config()
        self.load()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration values."""
        return {
            'model': None,  # Will be auto-selected from available models
            'ollama_host': 'http://localhost',
            'ollama_port': 11434,
            'max_file_size': 1024 * 1024,  # 1MB
            'max_display_files': 20,
            'enable_caching': True,
            'auto_backup': True,
            'code_extensions': [
                '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h',
                '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala',
                '.html', '.css', '.scss', '.less', '.vue', '.svelte',
                '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg',
                '.md', '.txt', '.sql', '.sh', '.bat', '.ps1'
            ],
            'ignore_dirs': [
                'node_modules', '.git', '__pycache__', '.venv', 'venv',
                'dist', 'build', '.next', '.nuxt', 'coverage', '.coverage',
                'logs', 'tmp', 'temp', '.cache', '.pytest_cache'
            ]
        }
    
    def load(self) -> bool:
        """Load configuration from file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    self._config.update(file_config)
                return True
        except Exception as e:
            print(f"Warning: Failed to load config from {self.config_file}: {e}")
        return False
    
    def save(self) -> bool:
        """Save configuration to file."""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error: Failed to save config to {self.config_file}: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self._config[key] = value
    
    def reset(self) -> bool:
        """Reset configuration to defaults."""
        self._config = self._load_default_config()
        return self.save()
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values."""
        return self._config.copy()
