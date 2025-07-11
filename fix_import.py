#!/usr/bin/env python3
"""
UXT Setup Script - Run this if you get import errors
"""

import os
import sys
from pathlib import Path

def create_config_py():
    """Create config.py with UXTConfig class."""
    config_content = '''import json
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
        return {
            'model': None,
            'ollama_host': 'http://localhost',
            'ollama_port': 11434,
            'max_file_size': 1024 * 1024,
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
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    self._config.update(file_config)
                return True
        except Exception:
            pass
        return False
    
    def save(self) -> bool:
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2)
            return True
        except Exception:
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        self._config[key] = value
    
    def reset(self) -> bool:
        self._config = self._load_default_config()
        return self.save()
    
    def get_all(self) -> Dict[str, Any]:
        return self._config.copy()
'''
    
    config_path = Path("config.py")
    
    if config_path.exists():
        print("✅ config.py already exists")
        return True
    
    try:
        with open(config_path, 'w') as f:
            f.write(config_content)
        print("✅ Created config.py")
        return True
    except Exception as e:
        print(f"❌ Failed to create config.py: {e}")
        return False

def test_import():
    """Test that UXT can be imported."""
    try:
        from config import UXTConfig
        import cli
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

if __name__ == "__main__":
    print("🔧 UXT Setup & Fix Script")
    print("-" * 30)
    
    success = True
    
    if not create_config_py():
        success = False
    
    if not test_import():
        success = False
    
    if success:
        print("\n🎉 Setup complete! Run: python uxt.py")
    else:
        print("\n❌ Setup failed. Check errors above.")
    
    sys.exit(0 if success else 1)
