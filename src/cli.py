from outline import OutlineNode, save_outline_to_file, load_outline_from_file
from ollama import OllamaClient
from editor import apply_edit, run_shell_command
from utils import user_confirm, print_yellow
import sys
import os

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
    print_yellow("""
██╗      ██╗   ██╗██╗  ██╗████████╗
╚██╗     ██║   ██║╚██╗██╔╝╚══██╔══╝
 ╚██╗    ██║   ██║ ╚███╔╝    ██║
 ██╔╝    ██║   ██║ ██╔██╗    ██║
██╔╝     ╚██████╔╝██╔╝ ██╗   ██║
╚═╝       ╚═════╝ ╚═╝  ╚═╝   ╚═╝

Turn any Ollama LLM into your agentic code partner!
""")

    outline_root = load_outline_from_file(DATA_PATH)
    client = OllamaClient()

    while True:
        print("\nCurrent Outline:")
        print_outline(outline_root)
        print("\nCommands: add <task>, ask <question>, quit")
        command = input("[uxt] > ").strip()

        if command in ("quit", "exit", "q"):
            print("Saving tasks and exiting...")
            save_outline_to_file(outline_root, DATA_PATH)
            sys.exit(0)

        if command.startswith("add "):
            task_title = command[4:].strip()
            outline_root.add_child(OutlineNode(task_title))
            print(f"Added task: {task_title}")
            save_outline_to_file(outline_root, DATA_PATH)
            continue

        if command.startswith("ask "):
            user_query = command[4:].strip()
            outline_context = gather_outline_text(outline_root)
            prompt = f"""
You are an agentic coding assistant.

You are working on the following tasks:
{outline_context}

The user said: {user_query}

If this requires code changes, respond in this format:

Edit: ./relative/path/to/file.py
<new full file content here>

If this requires running shell commands, respond in this format:

Run: <command>

Do not explain anything unless asked. Only give a single Edit or Run section.
Don't delete any of the user's code unless explicitly prompted to or it's heavily implied within the user's prompt.
"""
            response = client.chat(prompt)

            print("\n[uxt - Ollama response]:")
            print(response)

            lowered = response.lower()
            if any(keyword in lowered for keyword in ["edit:", "change:", "run:", "command:"]):
                if user_confirm("Apply the suggested edit or run the command?"):
                    lines = response.splitlines()
                    for line in lines:
                        if line.lower().startswith("edit:"):
                            filepath = line[5:].strip()
                            content_index = lines.index(line) + 1
                            new_content = "\n".join(lines[content_index:])
                            success = apply_edit(filepath, new_content)
                            if not success:
                                print("[ERROR] Failed to apply edit.")
                            break
                        elif line.lower().startswith("run:"):
                            cmd = line[4:].strip()
                            success = run_shell_command(cmd)
                            if not success:
                                print("[ERROR] Failed to run command.")
                            break
                else:
                    print("Edit/command skipped.")
            continue

        print("Unknown command. Use add <task>, ask <question>, or quit.")
