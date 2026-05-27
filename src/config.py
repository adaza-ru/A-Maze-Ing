import os
from typing import Optional, Tuple

from pydantic import BaseModel, Field, ValidationError


class MazeConfig(BaseModel):
    """
    Full configuration for maze generation and display.

    Loaded from a KEY=VALUE flat text file.
    Pydantic validates types and ranges automatically.
    """

    # ── Generation ─────────────────────────────────────────────────────────
    width: int = Field(default=20, ge=5, le=100)
    height: int = Field(default=42, ge=5, le=100)
    entry: str = Field(default="0,0")
    exit: str = Field(default="19,14")
    output_file: str = Field(default="maze.txt")
    perfect: bool = Field(default=True)
    seed: int = Field(default=42)
    algorithm: str = Field(default="dfs")

    # ── Display ────────────────────────────────────────────────────────────
    display_mode: str = Field(default="block")
    fps: int = Field(default=30, ge=1, le=60)

    # ── Colors (name, 0-255 index, or "random") ───────────────────────────
    wall_color:    str | int = Field(default="blue")
    floor_color:   str | int = Field(default="black")
    entry_color:   str | int = Field(default="magenta")
    exit_color:    str | int = Field(default="red")
    path_color:    str | int = Field(default="cyan")
    player_color:  str | int = Field(default="green")
    logo_42_color: str | int = Field(default="cyan")

    # ── Modes ──────────────────────────────────────────────────────────────
    # rainbow_mode: every second all cell colors randomize ("epileptic" mode).
    rainbow_mode: bool = Field(default=False)
    # play_mode: enables keyboard-driven player movement.
    play_mode: bool = Field(default=False)


def parse_flat_config(filepath: str) -> dict:
    """
    Parse a KEY=VALUE flat config file into a lowercase-keyed dict.

    Lines starting with '#' and empty lines are ignored.
    Keys with empty or 'NONE' values are skipped (field defaults apply).
    """
    config_dict: dict = {}
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            val_clean = value.strip()
            if val_clean.upper() in ("", "NONE"):
                continue
            config_dict[key.strip().lower()] = val_clean
    return config_dict


def load_config(filepath: str) -> Tuple[Optional[MazeConfig], float]:
    """
    Load and validate config from *filepath*.

    Returns:
        (MazeConfig, mtime)  on success.
        (None, 0.0)          on any error (file missing, bad values, …).
    """
    try:
        mtime = os.path.getmtime(filepath)
        raw = parse_flat_config(filepath)
        return MazeConfig(**raw), mtime
    except (FileNotFoundError, ValueError, ValidationError):
        return None, 0.0