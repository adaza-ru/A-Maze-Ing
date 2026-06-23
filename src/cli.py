"""
cli.py - Non-blocking vim-style command line overlay.

Owns all state and key-handling logic for the in-app command line:
  - ':' opens the command line.
  - ESC cancels and closes it.
  - ENTER submits the buffered text.

The engine only calls process_key() from state_idle / state_error, so
the command line is naturally restricted to those two states.

get_ui_bar() returns the text for the renderer's bottom status bar, or
an empty string when the renderer should fall back to its own default.
"""

import random
from typing import Any, Callable
from blessed.keyboard import Keystroke

from .config import (
    VALID_KEYS,
    BOOL_KEYS,
    COLOR_KEYS,
    VALID_DISPLAY_MODES,
    VALID_COLOR_NAMES,
)

# How many frames a status message stays visible.
_STATUS_MESSAGE_FRAMES = 20


class CommandLineInterface:
    """Non-blocking vim-style command line state machine."""

    def __init__(
        self,
        config_path: str = "config.txt",
        on_exit: Callable[[], None] = lambda: None,
        on_regenerate: Callable[[], None] = lambda: None,
    ) -> None:
        """
        Initialize an empty, inactive command line.

        Args:
            config_path:   Path to the config file this CLI edits.
            on_exit:       Called when the 'exit' command runs.
            on_regenerate: Called when the 'regenerate' command runs.
                           Expected to drive the engine FSM back to
                           state_boot so config and maze are reloaded.
        """
        self.is_active = False
        self.buffer = ""
        self.status_message = ""
        self._msg_timer = 0
        self.config_path = config_path
        self.on_exit = on_exit
        self.on_regenerate = on_regenerate

    def process_key(self, key: Keystroke) -> None:
        """
        Process one keystroke.

        Call once per frame, even with an empty Keystroke (e.g. when
        term.inkey(timeout=0) had nothing to report), so the status
        message timer ticks down at a steady rate regardless of input.

        Handles opening (':'), cancelling (ESC), editing (printable
        chars / backspace), and submitting (ENTER) the command line.
        """
        if self._msg_timer > 0:
            self._msg_timer -= 1
            if self._msg_timer <= 0:
                self.status_message = ""

        if not self.is_active:
            if key == ":":
                self.is_active = True
                self.buffer = ""
                self.status_message = ""
            return

        if key.is_sequence:
            if key.name == "KEY_ESCAPE":
                self.is_active = False
                self.buffer = ""
            elif key.name == "KEY_ENTER":
                self._execute_command()
            elif key.name in ("KEY_BACKSPACE", "KEY_DELETE"):
                self.buffer = self.buffer[:-1]
        else:
            if key.isprintable():
                self.buffer += key

    def _execute_command(self) -> None:
        """Parse and execute the buffered command."""
        cmd = self.buffer.strip()
        self.is_active = False
        self.buffer = ""

        if not cmd:
            return

        cmd_lower = cmd.lower()

        if cmd_lower == "exit":
            self.on_exit()
            return
        elif cmd_lower == "default":
            self._reset_renderer_defaults()
            return
        elif cmd_lower == "regenerate":
            self.on_regenerate()
            return
        elif cmd_lower == "showpath":
            self._set_config("show_path", "True")
            return
        elif cmd_lower == "hidepath":
            self._set_config("show_path", "False")
            return
        elif cmd_lower.startswith("set:"):
            parts = cmd[4:].split("=", 1)
            if len(parts) == 2:
                self._set_config(parts[0], parts[1])
            else:
                self._show_status("Format error. Usage: Set:<Key>=<Value>")
            return
        elif cmd_lower.startswith("randomize:"):
            key_target = cmd[10:].strip()
            if key_target.lower() == "all":
                self._randomize_all()
            else:
                self._randomize_key(key_target)
            return

        self._show_status(f"Comando '{cmd}' no reconocido.")

    def _reset_renderer_defaults(self) -> None:
        """Reset all renderer-related parameters to empty (default) values."""
        renderer_keys = list(COLOR_KEYS) + ["display_mode", "rainbow_mode", "show_path"]

        for k in renderer_keys:
            self._set_config(k, "")

        self._show_status("Valores del renderer reseteados a default.")

    def _show_status(self, msg: str) -> None:
        """Display *msg* in the status bar for _STATUS_MESSAGE_FRAMES frames."""
        self.status_message = msg
        self._msg_timer = _STATUS_MESSAGE_FRAMES

    def _set_config(self, key: str, value: str) -> None:
        """
        Write KEY=VALUE into config.txt, updating an existing line if found.

        Validates *key* against VALID_KEYS but not *value* — bad values
        are caught centrally by the engine's hot-reload validation and
        surfaced as config errors in state_error, avoiding duplicated
        validation logic between the CLI and config.py.
        """
        key_lower = key.strip().lower()
        if key_lower not in VALID_KEYS:
            self._show_status(f"Key '{key}' inválida.")
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except OSError:
            lines = []

        found = False
        for i, line in enumerate(lines):
            if line.strip().startswith("#") or "=" not in line:
                continue
            k, _ = line.split("=", 1)
            if k.strip().lower() == key_lower:
                lines[i] = f"{k.strip()}={value}\n"
                found = True
                break

        if not found:
            lines.append(f"{key.upper()}={value}\n")

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            self._show_status(f"Success: {key}={value}")
        except OSError as e:
            self._show_status(f"File error: {e}")

    def _read_current_dimensions(self) -> tuple[int, int]:
        """Reads the current width and height from the config file to validate bounds."""
        w, h = 20, 42  # defaults
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k, v = k.strip().lower(), v.strip()
                    if k == "width" and v.isdigit():
                        w = int(v)
                    elif k == "height" and v.isdigit():
                        h = int(v)
        except OSError:
            pass
        return w, h

    def _get_random_value(self, key_lower: str) -> Any:
        """Return a random valid value for *key_lower*, or None if unsupported."""
        if key_lower in COLOR_KEYS:
            colors = list(VALID_COLOR_NAMES - {"random"})
            return random.choice(colors)
        elif key_lower == "display_mode":
            return random.choice(list(VALID_DISPLAY_MODES))
        elif key_lower in ("width", "height"):
            return random.randint(10, 40)
        elif key_lower == "seed":
            return random.randint(1, 999999)
        elif key_lower in ("entry", "exit"):
            w, h = self._read_current_dimensions()
            # Genera coordenadas aleatorias dentro de los límites actuales
            return f"{random.randint(0, w - 1)},{random.randint(0, h - 1)}"
        return None

    def _randomize_key(self, key: str) -> None:
        """Randomize a single config key and write the result to disk."""
        key_lower = key.strip().lower()
        if key_lower not in VALID_KEYS or key_lower in BOOL_KEYS:
            self._show_status(f"'{key}' no se puede randomizar.")
            return

        val = self._get_random_value(key_lower)
        if val is not None:
            self._set_config(key, str(val))

    def _randomize_all(self) -> None:
        """
        Randomize every randomizable key and write the results to disk.

        width/height are processed first, then the rest in a fixed
        (sorted) order. entry/exit are randomized by reading the
        *current* width/height back from disk (_read_current_dimensions),
        so they must run after width/height have already been written —
        otherwise they could pick coordinates outside the newly chosen
        bounds. VALID_KEYS is a frozenset, whose iteration order is not
        guaranteed and varies between process runs (hash randomization),
        so it cannot be relied upon to put width/height first.
        """
        ordered_keys = ["width", "height"] + sorted(
            k for k in VALID_KEYS if k not in ("width", "height")
        )

        for k in ordered_keys:
            if k not in BOOL_KEYS and k != "output_file":
                val = self._get_random_value(k)
                if val is not None:
                    self._set_config(k, str(val))

        self._show_status("Todos los campos randomizados.")

    def get_ui_bar(self) -> str:
        """
        Return the text to render in the bottom status bar.

        Returns an empty string when neither the command line nor a
        status message is active, so the renderer falls back to its
        own default bar.
        """
        if self.is_active:
            return f"\n| COMMAND MODE: {self.buffer}\u2588"
        if self.status_message:
            return f"\n| {self.status_message}"
        return ""
