"""
File-system helpers for the scanner: discovering .java files while
skipping build artifacts / IDE folders / VCS folders.
"""

from pathlib import Path
from scanner.config import IGNORE_DIRS


def get_java_files(project_path):
    """
    Recursively find all .java files under project_path,
    skipping any path that contains an ignored directory name.
    Returns a list of pathlib.Path objects.
    """
    java_files = []
    root = Path(project_path)

    if not root.exists():
        raise FileNotFoundError(f"Project path does not exist: {project_path}")

    for file in root.rglob("*.java"):
        if any(part in IGNORE_DIRS for part in file.parts):
            continue
        java_files.append(file)

    return java_files


def read_source(file_path):
    """
    Read a Java source file safely, tolerating odd encodings.
    """
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()
