from colorama import Fore, Style

def user_confirm(prompt: str) -> bool:
    resp = input(f"{prompt} (y/n): ").strip().lower()
    return resp == "y"

def print_yellow(text: str):
    print(Fore.YELLOW + text + Style.RESET_ALL)
