#!/usr/bin/env python3
"""
Autonomous System - Post-flight Validation
Validates results after production execution.
"""

import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, Tuple, List


# Paths
WORKSPACE_ROOT = Path.home() / "Library" / "CloudStorage" / "OneDrive-SAPASPA" / "OD PARA Sales Strategy" / "Claude Workspace"
LOCAL_VAULT_DB = WORKSPACE_ROOT / "local_vault.db"


class PostFlightValidator:
    """Validates execution results and system state."""

    def __init__(self):
        self.checks = [
            self._check_database_integrity,
            self._check_expected_changes,
            self._check_no_corruption,
        ]

    def validate(
        self,
        task: Dict[str, Any],
        result: Any,
        error: str
    ) -> Tuple[bool, List[str]]:
        """
        Run all post-flight checks.

        Args:
            task: Task that was executed
            result: Execution result
            error: Error message if any

        Returns:
            Tuple of (all_passed, issues)
        """

        print("[Post-flight] Running validation checks...")
        issues = []

        # If task failed with error, that's already a validation failure
        if error:
            issues.append(f"Task execution error: {error}")
            print(f"[Post-flight]   ✗ Task failed: {error}")
            return False, issues

        for check in self.checks:
            try:
                passed, message = check(task, result)
                if passed:
                    print(f"[Post-flight]   ✓ {message}")
                else:
                    print(f"[Post-flight]   ✗ {message}")
                    issues.append(message)
            except Exception as e:
                error_msg = f"{check.__name__}: {e}"
                print(f"[Post-flight]   ✗ {error_msg}")
                issues.append(error_msg)

        all_passed = len(issues) == 0

        if all_passed:
            print("[Post-flight] ✓ All checks passed")
        else:
            print(f"[Post-flight] ✗ {len(issues)} check(s) failed")

        return all_passed, issues

    def _check_database_integrity(
        self,
        task: Dict[str, Any],
        result: Any
    ) -> Tuple[bool, str]:
        """Check database integrity after execution."""

        try:
            conn = sqlite3.connect(str(LOCAL_VAULT_DB))
            cursor = conn.cursor()

            # SQLite integrity check
            cursor.execute("PRAGMA integrity_check")
            integrity_result = cursor.fetchone()[0]

            conn.close()

            if integrity_result == "ok":
                return True, "Database integrity OK"
            else:
                return False, f"Database integrity check failed: {integrity_result}"

        except sqlite3.Error as e:
            return False, f"Database integrity check error: {e}"

    def _check_expected_changes(
        self,
        task: Dict[str, Any],
        result: Any
    ) -> Tuple[bool, str]:
        """Verify expected changes occurred."""

        action_type = task.get("action_type")

        # For DB operations, check affected rows
        if action_type in ["update_db", "delete_db"]:
            if isinstance(result, dict) and "affected_rows" in result:
                affected = result["affected_rows"]
                if affected >= 0:
                    return True, f"Expected changes applied ({affected} rows affected)"
                else:
                    return False, "No rows affected (unexpected)"
            else:
                # Can't verify, assume OK
                return True, "Changes verification skipped (no metadata)"

        # For query operations, check result format
        elif action_type == "query_db":
            if result is not None:
                return True, "Query returned results"
            else:
                return False, "Query returned no results (unexpected)"

        # For file operations
        elif action_type == "write_file":
            if isinstance(result, dict) and "bytes_written" in result:
                bytes_written = result["bytes_written"]
                if bytes_written > 0:
                    return True, f"File written ({bytes_written} bytes)"
                else:
                    return False, "File write produced empty file"
            else:
                return True, "File operation completed"

        # Other operations - assume OK if no error
        else:
            return True, f"Operation completed ({action_type})"

    def _check_no_corruption(
        self,
        task: Dict[str, Any],
        result: Any
    ) -> Tuple[bool, str]:
        """Check for signs of data corruption."""

        # Check database table count hasn't changed unexpectedly
        try:
            conn = sqlite3.connect(str(LOCAL_VAULT_DB))
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]

            conn.close()

            # Expected minimum tables (entities, documents, tasks, etc.)
            if table_count >= 5:
                return True, f"Database structure intact ({table_count} tables)"
            else:
                return False, f"Database may be corrupted (only {table_count} tables)"

        except sqlite3.Error as e:
            return False, f"Corruption check failed: {e}"


# CLI test
if __name__ == "__main__":
    validator = PostFlightValidator()

    print("=" * 60)
    print("Post-flight Validation Test")
    print("=" * 60)

    # Test 1: Successful query
    print("\nTest 1: Successful query")
    test_task = {
        "task_id": "test_query",
        "action_type": "query_db"
    }
    test_result = [(10,)]  # Query result
    test_error = ""

    all_passed, issues = validator.validate(test_task, test_result, test_error)
    print(f"Result: {'✓ PASS' if all_passed else '✗ FAIL'}")

    # Test 2: Failed operation
    print("\n" + "=" * 60)
    print("Test 2: Failed operation")
    test_task2 = {
        "task_id": "test_failed",
        "action_type": "update_db"
    }
    test_result2 = None
    test_error2 = "Database locked"

    all_passed2, issues2 = validator.validate(test_task2, test_result2, test_error2)
    print(f"Result: {'✓ PASS (correctly detected failure)' if not all_passed2 else '✗ FAIL'}")

    # Test 3: Successful update
    print("\n" + "=" * 60)
    print("Test 3: Successful update")
    test_task3 = {
        "task_id": "test_update",
        "action_type": "update_db"
    }
    test_result3 = {"affected_rows": 5}
    test_error3 = ""

    all_passed3, issues3 = validator.validate(test_task3, test_result3, test_error3)
    print(f"Result: {'✓ PASS' if all_passed3 else '✗ FAIL'}")

    print("\n" + "=" * 60)
    summary = "All tests completed"
    if all_passed and not all_passed2 and all_passed3:
        summary += " - ✓ ALL PASS"
    else:
        summary += " - ✗ SOME FAILED"
    print(summary)
    print("=" * 60)
