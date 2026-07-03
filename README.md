*This project has been created as part of the 42 curriculum by adaza-ru, jabad-di.*


# A-Maze-ing

## Description

A-Maze-ing is a complete Python-based maze generator and solver. The goal of this project is to create a program that takes a configuration file, generates a valid maze (which can be "perfect" with only a single path, or imperfect with loops), and writes it to an output file using a hexadecimal wall representation.

The project also features a visual renderer to display the generated maze, its entry and exit points, and the shortest solution path. Additionally, it includes a hardcoded "42" pattern watermark embedded within the maze geometry when dimensions permit.

## Instructions

To streamline compilation, installation, and execution, the project includes a Makefile.


### Commands

Run the following commands from the root of the repository:

    make install: Sets up the project environment. It creates a Python virtual environment (.venv), installs all required dependencies from requirements.txt, builds the reusable wheel package, and installs it.

    make run: Executes the main program using the .venv Python interpreter. By default, it runs python3 a_maze_ing.py config.txt.

    make debug: Runs the main script in debug mode using Python's built-in debugger (pdb).

    make lint: Runs flake8 and mypy to check for coding standards and type hints.

    make lint-strict: Runs the linters in strict mode for enhanced code quality checking.

    make build: Compiles the reusable generator module into a .whl and .tar.gz pip package.

    make clean: Removes all temporary files, caches (__pycache__, .mypy_cache), and build artifacts to keep the workspace clean.

## Configuration File Format

The program accepts a simple text-based configuration file. It uses a KEY=VALUE pair format on each line. Lines starting with # are treated as comments and ignored.
Example config.txt:

	#Mandatory For Generator
	WIDTH=15
	HEIGHT=15
	ENTRY=0,0
	EXIT=14,14
	OUTPUT_FILE=maze.txt
	PERFECT=True

	# Optional For Generator
	SEED=42

	# Optional For Renderer
	WALL_COLOR=magenta
	FLOOR_COLOR=black
	LOGO_42_COLOR=yellow
	ENTRY_COLOR=red
	EXIT_COLOR=green
	PATH_COLOR=white
	DISPLAY_MODE=block
	RAINBOW_MODE=False
	SHOW_PATH=True

## Algorithms
### Generation: Iterative Depth-First Search (DFS) Backtracker

We chose the Iterative DFS Backtracker for generating the maze structure. DFS naturally creates long, winding, and complex corridors, which are characteristic of classic and challenging mazes. Implementing it iteratively (using a stack) rather than recursively was a deliberate architectural choice to prevent Python recursion depth limits or stack overflows when generating massive grids.

### Solving: Breadth-First Search (BFS)

To find the solution, we implemented BFS. Because a maze is essentially an unweighted graph where every step costs the same, BFS is mathematically guaranteed to find the absolute shortest path from the entry to the exit. This perfectly satisfies the requirement to output the shortest valid sequence of movements.

## Reusable Code

As required, the core maze generation logic is entirely decoupled from the CLI and UI, wrapped in a standalone module that can be imported into future projects.

    The MazeGenerator Class: This single class handles the heavy lifting.

    Protocol Implementation: We utilized Python's typing.Protocol (MazeConfigProtocol) for configuration injection. This ensures high reusability because any external object or class that exposes the required attributes (width, height, entry, exit, etc.) can seamlessly configure the generator without being forced to inherit from a specific base class.

    Pip Packaging: The generator module is packaged using Python's standard build tools. Running make build generates a mazegen-*.whl and mazegen-*.tar.gz file at the repository root, which can be easily installed via pip in any external environment.

## Resources and AI Usage
### References

* [GeeksforGeeks: DFS (Depth-First Search) for a Graph](https://www.geeksforgeeks.org/dsa/depth-first-search-or-dfs-for-a-graph/)

* [GeeksforGeeks: BFS (Breadth-First Search) for a Graph](https://www.geeksforgeeks.org/dsa/breadth-first-search-or-bfs-for-a-graph/)

* Python 3 Official Docs

* blessed Library Documentation

* just_playback Library Documentation

* Python Packaging (pyproject.toml) Documentation

### AI Usage

Artificial Intelligence was used throughout the development cycle to boost productivity and ensure best practices:

* Drafting and Boilerplate: Assisted in structuring this README.md, writing the Makefile, and setting up the pyproject.toml.

* Debugging and Typing: Provided guidance in resolving complex strict type-hinting issues with mypy --strict.

* Refactoring: Helped migrate legacy ANSI escape code logic to the modern blessed terminal library.

* Architecture: Aided in designing the Finite State Machine (FSM) for the UI logic.

* Mentorship: Acted as a general tutor to explain package management, module isolation, and new tools quickly.

## Team and Project Management
### Roles

adaza-ru: Responsible for the graphical representation, global error handling, and the logical flow of the main engine/UI.

jabad-di: Responsible for the generator module, implementing the core DFS and BFS algorithms, and file output formatting.

### Planning Evolution

Initially, we planned highly ambitious bonus features: a playable mode, multiple generation algorithms, generation animations, and shape masks for the maze.

However, jabad-di had to take on heavy work hours in the hospitality sector. Recognizing this limitation, we adapted our scope. We dropped the generator-heavy bonuses, and adaza-ru stepped in to help finalize the generator. We then pivoted to highly impactful UI/UX bonuses: an audio manager to play music based on the mode, a rainbow visual mode, and a non-blocking command-line interface for a much smoother user experience.

### What Worked & Areas for Improvement

What Worked: Our agility and communication. When circumstances changed, we successfully pivoted our feature set without compromising the core project requirements.

What Could Be Improved: Our initial planning was somewhat unrealistic given external constraints. Moving forward, we want to adopt agile methodologies—setting smaller, incremental goals rather than trying to tackle a massive, monolithic project head-on right from the start.

### Tools Used

* Version Control: Git and GitHub.

* Environment/Packaging: pyproject.toml and standard virtual environments (venv).

* Code Quality: flake8 for strict style compliance and mypy for static type checking.