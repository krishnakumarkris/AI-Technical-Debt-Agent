"""
Data models for Phase 2 - the Dependency Scanner.

Distinct from scanner/models/project_model.py (which describes YOUR code),
these describe the EXTERNAL libraries your project pulls in.
"""

from dataclasses import dataclass, field, asdict
from typing import List


@dataclass
class DependencyModel:
    group: str
    artifact: str
    version: str
    scope: str = "compile"          # compile | test | provided | runtime ...
    source_file: str = ""


@dataclass
class PluginModel:
    name: str
    version: str = ""


@dataclass
class OutdatedDependency:
    group: str
    artifact: str
    current_version: str
    minimum_safe_version: str
    reason: str                     # e.g. CVE id / advisory text
    severity: str = "high"


@dataclass
class DependencyReport:
    build_tool: str                 # maven | gradle | unknown
    project_path: str
    dependencies: List[DependencyModel] = field(default_factory=list)
    plugins: List[PluginModel] = field(default_factory=list)
    detected_frameworks: List[str] = field(default_factory=list)
    outdated_dependencies: List[OutdatedDependency] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)
