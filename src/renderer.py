import sys
import os
from typing import List, Generator
from .config import MazeConfig
from .constants import (
    ANSICommand,
    DisplayMode,
    DISPLAY_CHARACTERS,
    RAINBOW_COLORS,
    resolve_color_code
)


def get_color_bg(color_code: int) -> str:
    """x"""
    return f"\033[48;5;{color_code}m"


def get_color_fg(color_code: int) -> str:
    """x"""
    return f"\033[38;5;{color_code}m"


def rainbow_cycle() -> Generator[int, None, None]:
    """x"""
    colors = list(RAINBOW_COLORS.values())
    while True:
        for color in colors:
            yield color


class AtomicRenderer:
    """x"""
    def __init__(self) -> None:
        self.terminal_width: int = 0
        self.terminal_height: int = 0
        self._update_term_size()

    def _update_term_size(self) -> None:
        """x"""
        try:
            size = os.get_terminal_size()
            self.terminal_width = size.columns
            self.terminal_height = size.lines
        except OSError:
            pass

    def _parse_hex_maze(self, raw_maze: List[str]) -> List[str]:
        """x"""
        if not raw_maze or raw_maze[0].startswith("Error"):
            return raw_maze

        height = len(raw_maze)
        width = len(raw_maze[0])
        grid = [
            ['1' for _ in range(width * 2 + 1)] for _ in range(height * 2 + 1)
        ]

        for y, row in enumerate(raw_maze):
            for x, char in enumerate(row):
                try:
                    val = int(char, 16)
                except ValueError:
                    continue

                cy, cx = y * 2 + 1, x * 2 + 1
                grid[cy][cx] = '0'

                if not (val & 1):
                    grid[cy - 1][cx] = '0'
                if not (val & 2):
                    grid[cy][cx + 1] = '0'
                if not (val & 4):
                    grid[cy + 1][cx] = '0'
                if not (val & 8):
                    grid[cy][cx - 1] = '0'

        return ["".join(row) for row in grid]

    def render_idle_frame(
        self,
        raw_maze: List[str],
        config: MazeConfig
    ) -> None:
        """x"""
        self._update_term_size()
        parsed_maze = self._parse_hex_maze(raw_maze)

        w_color = resolve_color_code(config.wall_color)
        f_color = resolve_color_code(config.floor_color)

        if config.display_mode.lower() == "ascii":
            mode_key = DisplayMode.ASCII
        else:
            mode_key = DisplayMode.BLOCK

        chars = DISPLAY_CHARACTERS[mode_key]

        rainbow_gen = rainbow_cycle()
        frame_lines: List[str] = []

        for row in parsed_maze:
            line_str = ""
            for char in row:
                current_w_color = (
                    next(rainbow_gen) if config.rainbow_mode else w_color
                )

                if char == '1':
                    if mode_key == DisplayMode.BLOCK:
                        line_str += (f"{get_color_bg(current_w_color)}"
                                     f"{chars['wall']}{ANSICommand.RESET}")
                    else:
                        line_str += (f"{get_color_fg(current_w_color)}"
                                     f"{chars['wall']}{ANSICommand.RESET}")

                elif char == '0':
                    if mode_key == DisplayMode.BLOCK:
                        line_str += (f"{get_color_bg(f_color)}{chars['floor']}"
                                     f"{ANSICommand.RESET}")
                    else:
                        line_str += (f"{get_color_fg(f_color)}{chars['floor']}"
                                     f"{ANSICommand.RESET}")

                else:
                    line_str += chars['floor']
            frame_lines.append(line_str)

        ui_header = (f" FPS: {config.fps} | Modo: {mode_key.upper()} | "
                     f"[/] Vim | [ESC] Salir ")
        frame_lines.insert(0, ui_header)
        frame_lines.insert(1, "-" * (config.width * 4 + 2))

        if len(frame_lines) > self.terminal_height:
            frame_buffer = (f"{ANSICommand.HOME_CURSOR}Terminal too little "
                            f"for display.{ANSICommand.CLEAR_DOWN}")
        else:
            frame_buffer = (ANSICommand.HOME_CURSOR + "\n".join(frame_lines)
                            + ANSICommand.CLEAR_DOWN)

        sys.stdout.write(frame_buffer)
        sys.stdout.flush()

    def cleanup(self) -> None:
        """x"""
        sys.stdout.write(f"{ANSICommand.SHOW_CURSOR}{ANSICommand.RESET}\n")
        sys.stdout.flush()
