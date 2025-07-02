import os
import shutil
import subprocess
import re

def backup_file(filepath: str):
    backup_path = f"{filepath}.bak"
    try:
        shutil.copy2(filepath, backup_path)
        print(f"[Backup] Created backup: {backup_path}")
    except Exception as e:
        print(f"[ERROR] Could not create backup for {filepath}: {e}")

def sanitize_code_content(content: str) -> str:
    """
    Remove Markdown code fences like ```jsx, ```typescript, ```py etc.
    Keeps only the raw code inside.
    """
    pattern = r"^```[a-zA-Z]*\n|```$"
    sanitized = re.sub(pattern, "", content, flags=re.MULTILINE)
    return sanitized.strip()

def apply_edit(filepath: str, new_content: str):
    if not os.path.exists(filepath):
        print(f"[ERROR] File does not exist: {filepath}")
        return False
    backup_file(filepath)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"[Edit] Applied changes to {filepath}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to write file {filepath}: {e}")
        return False

def run_shell_command(command: str):
    try:
        print(f"[Run] Executing: {command}")
        completed = subprocess.run(command, shell=True, check=True, text=True)
        print("[Run] Command finished successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed with code {e.returncode}")
        return False
