"""
engine.py - State-machine game loop.

State graph::

    state_boot -> state_generating -> state_idle
              -> state_error ->

blessed context managers (fullscreen, hidden_cursor) are entered in run()
and wrap the entire loop lifetime, so terminal state is always restored
cleanly - even on Ctrl-C or unexpected exceptions.
"""

import os
import sys
import time
import random
from dataclasses import dataclass, field
from typing import Callable, Optional

from .audio_manager import AudioManager
from .cli import CommandLineInterface
from .config import ConfigResult, MazeConfig, load_config
from .renderer import AtomicRenderer, MazeData, parse_output_file
from mazegen import MazeGenerator
from .constants import (
    CONFIG_FILE,
    _FPS
)


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
        config_errors: Error messages from the last failed config load.
        vim_buffer:    Accumulated keystrokes for the vim command line.
        generator_msg: Message from auto-generation (e.g. warnings).
    """

    config: Optional[MazeConfig] = None
    last_mtime: float = 0.0
    maze_data: Optional[MazeData] = None
    maze_signature: Optional[tuple[object, ...]] = None
    is_running: bool = True
    current_state: Optional[Callable[[], None]] = None
    config_errors: list[str] = field(default_factory=list)
    vim_buffer: str = ""
    generator_msg: str = ""


def _maze_signature(config: MazeConfig) -> tuple[object, ...]:
    """Fields that change the maze generation result."""
    return (
        config.width,
        config.height,
        config.entry,
        config.exit,
        config.perfect,
        config.seed,
    )


def _apply_config_result(ctx: EngineContext, result: ConfigResult) -> bool:
    """
    Store a ConfigResult into *ctx*.

    Returns True if the config is valid, False otherwise.
    Always updates last_mtime so hot-reload can detect the next change.
    """
    ctx.last_mtime = result.mtime
    if result.config:
        ctx.config = result.config
        ctx.config_errors = []
        return True
    ctx.config_errors = result.errors
    return False


def amazeing_engine() -> Callable[[], None]:
    """
    Build and return the main engine loop as a callable.
    """
    ctx = EngineContext()
    renderer = AtomicRenderer()
    term = renderer.term
    audio = AudioManager()

    def trigger_exit() -> None:
        """Signal the CLI 'exit' command to stop the engine."""
        ctx.current_state = state_exit

    def trigger_regenerate() -> None:
        """Signal the CLI 'regenerate' command to reload config and maze."""
        ctx.current_state = state_boot

    cli = CommandLineInterface(
        config_path=CONFIG_FILE,
        on_exit=trigger_exit,
        on_regenerate=trigger_regenerate,
    )

    def handle_input() -> None:
        """Capture non-blocking keyboard input and forward it to the CLI.

        Called every frame, even when no key was pressed, so the CLI's
        status-message timer ticks down at a steady rate.
        """
        key = term.inkey(timeout=0)
        cli.process_key(key)

    def state_boot() -> None:
        """Load and validate config; transition to generating or error."""
        ok = _apply_config_result(ctx, load_config(CONFIG_FILE))
        ctx.current_state = state_generating if ok else state_error

    def state_generating() -> None:
        """
        Generates the maze and saves it to the root dir,
        then transitions to idle.
        """
        if not ctx.config:
            ctx.current_state = state_error
            return

        project_root = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        output_file_name = ctx.config.output_file or "maze.txt"
        abs_output_file = os.path.join(project_root, output_file_name)

        ctx.generator_msg = ""

        try:
            entry_x, entry_y = map(int, ctx.config.entry.split(","))
            exit_x, exit_y = map(int, ctx.config.exit.split(","))

            effective_seed = (
                ctx.config.seed
                if ctx.config.seed is not None
                else random.randint(0, 2**32 - 1)
            )

            mg = MazeGenerator(
                width=ctx.config.width,
                height=ctx.config.height,
                entry=(entry_x, entry_y),
                exit=(exit_x, exit_y),
                output_file=abs_output_file,
                perfect=ctx.config.perfect,
                seed=effective_seed
            )

            skip_msg = mg.generator()
            if skip_msg:
                ctx.generator_msg = skip_msg

            ctx.maze_data = parse_output_file(abs_output_file)
            ctx.maze_signature = _maze_signature(ctx.config)
            ctx.current_state = state_idle

        except ValueError:
            ctx.config_errors = [
                "Format errors in config.txt points (expected 'x,y')"
            ]
            ctx.current_state = state_error
        except MazeGenerator.MazeError as e:
            ctx.config_errors = [f"Maze Generation failed: {e}"]
            ctx.current_state = state_error
        except Exception as e:
            ctx.config_errors = [f"Unexpected Generation error: {e}"]
            ctx.current_state = state_error

    def state_idle() -> None:
        """Main display loop: hot-reload config, then render one frame."""
        handle_input()

        if ctx.current_state != state_idle:
            return

        try:
            mtime = os.path.getmtime(CONFIG_FILE)
            if mtime > ctx.last_mtime:
                if ctx.config is not None:
                    previous_signature = _maze_signature(ctx.config)
                else:
                    previous_signature = None

                ok = _apply_config_result(ctx, load_config(CONFIG_FILE))
                if not ok:
                    ctx.current_state = state_error
                else:
                    if ctx.config is not None:
                        new_signature = _maze_signature(ctx.config)
                        if new_signature != previous_signature:
                            ctx.current_state = state_generating
                        else:
                            ctx.current_state = state_idle
                return

        except OSError:
            _apply_config_result(ctx, load_config(CONFIG_FILE))
            ctx.current_state = state_error
            return

        if ctx.config:
            audio.update_audio_state(
                ctx.config.display_mode,
                ctx.config.rainbow_mode
            )

            custom_ui = cli.get_ui_bar()

            if ctx.generator_msg:
                warning_ui = (f"\n\x1b[33m[Warning] "
                              f"{ctx.generator_msg}{term.normal}")
                custom_ui = warning_ui + custom_ui

            renderer.render_frame(ctx.maze_data, ctx.config, ui_bar=custom_ui)
            time.sleep(1.0 / _FPS)
        else:
            ctx.current_state = state_error

    def state_error() -> None:
        """Display all config errors; re-enter boot when file changes."""
        handle_input()
        audio.stop()

        custom_ui = cli.get_ui_bar()

        header = "Errors:"
        lines = [header] + [f"  {e}" for e in ctx.config_errors]

        if custom_ui:
            lines.append(custom_ui.lstrip("\n"))

        sys.stdout.write(
            term.clear + "\x1b[31m" + "\n".join(lines) + term.normal
        )
        sys.stdout.flush()

        try:
            mtime = os.path.getmtime(CONFIG_FILE)
            if mtime > ctx.last_mtime:
                ctx.current_state = state_boot
            else:
                time.sleep(1.0 / _FPS)
        except OSError:
            time.sleep(1.0 / _FPS)

    def state_exit() -> None:
        """Signal the main loop to stop."""
        ctx.is_running = False

    ctx.current_state = state_boot

    def run() -> None:
        """
        Start the engine loop (blocks until exit or Ctrl-C).

        term.fullscreen() switches to the alternate screen buffer and
        restores the original screen on exit - no manual cleanup needed.
        term.hidden_cursor() hides the cursor for the duration of the loop.
        """
        with term.fullscreen(), term.hidden_cursor(), term.cbreak():
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
                audio.stop()
                renderer.cleanup()

        print(
            "\x1b[35m" + "Thank you for your time!\U0001f499" + term.normal
        )

    return run
