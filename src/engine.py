from dataclasses import dataclass, field
import os
import sys
import time
from typing import Callable, Optional

from .config import MazeConfig, load_config
from .constants import ANSICommand
from .renderer import AtomicRenderer

CONFIG_FILE = "config.txt"
MAZE_FILE = "maze.txt"


def load_maze() -> list[str]:
    """x"""
    lines = []
    if not os.path.exists(MAZE_FILE):
        return ["Error: maze.txt don't exist"]

    with open(MAZE_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                break
            lines.append(line)
    return lines


@dataclass
class EngineContext:
    """x"""
    config: Optional[MazeConfig] = None
    last_mtime: float = 0.0
    maze_data: list[str] = field(default_factory=list)
    is_running: bool = True
    current_state: Optional[Callable[[], None]] = None

    player_x: int = 0
    player_y: int = 0
    vim_buffer: str = ""


def amazeing_engine() -> Callable[[], None]:
    """x"""
    ctx = EngineContext()
    renderer = AtomicRenderer()

    def state_boot():
        ctx.config, ctx.last_mtime = load_config(CONFIG_FILE)
        if not ctx.config:
            ctx.current_state = state_error
            return
        ctx.current_state = state_generating

    def state_generating():
        ctx.maze_data = load_maze()
        ctx.current_state = state_idle

    def state_idle():
        current_mtime = os.path.getmtime(CONFIG_FILE)
        if current_mtime > ctx.last_mtime:
            new_config, _ = load_config(CONFIG_FILE)
            if new_config:
                ctx.config = new_config
                ctx.last_mtime = current_mtime

        renderer.render_idle_frame(ctx.maze_data, ctx.config)
        time.sleep(1.0 / ctx.config.fps)

    def state_error():
        sys.stdout.write(f"{ANSICommand.HOME_CURSOR}Error reading config.txt."
                         f" {ANSICommand.CLEAR_DOWN}\n")
        sys.stdout.flush()

        current_mtime = os.path.getmtime(CONFIG_FILE)
        if current_mtime > ctx.last_mtime:
            ctx.current_state = state_boot
        else:
            time.sleep(0.5)

    def state_exit():
        ctx.is_running = False

    ctx.current_state = state_boot

    def run():
        sys.stdout.write(f"{ANSICommand.CLEAR_SCREEN}{ANSICommand.HOME_CURSOR}"
                         f"{ANSICommand.HIDE_CURSOR}")
        sys.stdout.flush()

        try:
            while ctx.is_running:
                ctx.current_state()

        except (KeyboardInterrupt, EOFError):
            ctx.current_state = state_exit
            ctx.current_state()

        finally:
            renderer.cleanup()
            print("Thank you for your time! <3")

    return run
