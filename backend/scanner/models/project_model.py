"""
Data models that represent a scanned Java project.

These are plain dataclasses (no ORM / pydantic dependency) so they can be
used directly inside the scanner, and converted to plain dicts (via
`to_dict()`) whenever they need to be returned from a FastAPI endpoint or
written to disk as JSON.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List


@dataclass
class ParameterModel:
    name: str
    datatype: str


@dataclass
class MethodModel:
    name: str
    return_type: str
    parameters: List[ParameterModel] = field(default_factory=list)
    modifiers: List[str] = field(default_factory=list)
    annotations: List[str] = field(default_factory=list)
    line_number: int = 0
    line_count: int = 0          # approximate method length -> useful for "long method" smell
    is_constructor: bool = False
    non_blank_lines: int = 0     # line_count minus blanks/comments -> used for duplicate detection
    body_hash: str = ""          # hash of normalized body text -> used for duplicate detection
    cyclomatic_complexity: int = 1
    max_nesting_depth: int = 0
    empty_catch_lines: List[int] = field(default_factory=list)
    magic_numbers: List[dict] = field(default_factory=list)
    unused_local_vars: List[dict] = field(default_factory=list)
    string_concat_in_loop_line: int = 0
    unclosed_resource_lines: List[int] = field(default_factory=list)
    catches_generic_exception_line: int = 0
    method_calls: List[str] = field(default_factory=list)
    external_type_accesses: Dict[str, int] = field(default_factory=dict)
    parameter_type_accesses: Dict[str, int] = field(default_factory=dict)
    has_javadoc: bool = True
    hardcoded_credential_lines: List[dict] = field(default_factory=list)


@dataclass
class FieldModel:
    name: str
    datatype: str
    modifiers: List[str] = field(default_factory=list)
    line_number: int = 0


@dataclass
class ClassModel:
    name: str
    package: str
    file_path: str
    class_type: str = "class"          # class | interface | enum | record
    modifiers: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    fields: List[FieldModel] = field(default_factory=list)
    methods: List[MethodModel] = field(default_factory=list)
    extends: str = ""
    implements: List[str] = field(default_factory=list)
    annotations: List[str] = field(default_factory=list)
    line_count: int = 0
    mutable_static_fields: List[dict] = field(default_factory=list)

    @property
    def fully_qualified_name(self):
        return f"{self.package}.{self.name}" if self.package else self.name


@dataclass
class FileParseError:
    file_path: str
    error: str


@dataclass
class ProjectModel:
    project_name: str
    project_path: str
    classes: List[ClassModel] = field(default_factory=list)
    dependencies: List[dict] = field(default_factory=list)   # edges: {"from": fqn, "to": fqn}
    errors: List[FileParseError] = field(default_factory=list)
    statistics: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)
