#!/usr/bin/env python3
"""
Autonomous System - Decision Router
Routes tasks based on risk level and permission profile.
"""

import json
from pathlib import Path
from typing import Dict, Any, Tuple
from enum import Enum

from risk_scorer import calculate_risk_score, RiskLevel


class ActionType(Enum):
    """Decision actions."""
    AUTO_EXECUTE = "auto_execute"
    CONDITIONAL_EXECUTE = "conditional_execute"
    ESCALATE_HUMAN = "escalate_human"
    BLOCK = "block"


PROFILES_DIR = Path(__file__).parent / "profiles"


def load_profile(profile_name: str = "autonomous") -> Dict[str, Any]:
    """Load permission profile configuration."""

    profile_path = PROFILES_DIR / f"{profile_name}.json"

    if not profile_path.exists():
        raise FileNotFoundError(f"Profile not found: {profile_path}")

    with open(profile_path, "r") as f:
        return json.load(f)


def make_decision(
    task: Dict[str, Any],
    profile_name: str = "autonomous",
    sandbox_score: int = None
) -> Tuple[ActionType, Dict[str, Any]]:
    """
    Make routing decision for a task.

    Args:
        task: Task payload
        profile_name: Permission profile to use
        sandbox_score: Optional pre-calculated sandbox score

    Returns:
        Tuple of (action, decision_metadata)
    """

    # Calculate risk
    risk_score, risk_level, breakdown = calculate_risk_score(task)

    # Load profile rules
    profile = load_profile(profile_name)
    rules = profile["rules"]

    # Get rule for risk level
    rule = rules.get(risk_level.value)
    if not rule:
        raise ValueError(f"No rule defined for risk level: {risk_level.value}")

    # Determine action
    action_str = rule["action"]
    action = ActionType(action_str)

    # Build decision metadata
    decision = {
        "action": action.value,
        "risk_score": risk_score,
        "risk_level": risk_level.value,
        "risk_breakdown": breakdown,
        "rule": rule,
        "requires_sandbox": rule.get("require_sandbox", False),
        "sandbox_threshold": rule.get("sandbox_threshold", 95),
        "notification_timing": rule.get("notification", "post_execution")
    }

    # Check conditional execution requirements
    if action == ActionType.CONDITIONAL_EXECUTE:
        conditions = rule.get("conditions", [])
        conditions_met = []

        for condition in conditions:
            if condition == "sandbox_test_passed":
                # Will be checked later in workflow
                conditions_met.append(True)
            elif condition.startswith("score_above_threshold:"):
                threshold = int(condition.split(":")[1])
                if sandbox_score is not None:
                    met = sandbox_score >= threshold
                    conditions_met.append(met)
                    decision["sandbox_score"] = sandbox_score
                    decision["sandbox_threshold_met"] = met
                else:
                    # Sandbox not yet run
                    conditions_met.append(None)

        decision["conditions"] = conditions
        decision["conditions_met"] = conditions_met

        # If sandbox score provided and doesn't meet threshold, escalate
        if sandbox_score is not None and not all(conditions_met):
            action = ActionType.ESCALATE_HUMAN
            decision["action"] = action.value
            decision["escalation_reason"] = f"Sandbox score {sandbox_score} below threshold {rule['sandbox_threshold']}"

    return action, decision


def explain_decision(task: Dict[str, Any], profile_name: str = "autonomous") -> str:
    """Generate human-readable explanation of routing decision."""

    action, decision = make_decision(task, profile_name)

    lines = [
        f"Task: {task.get('action_type', 'unknown')}",
        f"Risk Score: {decision['risk_score']}/100 ({decision['risk_level']})",
        f"\nDecision: {action.value.upper().replace('_', ' ')}",
        f"\nRule: {decision['rule']['description']}"
    ]

    if decision["requires_sandbox"]:
        lines.append(f"\nSandbox Required: YES (threshold: {decision['sandbox_threshold']}/100)")

    if action == ActionType.CONDITIONAL_EXECUTE:
        lines.append(f"\nConditions:")
        for condition in decision["conditions"]:
            lines.append(f"  - {condition}")

    lines.append(f"\nNotification: {decision['notification_timing']}")

    return "\n".join(lines)


# Test cases
TEST_SCENARIOS = [
    {
        "name": "LOW risk - DB Query",
        "task": {"action_type": "query_db", "payload": {}},
        "expected_action": ActionType.AUTO_EXECUTE
    },
    {
        "name": "MEDIUM risk - DB Update (sandbox pass)",
        "task": {"action_type": "update_db", "payload": {}},
        "sandbox_score": 92,
        "expected_action": ActionType.CONDITIONAL_EXECUTE  # Stays conditional (threshold met)
    },
    {
        "name": "MEDIUM risk - DB Update (sandbox fail)",
        "task": {"action_type": "update_db", "payload": {}},
        "sandbox_score": 85,
        "expected_action": ActionType.ESCALATE_HUMAN  # Below threshold
    },
    {
        "name": "CRITICAL risk - Send Email",
        "task": {"action_type": "send_email", "payload": {}},
        "expected_action": ActionType.BLOCK
    }
]


def run_tests():
    """Run test suite on decision scenarios."""

    print("=" * 60)
    print("Decision Router Test Suite")
    print("=" * 60)

    passed = 0
    failed = 0

    for test_case in TEST_SCENARIOS:
        print(f"\nTest: {test_case['name']}")
        print("-" * 60)

        sandbox_score = test_case.get("sandbox_score")
        action, decision = make_decision(
            test_case['task'],
            sandbox_score=sandbox_score
        )

        print(explain_decision(test_case['task']))

        if sandbox_score:
            print(f"\nSandbox Score: {sandbox_score}/100")
            if decision.get("sandbox_threshold_met") is not None:
                status = "MET" if decision["sandbox_threshold_met"] else "NOT MET"
                print(f"Threshold {decision['sandbox_threshold']}: {status}")

        if action == test_case['expected_action']:
            print(f"\n✓ PASS")
            passed += 1
        else:
            print(f"\n✗ FAIL (expected {test_case['expected_action'].value}, got {action.value})")
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
    elif "--decide" in sys.argv:
        # Make decision for a task from stdin or file
        task_json = sys.argv[sys.argv.index("--decide") + 1] if len(sys.argv) > sys.argv.index("--decide") + 1 else None

        if task_json:
            with open(task_json, "r") as f:
                task = json.load(f)
            print(explain_decision(task))
        else:
            print("Usage: decision_engine.py --decide <task.json>")
            sys.exit(1)
    else:
        print("Usage:")
        print("  decision_engine.py --test               Run test suite")
        print("  decision_engine.py --decide <task.json> Make decision for task")
