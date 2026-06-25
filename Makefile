
VENV        = .venv
PYTHON      = $(VENV)/bin/python3
PIP         = $(VENV)/bin/pip3
FLAKE8      = $(VENV)/bin/flake8
MYPY        = $(VENV)/bin/mypy

MAIN_SCRIPT = a_maze_ing.py 

EXCLUDE_DIRS = $(VENV),.mypy_cache,.pytest_cache,build,dist,*.egg-info
MYPY_EXCLUDE = (\.venv|\.mypy_cache|\.pytest_cache|build|dist)
TYPINGS_DIR  = typings


.PHONY: all help install run debug clean lint lint-strict build

all: help

help:
	@echo "======================================================================="
	@echo "                        A-MAZE-ING MAKEFILE                            "
	@echo "======================================================================="
	@echo "  make install      - Create .venv (if missing) and install dependencies"
	@echo "  make run          - Execute the main script ($(MAIN_SCRIPT)) inside .venv"
	@echo "  make debug        - Run in debug mode with pdb inside .venv"
	@echo "  make clean        - Remove temporary files, caches, and build artifacts"
	@echo "  make lint         - Run linters using .venv packages"
	@echo "  make lint-strict  - Run flake8 and mypy in strict mode"
	@echo "  make build        - Build the pip package using .venv tools"
	@echo "======================================================================="


$(PIP):
	@echo "Virtual environment not found. Creating .venv..."
	python3 -m venv $(VENV)
	@echo "Virtual environment created successfully."

clean:
	@echo "Cleaning the project environment..."
	find . -type d -name ".mypy_cache" -not -path "./$(VENV)/*" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -not -path "./$(VENV)/*" -exec rm -rf {} +
	find . -type d -name "build" -not -path "./$(VENV)/*" -exec rm -rf {} +
	find . -type d -name "dist" -not -path "./$(VENV)/*" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -not -path "./$(VENV)/*" -exec rm -rf {} +
	find . -type d -name "__pycache__" -not -path "./$(VENV)/*" -exec rm -rf {} +
	find . -type f -name "*.pyc" -not -path "./$(VENV)/*" -delete
	find . -type f -name "*.pyo" -not -path "./$(VENV)/*" -delete

build: clean
	@echo "Building the package..."
	$(PYTHON) -m build
	@echo "Moving wheel to root and cleaning up..."
	mv dist/mazegen-*.whl .
	rm -rf dist
	@echo "Package ready: $$(ls mazegen-*.whl)"

install: $(PIP) build
	@echo "Installing dependencies..."
	$(PIP) install -r requirements.txt
	@echo "Installing generated wheel..."
	$(PIP) install ./mazegen-*.whl --force-reinstall
	@echo "Environment ready and linked to the wheel!"

run:
	$(PYTHON) $(MAIN_SCRIPT)

debug:
	$(PYTHON) -m pdb $(MAIN_SCRIPT)

lint:
	$(FLAKE8) . --exclude=$(EXCLUDE_DIRS)
	MYPYPATH=$(TYPINGS_DIR) $(MYPY) . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs --exclude "$(MYPY_EXCLUDE)"

lint-strict:
	$(FLAKE8) . --exclude=$(EXCLUDE_DIRS)
	MYPYPATH=$(TYPINGS_DIR) $(MYPY) . --strict --exclude "$(MYPY_EXCLUDE)"
