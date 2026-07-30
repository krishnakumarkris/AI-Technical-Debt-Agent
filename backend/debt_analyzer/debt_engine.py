"""
Debt Engine
-----------
The single entry point for Phase 2 (Technical Debt Detection).

Given the ProjectModel produced by Phase 1's ProjectScanner, this:
  1. Builds an AnalysisContext (coupling metrics already computed by
     graph_builder, plus inheritance depth computed here from the
     "extends" edges already resolved by dependency_parser)
  2. Runs every registered rule against that context
  3. Scores the combined issues into a DebtReport

Usage:
    from debt_analyzer.debt_engine import DebtEngine
    report = DebtEngine().analyze(project_model)
"""

from debt_analyzer.rules.base_rule import AnalysisContext
from debt_analyzer.rules.long_method import LongMethodRule
from debt_analyzer.rules.long_parameter_list import LongParameterListRule
from debt_analyzer.rules.god_class import GodClassRule
from debt_analyzer.rules.large_class import LargeClassRule
from debt_analyzer.rules.high_coupling import HighCouplingRule
from debt_analyzer.rules.deep_inheritance import DeepInheritanceRule
from debt_analyzer.rules.duplicate_code import DuplicateCodeRule
from debt_analyzer.scoring import score_report
from scanner.utils.logger import logger


DEFAULT_RULES = [
    LongMethodRule(),
    LongParameterListRule(),
    GodClassRule(),
    LargeClassRule(),
    HighCouplingRule(),
    DeepInheritanceRule(),
    DuplicateCodeRule(),
]


def _compute_inheritance_depth(project):
    """
    Depth-of-Inheritance-Tree (DIT), computed only from "extends" edges that
    were already resolved against project classes by dependency_parser.py.
    External/library base classes are treated as depth 0 (we can't see how
    deep they go, and it's not actionable debt on this codebase anyway).
    """
    parent_map = {}
    for edge in project.dependencies:
        if edge.get("type") == "extends" and edge["from"] not in parent_map:
            parent_map[edge["from"]] = edge["to"]

    depth_cache = {}

    def depth_of(fqn, visited):
        if fqn in depth_cache:
            return depth_cache[fqn]
        parent = parent_map.get(fqn)
        if not parent or parent in visited:
            depth_cache[fqn] = 0
            return 0
        result = 1 + depth_of(parent, visited | {fqn})
        depth_cache[fqn] = result
        return result

    all_fqns = {c.fully_qualified_name for c in project.classes}
    return {fqn: depth_of(fqn, frozenset()) for fqn in all_fqns}


class DebtEngine:
    def __init__(self, rules=None):
        self.rules = rules if rules is not None else DEFAULT_RULES

    def analyze(self, project):
        coupling_metrics = (
            project.statistics.get("graph", {}).get("coupling_metrics", {})
        )
        inheritance_depth = _compute_inheritance_depth(project)

        context = AnalysisContext(
            project=project,
            coupling_metrics=coupling_metrics,
            inheritance_depth=inheritance_depth,
        )

        all_issues = []
        for rule in self.rules:
            rule_issues = rule.analyze(context)
            logger.info(f"{rule.name}: {len(rule_issues)} issue(s) found")
            all_issues.extend(rule_issues)

        report = score_report(project.project_name, all_issues)
        logger.info(
            f"Debt analysis complete: {len(all_issues)} total issues, "
            f"score={report.total_score}"
        )
        return report
