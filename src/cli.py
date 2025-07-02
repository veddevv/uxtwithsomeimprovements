import sys
import os
from outline import OutlineNode, save_outline_to_file, load_outline_from_file
from ollama import OllamaClient
from editor import apply_edit, run_shell_command
from utils import user_confirm, print_yellow

LOGO = r"""
██╗      ██╗   ██╗██╗  ██╗████████╗
╚██╗     ██║   ██║╚██╗██╔╝╚══██╔══╝
 ╚██╗    ██║   ██║ ╚███╔╝    ██║
 ██╔╝    ██║   ██║ ██╔██╗    ██║
██╔╝     ╚██████╔╝██╔╝ ██╗   ██║
╚═╝       ╚═════╝ ╚═╝  ╚═╝   ╚═╝
"""

DATA_PATH = os.path.join("data", "tasks.json")

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

def main_loop():
    print_yellow(LOGO)

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
Edit: ./relative/path/to/file.py
<new full file content here>

If this requires running shell commands:
Run: <command>

If this request can be broken down into subtasks:
Outline:
- Task 1
- Task 2

Do not explain anything unless asked.
Only respond with a single Edit, Run, or Outline section.

Never delete or modify user code unless the user's prompt explicitly requests it or clearly implies it.
"""

        response = client.chat(prompt)
        print("\n[uxt - Ollama response]:")
        print(response)

        lowered = response.lower()

        # Handle Outline
        if response.startswith("Outline:"):
            tasks = [line.strip("- ").strip() for line in response.splitlines() if line.startswith("- ")]
            for task in tasks:
                outline_root.add_child(OutlineNode(task))
            save_outline_to_file(outline_root, DATA_PATH)
            print("[uxt] Added outlined tasks.")
            continue

        # Handle Edit
        elif lowered.startswith("edit:"):
            lines = response.splitlines()
            filepath = lines[0][5:].strip()
            content = "\n".join(lines[1:])
            if user_confirm(f"Apply edit to {filepath}?"):
                success = apply_edit(filepath, content)
                if success:
                    print("[uxt] Edit applied.")
            continue

        # Handle Run
        elif lowered.startswith("run:"):
            command = response[4:].strip()
            if user_confirm(f"Run command: {command}?"):
                success = run_shell_command(command)
                if success:
                    print("[uxt] Command executed.")
            continue

        else:
            print("[uxt] Response not actionable or not formatted correctly.")
