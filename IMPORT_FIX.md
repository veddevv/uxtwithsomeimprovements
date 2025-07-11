# 🔧 Fix for ImportError: cannot import name 'UXTConfig' from 'config'

## Problem
You're getting this error when trying to run UXT:
```
ImportError: cannot import name 'UXTConfig' from 'config' (/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages/config/__init__.py)
```

## ✅ Quick Fix (1 command)

Run this in the `src` directory:

```bash
cd src
python3 fix_import.py
```

This will:
1. Create the missing `config.py` file with the `UXTConfig` class
2. Test that all imports work correctly
3. Confirm UXT is ready to run

## ✅ Manual Fix (if needed)

If the quick fix doesn't work, create the config.py file manually:

### Step 1: Create config.py
```bash
cd src
cat > config.py << 'EOF'
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

class UXTConfig:
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or str(Path.home() / ".uxt" / "config.json")
        self._config = {
            'model': None,
            'ollama_host': 'http://localhost',
            'ollama_port': 11434,
            'max_file_size': 1024 * 1024,
            'max_display_files': 20,
            'enable_caching': True,
            'auto_backup': True,
            'code_extensions': ['.py', '.js', '.ts', '.html', '.css', '.md'],
            'ignore_dirs': ['node_modules', '.git', '__pycache__']
        }
        self.load()
    
    def load(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                    self._config.update(file_config)
        except Exception:
            pass
    
    def save(self):
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
            return True
        except Exception:
            return False
    
    def get(self, key: str, default=None):
        return self._config.get(key, default)
    
    def set(self, key: str, value):
        self._config[key] = value
    
    def reset(self):
        return True
    
    def get_all(self):
        return self._config.copy()
EOF
```

### Step 2: Test the fix
```bash
python3 -c "from config import UXTConfig; print('✅ Import works!')"
```

### Step 3: Run UXT
```bash
python3 uxt.py
```

## ✅ Verification

You should see:
```
🔧 UXT Setup & Fix Script
------------------------------
✅ config.py already exists
✅ All imports successful
🎉 Setup complete! Run: python uxt.py
```

Then UXT should start normally:
```
██╗      ██╗   ██╗██╗  ██╗████████╗
╚██╗     ██║   ██║╚██╗██╔╝╚══██╔══╝
 ╚██╗    ██║   ██║ ╚███╔╝    ██║
 ██╔╝    ██║   ██║ ██╔██╗    ██║
██╔╝     ╚██████╔╝██╔╝ ██╗   ██║
╚═╝       ╚═════╝ ╚═╝  ╚═╝   ╚═╝
```

## 🤔 Why this happens

The error occurs because:
1. Python tries to import from a system-wide `config` package instead of the local `config.py`
2. The repository might be missing the `config.py` file
3. The import path resolution doesn't find the local file

The fix creates a robust import system that works regardless of how Python is run.

## 🚀 Next Steps

Once the import is fixed:
1. Install Ollama: `brew install ollama` (macOS) or visit https://ollama.ai
2. Pull a model: `ollama pull llama3:8b`
3. Start Ollama: `ollama serve`
4. Run UXT: `python3 uxt.py`

## 📞 Still having issues?

Run the diagnostic:
```bash
python3 fix_import.py
```

This will show exactly what's wrong and how to fix it.
