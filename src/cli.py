import sys
import os
import difflib
import threading
import time
import itertools
from pathlib import Path

from outline import OutlineNode, save_outline_to_file, load_outline_from_file
from ollama import OllamaClient
from editor import apply_edit, run_shell_command
from utils import user_confirm, print_yellow, draw_box, color_diff

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

def scan_codebase(root_dir="."):
    file_map = {}
    for path in Path(root_dir).rglob("*"):
        if path.is_file():
            try:
                content = path.read_text(encoding="utf-8")
                file_map[str(path)] = content
            except Exception:
                continue
    return file_map

def show_spinner(stop_event):
    spinner = itertools.cycle(["⠋", "⠙", "⠸", "⠴", "⠦", "⠇"])
    while not stop_event.is_set():
        sys.stdout.write(f"\r[uxt] Scanning codebase... {next(spinner)}")
        sys.stdout.flush()
        time.sleep(0.1)
    sys.stdout.write("\r[uxt] Codebase scan complete.         \n")

def main_loop():
    print_yellow(LOGO)

    UXT_HOME.mkdir(parents=True, exist_ok=True)
    print(f"[uxt] Using task storage: {DATA_PATH}")

    # Start spinner + scan
    stop_spinner = threading.Event()
    spinner_thread = threading.Thread(target=show_spinner, args=(stop_spinner,))
    spinner_thread.start()

    codebase = scan_codebase()

    stop_spinner.set()
    spinner_thread.join()

    print(f"[uxt] Scanned {len(codebase)} files in codebase.")

    outline_root = load_outline_from_file(DATA_PATH)
    client = OllamaClient()

    while True:
        print("\nCurrent Tasks:")
        print_outline(outline_root)
        user_input = input("\n[uxt] > ").strip()

        if user_input.lower() in ("quit", "exit", "q"):
            save_outline_to_file(outline_root, DATA_PATH)
            print("Goodbye!")
            break

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

        response = client.chat(prompt)
        print(draw_box("uxt - Ollama response", response))

        lines = response.strip().splitlines()
        edit_index = next((i for i, l in enumerate(lines) if l.lower().startswith("edit:")), None)
        run_index = next((i for i, l in enumerate(lines) if l.lower().startswith("run:")), None)
        outline_index = next((i for i, l in enumerate(lines) if l.lower().startswith("outline:")), None)

        if outline_index is not None:
            tasks = [line.strip("- ").strip() for line in lines if line.startswith("- ")]
            for task in tasks:
                outline_root.add_child(OutlineNode(task))
            save_outline_to_file(outline_root, DATA_PATH)
            print("[uxt] Added outlined tasks.")
            continue

        elif edit_index is not None:
            filepath = lines[edit_index][5:].strip()
            new_content = "\n".join(lines[edit_index + 1:])

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
                apply_edit(filepath, new_content)
                print("[uxt] Edit applied.")
            else:
                print("[uxt] Edit skipped.")
            continue

        elif run_index is not None:
            command = lines[run_index][4:].strip()
            print(draw_box("Shell Command", command))
            if user_confirm(f"Run command: {command}?"):
                run_shell_command(command)
            continue

        else:
            print("[uxt] No actionable section found (Edit/Run/Outline).")
