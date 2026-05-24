import os
from typing import Tuple, Optional
from pydantic import BaseModel, Field, ValidationError


class MazeConfig(BaseModel):
    width: int = Field(default=20, ge=5, le=100)
    height: int = Field(default=42, ge=5, le=100)
    entry: str = Field(default="0,0")
    exit: str = Field(default="19,14")
    output_file: str = Field(default="maze.txt")
    perfect: bool = Field(default=True)
    seed: int = Field(default=42)
    random: bool = Field(default=False)
    algorithm: str = Field(default="dfs")

    wall_color: str | int = Field(default="blue")
    floor_color: str | int = Field(default="black")
    player_color: str | int = Field(default="green")
    logo_42_color: str | int = Field(default="cyan")
    display_mode: str = Field(default="block")
    rainbow_mode: bool = Field(default=False)
    play_mode: bool = Field(default=False)
    fps: int = Field(default=30, ge=1, le=60)


def parse_flat_config(filepath: str) -> dict:
    config_dict = {}
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
    try:
        mtime = os.path.getmtime(filepath)
        raw_data = parse_flat_config(filepath)
        return MazeConfig(**raw_data), mtime
    except (FileNotFoundError, ValueError, ValidationError):
        return None, 0.0
