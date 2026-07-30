"""
Data models for the technical-debt analyzer output.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional


@dataclass
class DebtIssue:
    rule: str                      # e.g. "LongMethod", "GodClass"
    severity: str                  # low | medium | high | critical
    class_name: str                # fully qualified class name
    file_path: str = ""
    method_name: Optional[str] = None
    line_number: int = 0
    message: str = ""
    suggestion: str = ""
    metric_value: Optional[float] = None
    metric_threshold: Optional[float] = None


@dataclass
class ClassScore:
    class_name: str
    score: int
    issue_count: int


@dataclass
class DebtReport:
    project_name: str
    issues: List[DebtIssue] = field(default_factory=list)
    total_score: int = 0
    severity_counts: dict = field(default_factory=dict)
    rule_counts: dict = field(default_factory=dict)
    top_offenders: List[ClassScore] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)
