#!/usr/bin/env python3
"""
Autonomous System - Risk Scorer
Calculates risk score (0-100) for task safety assessment.
"""

import json
from typing import Dict, Any, Tuple
from enum import Enum


class RiskLevel(Enum):
    """Risk level categories."""
    LOW = "LOW"           # 0-30: auto-execute
    MEDIUM = "MEDIUM"     # 31-60: conditional execute (sandbox ≥90)
    HIGH = "HIGH"         # 61-85: human escalation
    CRITICAL = "CRITICAL" # 86-100: hard block


# Configurable weights (sum to 100)
RISK_WEIGHTS = {
    "external_action": 40,      # Email, API calls, external services
    "data_modification": 30,    # DB writes, file deletes
    "irreversibility": 20,      # Can't undo (payments, deletions)
    "financial_impact": 10      # Cost > $0
}


def calculate_risk_score(task: Dict[str, Any]) -> Tuple[int, RiskLevel, Dict[str, Any]]:
    """
    Calculate risk score for a task.

    Args:
        task: Task payload with action_type and details

    Returns:
        Tuple of (score, risk_level, breakdown)
    """

    action_type = task.get("action_type", "unknown")
    payload = task.get("payload", {})

    breakdown = {
        "external_action": 0,
        "data_modification": 0,
        "irreversibility": 0,
        "financial_impact": 0
    }

    # External action scoring
    external_actions = [
        "send_email", "api_call", "webhook", "slack_message",
        "http_post", "http_put", "http_delete", "external_service"
    ]
    if action_type in external_actions:
        breakdown["external_action"] = 100

    # Data modification scoring
    if action_type in ["write_db", "update_db", "delete_db"]:
        breakdown["data_modification"] = 100
    elif action_type in ["write_file", "delete_file"]:
        breakdown["data_modification"] = 70
    elif action_type in ["system_optimization", "file_migration", "bulk_operation"]:
        # System-level operations that modify many files
        breakdown["data_modification"] = 85
    elif action_type in ["execute_script", "run_command"]:
        # Scripts can do anything - assume high risk
        breakdown["data_modification"] = 80
    elif action_type in ["query_db", "read_file"]:
        breakdown["data_modification"] = 0  # Read-only

    # Irreversibility scoring
    irreversible_actions = [
        "delete_db", "delete_file", "send_email", "payment",
        "close_pr", "merge_pr", "deploy"
    ]
    if action_type in irreversible_actions:
        breakdown["irreversibility"] = 100
    elif action_type in ["system_optimization", "file_migration", "bulk_operation"]:
        # Bulk operations are hard to fully reverse
        breakdown["irreversibility"] = 70
    elif action_type in ["execute_script", "run_command"]:
        # Scripts may be irreversible
        breakdown["irreversibility"] = 60
    elif action_type in ["update_db", "write_file"]:
        # Partial irreversibility (can rollback but not perfectly)
        breakdown["irreversibility"] = 40

    # Financial impact scoring
    cost = payload.get("cost", 0)
    if cost > 0:
        if cost > 100:
            breakdown["financial_impact"] = 100
        elif cost > 10:
            breakdown["financial_impact"] = 70
        else:
            breakdown["financial_impact"] = 30

    # Calculate weighted score
    total_score = sum(
        breakdown[component] * RISK_WEIGHTS[component] / 100
        for component in breakdown
    )

    # Critical action boost (override to CRITICAL level)
    critical_actions = ["send_email", "payment", "delete_db", "deploy", "merge_pr"]
    if action_type in critical_actions:
        total_score = max(total_score, 86)  # Force CRITICAL threshold

    # Determine risk level
    if total_score <= 30:
        risk_level = RiskLevel.LOW
    elif total_score <= 60:
        risk_level = RiskLevel.MEDIUM
    elif total_score <= 85:
        risk_level = RiskLevel.HIGH
    else:
        risk_level = RiskLevel.CRITICAL

    return int(total_score), risk_level, breakdown


def explain_risk_score(task: Dict[str, Any]) -> str:
    """
    Generate human-readable explanation of risk score.

    Args:
        task: Task payload

    Returns:
        Formatted explanation string
    """

    score, level, breakdown = calculate_risk_score(task)

    lines = [
        f"Risk Score: {score}/100 ({level.value})",
        "\nBreakdown:"
    ]

    for component, value in breakdown.items():
        weight = RISK_WEIGHTS[component]
        contribution = value * weight / 100
        lines.append(
            f"  - {component}: {value}% × {weight}% weight = {contribution:.1f} points"
        )

    lines.append(f"\nRecommended Action:")
    if level == RiskLevel.LOW:
        lines.append("  → Auto-execute with sandbox validation")
    elif level == RiskLevel.MEDIUM:
        lines.append("  → Conditional execute (sandbox score ≥90 required)")
    elif level == RiskLevel.HIGH:
        lines.append("  → Human escalation required")
    else:
        lines.append("  → BLOCKED - Manual review mandatory")

    return "\n".join(lines)


# Test fixtures
TEST_TASKS = [
    {
        "name": "Simple DB Query",
        "task": {
            "action_type": "query_db",
            "payload": {"query": "SELECT COUNT(*) FROM entities"}
        },
        "expected_level": RiskLevel.LOW
    },
    {
        "name": "File Write (Workdir)",
        "task": {
            "action_type": "write_file",
            "payload": {"path": "/workdir/output.json", "content": "{}"}
        },
        "expected_level": RiskLevel.LOW  # Workdir write is safe
    },
    {
        "name": "DB Update",
        "task": {
            "action_type": "update_db",
            "payload": {"table": "entities", "updates": {"status": "active"}}
        },
        "expected_level": RiskLevel.MEDIUM
    },
    {
        "name": "Send Email",
        "task": {
            "action_type": "send_email",
            "payload": {"to": "test@example.com", "subject": "Test"}
        },
        "expected_level": RiskLevel.CRITICAL
    },
    {
        "name": "Delete Database Record",
        "task": {
            "action_type": "delete_db",
            "payload": {"table": "entities", "id": 123}
        },
        "expected_level": RiskLevel.CRITICAL
    },
    {
        "name": "System Optimization (Bulk File Operations)",
        "task": {
            "action_type": "system_optimization",
            "payload": {"commands": ["./scripts/migrate_root_files.sh"], "files_affected": 51}
        },
        "expected_level": RiskLevel.MEDIUM
    }
]


def run_tests():
    """Run test suite on sample tasks."""

    print("=" * 60)
    print("Risk Scorer Test Suite")
    print("=" * 60)

    passed = 0
    failed = 0

    for test_case in TEST_TASKS:
        print(f"\nTest: {test_case['name']}")
        print("-" * 60)

        score, level, breakdown = calculate_risk_score(test_case['task'])

        print(explain_risk_score(test_case['task']))

        if level == test_case['expected_level']:
            print(f"\n✓ PASS (expected {test_case['expected_level'].value})")
            passed += 1
        else:
            print(f"\n✗ FAIL (expected {test_case['expected_level'].value}, got {level.value})")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    import sys

    if "--test" in sys.argv:
        success = run_tests()
        sys.exit(0 if success else 1)
    elif "--score" in sys.argv:
        # Score a task from stdin or file
        task_json = sys.argv[sys.argv.index("--score") + 1] if len(sys.argv) > sys.argv.index("--score") + 1 else None

        if task_json:
            with open(task_json, "r") as f:
                task = json.load(f)
            print(explain_risk_score(task))
        else:
            print("Usage: risk_scorer.py --score <task.json>")
            sys.exit(1)
    else:
        print("Usage:")
        print("  risk_scorer.py --test              Run test suite")
        print("  risk_scorer.py --score <task.json> Score a specific task")
