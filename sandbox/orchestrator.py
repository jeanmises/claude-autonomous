#!/usr/bin/env python3
"""
Autonomous System - Sandbox Orchestrator
Coordinates sandbox execution with automatic fix iterations.
"""

import time
from typing import Dict, Any, Tuple
from pathlib import Path

from executor import SandboxExecutor
from score_calculator import ScoreCalculator
from fix_generator import FixGenerator


class SandboxOrchestrator:
    """Orchestrates sandbox testing with automatic fix iterations."""

    def __init__(
        self,
        task: Dict[str, Any],
        max_iterations: int = 5,
        target_score: int = 95
    ):
        self.task = task
        self.max_iterations = max_iterations
        self.target_score = target_score
        self.iteration_history = []

    def run(self) -> Tuple[bool, int, Dict[str, Any]]:
        """
        Run sandbox test with automatic fix iterations.

        Returns:
            Tuple of (success, final_score, results)
        """

        print(f"=== Sandbox Orchestrator ===")
        print(f"Task: {self.task.get('task_id')}")
        print(f"Action: {self.task.get('action_type')}")
        print(f"Target Score: {self.target_score}/100")
        print(f"Max Iterations: {self.max_iterations}")
        print()

        current_task = self.task.copy()
        best_score = 0
        best_result = None

        for iteration in range(1, self.max_iterations + 1):
            print(f"--- Iteration {iteration}/{self.max_iterations} ---")

            # Execute in sandbox
            executor = SandboxExecutor(current_task)

            if not executor.create_environment():
                print("✗ Failed to create sandbox environment")
                break

            start_time = time.time()
            success, result, error = executor.execute_task(iteration)
            execution_time = time.time() - start_time

            # Calculate score
            calculator = ScoreCalculator(current_task)
            score, breakdown = calculator.calculate_score(
                success,
                result,
                error,
                execution_time
            )

            print(f"Execution: {'SUCCESS' if success else 'FAILED'}")
            print(f"Score: {score}/100")
            if error:
                print(f"Error: {error}")

            # Record iteration
            iteration_record = {
                "iteration": iteration,
                "success": success,
                "score": score,
                "breakdown": breakdown,
                "error": error,
                "result": result,
                "execution_time": execution_time
            }
            self.iteration_history.append(iteration_record)

            # Track best result
            if score > best_score:
                best_score = score
                best_result = iteration_record

            # Cleanup sandbox
            executor.cleanup(keep_on_failure=(not success))

            # Check if target reached
            if score >= self.target_score:
                print(f"\n✓ Target score reached ({score} >= {self.target_score})")
                return True, score, best_result

            # Try to generate fix if not last iteration
            if iteration < self.max_iterations and not success:
                print(f"\nGenerating fix for iteration {iteration + 1}...")
                generator = FixGenerator(current_task)
                fixed_task = generator.generate_fix(error, iteration, self.iteration_history)

                if fixed_task:
                    current_task = fixed_task
                    print(f"✓ Fix applied: {fixed_task['fix_metadata']['fix_type']}")
                else:
                    print("✗ No fix available - task unfixable")
                    break
            elif iteration < self.max_iterations:
                # Success but score below target - harder to fix
                print(f"\n⚠ Task succeeded but score {score} below target {self.target_score}")
                print("  (Difficult to improve without more context)")
                break

            print()

        # Final result
        print(f"=== Final Result ===")
        print(f"Best Score: {best_score}/100")
        print(f"Iterations: {len(self.iteration_history)}")
        print(f"Target Reached: {'YES' if best_score >= self.target_score else 'NO'}")

        return best_score >= self.target_score, best_score, best_result


# CLI test
if __name__ == "__main__":
    import sys

    # Test 1: Task that succeeds immediately
    print("=" * 60)
    print("TEST 1: Task that succeeds immediately")
    print("=" * 60)

    test_task_1 = {
        "task_id": "test_success",
        "action_type": "query_db",
        "payload": {
            "query": "SELECT COUNT(*) FROM entities",
            "expected_result": "integer"
        }
    }

    orchestrator = SandboxOrchestrator(test_task_1, max_iterations=3, target_score=95)
    success, score, result = orchestrator.run()

    print(f"\n{'✓' if success else '✗'} Test 1: {'PASS' if success else 'FAIL'}")
    print()

    # Test 2: Task that fails initially but can be fixed
    print("=" * 60)
    print("TEST 2: Task with fixable error")
    print("=" * 60)

    test_task_2 = {
        "task_id": "test_fixable",
        "action_type": "query_db",
        "payload": {
            "query": "SELECT COUNT(*) FROM entities;;",  # Syntax error
            "expected_result": "integer"
        }
    }

    orchestrator2 = SandboxOrchestrator(test_task_2, max_iterations=3, target_score=95)
    success2, score2, result2 = orchestrator2.run()

    print(f"\n{'✓' if success2 else '✗'} Test 2: {'PASS' if success2 else 'FAIL'}")
    print()

    # Test 3: Task that fails with unfixable error
    print("=" * 60)
    print("TEST 3: Task with unfixable error")
    print("=" * 60)

    test_task_3 = {
        "task_id": "test_unfixable",
        "action_type": "write_file",
        "payload": {
            "file_path": "/root/forbidden.txt",  # Permission denied
            "content": "test"
        }
    }

    orchestrator3 = SandboxOrchestrator(test_task_3, max_iterations=3, target_score=95)
    success3, score3, result3 = orchestrator3.run()

    print(f"\n{'✓' if not success3 else '✗'} Test 3: {'PASS (correctly failed)' if not success3 else 'FAIL (should have failed)'}")
    print()

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Test 1 (Success): {'✓ PASS' if success else '✗ FAIL'}")
    print(f"Test 2 (Fixable): {'✓ PASS' if success2 else '✗ FAIL'}")
    print(f"Test 3 (Unfixable): {'✓ PASS' if not success3 else '✗ FAIL'}")

    all_passed = success and success2 and not success3
    print(f"\nOverall: {'✓ ALL PASS' if all_passed else '✗ SOME FAILED'}")

    sys.exit(0 if all_passed else 1)
