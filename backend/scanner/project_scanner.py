"""
Project Scanner
----------------
The orchestrator for Phase 1. Given a project directory, it:

  1. Discovers every .java file (utils/file_utils.py)
  2. Parses each one into ClassModel objects (java_parser/java_ast_parser.py)
  3. Resolves internal class-to-class dependencies (dependency_parser.py)
  4. Builds a dependency graph + coupling metrics (graph_builder.py)
  5. Packages everything into a single ProjectModel

This replaces the earlier skeleton version, which only counted files.
"""

import time
from pathlib import Path

from scanner.utils.file_utils import get_java_files
from scanner.utils.logger import logger
from scanner.java_parser.java_ast_parser import parse_java_file
from scanner.dependency_parser import build_dependency_edges
from scanner.graph_builder import build_and_analyze
from scanner.models.project_model import ProjectModel, FileParseError


class ProjectScanner:
    def __init__(self, project_path):
        self.project_path = Path(project_path)

    def scan(self):
        start_time = time.time()
        project_name = self.project_path.name

        logger.info(f"Scanning project: {self.project_path}")

        java_files = get_java_files(self.project_path)
        logger.info(f"Java files found: {len(java_files)}")

        project = ProjectModel(
            project_name=project_name,
            project_path=str(self.project_path),
        )

        for file_path in java_files:
            classes, error = parse_java_file(file_path)

            if error:
                project.errors.append(
                    FileParseError(file_path=str(file_path), error=error)
                )
                continue

            project.classes.extend(classes)

        logger.info(f"Classes parsed: {len(project.classes)}")

        # Dependency resolution + graph metrics only make sense once we know
        # about every class in the project, so this runs after the full loop.
        edges = build_dependency_edges(project.classes)
        project.dependencies = edges

        graph_stats = build_and_analyze(project.classes, edges)

        elapsed = round(time.time() - start_time, 3)

        project.statistics = {
            "total_files": len(java_files),
            "parsed_files": len(java_files) - len(project.errors),
            "failed_files": len(project.errors),
            "total_classes": len(
                [c for c in project.classes if c.class_type == "class"]
            ),
            "total_interfaces": len(
                [c for c in project.classes if c.class_type == "interface"]
            ),
            "total_enums": len(
                [c for c in project.classes if c.class_type == "enum"]
            ),
            "total_methods": sum(len(c.methods) for c in project.classes),
            "total_fields": sum(len(c.fields) for c in project.classes),
            "dependency_edges": len(edges),
            "circular_dependencies": len(graph_stats["circular_dependencies"]),
            "scan_time_seconds": elapsed,
            "graph": graph_stats,
        }

        logger.info(f"Scan complete in {elapsed}s")
        return project
