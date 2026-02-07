#!/usr/bin/env python3
"""
Autonomous System - Score Calculator
Calculates validation score (0-100) for sandbox task execution.
"""

from typing import Dict, Any, Tuple
from pathlib import Path
import json


class ScoreCalculator:
    """Calculates comprehensive score for task execution."""

    # Scoring weights (sum to 100)
    WEIGHTS = {
        "execution_success": 40,    # Task completed without errors
        "output_validity": 30,      # Output matches expected format/type
        "side_effects_clean": 20,   # No unexpected side effects
        "performance": 10           # Execution time within bounds
    }

    def __init__(self, task: Dict[str, Any]):
        self.task = task
        self.action_type = task.get("action_type")
        self.payload = task.get("payload", {})

    def calculate_score(
        self,
        success: bool,
        result: Any,
        error: str,
        execution_time: float,
        side_effects: Dict[str, Any] = None
    ) -> Tuple[int, Dict[str, Any]]:
        """
        Calculate overall score for task execution.

        Args:
            success: Whether task executed without exceptions
            result: Task execution result
            error: Error message if failed
            execution_time: Time taken (seconds)
            side_effects: Dict of detected side effects

        Returns:
            Tuple of (score, breakdown)
        """

        breakdown = {}
        side_effects = side_effects or {}

        # Component 1: Execution Success (40 points)
        if success:
            breakdown["execution_success"] = 100
        else:
            # Partial credit for known/recoverable errors
            if error and "syntax" in error.lower():
                breakdown["execution_success"] = 20  # Syntax error - easily fixable
            elif error and "permission" in error.lower():
                breakdown["execution_success"] = 0   # Permission error - not fixable
            else:
                breakdown["execution_success"] = 30  # Other errors - might be fixable

        # Component 2: Output Validity (30 points)
        breakdown["output_validity"] = self._score_output_validity(success, result)

        # Component 3: Side Effects Clean (20 points)
        breakdown["side_effects_clean"] = self._score_side_effects(side_effects)

        # Component 4: Performance (10 points)
        breakdown["performance"] = self._score_performance(execution_time)

        # Calculate weighted total
        total_score = sum(
            breakdown[component] * self.WEIGHTS[component] / 100
            for component in self.WEIGHTS
        )

        return int(total_score), breakdown

    def _score_output_validity(self, success: bool, result: Any) -> int:
        """Score output validity based on expected result type."""

        if not success:
            return 0

        expected_type = self.payload.get("expected_result")

        # No expectation defined - assume valid if no error
        if not expected_type:
            return result is not None and 80 or 60

        # Check type matching
        if expected_type == "integer":
            if isinstance(result, int):
                return 100
            elif isinstance(result, (list, tuple)) and len(result) > 0:
                # DB query result: [(count,)]
                if isinstance(result[0], (list, tuple)) and len(result[0]) > 0:
                    if isinstance(result[0][0], int):
                        return 100
                return 70
            return 40

        elif expected_type == "list":
            if isinstance(result, list):
                return 100
            return 50

        elif expected_type == "dict":
            if isinstance(result, dict):
                return 100
            return 50

        elif expected_type == "string":
            if isinstance(result, str):
                return 100
            return 50

        elif expected_type == "boolean":
            if isinstance(result, bool):
                return 100
            return 50

        # Unknown expected type
        return 70

    def _score_side_effects(self, side_effects: Dict[str, Any]) -> int:
        """Score side effects cleanliness."""

        if not side_effects:
            return 100  # No side effects detected

        # Count negative side effects
        negative_effects = 0

        if side_effects.get("unexpected_files_created", 0) > 0:
            negative_effects += 1

        if side_effects.get("unexpected_db_changes", False):
            negative_effects += 1

        if side_effects.get("resource_leaks", 0) > 0:
            negative_effects += 1

        if side_effects.get("permission_violations", False):
            negative_effects += 2  # More severe

        # Score based on severity
        if negative_effects == 0:
            return 100
        elif negative_effects == 1:
            return 70
        elif negative_effects == 2:
            return 40
        else:
            return 10

    def _score_performance(self, execution_time: float) -> int:
        """Score performance based on execution time."""

        # Expected time limits by action type
        time_limits = {
            "query_db": 1.0,        # 1 second
            "update_db": 2.0,       # 2 seconds
            "read_file": 0.5,       # 0.5 seconds
            "write_file": 1.0,      # 1 second
            "execute_script": 10.0, # 10 seconds
            "system_optimization": 30.0  # 30 seconds
        }

        limit = time_limits.get(self.action_type, 5.0)

        if execution_time <= limit:
            return 100
        elif execution_time <= limit * 2:
            return 70
        elif execution_time <= limit * 5:
            return 40
        else:
            return 10

    def explain_score(
        self,
        score: int,
        breakdown: Dict[str, int]
    ) -> str:
        """Generate human-readable explanation of score."""

        lines = [
            f"Overall Score: {score}/100",
            "\nBreakdown:"
        ]

        for component, value in breakdown.items():
            weight = self.WEIGHTS[component]
            contribution = value * weight / 100
            lines.append(
                f"  - {component}: {value}% × {weight}% weight = {contribution:.1f} points"
            )

        # Score interpretation
        lines.append("\nInterpretation:")
        if score >= 95:
            lines.append("  ✓ EXCELLENT - Ready for production execution")
        elif score >= 90:
            lines.append("  ✓ GOOD - Acceptable for auto-execution (MEDIUM risk threshold)")
        elif score >= 75:
            lines.append("  ⚠ FAIR - Needs improvement, escalate to human")
        elif score >= 50:
            lines.append("  ⚠ POOR - Significant issues, manual review required")
        else:
            lines.append("  ✗ FAILED - Critical issues, do not execute")

        return "\n".join(lines)


# Test cases
def run_tests():
    """Test score calculator with various scenarios."""

    print("=" * 60)
    print("Score Calculator Test Suite")
    print("=" * 60)

    test_cases = [
        {
            "name": "Perfect Execution",
            "task": {
                "action_type": "query_db",
                "payload": {"expected_result": "integer"}
            },
            "success": True,
            "result": [(42,)],
            "error": "",
            "execution_time": 0.1,
            "expected_score_min": 95
        },
        {
            "name": "Good Execution (Slow)",
            "task": {
                "action_type": "query_db",
                "payload": {"expected_result": "integer"}
            },
            "success": True,
            "result": [(42,)],
            "error": "",
            "execution_time": 1.5,  # Slightly over limit
            "expected_score_min": 85
        },
        {
            "name": "Syntax Error",
            "task": {
                "action_type": "query_db",
                "payload": {}
            },
            "success": False,
            "result": None,
            "error": "Syntax error in SQL",
            "execution_time": 0.0,
            "expected_score_min": 0,
            "expected_score_max": 40
        },
        {
            "name": "Success with Side Effects",
            "task": {
                "action_type": "write_file",
                "payload": {}
            },
            "success": True,
            "result": {"bytes_written": 100},
            "error": "",
            "execution_time": 0.2,
            "side_effects": {"unexpected_files_created": 1},
            "expected_score_min": 70,
            "expected_score_max": 90  # Adjusted - side effects not too severe
        }
    ]

    passed = 0
    failed = 0

    for test_case in test_cases:
        print(f"\nTest: {test_case['name']}")
        print("-" * 60)

        calculator = ScoreCalculator(test_case["task"])
        score, breakdown = calculator.calculate_score(
            test_case["success"],
            test_case["result"],
            test_case["error"],
            test_case["execution_time"],
            test_case.get("side_effects")
        )

        print(calculator.explain_score(score, breakdown))

        # Validate score
        expected_min = test_case.get("expected_score_min", 0)
        expected_max = test_case.get("expected_score_max", 100)

        if expected_min <= score <= expected_max:
            print(f"\n✓ PASS (score {score} in expected range {expected_min}-{expected_max})")
            passed += 1
        else:
            print(f"\n✗ FAIL (score {score}, expected {expected_min}-{expected_max})")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
