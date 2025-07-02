from colorama import Fore, Style
import difflib

def user_confirm(prompt: str) -> bool:
    resp = input(f"{prompt} (y/n): ").strip().lower()
    return resp == "y"

def print_yellow(text: str):
    print(Fore.YELLOW + text + Style.RESET_ALL)

def draw_box(title: str, content: str, color=Fore.WHITE):
    border = f"{color}╭─ {title} {'─' * (50 - len(title))}╮"
    lines = [f"{color}│ {line}" for line in content.strip().splitlines()]
    bottom = f"{color}╰{'─' * 54}╯"
    return "\n".join([border] + lines + [bottom])

def print_diff(from_text, to_text, filepath):
    diff = difflib.unified_diff(
        from_text.splitlines(),
        to_text.splitlines(),
        fromfile=filepath,
        tofile=f"{filepath} (edited)",
        lineterm=""
    )
    for line in diff:
        if line.startswith("+") and not line.startswith("+++"):
            print(Fore.GREEN + line)
        elif line.startswith("-") and not line.startswith("---"):
            print(Fore.RED + line)
        else:
            print(Style.DIM + line)
