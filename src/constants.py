"""
constants.py - Enums, display tables, color palette, and helpers.
"""

from enum import Enum


class DisplayMode(str, Enum):
    """Available visual rendering modes."""

    BLOCK = "block"
    ASCII = "ascii"
    CURSED = "cursed"

    def __str__(self) -> str:
        return self.value


class CellType(str, Enum):
    """
    Semantic type of a cell in the expanded maze matrix.

    The expanded matrix has size (h*2+1) x (w*2+1):
      - Odd  (row, col): cell centers  -> FLOOR / ENTRY / EXIT / LOGO / PATH
      - Even adjacent:   wall passages -> WALL or FLOOR / PATH
      - Even corners:    always WALL
    """

    WALL = "wall"
    FLOOR = "floor"
    ENTRY = "entry"
    EXIT = "exit"
    LOGO = "logo"
    PATH = "path"


DISPLAY_CHARACTERS: dict[DisplayMode, dict[CellType, str]] = {
    DisplayMode.BLOCK: {
        CellType.WALL: "  ",
        CellType.FLOOR: "  ",
        CellType.ENTRY: "◫◫",
        CellType.EXIT: "★★",
        CellType.LOGO: "⓸⓶",
        CellType.PATH: "░░",
    },
    DisplayMode.ASCII: {
        CellType.WALL: "##",
        CellType.FLOOR: "░░",
        CellType.ENTRY: "EE",
        CellType.EXIT: "XX",
        CellType.LOGO: "42",
        CellType.PATH: "..",
    },
    DisplayMode.CURSED: {
        CellType.WALL: "😂",
        CellType.FLOOR: "💟",
        CellType.ENTRY: "🍌",
        CellType.EXIT: "🍆",
        CellType.LOGO: "😻",
        CellType.PATH: "💦",
    },
}

COLOR_PALETTE: dict[str, int] = {
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


MANDATORY_KEYS: frozenset[str] = frozenset({
    "width", "height", "entry", "exit", "output_file", "perfect",
})


OPTIONAL_KEYS: frozenset[str] = frozenset({
    "seed",
    "wall_color", "floor_color", "entry_color", "exit_color",
    "path_color", "logo_42_color",
    "display_mode", "rainbow_mode", "show_path",
})


VALID_KEYS: frozenset[str] = MANDATORY_KEYS | OPTIONAL_KEYS


_BOOL_VALUES: frozenset[str] = frozenset({
    "true", "false", "yes", "no", "1", "0", "on", "off",
})


VALID_COLOR_NAMES: frozenset[str] = frozenset({
    "black", "red", "green", "yellow", "blue", "magenta",
    "cyan", "white", "grey", "bright_red", "bright_green",
    "bright_yellow", "bright_blue", "bright_magenta",
    "bright_cyan", "bright_white", "random",
})


VALID_DISPLAY_MODES: frozenset[str] = frozenset({"block", "ascii", "cursed"})


COLOR_KEYS: frozenset[str] = frozenset({
    "wall_color", "floor_color", "entry_color",
    "exit_color", "path_color", "logo_42_color",
})


BOOL_KEYS: frozenset[str] = frozenset({"perfect", "rainbow_mode", "show_path"})


_DIR_DELTA: dict[str, tuple[int, int]] = {
    'N': (-1, 0),
    'E': (0, +1),
    'S': (+1, 0),
    'W': (0, -1),
}


CONFIG_FILE = "config.txt"
_FPS = 30
_STATUS_MESSAGE_FRAMES = 20
_RAINBOW_INTERVAL: float = 1.0
