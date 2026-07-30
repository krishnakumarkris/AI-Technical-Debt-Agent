"""
Dependency Scanner Service
--------------------------
Entry point for Phase 2. Given a project root, detects whether it's a
Maven or Gradle project, runs the appropriate parser, then enriches the
result with:
  - detected frameworks (framework_signatures.py)
  - outdated/vulnerable dependency flags (vulnerability_data.py)

Usage:
    from dependency_scanner.dependency_scanner_service import DependencyScannerService
    report = DependencyScannerService().scan("path/to/project")
"""

from pathlib import Path

from dependency_scanner.models import DependencyReport, OutdatedDependency
from dependency_scanner.maven_parser import parse_pom
from dependency_scanner.gradle_parser import parse_gradle
from dependency_scanner.framework_signatures import detect_frameworks
from dependency_scanner.vulnerability_data import (
    KNOWN_MINIMUM_SAFE_VERSIONS,
    is_version_below,
)
from scanner.utils.logger import logger


def _find_build_file(project_path, filenames):
    """
    Look for the first matching build file, preferring the project root over
    nested modules (shallowest path wins).
    """
    root = Path(project_path)
    candidates = []
    for filename in filenames:
        candidates.extend(root.rglob(filename))
    if not candidates:
        return None
    return min(candidates, key=lambda p: len(p.parts))


def _check_outdated(dependencies):
    outdated = []
    for dep in dependencies:
        rule = KNOWN_MINIMUM_SAFE_VERSIONS.get(dep.artifact)
        if not rule:
            continue
        if dep.version == "unspecified":
            continue
        if is_version_below(dep.version, rule["minimum_safe_version"]):
            outdated.append(
                OutdatedDependency(
                    group=dep.group,
                    artifact=dep.artifact,
                    current_version=dep.version,
                    minimum_safe_version=rule["minimum_safe_version"],
                    reason=rule["reason"],
                    severity=rule["severity"],
                )
            )
    return outdated


class DependencyScannerService:
    def scan(self, project_path):
        pom_path = _find_build_file(project_path, ["pom.xml"])
        gradle_path = _find_build_file(
            project_path, ["build.gradle", "build.gradle.kts"]
        )

        if pom_path:
            logger.info(f"Maven project detected: {pom_path}")
            dependencies, plugins, warnings = parse_pom(pom_path)
            build_tool = "maven"
        elif gradle_path:
            logger.info(f"Gradle project detected: {gradle_path}")
            dependencies, plugins, warnings = parse_gradle(gradle_path)
            build_tool = "gradle"
        else:
            logger.warning("No pom.xml or build.gradle found in project.")
            return DependencyReport(
                build_tool="unknown",
                project_path=str(project_path),
                warnings=["No pom.xml or build.gradle(.kts) found in project."],
            )

        frameworks = detect_frameworks(dependencies)
        outdated = _check_outdated(dependencies)

        if outdated:
            logger.warning(f"{len(outdated)} outdated/vulnerable dependency(ies) found")

        return DependencyReport(
            build_tool=build_tool,
            project_path=str(project_path),
            dependencies=dependencies,
            plugins=plugins,
            detected_frameworks=frameworks,
            outdated_dependencies=outdated,
            warnings=warnings,
        )
