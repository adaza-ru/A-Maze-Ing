"""
renderer.py – Maze rendering pipeline.

Pipeline (one frame):
    output file
        │  parse_output_file()
        ▼
    MazeData            ← raw hex rows + entry/exit coords + path string
        │  build_cell_matrix()
        ▼
    list[list[CellType]]  ← expanded (h*2+1) x (w*2+1) semantic matrix
        │  render_matrix()          ← uses CellStyle built from MazeConfig
        ▼
    list[str]             ← one ANSI-colored string per row
        │  build_frame()
        ▼
    str                   ← final terminal frame ready for stdout.write()

Scalability hooks already in place:
  - play_mode   : pass player_pos to build_cell_matrix()
  - show_path   : pass show_path=True to build_cell_matrix()
  - animation   : pass each generation step's hex_rows directly to
                  build_cell_matrix() (bypassing parse_output_file)
  - rainbow_mode: AtomicRenderer._get_rainbow_override() refreshes
                  random colors every RAINBOW_INTERVAL seconds and
                  passes them as color_override to render_matrix()
  - vim cmdline : pass custom ui_bar string to render_frame() /
                  build_frame()
"""

import os
import random
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .config import MazeConfig
from .constants import (
    ANSICommand,
    CellType,
    DISPLAY_CHARACTERS,
    DisplayMode,
    resolve_color_code,
)


def get_color_bg(code: int) -> str:
    """Return ANSI escape sequence for a 256-color background."""
    return f"\033[48;5;{code}m"


def get_color_fg(code: int) -> str:
    """Return ANSI escape sequence for a 256-color foreground."""
    return f"\033[38;5;{code}m"


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

    hex_rows: List[str]
    entry: Tuple[int, int]
    exit_: Tuple[int, int]
    path: str


@dataclass
class CellStyle:
    """
    Visual style per cell type, derived from MazeConfig.

    Attributes:
        chars:  Two-column-wide display string for each CellType.
        colors: ANSI 256-color index for each CellType.
        use_bg: True → apply color as background (BLOCK mode).
                False → apply color as foreground (ASCII mode).
    """

    chars: Dict[CellType, str]
    colors: Dict[CellType, int]
    use_bg: bool


_DIR_DELTA: Dict[str, Tuple[int, int]] = {
    'N': (-1, 0),
    'E': (0, +1),
    'S': (+1, 0),
    'W': (0, -1),
}


def parse_output_file(filepath: str) -> Optional[MazeData]:
    """
    Read and parse a maze output file.

    Expected format::

        <hex row 0>
        <hex row 1>
        …
                        ← blank line separator
        entry_x,entry_y
        exit_x,exit_y
        NSEWNSEW…       ← shortest path

    Returns:
        MazeData on success, None on any read or format error.
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
    matrix: List[List[CellType]],
    path: str,
    start_cy: int,
    start_cx: int,
) -> None:
    """
    Trace *path* onto *matrix* starting at (start_cy, start_cx).

    Marks both the passage cell (between two centers) and the destination
    center as CellType.PATH.  ENTRY and EXIT cells are never overwritten.
    """
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
    player_pos: Optional[Tuple[int, int]] = None,
    show_path: bool = False,
) -> List[List[CellType]]:
    """
    Expand the hex grid into a 2D semantic matrix of size (h*2+1) x (w*2+1).

    Cell layout in expanded coordinates:
      - Odd  (cy, cx): original cell center   → FLOOR / ENTRY / EXIT / LOGO
      - Even adjacent: passage between cells  → WALL or FLOOR / PATH
      - Even corners:  structural walls       → always WALL

    LOGO detection: a hex cell with value 0xF (all 4 walls set) is part of
    the "42" pattern and rendered as CellType.LOGO.

    Args:
        maze_data:  Parsed maze output.
        player_pos: Optional (x, y) in cell coords to overlay PLAYER.
        show_path:  If True, trace the solution path onto the matrix.

    Returns:
        2D list of CellType values.
    """
    h = len(maze_data.hex_rows)
    w = len(maze_data.hex_rows[0]) if maze_data.hex_rows else 0
    exp_h = h * 2 + 1
    exp_w = w * 2 + 1

    matrix: List[List[CellType]] = [
        [CellType.WALL] * exp_w for _ in range(exp_h)
    ]

    for y, row in enumerate(maze_data.hex_rows):
        for x, char in enumerate(row):
            try:
                val = int(char, 16)
            except ValueError:
                continue

            cy, cx = y * 2 + 1, x * 2 + 1

            if val == 0xF:
                matrix[cy - 1][cx - 1] = CellType.LOGO
                matrix[cy - 1][cx] = CellType.LOGO
                matrix[cy - 1][cx + 1] = CellType.LOGO
                matrix[cy][cx - 1] = CellType.LOGO
                matrix[cy][cx] = CellType.LOGO
                matrix[cy][cx + 1] = CellType.LOGO
                matrix[cy + 1][cx - 1] = CellType.LOGO
                matrix[cy + 1][cx] = CellType.LOGO
                matrix[cy + 1][cx + 1] = CellType.LOGO

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

    if player_pos is not None:
        px, py = player_pos
        pcy, pcx = py * 2 + 1, px * 2 + 1
        if matrix[pcy][pcx] not in (CellType.ENTRY, CellType.EXIT):
            matrix[pcy][pcx] = CellType.PLAYER

    return matrix


def build_cell_style(config: MazeConfig, mode: DisplayMode) -> CellStyle:
    """
    Build a CellStyle from *config* and the current *mode*.

    Color fields that are absent from the config model fall back to
    sensible defaults via getattr so future config fields are optional.
    """
    def _color(attr: str, fallback: str) -> int:
        return resolve_color_code(getattr(config, attr, fallback))

    colors: Dict[CellType, int] = {
        CellType.WALL: _color('wall_color', 'blue'),
        CellType.FLOOR: _color('floor_color', 'black'),
        CellType.ENTRY: _color('entry_color', 'magenta'),
        CellType.EXIT: _color('exit_color', 'red'),
        CellType.LOGO: _color('logo_42_color', 'cyan'),
        CellType.PLAYER: _color('player_color', 'green'),
        CellType.PATH: _color('path_color', 'cyan'),
    }

    return CellStyle(
        chars=DISPLAY_CHARACTERS[mode].copy(),
        colors=colors,
        use_bg=(mode == DisplayMode.BLOCK),
    )


def render_matrix(
    matrix: List[List[CellType]],
    style: CellStyle,
    color_override: Optional[Dict[CellType, int]] = None,
) -> List[str]:
    """
    Transform a CellType matrix into a list of ANSI-colored strings.

    Args:
        matrix:         2D grid produced by build_cell_matrix().
        style:          Character and color mappings.
        color_override: Optional per-type color dict (e.g. for rainbow mode).
                        When provided it fully replaces style.colors.

    Returns:
        One rendered string per row, each ending with CLEAR_LINE.
    """
    effective = color_override if color_override is not None else style.colors
    lines: List[str] = []

    for row in matrix:
        parts: List[str] = []
        for cell in row:
            char = style.chars[cell]
            code = effective[cell]
            if style.use_bg:
                parts.append(f"{get_color_bg(code)}{char}{ANSICommand.RESET}")
            else:
                parts.append(f"{get_color_fg(code)}{char}{ANSICommand.RESET}")
        lines.append("".join(parts) + str(ANSICommand.CLEAR_LINE))

    return lines


def build_frame(
    rendered_lines: List[str],
    config: MazeConfig,
    mode: DisplayMode,
    term_width: int,
    term_height: int,
    maze_cols: int,
    maze_rows: int,
    ui_bar: str = "",
) -> str:
    """
    Assemble the final terminal frame string from rendered rows.

    Performs a size check: each cell is 2 terminal columns wide, so the
    required display width is maze_cols * 2.  Returns an error screen if
    the maze does not fit the current terminal.

    Args:
        rendered_lines: Output of render_matrix().
        config:         Current maze config (for FPS display, etc.).
        mode:           Current display mode.
        term_width:     Terminal width in columns.
        term_height:    Terminal height in lines.
        maze_cols:      Number of columns in the expanded matrix.
        maze_rows:      Number of rows in the expanded matrix.
        ui_bar:         Custom bottom bar string.
                        Defaults to the standard status bar if empty.

    Returns:
        Complete frame string ready for stdout.write().
    """
    header = (
        f"{ANSICommand.CLEAR_SCREEN}"
        f"{ANSICommand.CLEAR_SCROLLBACK}"
        f"{ANSICommand.HOME_CURSOR}"
    )

    display_w = maze_cols * 2

    if maze_rows > term_height or display_w > term_width:
        return (
            f"{header}"
            f"{get_color_fg(3)}"
            f"Terminal too small "
            f"(need {display_w}\u00d7{maze_rows},"
            f" have {term_width}\u00d7{term_height})"
            f"{ANSICommand.RESET}"
            f"{ANSICommand.CLEAR_DOWN}"
        )

    default_bar = (
        f"\nFPS: {config.fps}"
        f" | Mode: {str(mode).upper()}"
        f" | [/] Vim"
        f" | [ESC] Exit"
        f"{ANSICommand.CLEAR_DOWN}"
    )

    return header + "\n".join(rendered_lines) + (ui_bar or default_bar)


_RAINBOW_INTERVAL: float = 1.0


class AtomicRenderer:
    """
    Stateful renderer that owns terminal-size tracking, CellStyle caching,
    and rainbow-mode timing.

    Typical usage (from engine loop)::

        renderer = AtomicRenderer()
        renderer.render_frame(maze_data, config, show_path=True)

    The render pipeline is exposed as module-level functions so individual
    stages can be reused independently (e.g. for animation or testing).
    """

    def __init__(self) -> None:
        self.terminal_width: int = 0
        self.terminal_height: int = 0
        self._update_term_size()

        self._last_config: Optional[MazeConfig] = None
        self._cell_style: Optional[CellStyle] = None
        self._display_mode: Optional[DisplayMode] = None

        self._rainbow_ts: float = 0.0
        self._rainbow_override: Optional[Dict[CellType, int]] = None

    def _update_term_size(self) -> None:
        """Refresh cached terminal dimensions from the OS."""
        try:
            size = os.get_terminal_size()
            self.terminal_width = size.columns
            self.terminal_height = size.lines
        except OSError:
            pass

    def _resolve_mode(self, config: MazeConfig) -> DisplayMode:
        """Map config.display_mode string to a DisplayMode enum value."""
        if config.display_mode.lower() == "ascii":
            return DisplayMode.ASCII
        return DisplayMode.BLOCK

    def _get_style(self, config: MazeConfig, mode: DisplayMode) -> CellStyle:
        """Return a CellStyle, rebuilding the cache only if config changed."""
        if config != self._last_config or self._cell_style is None:
            self._cell_style = build_cell_style(config, mode)
            self._display_mode = mode
            self._last_config = config
        return self._cell_style

    def _get_rainbow_override(
        self,
        config: MazeConfig,
    ) -> Optional[Dict[CellType, int]]:
        """
        Return a full color-override dict for rainbow mode.

        All cell types receive a new random 256-color index together,
        refreshing once every RAINBOW_INTERVAL seconds ("epileptic" strobe).
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
        show_path: bool = False,
        player_pos: Optional[Tuple[int, int]] = None,
        ui_bar: str = "",
    ) -> None:
        """
        Render a single frame to stdout.

        Args:
            maze_data:  Parsed maze, or None to show a waiting screen.
            config:     Current maze configuration.
            show_path:  Whether to overlay the solution path.
            player_pos: Optional player position in cell coords (x, y).
            ui_bar:     Custom bottom status bar (e.g. vim command input).
                        Defaults to the standard bar when empty.
        """
        self._update_term_size()

        if maze_data is None:
            sys.stdout.write(
                f"{ANSICommand.CLEAR_SCREEN}{ANSICommand.HOME_CURSOR}"
                f"{get_color_fg(3)}Waiting for maze data\u2026"
                f"{ANSICommand.RESET}{ANSICommand.CLEAR_DOWN}"
            )
            sys.stdout.flush()
            return

        mode = self._resolve_mode(config)
        style = self._get_style(config, mode)
        rainbow = self._get_rainbow_override(config)

        matrix = build_cell_matrix(maze_data, player_pos, show_path)
        rendered = render_matrix(matrix, style, rainbow)

        maze_rows = len(matrix)
        maze_cols = len(matrix[0]) if matrix else 0

        frame = build_frame(
            rendered, config, mode,
            self.terminal_width, self.terminal_height,
            maze_cols, maze_rows,
            ui_bar,
        )

        sys.stdout.write(frame)
        sys.stdout.flush()

    def cleanup(self) -> None:
        """Restore cursor visibility and reset all terminal attributes."""
        sys.stdout.write(
            f"{ANSICommand.CLEAR_SCREEN}"
            f"{ANSICommand.CLEAR_SCROLLBACK}"
            f"{ANSICommand.HOME_CURSOR}"
            f"{ANSICommand.SHOW_CURSOR}"
        )
        sys.stdout.flush()
