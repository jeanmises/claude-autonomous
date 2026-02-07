#!/usr/bin/env python3
"""
Autonomous System - Pre-flight Validation
Checks system readiness before production execution.
"""

import sqlite3
import shutil
from pathlib import Path
from typing import Dict, Any, Tuple, List


# Paths
WORKSPACE_ROOT = Path.home() / "Library" / "CloudStorage" / "OneDrive-SAPASPA" / "OD PARA Sales Strategy" / "Claude Workspace"
LOCAL_VAULT_DB = WORKSPACE_ROOT / "local_vault.db"


class PreFlightValidator:
    """Validates system state before production execution."""

    def __init__(self):
        self.checks = [
            self._check_workspace_accessible,
            self._check_database_accessible,
            self._check_database_not_locked,
            self._check_onedrive_sync_healthy,
            self._check_disk_space,
        ]

    def validate(self, task: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Run all pre-flight checks.

        Args:
            task: Task to be executed

        Returns:
            Tuple of (all_passed, issues)
        """

        print("[Pre-flight] Running validation checks...")
        issues = []

        for check in self.checks:
            try:
                passed, message = check(task)
                if passed:
                    print(f"[Pre-flight]   ✓ {message}")
                else:
                    print(f"[Pre-flight]   ✗ {message}")
                    issues.append(message)
            except Exception as e:
                error_msg = f"{check.__name__}: {e}"
                print(f"[Pre-flight]   ✗ {error_msg}")
                issues.append(error_msg)

        all_passed = len(issues) == 0

        if all_passed:
            print("[Pre-flight] ✓ All checks passed")
        else:
            print(f"[Pre-flight] ✗ {len(issues)} check(s) failed")

        return all_passed, issues

    def _check_workspace_accessible(self, task: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if workspace directory is accessible."""

        if WORKSPACE_ROOT.exists() and WORKSPACE_ROOT.is_dir():
            return True, "Workspace accessible"
        else:
            return False, f"Workspace not accessible: {WORKSPACE_ROOT}"

    def _check_database_accessible(self, task: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if database is accessible."""

        if LOCAL_VAULT_DB.exists():
            try:
                conn = sqlite3.connect(str(LOCAL_VAULT_DB))
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                count = cursor.fetchone()[0]
                conn.close()

                if count > 0:
                    return True, f"Database accessible ({count} tables)"
                else:
                    return False, "Database has no tables"

            except sqlite3.Error as e:
                return False, f"Database error: {e}"
        else:
            return False, "Database file not found"

    def _check_database_not_locked(self, task: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if database is locked."""

        try:
            conn = sqlite3.connect(str(LOCAL_VAULT_DB), timeout=1.0)
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")
            conn.rollback()
            conn.close()
            return True, "Database not locked"
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower():
                return False, "Database is locked"
            else:
                return False, f"Database check failed: {e}"

    def _check_onedrive_sync_healthy(self, task: Dict[str, Any]) -> Tuple[bool, str]:
        """Check OneDrive sync status (basic check)."""

        # Basic check: see if .cloud files exist (indicates sync issues)
        cloud_files = list(WORKSPACE_ROOT.rglob("*.cloud"))

        if len(cloud_files) == 0:
            return True, "OneDrive sync healthy (no .cloud files)"
        else:
            return False, f"OneDrive sync issues detected ({len(cloud_files)} .cloud files)"

    def _check_disk_space(self, task: Dict[str, Any]) -> Tuple[bool, str]:
        """Check available disk space."""

        stat = shutil.disk_usage(WORKSPACE_ROOT)
        free_gb = stat.free / (1024 ** 3)

        # Require at least 1 GB free
        if free_gb >= 1.0:
            return True, f"Disk space sufficient ({free_gb:.1f} GB free)"
        else:
            return False, f"Low disk space ({free_gb:.1f} GB free)"


# CLI test
if __name__ == "__main__":
    validator = PreFlightValidator()

    print("=" * 60)
    print("Pre-flight Validation Test")
    print("=" * 60)

    test_task = {
        "task_id": "test_validation",
        "action_type": "query_db"
    }

    all_passed, issues = validator.validate(test_task)

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ Pre-flight validation PASSED")
    else:
        print("✗ Pre-flight validation FAILED")
        print("\nIssues:")
        for issue in issues:
            print(f"  - {issue}")
    print("=" * 60)
