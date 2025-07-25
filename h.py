#!/usr/bin/env python3
import sys
import re
from colorama import init, Fore, Style

# Initialize colorama (Windows, macOS, Linux)
init(autoreset=True)

# Define regex patterns and corresponding colors
HIGHLIGHTS = [
    # Hex pointers / addresses
    (re.compile(r'0x[0-9A-Fa-f]+'), Fore.CYAN),
    # Decimal numbers
    (re.compile(r'\b\d+\b'), Fore.YELLOW),
    # Braces and punctuation
    (re.compile(r'[\{\}]'), Fore.MAGENTA),
    # The “<repeats N times>” constructs
    (re.compile(r'<repeats\s+\d+\s+times>'), Fore.GREEN),
]

def colorize_line(line: str) -> str:
    """
    Applies all highlight rules to a single line of text.
    """
    # For each pattern, wrap matches in the ANSI color codes
    for pattern, color in HIGHLIGHTS:
        line = pattern.sub(lambda m: f"{color}{m.group(0)}{Style.RESET_ALL}", line)
    return line

def main():
    # Read from stdin line by line and print colorized output
    for raw_line in sys.stdin:
        sys.stdout.write(colorize_line(raw_line))

if __name__ == "__main__":
    main()
