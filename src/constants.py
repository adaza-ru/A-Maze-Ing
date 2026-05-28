import random
from enum import Enum
from typing import Dict


class ANSICommand(str, Enum):
    """ANSI escape sequences for terminal control."""

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
    """Available visual rendering modes."""

    BLOCK = "block"
    ASCII = "ascii"

    def __str__(self) -> str:
        return self.value


class CellType(str, Enum):
    """
    Semantic type of a cell in the expanded maze matrix.

    The expanded matrix has size (h*2+1) x (w*2+1):
      - Odd  (row, col): cell centers  → FLOOR / ENTRY / EXIT /
        LOGO / PLAYER / PATH
      - Even adjacent:   wall passages → WALL or FLOOR / PATH
      - Even corners:    always WALL
    """

    WALL = "wall"
    FLOOR = "floor"
    ENTRY = "entry"
    EXIT = "exit"
    LOGO = "logo"
    PLAYER = "player"
    PATH = "path"


DISPLAY_CHARACTERS: Dict[DisplayMode, Dict[CellType, str]] = {
    DisplayMode.BLOCK: {
        CellType.WALL: "  ",
        CellType.FLOOR: "  ",
        CellType.ENTRY: "EE",
        CellType.EXIT: "XX",
        CellType.LOGO: "42",
        CellType.PLAYER: "@@",
        CellType.PATH: "░░",
    },
    DisplayMode.ASCII: {
        CellType.WALL: "##",
        CellType.FLOOR: "  ",
        CellType.ENTRY: "E ",
        CellType.EXIT: "X ",
        CellType.LOGO: "42",
        CellType.PLAYER: "@ ",
        CellType.PATH: "..",
    },
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
    "bright_white": 15,
}


RAINBOW_COLORS: Dict[str, int] = {
    "red": 196,
    "orange": 208,
    "yellow": 226,
    "green": 46,
    "blue": 21,
    "indigo": 27,
    "violet": 93,
}


def resolve_color_code(color_input: str | int) -> int:
    """
    Resolve a color value to an ANSI 256-color index.

    Accepts:
      - An int  0-255   → used directly.
      - A named string  → looked up in COLOR_PALETTE.
      - A numeric string → parsed as int.
      - "random"        → random COLOR_PALETTE entry.

    Falls back to blue (4) on any invalid input.
    """
    if isinstance(color_input, int):
        return color_input if 0 <= color_input <= 255 else 4

    clean = str(color_input).strip().lower()

    if clean == "random":
        return random.choice(list(COLOR_PALETTE.values()))

    if clean in COLOR_PALETTE:
        return COLOR_PALETTE[clean]

    try:
        num = int(clean)
        return num if 0 <= num <= 255 else 4
    except ValueError:
        return 4
