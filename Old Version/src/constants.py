from enum import Enum
import random
from typing import Dict


class ANSICommand(str, Enum):
    """x"""
    HIDE_CURSOR = "\033[?25l"
    SHOW_CURSOR = "\033[?25h"
    HOME_CURSOR = "\033[H"
    CLEAR_SCROLLBACK = "\033[3J"
    CLEAR_SCREEN = "\033[2J"
    CLEAR_DOWN = "\033[J"
    CLEAR_LINE = "\033[K"
    RESET = "\033[0m"

    def __str__(self) -> str:
        return self.value


class DisplayMode(str, Enum):
    """x"""
    BLOCK = "block"
    ASCII = "ascii"

    def __str__(self) -> str:
        return self.value


DISPLAY_CHARACTERS: Dict[DisplayMode, Dict[str, str]] = {
    DisplayMode.BLOCK: {
        "wall": "  ",
        "floor": "  ",
        "entry": "EE",
        "exit": "XX",
        "path": "░░"
    },
    DisplayMode.ASCII: {
        "wall": "##",
        "floor": "  ",
        "entry": "E ",
        "exit": "X ",
        "path": ".."
    }
}


COLOR_PALETTE: Dict[str, int] = {
    "black": 0,
    "red": 1,
    "green": 2,
    "yellow": 3,
    "blue": 4,
    "magenta": 5,
    "cyan": 6,
    "white": 7,
    "grey": 8,
    "bright_red": 9,
    "bright_green": 10,
    "bright_yellow": 11,
    "bright_blue": 12,
    "bright_magenta": 13,
    "bright_cyan": 14,
    "bright_white": 15
}

RAINBOW_COLORS: Dict[str, int] = {
    "red": 196,
    "orange": 208,
    "yellow": 226,
    "green": 46,
    "blue": 21,
    "indigo": 27,
    "violet": 93
}


def resolve_color_code(color_input: str | int) -> int:
    """x"""
    if isinstance(color_input, int):
        return color_input if 0 <= color_input <= 255 else 4

    clean_input = str(color_input).strip().lower()

    if clean_input == "random":
        return random.choice(list(COLOR_PALETTE.values()))

    if clean_input in COLOR_PALETTE:
        return COLOR_PALETTE[clean_input]

    try:
        num = int(clean_input)
        return num if 0 <= num <= 255 else 4
    except ValueError:
        return 4
