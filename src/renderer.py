"""
renderer.py - Maze rendering pipeline (blessed backend).

Pipeline (one frame):
    output file
        |  parse_output_file()
        v
    MazeData              <- raw hex rows + entry/exit coords + path string
        |  build_cell_matrix()
        v
    list[list[CellType]]  <- expanded (h*2+1) x (w*2+1) semantic matrix
        |  render_matrix()     <- uses CellStyle + blessed Terminal
        v
    list[str]             <- one colored string per row
        |  build_frame()
        v
    str                   <- complete frame ready for stdout.write()
"""

import random
import sys
import time
from dataclasses import dataclass
from typing import Optional
from blessed import Terminal

from .config import MazeConfig
from .constants import (
    CellType,
    DISPLAY_CHARACTERS,
    DisplayMode,
    COLOR_PALETTE,
    _DIR_DELTA,
    _RAINBOW_INTERVAL
)


@dataclass
class MazeData:
    """
    Parsed content of a maze output file.

    Attributes:
        hex_rows: One hex string per maze row (one char per cell).
        entry:    Cell-space (x, y) of the entrance.
        exit_:    Cell-space (x, y) of the exit.
        path:     Solution as a sequence of N/E/S/W characters.
    """

    hex_rows: list[str]
    entry: tuple[int, int]
    exit_: tuple[int, int]
    path: str


@dataclass
class CellStyle:
    """
    Visual style per cell type, derived from MazeConfig.

    Attributes:
        chars:  Two-column-wide display string for each CellType.
        colors: ANSI 256-color index for each CellType.
        use_bg: True  -> color applied as background (BLOCK mode).
                False -> color applied as foreground (ASCII mode).
    """

    chars: dict[CellType, str]
    colors: dict[CellType, int]
    use_bg: bool


def resolve_color_code(color_input: str | int) -> int:
    """Resolve a color value to an ANSI 256-color index."""
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


def parse_output_file(filepath: str) -> Optional[MazeData]:
    """
    Read and parse a maze output file.

    Expected format::

        <hex row 0>
        <hex row 1>
        ...
                        <- blank line separator
        entry_x,entry_y
        exit_x,exit_y
        NSEWNSEW...     <- shortest path
    """
    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except (FileNotFoundError, OSError):
        return None

    parts = content.strip().split('\n\n', 1)
    if len(parts) < 2:
        return None

    hex_rows = [ln for ln in parts[0].splitlines() if ln.strip()]
    meta = [ln.strip() for ln in parts[1].splitlines() if ln.strip()]

    if len(meta) < 3:
        return None

    try:
        ex, ey = map(int, meta[0].split(','))
        xx, xy = map(int, meta[1].split(','))
    except (ValueError, IndexError):
        return None

    return MazeData(
        hex_rows=hex_rows,
        entry=(ex, ey),
        exit_=(xx, xy),
        path=meta[2],
    )


def _mark_path(
    matrix: list[list[CellType]],
    path: str,
    start_cy: int,
    start_cx: int,
) -> None:
    """Trace *path* onto *matrix*"""
    cy, cx = start_cy, start_cx

    for step in path.upper():
        if step not in _DIR_DELTA:
            continue

        dy, dx = _DIR_DELTA[step]

        wcy, wcx = cy + dy, cx + dx
        if matrix[wcy][wcx] not in (CellType.ENTRY, CellType.EXIT):
            matrix[wcy][wcx] = CellType.PATH

        cy, cx = cy + dy * 2, cx + dx * 2
        if matrix[cy][cx] not in (CellType.ENTRY, CellType.EXIT):
            matrix[cy][cx] = CellType.PATH


def build_cell_matrix(
    maze_data: MazeData,
    show_path: bool = False,
) -> list[list[CellType]]:
    """
    Expand the hex grid into a 2D semantic matrix of size (h*2+1) x (w*2+1).

    """
    h = len(maze_data.hex_rows)
    w = len(maze_data.hex_rows[0]) if maze_data.hex_rows else 0

    matrix: list[list[CellType]] = [
        [CellType.WALL] * (w * 2 + 1) for _ in range(h * 2 + 1)
    ]

    for y, row in enumerate(maze_data.hex_rows):
        for x, char in enumerate(row):
            try:
                val = int(char, 16)
            except ValueError:
                continue

            cy, cx = y * 2 + 1, x * 2 + 1

            if val == 0xF:
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        matrix[cy + dy][cx + dx] = CellType.LOGO
            else:
                matrix[cy][cx] = CellType.FLOOR

                if not (val & 0x1):
                    matrix[cy - 1][cx] = CellType.FLOOR
                if not (val & 0x2):
                    matrix[cy][cx + 1] = CellType.FLOOR
                if not (val & 0x4):
                    matrix[cy + 1][cx] = CellType.FLOOR
                if not (val & 0x8):
                    matrix[cy][cx - 1] = CellType.FLOOR

    ex, ey = maze_data.entry
    xx, xy = maze_data.exit_
    entry_cy, entry_cx = ey * 2 + 1, ex * 2 + 1
    exit_cy, exit_cx = xy * 2 + 1, xx * 2 + 1
    matrix[entry_cy][entry_cx] = CellType.ENTRY
    matrix[exit_cy][exit_cx] = CellType.EXIT

    if show_path and maze_data.path:
        _mark_path(matrix, maze_data.path, entry_cy, entry_cx)

    return matrix


def build_cell_style(config: MazeConfig, mode: DisplayMode) -> CellStyle:
    """
    Build a CellStyle from *config* and the current *mode*.

    Uses getattr with fallbacks so future config fields are never required.
    """
    def _color(attr: str, fallback: str) -> int:
        return resolve_color_code(getattr(config, attr, fallback))

    colors: dict[CellType, int] = {
        CellType.WALL: _color('wall_color', 'magenta'),
        CellType.FLOOR: _color('floor_color', 'black'),
        CellType.ENTRY: _color('entry_color', 'red'),
        CellType.EXIT: _color('exit_color', 'green'),
        CellType.LOGO: _color('logo_42_color', 'yellow'),
        CellType.PATH: _color('path_color', 'bright_white'),
    }

    return CellStyle(
        chars=DISPLAY_CHARACTERS[mode].copy(),
        colors=colors,
        use_bg=(mode == DisplayMode.BLOCK),
    )


def render_matrix(
    matrix: list[list[CellType]],
    style: CellStyle,
    term: Terminal,
    color_override: Optional[dict[CellType, int]] = None,
) -> list[str]:
    """
    Transform a CellType matrix into a list of colored strings.
    """
    effective = color_override if color_override is not None else style.colors
    lines: list[str] = []

    for row in matrix:
        parts: list[str] = []
        for cell in row:
            char = style.chars[cell]
            code = effective[cell]
            if style.use_bg:
                parts.append(f"\x1b[48;5;{code}m{char}{term.normal}")
            else:
                parts.append(f"\x1b[38;5;{code}m{char}{term.normal}")
        lines.append("".join(parts) + term.clear_eol)

    return lines


def build_frame(
    rendered_lines: list[str],
    mode: DisplayMode,
    term: Terminal,
    maze_cols: int,
    maze_rows: int,
    ui_bar: str = "",
) -> str:
    """
    Assemble the final terminal frame string from rendered rows.

    Uses term.width / term.height (always current) for the size check so
    terminal resize is handled automatically without a separate update call.

    Each cell renders as 2 terminal columns, so required width = maze_cols*2.
    """
    display_w = maze_cols * 2

    default_bar = (
        f"\n| Mode: {str(mode).upper()}"
        f" | [:] Vim"
        f" | [ESC] Exit"
    )

    if maze_rows > term.height or display_w > term.width:
        return (
            term.clear
            + f"\x1b[33mTerminal too small (need {display_w}x{maze_rows},"
            + f" have {term.width}x{term.height})"
            + f"\n{ui_bar or default_bar}"
        )

    return term.clear + "\n".join(rendered_lines) + (ui_bar or default_bar)


class AtomicRenderer:
    """
    Stateful renderer that owns the blessed Terminal, CellStyle caching,
    and rainbow-mode timing.

    Typical usage (from the engine loop)::

        renderer = AtomicRenderer()
        renderer.render_frame(maze_data, config)
    """

    def __init__(self) -> None:
        self.term: Terminal = Terminal()
        self._last_config: Optional[MazeConfig] = None
        self._cell_style: Optional[CellStyle] = None
        self._rainbow_ts: float = 0.0
        self._rainbow_override: Optional[dict[CellType, int]] = None

    def _resolve_mode(self, config: MazeConfig) -> DisplayMode:
        """Map config.display_mode string to a DisplayMode enum value."""
        if config.display_mode.lower() == "ascii":
            return DisplayMode.ASCII
        if config.display_mode.lower() == "cursed":
            return DisplayMode.CURSED
        return DisplayMode.BLOCK

    def _get_style(self, config: MazeConfig, mode: DisplayMode) -> CellStyle:
        """Return cached CellStyle, rebuilding only when config changes."""
        if config != self._last_config or self._cell_style is None:
            self._cell_style = build_cell_style(config, mode)
            self._last_config = config
        return self._cell_style

    def _get_rainbow_override(
        self,
        config: MazeConfig,
    ) -> Optional[dict[CellType, int]]:
        """
        Return a full color-override dict for rainbow mode.

        All cell types receive a new random 256-color index together,
        refreshing once every _RAINBOW_INTERVAL seconds.
        Returns None when rainbow mode is inactive.
        """
        if not config.rainbow_mode:
            self._rainbow_override = None
            return None

        now = time.monotonic()
        if now - self._rainbow_ts >= _RAINBOW_INTERVAL:
            self._rainbow_ts = now
            self._rainbow_override = {
                ct: random.randint(0, 255) for ct in CellType
            }

        return self._rainbow_override

    def render_frame(
        self,
        maze_data: Optional[MazeData],
        config: MazeConfig,
        ui_bar: str = "",
    ) -> None:
        """
        Render a single frame to stdout.

        show_path is read directly from config.show_path.
        """
        if maze_data is None:
            sys.stdout.write(
                self.term.clear
                + "\x1b[33mWaiting for maze data..."
                + self.term.normal
            )
            sys.stdout.flush()
            return

        mode = self._resolve_mode(config)
        style = self._get_style(config, mode)
        rainbow = self._get_rainbow_override(config)

        matrix = build_cell_matrix(maze_data, config.show_path)
        rendered = render_matrix(matrix, style, self.term, rainbow)

        maze_rows = len(matrix)
        maze_cols = len(matrix[0]) if matrix else 0

        frame = build_frame(
            rendered, mode, self.term,
            maze_cols, maze_rows,
            ui_bar,
        )

        sys.stdout.write(frame)
        sys.stdout.flush()

    def cleanup(self) -> None:
        """
        Reset terminal attributes before
        the context managers restore state.
        """
        sys.stdout.write(self.term.normal + "\n")
        sys.stdout.flush()
