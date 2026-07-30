"""
Central configuration for the scanner module.
Defines base paths used across the scanner package.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Directories that should never be scanned
IGNORE_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    "target",
    "build",
    "out",
    "__pycache__",
    "node_modules",
    "venv",
}
