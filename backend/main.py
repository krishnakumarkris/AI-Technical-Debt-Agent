"""
Entry point to run the Phase 1 scanner standalone (no API layer yet).

Usage:
    python main.py
    python main.py path/to/other/project
"""

import sys
import json

from scanner.scanner_service import ScannerService


def main():
    project_path = sys.argv[1] if len(sys.argv) > 1 else "scanner/uploads/SampleProject"

    service = ScannerService()
    result = service.scan(project_path)

    print("\n===== SCAN SUMMARY =====")
    print(json.dumps(result["statistics"], indent=2, default=str))

    debt_report = result.get("debt_report")
    if debt_report:
        print("\n===== TECHNICAL DEBT SUMMARY =====")
        print(f"Total debt score: {debt_report['total_score']}")
        print(f"Issues by severity: {debt_report['severity_counts']}")
        print(f"Issues by rule: {debt_report['rule_counts']}")
        print("\nTop offenders (classes to refactor first):")
        for offender in debt_report["top_offenders"]:
            print(
                f"  - {offender['class_name']}: "
                f"score={offender['score']} ({offender['issue_count']} issue(s))"
            )

    dependency_report = result.get("dependency_report")
    if dependency_report:
        print("\n===== DEPENDENCY SCAN SUMMARY =====")
        print(f"Build tool: {dependency_report['build_tool']}")
        print(f"Dependencies found: {len(dependency_report['dependencies'])}")
        print(f"Detected frameworks: {dependency_report['detected_frameworks']}")
        if dependency_report["outdated_dependencies"]:
            print("Outdated / vulnerable dependencies:")
            for od in dependency_report["outdated_dependencies"]:
                print(
                    f"  - [{od['severity'].upper()}] {od['group']}:{od['artifact']} "
                    f"{od['current_version']} (needs >= {od['minimum_safe_version']}) "
                    f"- {od['reason']}"
                )
        if dependency_report["warnings"]:
            print("Warnings:")
            for w in dependency_report["warnings"]:
                print(f"  - {w}")

    print(f"\nFull result written to: {result.get('_output_file')}")


if __name__ == "__main__":
    main()
