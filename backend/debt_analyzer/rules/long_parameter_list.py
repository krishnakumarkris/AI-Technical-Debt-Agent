"""
Long Parameter List
--------------------
Methods with many parameters are hard to call correctly and usually signal
that a group of parameters should be its own object (Introduce Parameter
Object / Preserve Whole Object).
"""

from debt_analyzer.rules.base_rule import BaseRule
from debt_analyzer.models import DebtIssue
from debt_analyzer import thresholds


class LongParameterListRule(BaseRule):
    name = "LongParameterList"

    def analyze(self, context):
        issues = []
        for cls in context.project.classes:
            for method in cls.methods:
                count = len(method.parameters)
                if count > thresholds.LONG_PARAMETER_LIST:
                    param_names = ", ".join(p.name for p in method.parameters)
                    issues.append(
                        DebtIssue(
                            rule=self.name,
                            severity="medium",
                            class_name=cls.fully_qualified_name,
                            file_path=cls.file_path,
                            method_name=method.name,
                            line_number=method.line_number,
                            message=(
                                f"Method '{method.name}' takes {count} parameters "
                                f"({param_names}); threshold is {thresholds.LONG_PARAMETER_LIST}."
                            ),
                            suggestion=(
                                "Group related parameters into a single object "
                                "(Introduce Parameter Object) to simplify the signature."
                            ),
                            metric_value=count,
                            metric_threshold=thresholds.LONG_PARAMETER_LIST,
                        )
                    )
        return issues
