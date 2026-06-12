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
from dataclasses import dataclass, field
from typing import Callable, Optional

from .audio_manager import AudioManager
from .cli import CommandLineInterface
from .config import ConfigResult, MazeConfig, load_config
from .renderer import AtomicRenderer, MazeData, parse_output_file

CONFIG_FILE = "config.txt"
_FPS = 30


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
    """

    config: Optional[MazeConfig] = None
    last_mtime: float = 0.0
    maze_data: Optional[MazeData] = None
    is_running: bool = True
    current_state: Optional[Callable[[], None]] = None
    config_errors: list[str] = field(default_factory=list)
    vim_buffer: str = ""


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

    Hot-reload: state_idle watches config.txt mtime and reloads on change.

    Returns:
        A zero-argument callable that runs the loop until exit.
    """
    ctx = EngineContext()
    renderer = AtomicRenderer()
    term = renderer.term
    
    audio = AudioManager()
    cli = CommandLineInterface()

    def handle_input():
        """Captura inputs no bloqueantes de teclado"""
        key = term.inkey(timeout=0)  # No bloqueante
        if key:
            cli.process_key(key)

    # -- States ---------------------------------------------------------------

    def state_boot() -> None:
        """Load and validate config; transition to generating or error."""
        ok = _apply_config_result(ctx, load_config(CONFIG_FILE))
        ctx.current_state = state_generating if ok else state_error

    def state_generating() -> None:
        """Parse the maze output file; transition to idle."""
        output_file = ctx.config.output_file if ctx.config else "maze.txt"
        ctx.maze_data = parse_output_file(output_file)
        ctx.current_state = state_idle

    def state_idle() -> None:
        """Main display loop: hot-reload config, then render one frame."""
        handle_input()
        
        try:
            mtime = os.path.getmtime(CONFIG_FILE)
            if mtime > ctx.last_mtime:
                ok = _apply_config_result(ctx, load_config(CONFIG_FILE))
                if not ok:
                    ctx.current_state = state_error
                    return
        except OSError:
            # Si el archivo desaparece, cargamos la configuración de nuevo
            # (que forzará un error de "File not found" a través de validate_config_file)
            _apply_config_result(ctx, load_config(CONFIG_FILE))
            ctx.current_state = state_error
            return

        if ctx.config:
            # Controlar el Audio
            audio.update_audio_state(ctx.config.display_mode, ctx.config.rainbow_mode)
            
            # Controlar la UI Inferior y renderizar
            custom_ui = cli.get_ui_bar("")
            renderer.render_frame(ctx.maze_data, ctx.config, ui_bar=custom_ui)
            time.sleep(1.0 / _FPS)
        else:
            ctx.current_state = state_error

    def state_error() -> None:
        """Display all config errors; re-enter boot when file changes."""
        handle_input()
        audio.stop() # Parar música en modo de error

        custom_ui = cli.get_ui_bar("") 
        
        header = f"Errors in {CONFIG_FILE}:"
        lines = [header] + [f"  {e}" for e in ctx.config_errors]
        
        if custom_ui:
            lines.append(custom_ui)
            
        sys.stdout.write(term.clear + term.color(1) + "\n".join(lines) + term.normal)
        sys.stdout.flush()

        try:
            mtime = os.path.getmtime(CONFIG_FILE)
            # Si estábamos en un error de "File not found" (_last_mtime es 0.0 o menor)
            # y ahora sí existe y tiene un mtime real, o simplemente ha cambiado:
            if mtime > ctx.last_mtime:
                ctx.current_state = state_boot
            else:
                time.sleep(1.0 / _FPS)
        except OSError:
            # El archivo sigue sin existir, esperamos y reintentamos en el siguiente frame.
            time.sleep(1.0 / _FPS)

    def state_exit() -> None:
        """Signal the main loop to stop."""
        ctx.is_running = False

    ctx.current_state = state_boot

    # -- Main loop ------------------------------------------------------------

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
                audio.stop()  # MUY IMPORTANTE limpiar el proceso mpg123
                renderer.cleanup()

        print(term.color(5) + "Thank you for your time! \U0001f499" + term.normal)

    return run