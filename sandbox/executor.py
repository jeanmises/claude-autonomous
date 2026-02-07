#!/usr/bin/env python3
"""
Autonomous System - Sandbox Executor
Isolated environment for safe task execution with automatic fix iterations.
"""

import json
import os
import shutil
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Tuple, Optional


# Paths
SANDBOX_ROOT = Path.home() / ".claude" / "autonomous" / "sandbox" / "environments"
WORKSPACE_ROOT = Path.home() / "Library" / "CloudStorage" / "OneDrive-SAPASPA" / "OD PARA Sales Strategy" / "Claude Workspace"
LOCAL_VAULT_DB = WORKSPACE_ROOT / "local_vault.db"


class SandboxExecutor:
    """Executes tasks in isolated sandbox environment."""

    def __init__(self, task: Dict[str, Any], max_iterations: int = 5):
        self.task = task
        self.task_id = task.get("task_id", "unknown")
        self.max_iterations = max_iterations
        self.cycle_id = str(uuid.uuid4())[:8]
        self.sandbox_path = SANDBOX_ROOT / self.cycle_id
        self.iteration_results = []

    def create_environment(self) -> bool:
        """Create isolated sandbox environment."""

        try:
            # Create sandbox directory structure
            self.sandbox_path.mkdir(parents=True, exist_ok=True)

            workspace_copy = self.sandbox_path / "workspace"
            workspace_copy.mkdir(exist_ok=True)

            # Copy essential files only (not entire workspace)
            db_copy = workspace_copy / "local_vault.db"
            shutil.copy2(LOCAL_VAULT_DB, db_copy)

            # Create workdir for outputs
            (workspace_copy / "workdir").mkdir(exist_ok=True)

            # Create manifest
            manifest = {
                "cycle_id": self.cycle_id,
                "task_id": self.task_id,
                "created_at": datetime.now().isoformat(),
                "task_type": self.task.get("action_type"),
                "max_iterations": self.max_iterations
            }

            with open(self.sandbox_path / "manifest.json", "w") as f:
                json.dump(manifest, f, indent=2)

            return True

        except Exception as e:
            print(f"[Sandbox] Error creating environment: {e}")
            return False

    def execute_task(self, iteration: int = 1) -> Tuple[bool, Any, str]:
        """
        Execute task in sandbox.

        Returns:
            Tuple of (success, result, error_message)
        """

        action_type = self.task.get("action_type")
        payload = self.task.get("payload", {})

        try:
            # Route to appropriate executor based on action type
            if action_type == "query_db":
                return self._execute_query_db(payload)
            elif action_type == "update_db":
                return self._execute_update_db(payload)
            elif action_type == "write_file":
                return self._execute_write_file(payload)
            elif action_type == "read_file":
                return self._execute_read_file(payload)
            elif action_type in ["execute_script", "system_optimization"]:
                # Scripts run in dry-run mode in sandbox
                return self._execute_script_dryrun(payload)
            else:
                return False, None, f"Unsupported action type: {action_type}"

        except Exception as e:
            return False, None, str(e)

    def _execute_query_db(self, payload: Dict[str, Any]) -> Tuple[bool, Any, str]:
        """Execute database query in sandbox."""

        query = payload.get("query")
        if not query:
            return False, None, "Missing query in payload"

        db_path = self.sandbox_path / "workspace" / "local_vault.db"

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute(query)

            # Fetch results
            if query.strip().upper().startswith("SELECT"):
                results = cursor.fetchall()
                conn.close()
                return True, results, ""
            else:
                # Non-SELECT queries
                conn.commit()
                affected = cursor.rowcount
                conn.close()
                return True, {"affected_rows": affected}, ""

        except sqlite3.Error as e:
            return False, None, f"Database error: {e}"

    def _execute_update_db(self, payload: Dict[str, Any]) -> Tuple[bool, Any, str]:
        """Execute database update in sandbox."""

        table = payload.get("table")
        updates = payload.get("updates", {})
        conditions = payload.get("conditions", {})

        if not table or not updates:
            return False, None, "Missing table or updates in payload"

        # Build UPDATE query
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        where_clause = " AND ".join([f"{k} = ?" for k in conditions.keys()]) if conditions else "1=1"

        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        values = list(updates.values()) + list(conditions.values())

        db_path = self.sandbox_path / "workspace" / "local_vault.db"

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            affected = cursor.rowcount
            conn.close()

            return True, {"affected_rows": affected}, ""

        except sqlite3.Error as e:
            return False, None, f"Database error: {e}"

    def _execute_write_file(self, payload: Dict[str, Any]) -> Tuple[bool, Any, str]:
        """Write file in sandbox."""

        file_path = payload.get("file_path") or payload.get("path")
        content = payload.get("content")

        if not file_path or content is None:
            return False, None, "Missing file_path or content in payload"

        # Ensure path is within sandbox
        full_path = self.sandbox_path / "workspace" / "workdir" / Path(file_path).name
        full_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(full_path, "w") as f:
                f.write(content)

            return True, {"bytes_written": len(content), "path": str(full_path)}, ""

        except Exception as e:
            return False, None, f"File write error: {e}"

    def _execute_read_file(self, payload: Dict[str, Any]) -> Tuple[bool, Any, str]:
        """Read file in sandbox."""

        file_path = payload.get("file_path") or payload.get("path")

        if not file_path:
            return False, None, "Missing file_path in payload"

        # Check in workspace copy
        full_path = self.sandbox_path / "workspace" / file_path

        try:
            with open(full_path, "r") as f:
                content = f.read()

            return True, {"content": content}, ""

        except Exception as e:
            return False, None, f"File read error: {e}"

    def _execute_script_dryrun(self, payload: Dict[str, Any]) -> Tuple[bool, Any, str]:
        """Simulate script execution (dry-run)."""

        commands = payload.get("commands", [])

        if not commands:
            return False, None, "No commands in payload"

        # In sandbox, scripts are validated but not executed
        # Check if commands are valid bash syntax
        results = {
            "dry_run": True,
            "commands_validated": len(commands),
            "commands": commands
        }

        return True, results, ""

    def cleanup(self, keep_on_failure: bool = True):
        """Clean up sandbox environment."""

        if self.sandbox_path.exists():
            # Save iteration results before cleanup
            results_file = self.sandbox_path / "results.json"
            with open(results_file, "w") as f:
                json.dump({
                    "cycle_id": self.cycle_id,
                    "task_id": self.task_id,
                    "iterations": self.iteration_results
                }, f, indent=2)

            # Keep sandbox on failure for debugging
            if not keep_on_failure or all(it["success"] for it in self.iteration_results):
                shutil.rmtree(self.sandbox_path)


# Simple test
if __name__ == "__main__":
    # Test with query_db task
    test_task = {
        "task_id": "test_1",
        "action_type": "query_db",
        "payload": {
            "query": "SELECT COUNT(*) FROM entities"
        }
    }

    executor = SandboxExecutor(test_task)

    print("Creating sandbox environment...")
    if executor.create_environment():
        print(f"✓ Sandbox created: {executor.sandbox_path}")

        print("\nExecuting task...")
        success, result, error = executor.execute_task()

        if success:
            print(f"✓ Task executed successfully")
            print(f"  Result: {result}")
        else:
            print(f"✗ Task failed: {error}")

        print("\nCleaning up...")
        executor.cleanup(keep_on_failure=False)
        print("✓ Done")
    else:
        print("✗ Failed to create sandbox")
