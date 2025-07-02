from colorama import Fore, Style
import difflib

def user_confirm(prompt: str) -> bool:
    resp = input(f"{prompt} (y/n): ").strip().lower()
    return resp == "y"

def print_yellow(text: str):
    print(Fore.YELLOW + text + Style.RESET_ALL)


def draw_box(title: str, content: str, color=Fore.MAGENTA):
    width = 60
    top = f"{color}╭─ {title} {'─' * (width - len(title) - 3)}╮"
    body = "\n".join([f"{color}│ {Style.RESET_ALL}{line}" for line in content.strip().splitlines()])
    bottom = f"{color}╰{'─' * (width)}╯{Style.RESET_ALL}"
    return f"{top}\n{body}\n{bottom}"

def color_diff(diff_text: str) -> str:
    lines = diff_text.splitlines()
    colored = []
    for line in lines:
        if line.startswith("+") and not line.startswith("+++"):
            colored.append(Fore.GREEN + line + Style.RESET_ALL)
        elif line.startswith("-") and not line.startswith("---"):
            colored.append(Fore.RED + line + Style.RESET_ALL)
        elif line.startswith("@@"):
            colored.append(Fore.YELLOW + line + Style.RESET_ALL)
        else:
            colored.append(Style.DIM + line + Style.RESET_ALL)
    return "\n".join(colored)


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
