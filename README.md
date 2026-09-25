<div align="center">

# A-Maze-ing — Maze Generator & Solver

**A configurable maze generator and solver in Python: an iterative DFS backtracker builds the maze, BFS solves it with a guaranteed shortest path, and a terminal renderer displays both — plus a pip-installable, framework-agnostic generator module.**

![Python](https://img.shields.io/badge/language-Python_3.10+-3776AB?logo=python&logoColor=white)
![flake8](https://img.shields.io/badge/linting-flake8-yellow)
![mypy](https://img.shields.io/badge/typing-mypy_strict-blue)
![Team Project](https://img.shields.io/badge/team-2_developers-orange)

*This project has been created as part of the 42 curriculum by adaza-ru, jabad-di.*

</div>

---

## Table of Contents

- [Overview](#overview)
- [Getting Started](#getting-started)
- [Interactive CLI Commands](#interactive-cli-commands)
- [Configuration File Format](#configuration-file-format)
- [Algorithms](#algorithms)
  - [Generation: Iterative DFS Backtracker](#generation-iterative-dfs-backtracker)
  - [Solving: BFS](#solving-bfs)
- [Reusable Module & Packaging](#reusable-module--packaging)
- [Resources](#resources)
- [Team & Retrospective](#team--retrospective)
- [Notes](#notes)

---

## Overview

A-Maze-ing takes a configuration file, generates a valid maze — either "perfect" (exactly one path between any two points) or imperfect (with loops) — and writes it to a file using a hexadecimal wall representation. A terminal renderer then displays the maze, its entry and exit points, and the shortest solution path. When the dimensions allow for it, a hardcoded "42" pattern is embedded as a watermark directly in the maze geometry.

## Getting Started

### Commands

Run from the root of the repository:

| Command | Description |
|---|---|
| `make install` | Creates a virtual environment (`.venv`), installs dependencies from `requirements.txt`, builds and installs the reusable wheel package |
| `make run` | Runs the main program with the `.venv` interpreter (`python3 a_maze_ing.py config.txt` by default) |
| `make debug` | Runs the main script under Python's `pdb` debugger |
| `make lint` | Runs `flake8` and `mypy` |
| `make lint-strict` | Runs both linters in strict mode |
| `make build` | Builds the reusable generator module into a `.whl` and `.tar.gz` pip package |
| `make clean` | Removes caches (`__pycache__`, `.mypy_cache`) and build artifacts |

### Manual usage

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 a_maze_ing.py config.txt
```

## Interactive CLI Commands

While the program is running, a non-blocking CLI accepts commands to tweak the maze live, without editing `config.txt` and restarting:

| Command | Description |
|---|---|
| `set:<key>=<value>` | Set a specific config value |
| `randomize:<key>` | Randomize a specific config value |
| `randomize:all` | Randomize every config value |
| `regenerate` | Generate a new maze using the same seed |
| `default` | Reset all config values to their defaults |
| `showpath` | Show the shortest path to the exit |
| `hidepath` | Hide the shortest path |
| `exit` | Quit the program |

## Configuration File Format

Plain `KEY=VALUE` pairs, one per line; lines starting with `#` are comments.

```ini
# Mandatory for the generator
WIDTH=15
HEIGHT=15
ENTRY=0,0
EXIT=14,14
OUTPUT_FILE=maze.txt
PERFECT=True

# Optional for the generator
SEED=42

# Optional for the renderer
WALL_COLOR=magenta
FLOOR_COLOR=black
LOGO_42_COLOR=yellow
ENTRY_COLOR=red
EXIT_COLOR=green
PATH_COLOR=white
DISPLAY_MODE=block
RAINBOW_MODE=False
SHOW_PATH=True
```

## Algorithms

### Generation: Iterative DFS Backtracker

DFS naturally produces the long, winding corridors characteristic of classic mazes. It's implemented **iteratively**, with an explicit stack rather than recursive calls — a deliberate choice to avoid Python's recursion depth limit on large grids.

### Solving: BFS

A maze is an unweighted graph where every step costs the same, so BFS is guaranteed to find the shortest entry-to-exit path — exactly what's needed to output the shortest valid sequence of movements.

## Reusable Module & Packaging

The core maze-generation logic is fully decoupled from the CLI and the UI, wrapped in a standalone module meant to be imported into other projects:

- **`MazeGenerator`** — the class that does the heavy lifting.
- **Protocol-based configuration** — instead of requiring config objects to inherit from a specific base class, the generator accepts anything satisfying `MazeConfigProtocol` (`typing.Protocol`): any object exposing the right attributes (`width`, `height`, `entry`, `exit`, ...) works, structurally, with no inheritance required.
- **Pip packaging** — `make build` produces a `mazegen-*.whl` and `mazegen-*.tar.gz` at the repository root, installable with `pip` in any external environment.

## Resources

- [GeeksforGeeks — DFS for a Graph](https://www.geeksforgeeks.org/dsa/depth-first-search-or-dfs-for-a-graph/)
- [GeeksforGeeks — BFS for a Graph](https://www.geeksforgeeks.org/dsa/breadth-first-search-or-bfs-for-a-graph/)
- Python 3 official documentation
- `blessed` library documentation
- `just_playback` library documentation
- Python packaging (`pyproject.toml`) documentation

## Team & Retrospective

**Roles**

- **adaza-ru** — graphical representation, global error handling, and the main engine/UI logic.
- **jabad-di** — the generator module, the DFS/BFS algorithms, and file output formatting.

**How the scope changed**

The original plan included several ambitious bonuses: a playable mode, multiple generation algorithms, generation animations, and shape masks. When jabad-di's hours at a hospitality job increased partway through, the team reassessed rather than pushing through the original scope: the generator-heavy bonuses were dropped, adaza-ru stepped in to help finish the generator, and the remaining time went into UI/UX bonuses with a better effort-to-impact ratio — an audio manager tied to the maze mode, a rainbow visual mode, and a non-blocking CLI.

**What worked, and what's next**

Communication made the pivot possible — the feature set changed without compromising the core requirements. The main lesson for next time is on the planning side: the initial scope assumed availability that didn't hold, and smaller, incremental milestones would have absorbed that kind of change more gracefully than a single large plan set at the start.

## Notes

Originally built as part of the 42 curriculum, by adaza-ru and jabad-di. AI tools were used throughout — help structuring this README, the Makefile, and `pyproject.toml`; guidance on strict `mypy` typing issues; assistance migrating legacy ANSI escape-code logic to the `blessed` library; and design input on the UI's finite state machine. All architecture, algorithm implementation, and final decisions were the authors' own.