"""
Maze Generator Module.

This module provides a robust, compliant class for generating and solving
mazes. It includes features to enforce the "42" watermark, perfect/imperfect
generation modes, strict input validation using Pydantic, and a BFS-based
shortest-path solver.

Quickstart::

    from generator import MazeGenerator

    mg = MazeGenerator(
        width=35, height=37,
        entry=(10, 16), exit_point=(3, 17),
        output_file="maze.txt",
        perfect=True, seed=176660,
    )
    msg = mg.generator()
    if msg:
        # The caller decides how to handle the warning (stderr, log, GUI…)
        import sys
        print(msg, file=sys.stderr)
    path = mg.solve()
    mg.write_to_file(path)
"""

from __future__ import annotations

import os
import random
from collections import deque
from enum import Enum
from typing import Optional, Protocol, runtime_checkable

from pydantic import BaseModel, Field, model_validator

__all__: list[str] = [
    "Direction",
    "MazeConfig",
    "MazeConfigError",
    "MazeConfigProtocol",
    "MazeGenerator",
    "MazeIOError",
]

__version__: str = "1.0.0"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class MazeError(Exception):
    """Base exception for maze-related errors."""


class MazeConfigError(MazeError):
    """Exception raised for invalid maze configurations."""


class MazeSolveError(MazeError):
    """Exception raised when no path exists between entry and exit."""


class MazeIOError(MazeError):
    """Exception raised for file-related errors."""


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class MazeConfigProtocol(Protocol):
    """Protocol defining the required configuration for the MazeGenerator.

    Any class exposing these attributes satisfies the protocol and can
    serve as a configuration source.
    """

    width: int
    height: int
    entry: tuple[int, int]
    exit_point: tuple[int, int]
    output_file: str
    perfect: bool
    seed: Optional[int]


# ---------------------------------------------------------------------------
# Pydantic configuration model
# ---------------------------------------------------------------------------


class MazeConfig(BaseModel):
    """Pydantic v2 model for validating the maze configuration.

    Attributes:
        width: Number of columns (>= 2).
        height: Number of rows (>= 2).
        entry: Entry cell (x, y), must be inside the maze.
        exit_point: Exit cell (x, y), must be inside the maze.
        output_file: Path to write the hex-encoded output.
        perfect: Generate a perfect maze when True.
        seed: Optional integer seed for the RNG.
    """

    width: int = Field(..., ge=2)
    height: int = Field(..., ge=2)
    entry: tuple[int, int]
    exit_point: tuple[int, int]
    output_file: str = Field(..., min_length=1)
    perfect: bool = True
    seed: Optional[int] = None

    @model_validator(mode="after")
    def _validate_points(self) -> MazeConfig:
        """Validate entry and exit against maze bounds and uniqueness.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If entry or exit is out of bounds, or they are
                the same cell.
        """
        ex, ey = self.entry
        if not (0 <= ex < self.width and 0 <= ey < self.height):
            raise ValueError(
                f"Entry {self.entry} out of bounds "
                f"({self.width}x{self.height})."
            )
        zx, zy = self.exit_point
        if not (0 <= zx < self.width and 0 <= zy < self.height):
            raise ValueError(
                f"Exit {self.exit_point} out of bounds "
                f"({self.width}x{self.height})."
            )
        if self.entry == self.exit_point:
            raise ValueError("Entry and exit cannot be the same cell.")
        return self


# ---------------------------------------------------------------------------
# Direction enumeration
# ---------------------------------------------------------------------------


class Direction(Enum):
    """Cardinal directions with grid deltas and 4-bit wall encoding.

    Each member stores ``(dx, dy, wall_bit, opposite_wall_bit, char)``.

    Bit assignment:
        bit 0 (value 1) — North wall
        bit 1 (value 2) — East  wall
        bit 2 (value 4) — South wall
        bit 3 (value 8) — West  wall

    A wall bit being **set** means the wall is **closed**.
    """

    NORTH = (0, -1, 1, 4, "N")
    EAST = (1, 0, 2, 8, "E")
    SOUTH = (0, 1, 4, 1, "S")
    WEST = (-1, 0, 8, 2, "W")

    @property
    def dx(self) -> int:
        """Horizontal cell offset."""
        return int(self.value[0])

    @property
    def dy(self) -> int:
        """Vertical cell offset."""
        return int(self.value[1])

    @property
    def bit(self) -> int:
        """Wall bit for the current cell in this direction."""
        return int(self.value[2])

    @property
    def opp(self) -> int:
        """Wall bit for the neighbour cell facing back."""
        return int(self.value[3])

    @property
    def char(self) -> str:
        """Single-character direction label (N/E/S/W)."""
        return str(self.value[4])


# ---------------------------------------------------------------------------
# Maze generator
# ---------------------------------------------------------------------------


class MazeGenerator:
    """Generate and solve mazes using the Iterative DFS Backtracker.

    The "42" pattern is carved as fully-enclosed obstacle cells when the
    maze is large enough and neither entry nor exit collides with it.

    Args:
        width: Number of columns (>= 2).
        height: Number of rows (>= 2).
        entry: (x, y) entry cell.
        exit_point: (x, y) exit cell.
        output_file: Path for the hex-encoded output file.
        perfect: Produce a perfect maze (spanning tree) if True.
        seed: Optional RNG seed for reproducibility.

    Raises:
        MazeConfigError: If any argument fails Pydantic validation.

    Example::

        mg = MazeGenerator(
            width=20, height=15,
            entry=(0, 0), exit_point=(19, 14),
            output_file="maze.txt",
            perfect=True, seed=42,
        )
        msg = mg.generator()
        path = mg.solve()
        mg.write_to_file(path)
    """

    def __init__(
        self,
        width: int,
        height: int,
        entry: tuple[int, int],
        exit_point: tuple[int, int],
        output_file: str,
        perfect: bool = True,
        seed: Optional[int] = None,
    ) -> None:
        try:
            self.config: MazeConfig = MazeConfig(
                width=width,
                height=height,
                entry=entry,
                exit_point=exit_point,
                output_file=output_file,
                perfect=perfect,
                seed=seed,
            )
        except ValueError as exc:
            raise MazeConfigError(str(exc)) from exc

        self.grid: list[list[int]] = [
            [15] * self.config.width
            for _ in range(self.config.height)
        ]
        self.reserve_cell: set[tuple[int, int]] = set()

    # ------------------------------------------------------------------
    # Private helpers — "42" pattern
    # ------------------------------------------------------------------

    @staticmethod
    def _get_template_42() -> set[tuple[int, int]]:
        """Return relative (x, y) coordinates forming the '42' glyph.

        Bounding box is 7 columns x 5 rows:
        digit '4' occupies columns 0-2, digit '2' occupies columns 4-6.

        Returns:
            Set of relative integer coordinate pairs.
        """
        four: set[tuple[int, int]] = {
            (0, 0), (0, 1), (0, 2),
            (1, 2),
            (2, 0), (2, 1), (2, 2), (2, 3), (2, 4),
        }
        two: set[tuple[int, int]] = {
            (4, 0), (5, 0), (6, 0),
            (6, 1),
            (4, 2), (5, 2), (6, 2),
            (4, 3),
            (4, 4), (5, 4), (6, 4),
        }
        return four | two

    def _get_centered_42(self) -> set[tuple[int, int]]:
        """Return absolute (x, y) coords for the centred '42' pattern.

        Returns an empty set when the maze is too small
        (width < 15 or height < 10).

        Returns:
            Absolute coordinate set, or empty set if too small.
        """
        if self.config.width < 15 or self.config.height < 10:
            return set()

        template = self._get_template_42()
        offset_x: int = (self.config.width - 7) // 2
        offset_y: int = (self.config.height - 5) // 2

        result: set[tuple[int, int]] = set()
        for rx, ry in template:
            ax: int = rx + offset_x
            ay: int = ry + offset_y
            if (
                0 <= ax < self.config.width
                and 0 <= ay < self.config.height
            ):
                result.add((ax, ay))
        return result

    # ------------------------------------------------------------------
    # Private helpers — DFS generation
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_dfs(
        grid: list[list[int]],
        width: int,
        height: int,
        seed: Optional[int],
        reserved_cells: set[tuple[int, int]],
    ) -> None:
        """Iterative DFS Backtracker maze generation algorithm.

        Carves passages through *grid* using iterative depth-first
        search, treating *reserved_cells* as permanently visited
        obstacles. Each wall is removed by clearing the appropriate
        bit with the ``&= ~bit`` idiom.

        Args:
            grid: 2-D grid initialised to 15 (all walls closed).
            width: Number of columns.
            height: Number of rows.
            seed: Optional RNG seed; calls ``random.seed`` when set.
            reserved_cells: Cells to treat as unvisitable obstacles.
        """
        if seed is not None:
            random.seed(seed)

        start_x: int = 0
        start_y: int = 0
        while (start_x, start_y) in reserved_cells:
            start_x += 1
            if start_x >= width:
                start_x = 0
                start_y += 1
            if start_y >= height:
                return  # every cell is reserved

        stack: list[tuple[int, int]] = [(start_x, start_y)]
        visited: set[tuple[int, int]] = {(start_x, start_y)}
        visited.update(reserved_cells)

        while stack:
            cx, cy = stack[-1]
            neighbors: list[tuple[int, int, Direction]] = []

            for d in Direction:
                nx, ny = cx + d.dx, cy + d.dy
                if (
                    0 <= nx < width
                    and 0 <= ny < height
                    and (nx, ny) not in visited
                ):
                    neighbors.append((nx, ny, d))

            if neighbors:
                tx, ty, chosen = random.choice(neighbors)
                grid[cy][cx] &= ~chosen.bit
                grid[ty][tx] &= ~chosen.opp
                visited.add((tx, ty))
                stack.append((tx, ty))
            else:
                stack.pop()

    def _reset_grid(self) -> None:
        """Reset every cell to 15 (all walls closed)."""
        self.grid = [
            [15] * self.config.width
            for _ in range(self.config.height)
        ]

    # ------------------------------------------------------------------
    # Private helpers — 3x3 open-area constraint
    # ------------------------------------------------------------------

    def _is_3x3_open(self, bx: int, by: int) -> bool:
        """Return True if the 3x3 block at (bx, by) is fully open.

        A block is fully open when all 12 internal connections
        (6 east walls in columns 0-1, 6 south walls in rows 0-1)
        have their bits cleared.

        Args:
            bx: Left column of the 3x3 block.
            by: Top row of the 3x3 block.

        Returns:
            True when no internal wall remains in the block.
        """
        if bx + 2 >= self.config.width or by + 2 >= self.config.height:
            return False

        for row in range(3):          # east walls: columns 0 and 1
            for col in range(2):
                if self.grid[by + row][bx + col] & Direction.EAST.bit:
                    return False

        for row in range(2):          # south walls: rows 0 and 1
            for col in range(3):
                if self.grid[by + row][bx + col] & Direction.SOUTH.bit:
                    return False

        return True

    def _makes_3x3_open(
        self,
        cx: int,
        cy: int,
        nx: int,
        ny: int,
        d: Direction,
    ) -> bool:
        """Check if removing a wall would create a 3x3 fully-open block.

        The wall is temporarily removed, all potentially affected 3x3
        blocks are checked, then the wall is restored regardless of the
        outcome.

        Args:
            cx: Source cell column.
            cy: Source cell row.
            nx: Neighbour cell column.
            ny: Neighbour cell row.
            d: Direction of the wall being tested.

        Returns:
            True if the removal would create a 3x3 open area.
        """
        self.grid[cy][cx] &= ~d.bit
        self.grid[ny][nx] &= ~d.opp

        # A 3x3 block at (bx, by) contains both cells when:
        #   bx in [max(cx,nx)-2 .. min(cx,nx)]
        #   by in [max(cy,ny)-2 .. min(cy,ny)]
        bx_lo: int = max(0, max(cx, nx) - 2)
        bx_hi: int = min(self.config.width - 3, min(cx, nx))
        by_lo: int = max(0, max(cy, ny) - 2)
        by_hi: int = min(self.config.height - 3, min(cy, ny))

        found: bool = False
        for bx in range(bx_lo, bx_hi + 1):
            if found:
                break
            for by in range(by_lo, by_hi + 1):
                if self._is_3x3_open(bx, by):
                    found = True
                    break

        self.grid[cy][cx] |= d.bit
        self.grid[ny][nx] |= d.opp

        return found

    def _break_imperfections(
        self, reserved: set[tuple[int, int]]
    ) -> None:
        """Break a controlled number of walls to create loops.

        Approximately 5% of eligible interior walls are removed at
        random. Any candidate that would produce a 3x3 fully-open
        cell block is skipped.

        Args:
            reserved: Cells whose walls must not be modified.
        """
        candidates: list[tuple[int, int, int, int, Direction]] = []

        for y in range(self.config.height):
            for x in range(self.config.width):
                if (x, y) in reserved:
                    continue
                for d in (Direction.EAST, Direction.SOUTH):
                    wnx: int = x + d.dx
                    wny: int = y + d.dy
                    if (
                        0 <= wnx < self.config.width
                        and 0 <= wny < self.config.height
                        and (wnx, wny) not in reserved
                        and self.grid[y][x] & d.bit
                    ):
                        candidates.append((x, y, wnx, wny, d))

        if not candidates:
            return

        random.shuffle(candidates)
        target: int = max(1, len(candidates) // 20)
        broken: int = 0

        for wx, wy, wnx, wny, wd in candidates:
            if broken >= target:
                break
            if not self._makes_3x3_open(wx, wy, wnx, wny, wd):
                self.grid[wy][wx] &= ~wd.bit
                self.grid[wny][wnx] &= ~wd.opp
                broken += 1

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generator(self) -> Optional[str]:
        """Generate the maze with the Iterative DFS Backtracker.

        If the maze is large enough (>= 15x10) and neither entry nor
        exit collides with the "42" pattern, the pattern cells are
        reserved as solid obstacles. Otherwise the pattern is omitted
        and a descriptive message is returned so the **caller** can
        decide how to surface it (print to stderr, log, display in a
        GUI, etc.).

        Returns:
            None when the "42" pattern was applied successfully, or a
            non-empty string explaining why it was skipped.
        """
        self._reset_grid()

        effective_reserves: set[tuple[int, int]] = set()
        skip_msg: Optional[str] = None

        if self.config.width < 15 or self.config.height < 10:
            skip_msg = "Skipped '42' pattern: Size too small."
        else:
            centered = self._get_centered_42()
            if (
                self.config.entry in centered
                or self.config.exit_point in centered
            ):
                skip_msg = (
                    "Skipped '42' pattern: "
                    "Collision with entry/exit coordinates."
                )
            else:
                effective_reserves = centered
                self.reserve_cell = centered
                for rx, ry in effective_reserves:
                    self.grid[ry][rx] = 15

        self._apply_dfs(
            self.grid,
            self.config.width,
            self.config.height,
            self.config.seed,
            effective_reserves,
        )

        if not self.config.perfect:
            self._break_imperfections(effective_reserves)

        return skip_msg

    def solve(self) -> str:
        """Find the shortest path from entry to exit using BFS.

        Uses ``collections.deque`` for O(V + E) complexity. A move is
        allowed if and only if the corresponding wall bit in the source
        cell is 0 (open).

        Returns:
            Concatenated direction characters ('N', 'E', 'S', 'W')
            representing the shortest path.

        Raises:
            MazeSolveError: If no path exists between entry and exit.
        """
        if self.config.entry == self.config.exit_point:
            return ""

        queue: deque[tuple[int, int]] = deque([self.config.entry])
        visited: set[tuple[int, int]] = {self.config.entry}
        came_from: dict[
            tuple[int, int], tuple[tuple[int, int], str]
        ] = {}

        while queue:
            cx, cy = queue.popleft()

            if (cx, cy) == self.config.exit_point:
                path: list[str] = []
                pos: tuple[int, int] = (cx, cy)
                while pos in came_from:
                    prev, ch = came_from[pos]
                    path.append(ch)
                    pos = prev
                path.reverse()
                return "".join(path)

            for d in Direction:
                if self.grid[cy][cx] & d.bit:
                    continue  # wall is closed
                pnx: int = cx + d.dx
                pny: int = cy + d.dy
                if (
                    0 <= pnx < self.config.width
                    and 0 <= pny < self.config.height
                    and (pnx, pny) not in visited
                ):
                    visited.add((pnx, pny))
                    came_from[(pnx, pny)] = ((cx, cy), d.char)
                    queue.append((pnx, pny))

        raise MazeSolveError(
            f"No path found from {self.config.entry} "
            f"to {self.config.exit_point}."
        )

    def hex_representation(self) -> list[str]:
        """Return the maze as a list of uppercase hex row strings.

        Each cell is encoded as one character ('0'-'F') representing
        its 4-bit wall configuration. Rows are ordered top to bottom.

        Returns:
            List of strings, one per row, each with *width* characters.
        """
        return [
            "".join(f"{cell:X}" for cell in row)
            for row in self.grid
        ]

    def write_to_file(self, path_str: str) -> None:
        """Write the maze and solution to the configured output file.

        Output format::

            <hex rows, one per line>

            <entry_x>,<entry_y>
            <exit_x>,<exit_y>
            <path_string>

        All lines end with newline. UTF-8 encoding is used throughout.

        Args:
            path_str: Directional path string returned by :meth:`solve`.

        Raises:
            MazeIOError: On permission errors, if the output path is a
                directory, or on other OS-level write failures.
        """
        out: str = self.config.output_file
        ex, ey = self.config.entry
        zx, zy = self.config.exit_point

        lines: list[str] = self.hex_representation() + [
            "",
            f"{ex},{ey}",
            f"{zx},{zy}",
            path_str,
        ]
        content: str = "\n".join(lines) + "\n"

        if os.path.isfile(out):
            try:
                with open(out, "r", encoding="utf-8") as fh:
                    fh.read()
            except UnicodeDecodeError:
                pass  # non-UTF-8 file will be overwritten below

        try:
            with open(out, "w", encoding="utf-8") as fh:
                fh.write(content)
        except IsADirectoryError as exc:
            raise MazeIOError(
                f"Output path '{out}' is a directory."
            ) from exc
        except PermissionError as exc:
            raise MazeIOError(
                f"Permission denied writing to '{out}'."
            ) from exc
        except OSError as exc:
            raise MazeIOError(f"OS error writing to '{out}': {exc}") from exc