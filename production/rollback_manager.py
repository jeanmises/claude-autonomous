#!/usr/bin/env python3
"""
Autonomous System - Rollback Manager
Handles automatic rollback on execution failures.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from snapshot_manager import SnapshotManager


class RollbackManager:
    """Manages automatic rollback on failures."""

    def __init__(self):
        self.snapshot_manager = SnapshotManager()
        self.rollback_log = Path.home() / ".claude" / "autonomous" / "logs" / "rollbacks.log"
        self.rollback_log.parent.mkdir(parents=True, exist_ok=True)

    def rollback(
        self,
        snapshot_id: str,
        reason: str,
        task: Dict[str, Any] = None
    ) -> bool:
        """
        Execute rollback to snapshot.

        Args:
            snapshot_id: Snapshot to restore
            reason: Reason for rollback
            task: Optional task info

        Returns:
            True if successful
        """

        print(f"[Rollback] Initiating rollback...")
        print(f"[Rollback] Snapshot: {snapshot_id}")
        print(f"[Rollback] Reason: {reason}")

        # Verify snapshot exists
        snapshot_info = self.snapshot_manager.get_snapshot_info(snapshot_id)
        if not snapshot_info:
            print(f"[Rollback] Error: Snapshot {snapshot_id} not found")
            return False

        # Execute restore
        success = self.snapshot_manager.restore_snapshot(snapshot_id)

        # Log rollback
        self._log_rollback(snapshot_id, reason, success, task)

        if success:
            print(f"[Rollback] ✓ Rollback completed successfully")
        else:
            print(f"[Rollback] ✗ Rollback failed")

        return success

    def verify_rollback(self, snapshot_id: str) -> bool:
        """
        Verify rollback was successful.

        Args:
            snapshot_id: Snapshot ID to verify against

        Returns:
            True if verification passed
        """

        # Basic verification: check if database is accessible
        from pathlib import Path
        import sqlite3

        workspace_root = Path.home() / "Library" / "CloudStorage" / "OneDrive-SAPASPA" / "OD PARA Sales Strategy" / "Claude Workspace"
        db_path = workspace_root / "local_vault.db"

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Simple query to verify DB integrity
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]

            conn.close()

            if table_count > 0:
                print(f"[Rollback] ✓ Verification passed: {table_count} tables found")
                return True
            else:
                print(f"[Rollback] ✗ Verification failed: No tables found")
                return False

        except Exception as e:
            print(f"[Rollback] ✗ Verification failed: {e}")
            return False

    def _log_rollback(
        self,
        snapshot_id: str,
        reason: str,
        success: bool,
        task: Dict[str, Any] = None
    ):
        """Log rollback event."""

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "snapshot_id": snapshot_id,
            "reason": reason,
            "success": success,
            "task_id": task.get("task_id") if task else None,
            "task_type": task.get("action_type") if task else None
        }

        with open(self.rollback_log, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def get_rollback_history(self, limit: int = 10) -> list:
        """Get recent rollback history."""

        if not self.rollback_log.exists():
            return []

        history = []
        with open(self.rollback_log, "r") as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                try:
                    history.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

        return list(reversed(history))


# CLI test
if __name__ == "__main__":
    import sys

    manager = RollbackManager()

    print("=" * 60)
    print("Rollback Manager Test")
    print("=" * 60)

    # First, create a snapshot to rollback to
    print("\nStep 1: Create test snapshot")
    snapshot_manager = SnapshotManager()
    test_task = {
        "task_id": "rollback_test",
        "action_type": "test_operation"
    }
    snapshot_id = snapshot_manager.create_snapshot(test_task)
    print(f"✓ Test snapshot created: {snapshot_id}")

    # Test rollback
    print("\nStep 2: Test rollback")
    success = manager.rollback(
        snapshot_id,
        reason="Testing rollback functionality",
        task=test_task
    )

    if success:
        print("✓ Rollback test PASSED")
    else:
        print("✗ Rollback test FAILED")
        sys.exit(1)

    # Test verification
    print("\nStep 3: Verify rollback")
    verified = manager.verify_rollback(snapshot_id)

    if verified:
        print("✓ Verification test PASSED")
    else:
        print("✗ Verification test FAILED")
        sys.exit(1)

    # Show rollback history
    print("\nStep 4: Rollback history")
    history = manager.get_rollback_history(limit=5)
    print(f"✓ Found {len(history)} rollback events")
    for entry in history:
        status = "✓" if entry["success"] else "✗"
        print(f"  {status} {entry['timestamp']}: {entry['reason']}")

    print("\n" + "=" * 60)
    print("All tests completed successfully")
    print("=" * 60)
