"""Maze Configuration Parser and Validator."""

import os
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, ValidationError, field_validator
from .constants import (
    MANDATORY_KEYS,
    VALID_KEYS,
    _BOOL_VALUES,
    VALID_COLOR_NAMES,
    VALID_DISPLAY_MODES,
    COLOR_KEYS,
    BOOL_KEYS,
    CONFIG_FILE
)


class MazeConfig(BaseModel):
    """
    Full configuration for maze generation and display.

    Loaded from a KEY=VALUE flat text file.
    Pydantic validates types and ranges automatically.
    """

    width: int = Field(..., ge=3, le=1000)
    height: int = Field(..., ge=3, le=1000)
    entry: str = Field(...)
    exit: str = Field(...)
    output_file: str = Field(..., min_length=1, max_length=255)
    perfect: bool = Field(...)
    seed: int | None = Field(default=None)

    wall_color: str | int = Field(default="magenta")
    floor_color: str | int = Field(default="black")
    entry_color: str | int = Field(default="red")
    exit_color: str | int = Field(default="green")
    path_color: str | int = Field(default="bright_white")
    logo_42_color: str | int = Field(default="yellow")
    display_mode: str = Field(default="block")

    rainbow_mode: bool = Field(default=False)
    show_path: bool = Field(default=False)

    @field_validator("display_mode")
    @classmethod
    def _normalize_display_mode(cls, v: str) -> str:
        """Normalize display_mode to lowercase."""
        return v.lower()

    @field_validator("output_file")
    @classmethod
    def _check_output_name(cls, output: str) -> str:
        """Normalize display_mode to lowercase."""
        if output == CONFIG_FILE:
            raise ValueError("The output file can not be the config input.")
        return output


@dataclass
class ConfigResult:
    """Result of a load_config() call."""

    config: MazeConfig | None
    mtime: float
    errors: list[str] = field(default_factory=list)


def _is_valid_color(value: str) -> bool:
    """Return True if value is a known color name or an int in 0-255."""
    clean = value.strip().lower()
    if clean in VALID_COLOR_NAMES:
        return True
    try:
        return 0 <= int(clean) <= 255
    except ValueError:
        return False


def _validate_coordinates(
    parsed: dict[str, str],
    errors: list[str],
) -> None:
    """
    Cross-field check: entry and exit must be within bounds and differ.
    """
    try:
        w = int(parsed.get("width", "0"))
        h = int(parsed.get("height", "0"))
    except ValueError:
        return

    if w <= 0 or h <= 0:
        return

    coords: dict[str, tuple[int, int]] = {}
    for key in ("entry", "exit"):
        val = parsed.get(key, "")
        if not val:
            continue
        parts = val.split(',')
        if len(parts) != 2:
            continue
        try:
            coords[key] = (int(parts[0]), int(parts[1]))
        except ValueError:
            continue

    for key, (x, y) in coords.items():
        if not (0 <= x < w):
            errors.append(
                f"'{key}' x={x} out of bounds "
                f"for width={w} (0 to {w - 1})"
            )
        if not (0 <= y < h):
            errors.append(
                f"'{key}' y={y} out of bounds "
                f"for height={h} (0 to {h - 1})"
            )

    if len(coords) == 2 and coords["entry"] == coords["exit"]:
        errors.append("'entry' and 'exit' must be different coordinates")


def validate_config_file(filepath: str) -> list[str]:
    """
    Parse and validate *filepath*, returning all errors found.
    """
    errors: list[str] = []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_lines = f.readlines()
    except FileNotFoundError:
        return [f"File not found: '{filepath}'"]
    except UnicodeDecodeError:
        return [
            f"Cannot read '{filepath}': Invalid encoding."
            "Please save as UTF-8."
        ]
    except OSError as e:
        return [f"Cannot read '{filepath}': {e}"]

    parsed: dict[str, str] = {}

    for i, line in enumerate(raw_lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        if '=' not in stripped:
            errors.append(f"Line {i}: missing '=' - '{stripped}'")
            continue

        key_raw, value = stripped.split('=', 1)
        key = key_raw.strip().lower()
        value = value.strip()

        if key not in VALID_KEYS:
            errors.append(f"Line {i}: unknown key '{key}'")
            continue

        parsed[key] = value

    for key in sorted(MANDATORY_KEYS):
        if key not in parsed:
            errors.append(f"Missing mandatory key '{key}'")
        elif not parsed[key]:
            errors.append(f"Mandatory key '{key}' must have a value")

    val = parsed.get("width", "")
    if val:
        try:
            w = int(val)
            if not (3 <= w <= 1000):
                errors.append(f"'width' must be 3-1000, got {w}")
        except ValueError:
            errors.append(f"'width' must be an integer, got '{val}'")

    val = parsed.get("height", "")
    if val:
        try:
            h = int(val)
            if not (3 <= h <= 1000):
                errors.append(f"'height' must be 3-1000, got {h}")
        except ValueError:
            errors.append(f"'height' must be an integer, got '{val}'")

    for coord_key in ("entry", "exit"):
        val = parsed.get(coord_key, "")
        if not val:
            continue
        parts = val.split(',')
        if len(parts) != 2:
            errors.append(
                f"'{coord_key}' must be 'x,y' format, got '{val}'"
            )
        else:
            try:
                int(parts[0])
                int(parts[1])
            except ValueError:
                errors.append(
                    f"'{coord_key}' coords must be integers, got '{val}'"
                )

    val = parsed.get("seed", "")
    if val:
        try:
            int(val)
        except ValueError:
            errors.append(f"'seed' must be an integer, got '{val}'")

    for key in sorted(BOOL_KEYS):
        val = parsed.get(key, "")
        if val and val.lower() not in _BOOL_VALUES:
            errors.append(
                f"'{key}' must be a boolean "
                f"(true/false/yes/no/1/0), got '{val}'"
            )

    for key in sorted(COLOR_KEYS):
        val = parsed.get(key, "")
        if val and not _is_valid_color(val):
            errors.append(
                f"'{key}' is not a valid color "
                f"(name or 0-255), got '{val}'"
            )

    val = parsed.get("display_mode", "")
    if val and val.lower() not in VALID_DISPLAY_MODES:
        errors.append(
            f"'display_mode' must be one of "
            f"{sorted(VALID_DISPLAY_MODES)}, got '{val}'"
        )

    _validate_coordinates(parsed, errors)

    return errors


def parse_flat_config(filepath: str) -> dict[str, str]:
    """
    Parse a KEY=VALUE flat config file into a lowercase-keyed dict.

    Lines starting with '#' and empty lines are ignored.
    Keys with empty or 'NONE' values are skipped (field defaults apply).
    """
    config_dict: dict[str, str] = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith('#') or '=' not in stripped:
                continue
            key, value = stripped.split('=', 1)
            val_clean = value.strip()
            if not val_clean or val_clean.upper() == "NONE":
                continue
            config_dict[key.strip().lower()] = val_clean
    return config_dict


def load_config(filepath: str) -> ConfigResult:
    """
    Validate, parse and return the config at *filepath*.
    """
    try:
        mtime = os.path.getmtime(filepath)
    except OSError:
        mtime = 0.0

    errors = validate_config_file(filepath)
    if errors:
        return ConfigResult(config=None, mtime=mtime, errors=errors)

    try:
        raw = parse_flat_config(filepath)
        config = MazeConfig.model_validate(raw)

        if config.display_mode == "cursed":
            config.rainbow_mode = False

        return ConfigResult(config=config, mtime=mtime, errors=[])
    except (ValueError, ValidationError) as e:
        return ConfigResult(config=None, mtime=mtime, errors=[str(e)])
    except UnicodeDecodeError:
        return ConfigResult(
            config=None,
            mtime=mtime,
            errors=[f"Invalid encoding in {filepath}. Please save as UTF-8."]
        )
