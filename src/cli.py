import sys
import os
import difflib
import threading
import time
import itertools
import logging
from pathlib import Path
from typing import Dict, Set, Optional, Tuple
from datetime import datetime

from outline import OutlineNode, save_outline_to_file, load_outline_from_file
from ollama import OllamaClient
from editor import apply_edit, run_shell_command, sanitize_code_content
from utils import user_confirm, print_yellow, draw_box, color_diff

# Import config with explicit path handling to avoid conflicts
try:
    from .config import UXTConfig
except ImportError:
    # Fallback for direct execution - be more specific about the import
    import sys
    import importlib.util
    from pathlib import Path
    
    current_dir = Path(__file__).parent
    config_path = current_dir / "config.py"
    
    if config_path.exists():
        # Load the local config.py file directly
        spec = importlib.util.spec_from_file_location("config", config_path)
        config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config_module)
        UXTConfig = config_module.UXTConfig
    else:
        # Create a minimal config if file doesn't exist
        print("[WARNING] config.py not found, creating minimal configuration...")
        
        class UXTConfig:
            def __init__(self):
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
            
            def get(self, key, default=None):
                return self._config.get(key, default)
            
            def set(self, key, value):
                self._config[key] = value
            
            def save(self):
                return True
            
            def reset(self):
                return True

LOGO = r"""
██╗      ██╗   ██╗██╗  ██╗████████╗
╚██╗     ██║   ██║╚██╗██╔╝╚══██╔══╝
 ╚██╗    ██║   ██║ ╚███╔╝    ██║
 ██╔╝    ██║   ██║ ██╔██╗    ██║
██╔╝     ╚██████╔╝██╔╝ ██╗   ██║
╚═╝       ╚═════╝ ╚═╝  ╚═╝   ╚═╝
"""

UXT_HOME = Path.home() / ".uxt"
DATA_PATH = UXT_HOME / "tasks.json"

# Global config instance
config = UXTConfig()

class CodebaseCache:
    """Caches file contents and modification times to avoid unnecessary re-reads."""
    
    def __init__(self):
        self.cache: Dict[str, str] = {}
        self.mtimes: Dict[str, float] = {}
        
    def is_stale(self, filepath: str) -> bool:
        """Check if cached file is stale based on modification time."""
        try:
            current_mtime = os.path.getmtime(filepath)
            return filepath not in self.mtimes or self.mtimes[filepath] != current_mtime
        except OSError:
            return True
            
    def update(self, filepath: str, content: str):
        """Update cache with new content and mtime."""
        self.cache[filepath] = content
        try:
            self.mtimes[filepath] = os.path.getmtime(filepath)
        except OSError:
            pass
            
    def get(self, filepath: str) -> Optional[str]:
        """Get cached content if not stale."""
        if not self.is_stale(filepath):
            return self.cache.get(filepath)
        return None

def print_outline(node: OutlineNode, prefix=""):
    print(prefix + "- " + node.title)
    for child in node.children:
        print_outline(child, prefix + "  ")

def gather_outline_text(node: OutlineNode, indent=0):
    spacer = "  " * indent
    text = f"{spacer}- {node.title}\n"
    for child in node.children:
        text += gather_outline_text(child, indent + 1)
    return text

def should_scan_file(path: Path) -> bool:
    """Determine if a file should be included in the codebase scan."""
    code_extensions = set(config.get('code_extensions', []))
    max_file_size = config.get('max_file_size', 1024 * 1024)
    ignore_dirs = set(config.get('ignore_dirs', []))
    
    if path.suffix.lower() not in code_extensions:
        return False
        
    # Skip files that are too large
    try:
        if path.stat().st_size > max_file_size:
            return False
    except OSError:
        return False
        
    # Skip files in ignored directories
    for part in path.parts:
        if part in ignore_dirs:
            return False
            
    return True

def scan_codebase(root_dir=".", cache: Optional[CodebaseCache] = None) -> Dict[str, str]:
    """Efficiently scan codebase with caching and filtering."""
    file_map = {}
    scanned_count = 0
    cached_count = 0
    
    if cache is None:
        cache = CodebaseCache()
    
    for path in Path(root_dir).rglob("*"):
        if not path.is_file() or not should_scan_file(path):
            continue
            
        filepath = str(path)
        
        # Try to get from cache first
        cached_content = cache.get(filepath)
        if cached_content is not None:
            file_map[filepath] = cached_content
            cached_count += 1
            continue
            
        # Read file and update cache
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            file_map[filepath] = content
            cache.update(filepath, content)
            scanned_count += 1
        except Exception as e:
            logging.debug(f"Failed to read {filepath}: {e}")
            continue
    
    if scanned_count > 0 or cached_count > 0:
        logging.info(f"Scanned {scanned_count} files, used {cached_count} from cache")
    
    return file_map

def show_spinner(stop_event, message="Scanning codebase"):
    """Show a spinner with customizable message."""
    spinner = itertools.cycle(["⠋", "⠙", "⠸", "⠴", "⠦", "⠇"])
    while not stop_event.is_set():
        sys.stdout.write(f"\r[uxt] {message}... {next(spinner)}")
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write(f"\r[uxt] {message} complete.         \n")

class ResponseHandler:
    """Handles parsing and execution of AI responses."""
    
    @staticmethod
    def parse_response(response: str) -> Tuple[Optional[str], Optional[dict]]:
        """Parse AI response and return action type and details."""
        lines = response.strip().splitlines()
        
        edit_index = next((i for i, l in enumerate(lines) if l.lower().startswith("edit:")), None)
        run_index = next((i for i, l in enumerate(lines) if l.lower().startswith("run:")), None)
        outline_index = next((i for i, l in enumerate(lines) if l.lower().startswith("outline:")), None)
        
        if outline_index is not None:
            tasks = [line.strip("- ").strip() for line in lines if line.startswith("- ")]
            return "outline", {"tasks": tasks}
            
        elif edit_index is not None:
            filepath = lines[edit_index][5:].strip()
            new_content = "\n".join(lines[edit_index + 1:])
            return "edit", {"filepath": filepath, "content": new_content}
            
        elif run_index is not None:
            command = lines[run_index][4:].strip()
            return "run", {"command": command}
            
        return None, None
    
    @staticmethod
    def handle_outline(outline_root: OutlineNode, tasks: list) -> bool:
        """Handle outline creation."""
        for task in tasks:
            outline_root.add_child(OutlineNode(task))
        save_outline_to_file(outline_root, DATA_PATH)
        print(f"[uxt] Added {len(tasks)} outlined tasks.")
        return True
    
    @staticmethod
    def handle_edit(filepath: str, new_content: str) -> bool:
        """Handle file editing with preview and confirmation."""
        new_content = sanitize_code_content(new_content)
        
        # Validate filepath
        if not filepath or filepath.startswith('/') or '..' in filepath:
            print("[uxt] Error: Invalid file path")
            return False
        
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                old_content = f.read()
        else:
            old_content = ""
            
        diff_text = "\n".join(difflib.unified_diff(
            old_content.splitlines(),
            new_content.splitlines(),
            fromfile=filepath,
            tofile=f"{filepath} (edited)",
            lineterm=""
        ))
        
        print(draw_box(f"Preview Edit: {filepath}", color_diff(diff_text)))
        
        if user_confirm(f"Apply edit to {filepath}?"):
            if apply_edit(filepath, new_content):
                print("[uxt] Edit applied successfully.")
                return True
            else:
                print("[uxt] Edit failed.")
                return False
        else:
            print("[uxt] Edit skipped.")
            return False
    
    @staticmethod
    def handle_run(command: str) -> bool:
        """Handle shell command execution with validation."""
        # Basic validation for dangerous commands
        dangerous_patterns = ['rm -rf', 'del /s', 'format', 'mkfs', 'dd if=']
        if any(pattern in command.lower() for pattern in dangerous_patterns):
            print("[uxt] Warning: Potentially dangerous command detected!")
            if not user_confirm("This command could be destructive. Continue anyway?"):
                return False
        
        print(draw_box("Shell Command", command))
        if user_confirm(f"Run command: {command}?"):
            return run_shell_command(command)
        return False

def display_scan_results(codebase: Dict[str, str]):
    """Display codebase scan results in a user-friendly format."""
    max_display_files = config.get('max_display_files', 20)
    total_files = len(codebase)
    print(f"[uxt] Scanned {total_files} code files:")
    
    # Group files by extension for better overview
    by_extension = {}
    for filepath in codebase.keys():
        ext = Path(filepath).suffix.lower()
        by_extension.setdefault(ext, []).append(filepath)
    
    # Show overview by file type
    if len(by_extension) > 1:
        for ext, files in sorted(by_extension.items()):
            print(f"  {ext or '(no ext)'}: {len(files)} files")
        print()
    
    # Show individual files (up to limit)
    displayed_files = list(codebase.keys())[:max_display_files]
    for filepath in displayed_files:
        print(f"  - {filepath}")
    
    if total_files > max_display_files:
        print(f"  ... and {total_files - max_display_files} more")

def get_user_input() -> str:
    """Get user input with basic command handling."""
    try:
        user_input = input("\n[uxt] > ").strip()
        
        # Handle special commands
        if user_input.lower() in ("help", "h", "?"):
            print_help()
            return ""
        elif user_input.lower() in ("clear", "cls"):
            os.system('cls' if os.name == 'nt' else 'clear')
            return ""
        elif user_input.lower().startswith("config"):
            handle_config_command(user_input)
            return ""
            
        return user_input
    except KeyboardInterrupt:
        print("\n[uxt] Use 'quit' or 'exit' to leave.")
        return ""
    except EOFError:
        return "quit"

def handle_config_command(command: str):
    """Handle configuration commands."""
    parts = command.split()
    
    if len(parts) == 1:
        # Show current config
        print(draw_box("Current Configuration", 
                      f"Model: {config.get('model')}\n"
                      f"Max file size: {config.get('max_file_size') // 1024}KB\n"
                      f"Max display files: {config.get('max_display_files')}\n"
                      f"Enable caching: {config.get('enable_caching')}\n"
                      f"Auto backup: {config.get('auto_backup')}"))
    elif len(parts) == 3 and parts[1] == "set":
        # Set config value
        key, value = parts[2].split('=', 1) if '=' in parts[2] else (parts[2], None)
        if value is None:
            print("[uxt] Usage: config set key=value")
            return
        
        # Try to parse value as appropriate type
        if value.lower() in ('true', 'false'):
            value = value.lower() == 'true'
        elif value.isdigit():
            value = int(value)
        
        config.set(key, value)
        if config.save():
            print(f"[uxt] Set {key} = {value}")
        else:
            print("[uxt] Failed to save configuration")
    elif len(parts) == 2 and parts[1] == "reset":
        if config.reset():
            print("[uxt] Configuration reset to defaults")
        else:
            print("[uxt] Failed to reset configuration")
    else:
        print("[uxt] Usage: config [set key=value|reset]")

def print_help():
    """Display help information."""
    help_text = """
Available commands:
  help, h, ?        - Show this help
  clear, cls        - Clear screen
  config            - Show current configuration
  config set key=value - Set configuration value
  config reset      - Reset configuration to defaults
  quit, exit, q     - Exit the application
  
You can also ask the AI to:
  - Edit files: "Fix the bug in main.py"
  - Run commands: "Install the dependencies"
  - Create tasks: "Break down the user authentication feature"
    """
    print(draw_box("Help", help_text.strip()))
def main_loop():
    """Main application loop with improved error handling and caching."""
    print_yellow(LOGO)

    # Setup logging
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(UXT_HOME / "uxt.log"),
            logging.StreamHandler()
        ]
    )
    
    UXT_HOME.mkdir(parents=True, exist_ok=True)
    print(f"[uxt] Using task storage: {DATA_PATH}")

    # Initialize components
    outline_root = load_outline_from_file(DATA_PATH)
    cache = CodebaseCache()
    response_handler = ResponseHandler()
    
    # Initialize AI client with error handling
    try:
        client = OllamaClient(
            host=config.get('ollama_host', 'http://localhost'),
            port=config.get('ollama_port', 11434),
            model=config.get('model')
        )
    except Exception as e:
        print(f"[uxt] Error initializing Ollama client: {e}")
        print("[uxt] Please ensure Ollama is running and try again.")
        return

    print("[uxt] Type 'help' for available commands.")

    while True:
        try:
            # Scan codebase with caching
            use_cache = config.get('enable_caching', True)
            if use_cache:
                stop_spinner = threading.Event()
                spinner_thread = threading.Thread(target=show_spinner, args=(stop_spinner, "Scanning codebase"))
                spinner_thread.start()

                codebase = scan_codebase(cache=cache)

                stop_spinner.set()
                spinner_thread.join()
            else:
                codebase = scan_codebase()

            # Display results
            display_scan_results(codebase)

            print("\nCurrent Tasks:")
            print_outline(outline_root)
            
            # Get user input
            user_input = get_user_input()
            if not user_input:
                continue
                
            if user_input.lower() in ("quit", "exit", "q"):
                save_outline_to_file(outline_root, DATA_PATH)
                print("Goodbye!")
                break

            # Prepare AI prompt
            outline_context = gather_outline_text(outline_root)
            prompt = f"""You are an agentic coding assistant.

You are working on the following tasks:
{outline_context}

The user said:
\"\"\"{user_input}\"\"\"

Respond with one of the following formats:

If this requires code changes:
Edit: ./relative/path/to/file.ext
<new full file content here>

If this requires running shell commands:
Run: <command>

If this request can be broken down into subtasks:
Outline:
- Task 1
- Task 2

Do not explain anything unless asked.
Only respond with a single Edit, Run, or Outline section.

Never delete or modify user code unless the user's prompt explicitly requests it or clearly implies it."""

            # Get AI response
            try:
                response = client.chat(prompt)
                print(draw_box("uxt - Ollama response", response))
            except Exception as e:
                print(f"[uxt] Error getting AI response: {e}")
                continue

            # Parse and handle response
            action_type, details = response_handler.parse_response(response)
            
            if action_type == "outline":
                response_handler.handle_outline(outline_root, details["tasks"])
            elif action_type == "edit":
                response_handler.handle_edit(details["filepath"], details["content"])
            elif action_type == "run":
                response_handler.handle_run(details["command"])
            else:
                print("[uxt] No actionable section found (Edit/Run/Outline).")
                
        except KeyboardInterrupt:
            print("\n[uxt] Interrupted. Use 'quit' to exit.")
            continue
        except Exception as e:
            print(f"[uxt] Unexpected error: {e}")
            logging.exception("Unexpected error in main loop")
            continue
