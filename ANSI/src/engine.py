import os
import sys
import time
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

from .config import MazeConfig, load_config
from .constants import ANSICommand
from .renderer import AtomicRenderer, MazeData, parse_output_file

CONFIG_FILE = "config.txt"


@dataclass
class EngineContext:
    """
    Mutable state shared across engine state functions.

    Attributes:
        config:        Current validated maze configuration.
        last_mtime:    mtime of config.txt at last successful load
                       (used for hot-reload detection).
        maze_data:     Parsed maze output, None until first successful read.
        is_running:    Main loop guard; set to False to exit cleanly.
        current_state: Pointer to the active state function.
        show_path:     Whether the solution path overlay is visible.
        player_pos:    Player position in cell coords (x, y) for play mode.
        vim_buffer:    Accumulated keystrokes for the vim command line.
    """

    config: Optional[MazeConfig] = None
    last_mtime: float = 0.0
    maze_data: Optional[MazeData] = None
    is_running: bool = True
    current_state: Optional[Callable[[], None]] = None

    show_path: bool = False
    player_pos: Optional[Tuple[int, int]] = None
    vim_buffer: str = ""


def amazeing_engine() -> Callable[[], None]:
    """
    Build and return the main engine loop as a callable.

    The engine is a simple state machine::

        state_boot → state_generating → state_idle
                  ↘ state_error ↗

    Hot-reload: state_idle watches config.txt mtime and reloads on change.

    Returns:
        A zero-argument callable that runs the loop until exit.
    """
    ctx = EngineContext()
    renderer = AtomicRenderer()

    def state_boot() -> None:
        """Load and validate config; transition to generating or error."""
        ctx.config, ctx.last_mtime = load_config(CONFIG_FILE)
        if not ctx.config:
            ctx.current_state = state_error
            return
        ctx.current_state = state_generating

    def state_generating() -> None:
        """Parse the maze output file; transition to idle."""
        output_file = ctx.config.output_file if ctx.config else "maze.txt"
        ctx.maze_data = parse_output_file(output_file)
        ctx.current_state = state_idle

    def state_idle() -> None:
        """Main display loop: hot-reload config, then render one frame."""
        try:
            mtime = os.path.getmtime(CONFIG_FILE)
            if mtime > ctx.last_mtime:
                new_config, _ = load_config(CONFIG_FILE)
                if new_config:
                    ctx.config = new_config
                    ctx.last_mtime = mtime
        except OSError:
            pass

        if ctx.config:
            renderer.render_frame(
                ctx.maze_data,
                ctx.config,
                show_path=ctx.show_path,
                player_pos=ctx.player_pos,
            )
            time.sleep(1.0 / ctx.config.fps)
        else:
            ctx.current_state = state_error

    def state_error() -> None:
        """Display config error; re-enter boot on file change."""
        sys.stdout.write(
            f"{ANSICommand.HOME_CURSOR}"
            f"Error reading {CONFIG_FILE}."
            f"{ANSICommand.CLEAR_DOWN}\n"
        )
        sys.stdout.flush()

        try:
            mtime = os.path.getmtime(CONFIG_FILE)
            if mtime > ctx.last_mtime:
                ctx.current_state = state_boot
            else:
                time.sleep(0.5)
        except OSError:
            time.sleep(0.5)

    def state_exit() -> None:
        """Signal the main loop to stop."""
        ctx.is_running = False

    ctx.current_state = state_boot

    def run() -> None:
        """Start the engine loop (blocks until exit or Ctrl-C)."""
        sys.stdout.write(
            f"{ANSICommand.CLEAR_SCREEN}"
            f"{ANSICommand.HOME_CURSOR}"
            f"{ANSICommand.HIDE_CURSOR}"
        )
        sys.stdout.flush()

        try:
            while ctx.is_running:
                if ctx.current_state is not None:
                    ctx.current_state()
                else:
                    break

        except (KeyboardInterrupt, EOFError):
            ctx.current_state = state_exit
            ctx.current_state()

        finally:
            renderer.cleanup()
            print("\033[38;5;5mThank you for your time! 💙")

    return run
