#!/usr/bin/env python3
"""
Autonomous System - Snapshot Manager
Creates and manages backups for safe production execution.
"""

import shutil
import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional


# Paths
SNAPSHOT_ROOT = Path.home() / ".claude" / "autonomous" / "snapshots"
WORKSPACE_ROOT = Path.home() / "Library" / "CloudStorage" / "OneDrive-SAPASPA" / "OD PARA Sales Strategy" / "Claude Workspace"
LOCAL_VAULT_DB = WORKSPACE_ROOT / "local_vault.db"


class SnapshotManager:
    """Manages snapshots for rollback capability."""

    def __init__(self):
        SNAPSHOT_ROOT.mkdir(parents=True, exist_ok=True)

    def create_snapshot(
        self,
        task: Dict[str, Any],
        affected_files: List[Path] = None
    ) -> str:
        """
        Create snapshot before task execution.

        Args:
            task: Task being executed
            affected_files: Optional list of files that will be modified

        Returns:
            Snapshot ID
        """

        snapshot_id = str(uuid.uuid4())[:8]
        snapshot_path = SNAPSHOT_ROOT / snapshot_id
        snapshot_path.mkdir(parents=True, exist_ok=True)

        # Create metadata
        metadata = {
            "snapshot_id": snapshot_id,
            "task_id": task.get("task_id"),
            "task_type": task.get("action_type"),
            "created_at": datetime.now().isoformat(),
            "affected_files": [str(f) for f in (affected_files or [])]
        }

        # Always backup database
        try:
            db_backup = snapshot_path / "local_vault.db"
            shutil.copy2(LOCAL_VAULT_DB, db_backup)
            metadata["database_backup"] = str(db_backup)
        except Exception as e:
            print(f"[Snapshot] Warning: Could not backup database: {e}")
            metadata["database_backup"] = None

        # Backup affected files
        if affected_files:
            files_dir = snapshot_path / "files"
            files_dir.mkdir(exist_ok=True)

            for file_path in affected_files:
                if file_path.exists():
                    try:
                        # Preserve directory structure
                        relative = file_path.relative_to(WORKSPACE_ROOT)
                        backup_path = files_dir / relative
                        backup_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(file_path, backup_path)
                    except Exception as e:
                        print(f"[Snapshot] Warning: Could not backup {file_path}: {e}")

        # Save metadata
        with open(snapshot_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        print(f"[Snapshot] Created snapshot: {snapshot_id}")
        return snapshot_id

    def restore_snapshot(self, snapshot_id: str) -> bool:
        """
        Restore from snapshot.

        Args:
            snapshot_id: Snapshot to restore

        Returns:
            True if successful
        """

        snapshot_path = SNAPSHOT_ROOT / snapshot_id

        if not snapshot_path.exists():
            print(f"[Snapshot] Error: Snapshot {snapshot_id} not found")
            return False

        # Load metadata
        with open(snapshot_path / "metadata.json", "r") as f:
            metadata = json.load(f)

        print(f"[Snapshot] Restoring snapshot {snapshot_id}...")

        # Restore database
        db_backup = snapshot_path / "local_vault.db"
        if db_backup.exists():
            try:
                shutil.copy2(db_backup, LOCAL_VAULT_DB)
                print(f"[Snapshot]   ✓ Database restored")
            except Exception as e:
                print(f"[Snapshot]   ✗ Database restore failed: {e}")
                return False

        # Restore files
        files_dir = snapshot_path / "files"
        if files_dir.exists():
            for backup_file in files_dir.rglob("*"):
                if backup_file.is_file():
                    try:
                        relative = backup_file.relative_to(files_dir)
                        target = WORKSPACE_ROOT / relative
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(backup_file, target)
                        print(f"[Snapshot]   ✓ Restored: {relative}")
                    except Exception as e:
                        print(f"[Snapshot]   ✗ Failed to restore {relative}: {e}")

        print(f"[Snapshot] Snapshot {snapshot_id} restored")
        return True

    def list_snapshots(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent snapshots.

        Args:
            limit: Maximum number to return

        Returns:
            List of snapshot metadata
        """

        snapshots = []

        for snapshot_dir in sorted(SNAPSHOT_ROOT.iterdir(), reverse=True)[:limit]:
            if snapshot_dir.is_dir():
                metadata_file = snapshot_dir / "metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, "r") as f:
                        snapshots.append(json.load(f))

        return snapshots

    def cleanup_old_snapshots(self, days: int = 30) -> int:
        """
        Remove snapshots older than specified days.

        Args:
            days: Age threshold

        Returns:
            Number of snapshots removed
        """

        cutoff = datetime.now() - timedelta(days=days)
        removed = 0

        for snapshot_dir in SNAPSHOT_ROOT.iterdir():
            if snapshot_dir.is_dir():
                metadata_file = snapshot_dir / "metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, "r") as f:
                        metadata = json.load(f)

                    created = datetime.fromisoformat(metadata["created_at"])
                    if created < cutoff:
                        shutil.rmtree(snapshot_dir)
                        removed += 1
                        print(f"[Snapshot] Removed old snapshot: {snapshot_dir.name}")

        return removed

    def get_snapshot_info(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """Get snapshot metadata."""

        snapshot_path = SNAPSHOT_ROOT / snapshot_id
        metadata_file = snapshot_path / "metadata.json"

        if metadata_file.exists():
            with open(metadata_file, "r") as f:
                return json.load(f)

        return None


# CLI test
if __name__ == "__main__":
    manager = SnapshotManager()

    print("=" * 60)
    print("Snapshot Manager Test")
    print("=" * 60)

    # Test 1: Create snapshot
    print("\nTest 1: Create snapshot")
    test_task = {
        "task_id": "test_snapshot",
        "action_type": "update_db"
    }

    snapshot_id = manager.create_snapshot(test_task)
    print(f"✓ Snapshot created: {snapshot_id}")

    # Test 2: List snapshots
    print("\nTest 2: List snapshots")
    snapshots = manager.list_snapshots(limit=5)
    print(f"✓ Found {len(snapshots)} snapshots")
    for snap in snapshots:
        print(f"  - {snap['snapshot_id']}: {snap['task_type']} ({snap['created_at']})")

    # Test 3: Get snapshot info
    print("\nTest 3: Get snapshot info")
    info = manager.get_snapshot_info(snapshot_id)
    if info:
        print(f"✓ Snapshot info retrieved")
        print(f"  Task: {info['task_type']}")
        print(f"  Created: {info['created_at']}")

    # Test 4: Cleanup (but keep recent)
    print("\nTest 4: Cleanup old snapshots")
    removed = manager.cleanup_old_snapshots(days=30)
    print(f"✓ Removed {removed} old snapshots")

    print("\n" + "=" * 60)
    print("All tests completed")
    print("=" * 60)
    print(f"\nSnapshot directory: {SNAPSHOT_ROOT}")
    print(f"Test snapshot ID: {snapshot_id}")
    print("\nNote: Test snapshot NOT removed (for manual inspection)")
