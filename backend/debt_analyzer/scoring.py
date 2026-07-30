"""
Turns a flat list of DebtIssue objects into a scored DebtReport:
  - total_score: sum of severity weights across every issue
  - severity_counts / rule_counts: quick breakdowns for the dashboard
  - top_offenders: the classes with the highest cumulative debt score,
    i.e. "which classes should I refactor first" (Phase 5 question)
"""

from collections import defaultdict

from debt_analyzer.models import DebtReport, ClassScore
from debt_analyzer import thresholds


def score_report(project_name, issues, top_n=10):
    severity_counts = defaultdict(int)
    rule_counts = defaultdict(int)
    class_scores = defaultdict(int)
    class_issue_counts = defaultdict(int)

    total_score = 0

    for issue in issues:
        weight = thresholds.SEVERITY_WEIGHTS.get(issue.severity, 1)
        total_score += weight
        severity_counts[issue.severity] += 1
        rule_counts[issue.rule] += 1
        class_scores[issue.class_name] += weight
        class_issue_counts[issue.class_name] += 1

    top_offenders = sorted(
        (
            ClassScore(
                class_name=name,
                score=score,
                issue_count=class_issue_counts[name],
            )
            for name, score in class_scores.items()
        ),
        key=lambda c: c.score,
        reverse=True,
    )[:top_n]

    return DebtReport(
        project_name=project_name,
        issues=issues,
        total_score=total_score,
        severity_counts=dict(severity_counts),
        rule_counts=dict(rule_counts),
        top_offenders=top_offenders,
    )
