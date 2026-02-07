#!/usr/bin/env python3
"""
Autonomous System - Production Executor
Safe production execution with automatic rollback on failure.
"""

import time
import sys
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "sandbox"))

import sqlite3
from snapshot_manager import SnapshotManager
from rollback_manager import RollbackManager
from validation.pre_flight import PreFlightValidator
from validation.post_flight import PostFlightValidator

# Workspace path
WORKSPACE_ROOT = Path.home() / "Library" / "CloudStorage" / "OneDrive-SAPASPA" / "OD PARA Sales Strategy" / "Claude Workspace"
LOCAL_VAULT_DB = WORKSPACE_ROOT / "local_vault.db"


class ProductionExecutor:
    """
    Executes tasks in production with full safety measures.

    Flow:
    1. Pre-flight validation
    2. Create snapshot
    3. Execute task
    4. Post-flight validation
    5. Rollback if validation fails
    """

    def __init__(self):
        self.snapshot_manager = SnapshotManager()
        self.rollback_manager = RollbackManager()
        self.pre_flight_validator = PreFlightValidator()
        self.post_flight_validator = PostFlightValidator()

    def execute(self, task: Dict[str, Any]) -> Tuple[bool, Any, str, Optional[str]]:
        """
        Execute task with full safety protocol.

        Args:
            task: Task to execute

        Returns:
            Tuple of (success, result, error, snapshot_id)
        """

        task_id = task.get("task_id", "unknown")
        print(f"\n{'='*60}")
        print(f"Production Execution: {task_id}")
        print(f"{'='*60}")

        snapshot_id = None

        # Step 1: Pre-flight validation
        print("\n[1/5] Pre-flight Validation")
        pre_flight_passed, pre_flight_issues = self.pre_flight_validator.validate(task)

        if not pre_flight_passed:
            error = f"Pre-flight validation failed: {'; '.join(pre_flight_issues)}"
            print(f"\n✗ Execution aborted: {error}")
            return False, None, error, None

        # Step 2: Create snapshot
        print("\n[2/5] Creating Snapshot")
        try:
            snapshot_id = self.snapshot_manager.create_snapshot(task)
            print(f"✓ Snapshot created: {snapshot_id}")
        except Exception as e:
            error = f"Snapshot creation failed: {e}"
            print(f"\n✗ Execution aborted: {error}")
            return False, None, error, None

        # Step 3: Execute task
        print("\n[3/5] Executing Task")
        try:
            start_time = time.time()
            success, result, error = self._execute_task_direct(task)
            execution_time = time.time() - start_time

            if success:
                print(f"✓ Task executed successfully ({execution_time:.2f}s)")
            else:
                print(f"✗ Task execution failed: {error}")

        except Exception as e:
            success = False
            result = None
            error = f"Execution exception: {e}"
            print(f"✗ Task execution failed: {error}")

        # Step 4: Post-flight validation
        print("\n[4/5] Post-flight Validation")
        post_flight_passed, post_flight_issues = self.post_flight_validator.validate(
            task, result, error
        )

        if not post_flight_passed:
            print(f"✗ Post-flight validation failed")

        # Step 5: Rollback if needed
        if not success or not post_flight_passed:
            print("\n[5/5] Rollback")
            rollback_reason = error if error else f"Post-flight validation failed: {'; '.join(post_flight_issues)}"

            rollback_success = self.rollback_manager.rollback(
                snapshot_id,
                reason=rollback_reason,
                task=task
            )

            if rollback_success:
                verified = self.rollback_manager.verify_rollback(snapshot_id)
                if verified:
                    print("✓ Rollback completed and verified")
                else:
                    print("⚠ Rollback completed but verification failed")

            final_error = f"Execution failed and rolled back: {rollback_reason}"
            print(f"\n{'='*60}")
            print(f"✗ Production execution FAILED (rolled back)")
            print(f"{'='*60}")

            return False, None, final_error, snapshot_id

        else:
            print("\n[5/5] Rollback")
            print("✓ Rollback not needed - execution successful")

            print(f"\n{'='*60}")
            print(f"✓ Production execution SUCCESSFUL")
            print(f"{'='*60}")

            return True, result, "", snapshot_id

    def _execute_task_direct(self, task: Dict[str, Any]) -> Tuple[bool, Any, str]:
        """
        Execute task directly on production workspace.

        Args:
            task: Task to execute

        Returns:
            Tuple of (success, result, error)
        """

        action_type = task.get("action_type")
        payload = task.get("payload", {})

        try:
            if action_type == "query_db":
                return self._execute_query_db(payload)
            elif action_type == "update_db":
                return self._execute_update_db(payload)
            elif action_type == "write_file":
                return self._execute_write_file(payload)
            elif action_type == "read_file":
                return self._execute_read_file(payload)
            else:
                return False, None, f"Unsupported action type: {action_type}"

        except Exception as e:
            return False, None, str(e)

    def _execute_query_db(self, payload: Dict[str, Any]) -> Tuple[bool, Any, str]:
        """Execute database query."""

        query = payload.get("query")
        if not query:
            return False, None, "Missing query in payload"

        try:
            conn = sqlite3.connect(str(LOCAL_VAULT_DB))
            cursor = conn.cursor()
            cursor.execute(query)

            if query.strip().upper().startswith("SELECT"):
                results = cursor.fetchall()
                conn.close()
                return True, results, ""
            else:
                conn.commit()
                affected = cursor.rowcount
                conn.close()
                return True, {"affected_rows": affected}, ""

        except sqlite3.Error as e:
            return False, None, f"Database error: {e}"

    def _execute_update_db(self, payload: Dict[str, Any]) -> Tuple[bool, Any, str]:
        """Execute database update."""

        table = payload.get("table")
        updates = payload.get("updates", {})
        conditions = payload.get("conditions", {})

        if not table or not updates:
            return False, None, "Missing table or updates in payload"

        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        where_clause = " AND ".join([f"{k} = ?" for k in conditions.keys()]) if conditions else "1=1"

        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        values = list(updates.values()) + list(conditions.values())

        try:
            conn = sqlite3.connect(str(LOCAL_VAULT_DB))
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            affected = cursor.rowcount
            conn.close()

            return True, {"affected_rows": affected}, ""

        except sqlite3.Error as e:
            return False, None, f"Database error: {e}"

    def _execute_write_file(self, payload: Dict[str, Any]) -> Tuple[bool, Any, str]:
        """Write file in workspace."""

        file_path = payload.get("file_path") or payload.get("path")
        content = payload.get("content")

        if not file_path or content is None:
            return False, None, "Missing file_path or content in payload"

        full_path = WORKSPACE_ROOT / "workdir" / Path(file_path).name
        full_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(full_path, "w") as f:
                f.write(content)

            return True, {"bytes_written": len(content), "path": str(full_path)}, ""

        except Exception as e:
            return False, None, f"File write error: {e}"

    def _execute_read_file(self, payload: Dict[str, Any]) -> Tuple[bool, Any, str]:
        """Read file from workspace."""

        file_path = payload.get("file_path") or payload.get("path")

        if not file_path:
            return False, None, "Missing file_path in payload"

        full_path = WORKSPACE_ROOT / file_path

        try:
            with open(full_path, "r") as f:
                content = f.read()

            return True, {"content": content}, ""

        except Exception as e:
            return False, None, f"File read error: {e}"


# CLI test
if __name__ == "__main__":
    executor = ProductionExecutor()

    print("="*60)
    print("Production Executor Test Suite")
    print("="*60)

    # Test 1: Successful execution
    print("\n\nTEST 1: Successful Query Execution")
    print("-"*60)

    test_task_1 = {
        "task_id": "prod_test_1",
        "action_type": "query_db",
        "payload": {
            "query": "SELECT COUNT(*) FROM entities",
            "expected_result": "integer"
        }
    }

    success1, result1, error1, snapshot1 = executor.execute(test_task_1)

    if success1:
        print(f"\n✓ Test 1 PASSED")
    else:
        print(f"\n✗ Test 1 FAILED: {error1}")

    # Test 2: Failed execution with rollback
    print("\n\n" + "="*60)
    print("TEST 2: Failed Execution (Invalid Query)")
    print("-"*60)

    test_task_2 = {
        "task_id": "prod_test_2",
        "action_type": "query_db",
        "payload": {
            "query": "SELECT * FROM nonexistent_table_xyz"
        }
    }

    success2, result2, error2, snapshot2 = executor.execute(test_task_2)

    if not success2 and "rolled back" in error2:
        print(f"\n✓ Test 2 PASSED (correctly failed and rolled back)")
    else:
        print(f"\n✗ Test 2 FAILED (should have rolled back)")

    # Summary
    print("\n\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Test 1 (Success): {'✓ PASS' if success1 else '✗ FAIL'}")
    print(f"Test 2 (Rollback): {'✓ PASS' if not success2 else '✗ FAIL'}")

    overall = success1 and not success2
    print(f"\nOverall: {'✓ ALL TESTS PASSED' if overall else '✗ SOME TESTS FAILED'}")
    print("="*60)

    sys.exit(0 if overall else 1)
